from datetime import datetime, timedelta

from django import http
from django.shortcuts import get_object_or_404, redirect

import commonware.log
from commonware.response.decorators import xframe_allow
import jingo
from session_csrf import anonymous_csrf_exempt
from tower import ugettext as _
import waffle

from abuse.models import send_abuse_report
from access import acl
import amo
from amo.decorators import (login_required, permission_required, post_required,
                            write)
from amo.forms import AbuseForm
from amo.helpers import absolutify
from amo.urlresolvers import reverse
from amo.utils import paginate
from devhub.views import _get_items
from lib.pay_server import client
from market.models import PreApprovalUser
import paypal
from users.models import UserProfile
from users.tasks import delete_photo as delete_photo_task
from users.views import logout
from mkt.account.forms import CurrencyForm
from mkt.site import messages
from . import forms
from .utils import purchase_list

log = commonware.log.getLogger('mkt.account')
paypal_log = commonware.log.getLogger('mkt.paypal')


@write
@login_required
@xframe_allow
def payment(request, status=None):
    # Note this is not post required, because PayPal does not reply with a
    # POST but a GET, that's a sad face.
    pre, created = (PreApprovalUser.objects
                                   .safer_get_or_create(user=request.amo_user))

    context = {'preapproval': pre,
               'currency': CurrencyForm(initial={'currency':
                                                 pre.currency or 'USD'})}

    if status:
        data = request.session.get('setup-preapproval', {})

        context['status'] = status

        if status == 'complete':
            # The user has completed the setup at PayPal and bounced back.
            if 'setup-preapproval' in request.session:
                if waffle.flag_is_active(request, 'solitude-payments'):
                    client.put_preapproval(data={'uuid': request.amo_user},
                                           pk=data['solitude-key'])

                paypal_log.info(u'Preapproval key created: %s' %
                                request.amo_user.pk)
                amo.log(amo.LOG.PREAPPROVAL_ADDED)
                # TODO(solitude): once this is turned off, we will want to
                # keep preapproval table populated with something, perhaps
                # a boolean inplace of pre-approval key.
                pre.update(paypal_key=data.get('key'),
                           paypal_expiry=data.get('expiry'))

                # If there is a target, bounce to it and don't show a message
                # we'll let whatever set this up worry about that.
                if data.get('complete'):
                    return redirect(data['complete'])

                messages.success(request,
                    _("You're all set for instant app purchases with PayPal."))
                del request.session['setup-preapproval']

        elif status == 'cancel':
            # The user has chosen to cancel out of PayPal. Nothing really
            # to do here, PayPal just bounce to the cancel page if defined.
            if data.get('cancel'):
                return redirect(data['cancel'])

            messages.success(request,
                _('Your payment pre-approval has been cancelled.'))

        elif status == 'remove':
            # The user has an pre approval key set and chooses to remove it
            if waffle.flag_is_active(request, 'solitude-payments'):
                other = client.lookup_buyer_paypal(request.amo_user)
                if other:
                    client.patch_buyer_paypal(pk=other['resource_pk'],
                                              data={'key': ''})

            if pre.paypal_key:
                # TODO(solitude): again, we'll want to maintain some local
                # state in zamboni, so this will probably change to a
                # boolean in the future.
                pre.update(paypal_key='')

                amo.log(amo.LOG.PREAPPROVAL_REMOVED)
                messages.success(request,
                    _('Your payment pre-approval has been disabled.'))
                paypal_log.info(u'Preapproval key removed for user: %s'
                                % request.amo_user)

    return jingo.render(request, 'account/payment.html', context)


@write
@post_required
@login_required
def currency(request, do_redirect=True):
    pre, created = (PreApprovalUser.objects
                        .safer_get_or_create(user=request.amo_user))
    currency = CurrencyForm(request.POST or {},
                            initial={'currency': pre.currency or 'USD'})
    if currency.is_valid():
        pre.update(currency=currency.cleaned_data['currency'])
        if do_redirect:
            messages.success(request, _('Currency saved.'))
            amo.log(amo.LOG.CURRENCY_UPDATED)
            return redirect(reverse('account.payment'))
    else:
        return jingo.render(request, 'account/payment.html',
                            {'preapproval': pre,
                             'currency': currency})


@write
@login_required
def preapproval(request, complete=None, cancel=None):
    if waffle.switch_is_active('currencies'):
        failure = currency(request, do_redirect=False)
        if failure:
            return failure

    today = datetime.today()
    data = {
        'startDate': today,
        'endDate': today + timedelta(days=365),
    }
    store = {
        'expiry': data['endDate'],
        'solitude-key': None,
        'complete': complete,
        'cancel': cancel,
    }

    if waffle.flag_is_active(request, 'solitude-payments'):
        client.create_buyer_if_missing(request.amo_user)
        try:
            result = client.post_preapproval(data={
                'start': data['startDate'].date(),
                'end': data['endDate'].date(),
                'uuid': request.amo_user,
                'return_url': absolutify(reverse('account.payment',
                                                 args=['complete'])),
                'cancel_url': absolutify(reverse('account.payment',
                                                  args=['cancel'])),
            })
        except client.Error:
            paypal_log.error(u'preapproval', exc_info=True)
            raise

        store.update({'key': result['key'], 'solitude-key': result['pk']})
        url = result['paypal_url']

    else:
        # TODO(solitude): remove this.
        data.update({'pattern': 'account.payment'})
        try:
            result = paypal.get_preapproval_key(data)
        except paypal.PaypalError, e:
            paypal_log.error(u'Preapproval key: %s' % e, exc_info=True)
            raise

        store.update({'key': result['preapprovalKey']})
        url = paypal.get_preapproval_url(result['preapprovalKey'])

    paypal_log.info(u'Got preapproval key for user: %s' % request.amo_user.pk)
    request.session['setup-preapproval'] = store
    return redirect(url)


def purchases(request, product_id=None, template=None):
    """A list of purchases that a user has made through the Marketplace."""
    products, contributions, listing = purchase_list(request,
                                                     request.amo_user,
                                                     product_id)
    return jingo.render(request, 'account/purchases.html',
                        {'pager': products,
                         'listing_filter': listing,
                         'contributions': contributions,
                         'single': bool(product_id),
                         'show_link': True})


@write
def account_settings(request):
    # Don't use `request.amo_user` because it's too cached.
    amo_user = request.amo_user.user.get_profile()
    form = forms.UserEditForm(request.POST or None, instance=amo_user)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, _('Profile Updated'))
            amo.log(amo.LOG.USER_EDITED)
            return redirect('account.settings')
        else:
            messages.form_errors(request)
    return jingo.render(request, 'account/settings.html',
                        {'form': form, 'amouser': amo_user})


def account_about(request):
    return jingo.render(request, 'account/about.html')


@write
@login_required
@permission_required('Users', 'Edit')
def admin_edit(request, user_id):
    amouser = get_object_or_404(UserProfile, pk=user_id)
    form = forms.AdminUserEditForm(request.POST or None, request.FILES or None,
                                   instance=amouser)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _('Profile Updated'))
        return redirect('zadmin.index')
    return jingo.render(request, 'account/settings.html',
                        {'form': form, 'amouser': amouser})


def delete(request):
    amouser = request.amo_user
    form = forms.UserDeleteForm(request.POST or None, request=request)
    if request.method == 'POST' and form.is_valid():
        messages.success(request, _('Profile Deleted'))
        amouser.anonymize()
        logout(request)
        form = None
        return redirect('users.login')
    return jingo.render(request, 'account/delete.html',
                        {'form': form, 'amouser': amouser})


@post_required
def delete_photo(request):
    request.amo_user.update(picture_type='')
    delete_photo_task.delay(request.amo_user.picture_path)
    log.debug(u'User (%s) deleted photo' % request.amo_user)
    messages.success(request, _('Photo Deleted'))
    amo.log(amo.LOG.USER_EDITED)
    return http.HttpResponse()


def profile(request, username):
    if username.isdigit():
        user = get_object_or_404(UserProfile, id=username)
    else:
        user = get_object_or_404(UserProfile, username=username)

    edit_any_user = acl.action_allowed(request, 'Users', 'Edit')
    own_profile = (request.user.is_authenticated() and
                   request.amo_user.id == user.id)

    submissions = []
    if user.is_developer:
        submissions = paginate(request,
                               user.apps_listed.order_by('-weekly_downloads'),
                               per_page=5)

    reviews = user.reviews.filter(addon__type=amo.ADDON_WEBAPP)
    reviews = paginate(request, reviews, per_page=5)

    data = {'profile': user, 'edit_any_user': edit_any_user,
            'submissions': submissions, 'own_profile': own_profile,
            'reviews': reviews}

    return jingo.render(request, 'account/profile.html', data)


@login_required
def activity_log(request, userid):
    all_apps = request.amo_user.addons.filter(type=amo.ADDON_WEBAPP)
    return jingo.render(request, 'account/activity.html',
                        {'log': _get_items(None, all_apps)})


@anonymous_csrf_exempt
def abuse(request, user_id):
    user = get_object_or_404(UserProfile, pk=user_id)
    form = AbuseForm(request.POST or None, request=request)
    if request.method == 'POST' and form.is_valid():
        send_abuse_report(request, user, form.cleaned_data['text'])
        messages.success(request, _('Abuse reported.'))
        # We don't have a profile page to redirect back to. Once the abuse
        # is reported, that would be the place I'd recommend redirecting
        # back to.
        return redirect('/')
    else:
        return jingo.render(request, 'account/abuse.html',
                            {'user': user, 'abuse_form': form})

