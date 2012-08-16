from django import forms

import happyforms
from tower import ugettext_lazy as _

from addons.models import Persona
import amo
from amo.utils import raise_required
from personasrq.models import PersonaLock
from personasrq.tasks import send_mail


class PersonaReviewForm(happyforms.Form):
    persona = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.TypedChoiceField(
        choices=amo.REVIEW_ACTIONS.items(),
        widget=forms.HiddenInput(attrs={'class': 'action'}),
        coerce=int, empty_value=None
    )
    reject_reason = forms.TypedChoiceField(
        choices=amo.PERSONA_REJECT_REASONS.items() + [('duplicate', '')],
        widget=forms.HiddenInput(attrs={'class': 'reject-reason'}),
        required=False, coerce=int, empty_value=None)
    comment = forms.CharField(required=False,
        widget=forms.HiddenInput(attrs={'class': 'comment'}))

    def clean_persona(self):
        if not Persona.objects.get(id=self.cleaned_data['persona']):
            raise forms.ValidationError(_('Theme does not exist.'))
        return self.cleaned_data['persona']

    def clean_action(self):
        if ('action' in self.cleaned_data and
            self.cleaned_data['action'] not in amo.REVIEW_ACTIONS.keys()):
            raise forms.ValidationError(_('Action not recognized.'))
        return self.cleaned_data['action']

    def clean_reject_reason(self):
        if ('action' in self.cleaned_data and
            self.cleaned_data['action'] == amo.ACTION_REJECT
            and not self.cleaned_data['reject_reason']):
            raise_required()
        return self.cleaned_data['reject_reason']

    def clean_comment(self):
        # Comment field needed for duplicate, flag, moreinfo, and reject.
        if ('action' in self.cleaned_data
            and self.cleaned_data['action'] != amo.ACTION_APPROVE
            and not self.cleaned_data['comment']):
            raise_required()
        return self.cleaned_data['comment']

    def save(self):
        try:
            persona = Persona.objects.get(
                persona_id=self.cleaned_data['persona'])
            persona_lock = PersonaLock.objects.get(persona=persona)
        except (Persona.DoesNotExist, PersonaLock.DoesNotExist):
            # This shouldn't happen so just discard the review.
            return

        send_mail(self.cleaned_data, persona, persona_lock)
        persona_lock.delete()
