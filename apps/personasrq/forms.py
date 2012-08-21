from django import forms

import happyforms
from tower import ugettext_lazy as _

import amo


class PersonaReviewForm(happyforms.Form):
    persona = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices={
            'moreinfo': _('Request More Info'),
            'flag': _('Flag'),
            'duplicate': _('Duplicate'),
            'reject': _('Reject'),
            'approve': _('Approve')
        }.items(),
        widget=forms.HiddenInput()
    )
    reject_reason = forms.ChoiceField(
        choices=amo.PERSONA_REJECTION_REASONS.items(),
        widget=forms.HiddenInput()
    )
    comment = forms.CharField(required=False, widget=forms.HiddenInput())
