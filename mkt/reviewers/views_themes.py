import datetime
import json

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.forms.formsets import formset_factory
from django.shortcuts import get_object_or_404, redirect
from django.utils.datastructures import MultiValueDictKeyError

from elasticutils.contrib.django import S
import jingo
from waffle.decorators import waffle_switch

import amo
from access import acl
from addons.models import Addon, Persona
from amo.decorators import json_view, post_required
from amo.urlresolvers import reverse
from amo.utils import paginate
from devhub.models import ActivityLog
from editors.models import RereviewQueueTheme
from editors.views import reviewer_required
from search.views import name_only_query
from zadmin.decorators import admin_required

import mkt.constants.reviewers as rvw

from . import forms
from .models import ThemeLock
from .views import context, _get_search_form, queue_counts, QUEUE_PER_PAGE


@waffle_switch('mkt-themes')
@reviewer_required('persona')
def pending_themes(request):
    pending_themes = Addon.objects.filter(status=amo.STATUS_PENDING,
                                          type=amo.ADDON_PERSONA)

    search_form = _get_search_form(request)
    per_page = request.GET.get('per_page', QUEUE_PER_PAGE)
    pager = paginate(request, pending_themes, per_page)

    return jingo.render(request, 'reviewers/themes/list.html', context(**{
        'addons': pager.object_list,
        'pager': pager,
        'tab': 'themes',
        'STATUS_CHOICES': amo.STATUS_CHOICES,
        'search_form': search_form,
    }))


@json_view
@waffle_switch('mkt-themes')
@admin_required(reviewers=True)
def themes_search(request):
    search_form = forms.ThemeSearchForm(request.GET)
    if search_form.is_valid():
        # ES query on name.
        themes = (S(Addon).filter(type=amo.ADDON_PERSONA,
                                  status=amo.STATUS_PENDING)
            .query(or_=name_only_query(search_form.cleaned_data['q'].lower()))
            [:100])

        now = datetime.datetime.now()
        reviewers = []
        for theme in themes:
            try:
                themelock = theme.persona.themelock
                if themelock.expiry > now:
                    reviewers.append(themelock.reviewer.email)
                else:
                    reviewers.append('')
            except ObjectDoesNotExist:
                reviewers.append('')

        themes = list(themes.values_dict('name', 'slug', 'status'))
        for theme, reviewer in zip(themes, reviewers):
            # Dehydrate.
            theme['reviewer'] = reviewer
        return {'objects': themes, 'meta': {'total_count': len(themes)}}


@waffle_switch('mkt-themes')
@reviewer_required('persona')
def themes_queue(request):
    # By default, redirect back to the queue after a commit.
    request.session['theme_redirect_url'] = reverse(
        'reviewers.themes.queue_themes')

    return _themes_queue(request)


@waffle_switch('mkt-themes')
@admin_required(reviewers=True)
def themes_queue_flagged(request):
    # By default, redirect back to the queue after a commit.
    request.session['theme_redirect_url'] = reverse(
        'reviewers.themes.queue_flagged')

    return _themes_queue(request, flagged=True)


@waffle_switch('mkt-themes')
@admin_required(reviewers=True)
def themes_queue_rereview(request):
    # By default, redirect back to the queue after a commit.
    request.session['theme_redirect_url'] = reverse(
        'reviewers.themes.queue_rereview')

    return _themes_queue(request, rereview=True)


def _themes_queue(request, flagged=False, rereview=False):
    themes = _get_themes(request, request.amo_user, flagged=flagged,
                         rereview=rereview)

    ThemeReviewFormset = formset_factory(forms.ThemeReviewForm)
    formset = ThemeReviewFormset(
        initial=[{'theme': theme.id} for theme in themes])

    return jingo.render(request, 'reviewers/themes/queue.html', context(**{
        'actions': get_actions_json(),
        'formset': formset,
        'flagged': flagged,
        'queue_counts': queue_counts(),
        'reject_reasons': rvw.THEME_REJECT_REASONS.items(),
        'rereview': rereview,
        'reviewable': True,
        'theme_formsets': zip(themes, formset),
        'theme_count': len(themes),
        'tab': 'flagged' if flagged else 'pending'
    }))


def _get_themes(request, reviewer, flagged=False, rereview=False):
    """Check out themes.

    :param flagged: Flagged themes (amo.STATUS_REVIEW_PENDING)
    :param rereview: Re-uploaded themes (RereviewQueueTheme)

    """
    num = 0
    themes = []
    locks = []

    # Calculate number of themes to check out.
    if rereview:
        # Rereview themes.
        num, themes, locks = _get_rereview_themes(reviewer)
    else:
        # Pending and flagged themes.
        status = amo.STATUS_REVIEW_PENDING if flagged else amo.STATUS_PENDING
        locks = ThemeLock.objects.filter(
            reviewer=reviewer, theme__addon__status=status)
        num, themes = _calc_num_themes_checkout(locks)
        if themes:
            return themes

        themes = list(Persona.objects.no_cache().filter(
            addon__status=status, themelock=None))[:num]

    # Don't allow self-reviews.
    if (not settings.ALLOW_SELF_REVIEWS and
        not acl.action_allowed(request, 'Admin', '%')):
        themes = themes.exclude(addon__addonuser__user=reviewer)

    # Check out themes by setting lock.
    expiry = get_updated_expiry()
    for theme in themes:
        ThemeLock.objects.create(theme=theme, reviewer=reviewer, expiry=expiry)

    if not themes:
        # Empty pool? Go look for some expired locks.
        expired_locks = ThemeLock.objects.filter(
            expiry__lte=datetime.datetime.now(),
            theme__addon__status=status)[:rvw.THEME_INITIAL_LOCKS]
        for lock in expired_locks:
            # Steal expired locks.
            lock.reviewer = reviewer
            lock.expiry = expiry
            lock.save()
            themes = [lock.theme for lock in expired_locks]

    return [lock.theme for lock in locks]


def _calc_num_themes_checkout(locks):
    """
    Calculate number of themes to check out based on how many themes user
    currently has checked out.
    """
    current_num = locks.count()

    if current_num < rvw.THEME_INITIAL_LOCKS:
        # Check out themes from the pool if none or not enough checked out.
        return rvw.THEME_INITIAL_LOCKS - current_num, []
    else:
        # Update the expiry on currently checked-out themes.
        locks.update(expiry=get_updated_expiry())
        return 0, [lock.theme for lock in locks]


def _get_rereview_themes(reviewer):
    """Check out re-uploaded themes."""
    rereviews = RereviewQueueTheme.objects.filter(
        theme__themelock__reviewer=reviewer)

    num, locks = _calc_num_themes_checkout(
        [rrq.theme.themelock for rrq in rereviews])

    themes = list(
        RereviewQueueTheme.objects.filter(theme__themelock=None))[:num]

    return num, themes, locks


@waffle_switch('mkt-themes')
@post_required
@reviewer_required('persona')
def themes_commit(request):
    reviewer = request.user.get_profile()
    ThemeReviewFormset = formset_factory(forms.ThemeReviewForm)
    formset = ThemeReviewFormset(request.POST)

    for form in formset:
        try:
            lock = ThemeLock.objects.filter(
                theme_id=form.data[form.prefix + '-theme'],
                reviewer=reviewer)
        except MultiValueDictKeyError:
            # Address off-by-one error caused by management form.
            continue
        if lock and form.is_valid():
            form.save()

    if 'theme_redirect_url' in request.session:
        return redirect(request.session['theme_redirect_url'])
    else:
        return redirect(reverse('reviewers.themes.queue_themes'))


@json_view
@admin_required(reviewers=True)
def themes_more_flagged(request):
    return themes_more(request, flagged=True)


@waffle_switch('mkt-themes')
@reviewer_required('persona')
def themes_single(request, slug):
    """
    Like a detail page, manually review a single theme if it is pending
    and isn't locked.
    """
    reviewer = request.user.get_profile()
    reviewable = True

    # Don't review an already reviewed theme.
    theme = get_object_or_404(Persona, addon__slug=slug)
    if theme.addon.status != amo.STATUS_PENDING:
        reviewable = False

    if (not settings.ALLOW_SELF_REVIEWS and
        not acl.action_allowed(request, 'Admin', '%') and
        theme.addon.has_author(request.amo_user)):
        reviewable = False

    # Don't review a locked theme (that's not locked to self).
    try:
        lock = theme.themelock
        if (lock.reviewer.id != reviewer.id and
            lock.expiry > datetime.datetime.now()):
            reviewable = False
        elif (lock.reviewer.id != reviewer.id and
              lock.expiry < datetime.datetime.now()):
            # Steal expired lock.
            lock.reviewer = reviewer
            lock.expiry = get_updated_expiry()
            lock.save()
        else:
            # Update expiry.
            lock.expiry = get_updated_expiry()
            lock.save()
    except ThemeLock.DoesNotExist:
        # Create lock if not created.
        ThemeLock.objects.create(theme=theme, reviewer=reviewer,
                                 expiry=get_updated_expiry())

    ThemeReviewFormset = formset_factory(forms.ThemeReviewForm)
    formset = ThemeReviewFormset(initial=[{'theme': theme.id}])

    # Since we started the review on the single page, we want to return to the
    # single page rather than get shot back to the queue.
    request.session['theme_redirect_url'] = reverse('reviewers.themes.single',
                                                    args=[theme.addon.slug])

    return jingo.render(request, 'reviewers/themes/single.html', context(**{
        'formset': formset,
        'theme': theme,
        'theme_formsets': zip([theme], formset),
        'theme_reviews': paginate(request, ActivityLog.objects.filter(
            action=amo.LOG.THEME_REVIEW.id,
            _arguments__contains=theme.addon.id)),
        'actions': get_actions_json(),
        'theme_count': 1,
        'reviewable': reviewable,
        'reject_reasons': rvw.THEME_REJECT_REASONS.items(),
        'action_dict': rvw.REVIEW_ACTIONS,
    }))


@waffle_switch('mkt-themes')
@reviewer_required('persona')
def themes_logs(request):
    data = request.GET.copy()

    if not data.get('start') and not data.get('end'):
        today = datetime.date.today()
        data['start'] = datetime.date(today.year, today.month, 1)

    form = forms.ReviewAppLogForm(data)

    theme_logs = ActivityLog.objects.filter(action=amo.LOG.THEME_REVIEW.id)

    if form.is_valid():
        data = form.cleaned_data
        if data.get('start'):
            theme_logs = theme_logs.filter(created__gte=data['start'])
        if data.get('end'):
            theme_logs = theme_logs.filter(created__lt=data['end'])
        if data.get('search'):
            term = data['search']
            theme_logs = theme_logs.filter(
                Q(_details__icontains=term) |
                Q(user__display_name__icontains=term) |
                Q(user__username__icontains=term)).distinct()

    pager = paginate(request, theme_logs, 30)
    data = context(form=form, pager=pager, ACTION_DICT=rvw.REVIEW_ACTIONS,
                   REJECT_REASONS=rvw.THEME_REJECT_REASONS)
    return jingo.render(request, 'reviewers/themes/logs.html', data)


@waffle_switch('mkt-themes')
@reviewer_required('persona')
def themes_history(request, username):
    if not username:
        username = request.amo_user.username

    return jingo.render(request, 'reviewers/themes/history.html', context(**{
        'theme_reviews': paginate(request, ActivityLog.objects.filter(
            action=amo.LOG.THEME_REVIEW.id, user__username=username), 20),
        'user_history': True,
        'username': username,
        'reject_reasons': rvw.THEME_REJECT_REASONS.items(),
        'action_dict': rvw.REVIEW_ACTIONS,
    }))


def get_actions_json():
    return json.dumps({
        'moreinfo': rvw.ACTION_MOREINFO,
        'flag': rvw.ACTION_FLAG,
        'duplicate': rvw.ACTION_DUPLICATE,
        'reject': rvw.ACTION_REJECT,
        'approve': rvw.ACTION_APPROVE,
    })


def get_updated_expiry():
    return (datetime.datetime.now() +
            datetime.timedelta(minutes=rvw.THEME_LOCK_EXPIRY))
