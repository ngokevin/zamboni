from django import forms

import happyforms
from tower import ugettext_lazy as _

import amo


class PersonaReviewForm(happyforms.Form):
    persona = forms.IntegerField(
        widget=forms.HiddenInput(attrs={'class': 'persona_id'}))
    action = forms.ChoiceField(
        choices={
            'moreinfo': _('Request More Info'),
            'flag': _('Flag'),
            'duplicate': _('Duplicate'),
            'reject': _('Reject'),
            'approve': _('Approve')
        }.items(),
        widget=forms.HiddenInput(attrs={'class': 'action'})
    )
    reject_reason = forms.ChoiceField(
        choices=amo.PERSONA_REJECTION_REASONS.items(),
        widget=forms.HiddenInput(attrs={'class': 'reject_reason'})
    )
    comment = forms.CharField(required=False,
        widget=forms.HiddenInput(attrs={'class': 'comment'}))
