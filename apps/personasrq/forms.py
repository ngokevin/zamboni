from django import forms

import happyforms
from tower import ugettext_lazy as _

from addons.models import Persona
import amo
from amo.utils import raise_required
from personasrq.models import PersonaLock


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

    def clean_persona(self):
        if not Persona.objects.get(id=self.cleaned_data['persona']):
            raise forms.ValidationError('Persona does not exist.')

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
        # Comment field needed for duplicate, flag, moreinfo, and reject.
        if ('action' in self.cleaned_data and
            (d['action'] == 'duplicate' or d['action'] == 'flag' or
             d['action'] == 'moreinfo' or d['action'] == 'reject')
            and not d['comment']):
            raise_required()
        return self.cleaned_data['reject_reason']

    def save(self):
        persona = Persona.objects.get(id=self.cleaned_data['persona'])
        persona_lock = PersonaLock.objects.get(persona=persona)

        action = self.cleaned_data['action']
        reason = (amo.PERSONA_REJECT_REASONS[int(
                  self.cleaned_data['reject_reason'])])
        comment = self.cleaned_data['comment']

        if action == 'approve':
            persona.addon.set_status(amo.STATUS_PUBLIC)

        elif action == 'reject':
            persona.addon.set_status(amo.STATUS_REJECTED)
            reason = (amo.PERSONA_REJECT_REASONS[int(
                      self.cleaned_data['reject_reason'])])

        elif action == 'duplicate':
            persona.addon.set_status(amo.STATUS_REJECTED)

        elif action == 'flag':
            persona.addon.set_status(amo.STATUS_PENDING)

        elif action == 'moreinfo':
            persona.addon.set_status(amo.STATUS_PENDING)
