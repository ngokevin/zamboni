import copy

from django import forms

import happyforms
from tower import ugettext as _, ugettext_lazy as _lazy

import amo
from amo.utils import raise_required
from addons.models import Persona
from editors.forms import ReviewAddonForm, ReviewLogForm
from mkt.reviewers.utils import ReviewHelper
import mkt.constants.reviewers as rvw
from .models import ThemeLock
from .tasks import send_mail


class ReviewAppForm(ReviewAddonForm):

    def __init__(self, *args, **kw):
        kw.update(type=amo.CANNED_RESPONSE_APP)
        super(ReviewAppForm, self).__init__(*args, **kw)
        # We don't want to disable any app files:
        self.addon_files_disabled = tuple([])
        self.fields['notify'].label = _lazy(
            u'Notify me the next time the manifest is updated. (Subsequent '
             'updates will not generate an email.)')


def get_review_form(data, request=None, addon=None, version=None):
    helper = ReviewHelper(request=request, addon=addon, version=version)
    return ReviewAppForm(data, helper=helper)


class ReviewAppLogForm(ReviewLogForm):

    def __init__(self, *args, **kwargs):
        super(ReviewAppLogForm, self).__init__(*args, **kwargs)
        self.fields['search'].widget.attrs = {
            # L10n: Descript of what can be searched for.
            'placeholder': _lazy(u'app, reviewer, or comment'),
            'size': 30}


class AppQueueSearchForm(happyforms.Form):
    text_query = forms.CharField(
                    required=False,
                    label=_lazy(u'Search by app name or author email'))
    searching = forms.BooleanField(widget=forms.HiddenInput, required=False,
                                   initial=True)
    admin_review = forms.ChoiceField(required=False,
                                     choices=[('', ''),
                                              ('1', _lazy(u'yes')),
                                              ('0', _lazy(u'no'))],
                                     label=_lazy(u'Admin Flag'))
    waiting_time_days = forms.ChoiceField(
                required=False,
                label=_lazy(u'Days Since Submission'),
                choices=([('', '')] +
                         [(i, i) for i in range(1, 10)] + [('10+', '10+')]))
    device_type_ids = forms.MultipleChoiceField(
                required=False,
                label=_lazy(u'Device Type'),
                choices=[(d.id, d.name)
                         for d in amo.DEVICE_TYPES.values()])

    premium_types = copy.deepcopy(amo.ADDON_PREMIUM_TYPES)
    premium_types[amo.ADDON_OTHER_INAPP] = _('Other system')
    premium_type_ids = forms.MultipleChoiceField(
                required=False,
                label=_lazy(u'Premium Type'),
                choices=premium_types.items())

    def __init__(self, *args, **kw):
        super(AppQueueSearchForm, self).__init__(*args, **kw)

    def filter_qs(self, qs):
        data = self.cleaned_data
        if data['admin_review']:
            qs = qs.filter(admin_review=data['admin_review'])
        if data['text_query']:
            lang = get_language()
            joins = [
                'LEFT JOIN addons_users au on (au.addon_id = addons.id)',
                'LEFT JOIN users u on (u.id = au.user_id)',
                """LEFT JOIN translations AS supportemail_default ON
                        (supportemail_default.id = addons.supportemail AND
                         supportemail_default.locale=addons.defaultlocale)""",
                """LEFT JOIN translations AS supportemail_local ON
                        (supportemail_local.id = addons.supportemail AND
                         supportemail_local.locale=%%(%s)s)"""
                         % qs._param(lang),
                """LEFT JOIN translations AS ad_name_local ON
                        (ad_name_local.id = addons.name AND
                         ad_name_local.locale=%%(%s)s)"""
                         % qs._param(lang)]
            qs.base_query['from'].extend(joins)
            fuzzy_q = u'%' + data['text_query'] + u'%'
            qs = qs.filter_raw(
                    Q('addon_name LIKE', fuzzy_q) |
                    # Search translated add-on names / support emails in
                    # the editor's locale:
                    Q('ad_name_local.localized_string LIKE', fuzzy_q) |
                    Q('supportemail_default.localized_string LIKE', fuzzy_q) |
                    Q('supportemail_local.localized_string LIKE', fuzzy_q) |
                    Q('au.role IN', [amo.AUTHOR_ROLE_OWNER,
                                     amo.AUTHOR_ROLE_DEV],
                      'u.email LIKE', fuzzy_q))
        if data['waiting_time_days']:
            if data['waiting_time_days'] == '10+':
                # Special case
                args = ('waiting_time_days >=',
                        int(data['waiting_time_days'][:-1]))
            else:
                args = ('waiting_time_days <=', data['waiting_time_days'])

            qs = qs.having(*args)
        return qs


class ThemeReviewForm(happyforms.Form):
    theme = forms.ModelChoiceField(queryset=Persona.objects.all(),
                                   widget=forms.HiddenInput())
    action = forms.TypedChoiceField(
        choices=rvw.REVIEW_ACTIONS.items(),
        widget=forms.HiddenInput(attrs={'class': 'action'}),
        coerce=int, empty_value=None
    )
    # Duplicate is the same as rejecting but has its own flow.
    reject_reason = forms.TypedChoiceField(
        choices=rvw.THEME_REJECT_REASONS.items() + [('duplicate', '')],
        widget=forms.HiddenInput(attrs={'class': 'reject-reason'}),
        required=False, coerce=int, empty_value=None)
    comment = forms.CharField(required=False,
        widget=forms.HiddenInput(attrs={'class': 'comment'}))

    def clean_theme(self):
        theme = self.cleaned_data['theme']
        try:
            ThemeLock.objects.get(theme=theme)
        except (ThemeLock.DoesNotExist):
            raise forms.ValidationError(
                _('Someone else is reviewing this theme.'))
        return theme

    def clean_reject_reason(self):
        reject_reason = self.cleaned_data.get('reject_reason', None)
        if (self.cleaned_data.get('action') == rvw.ACTION_REJECT
            and reject_reason == None):
            raise_required()
        return reject_reason

    def clean_comment(self):
        # Comment field needed for duplicate, flag, moreinfo, and other reject
        # reason.
        action = self.cleaned_data.get('action')
        reject_reason = self.cleaned_data.get('reject_reason')
        comment = self.cleaned_data.get('comment')
        if (not comment and (action == rvw.ACTION_FLAG or
                             action == rvw.ACTION_MOREINFO or
                             (action == rvw.ACTION_REJECT and
                              reject_reason == 0))):
            raise_required()
        return comment

    def save(self):
        theme_lock = ThemeLock.objects.get(theme=self.cleaned_data['theme'])
        send_mail(self.cleaned_data, theme_lock)
        theme_lock.delete()
