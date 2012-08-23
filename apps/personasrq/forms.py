from django import forms

import happyforms
from tower import ugettext_lazy as _

import amo
from amo.utils import raise_required


class PersonaReviewForm(happyforms.Form):
    persona = forms.IntegerField(
        widget=forms.HiddenInput(attrs={'class': 'persona_id'}))
    action = forms.ChoiceField(
        choices=amo.REVIEW_CHOICES.items(),
        widget=forms.HiddenInput(attrs={'class': 'action'})
    )
    reject_reason = forms.ChoiceField(
        choices=amo.PERSONA_REJECT_REASONS.items(),
        widget=forms.HiddenInput(attrs={'class': 'reject_reason'}),
        required=False
    )
    comment = forms.CharField(required=False,
        widget=forms.HiddenInput(attrs={'class': 'comment'}))

    def clean_action(self):
        if ('action' in self.cleaned_data and
            self.cleaned_data['action'] not in amo.REVIEW_CHOICES.keys()):
            raise forms.ValidationError('Action not recognized')
        return self.cleaned_data['action']

    def clean_reject_reason(self):
        if ('action' in self.cleaned_data and
            self.cleaned_data['action'] == 'reject'
            and not self.cleaned_data['reject_reason']):
            raise_required()
        return self.cleaned_data['reject_reason']

    def clean_comment(self):
        d = self.cleaned_data
        # Comment field needed for duplicate, flag, moreinfo, and other reason
        # for rejection.
        if ('action' in self.cleaned_data and
            (d['action'] == 'duplicate' or d['action'] == 'flag' or
             d['action'] == 'moreinfo' or
            (d['action'] == 'reject' and d['reject_reason'] == '0'))
            and not d['comment']):
            raise_required()
        return self.cleaned_data['reject_reason']
