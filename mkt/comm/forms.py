from django import forms

import happyforms
from tower import ugettext as _

from mkt.api.forms import SluggableModelChoiceField
from mkt.constants import comm
from mkt.webapps.models import Webapp


class AppSlugForm(happyforms.Form):
    app = SluggableModelChoiceField(queryset=Webapp.objects.all(),
                                    sluggable_to_field_name='app_slug')


class CreateCommThreadForm(happyforms.Form):
    app = SluggableModelChoiceField(queryset=Webapp.objects.all(),
                                    sluggable_to_field_name='app_slug')
    version = forms.CharField()
    note_type = forms.TypedChoiceField(
        empty_value=comm.NO_ACTION,
        choices=[(note, note) for note in comm.NOTE_TYPES], coerce=int)
    body = forms.CharField()

    def clean_version(self):
        version_num = self.cleaned_data['version']
        versions = self.cleaned_data['app'].versions.filter(
            version=version_num).order_by('-created')
        if versions.exists():
            return versions[0]
        raise forms.ValidationError(
            _('Version %s does not exist' % version_num))

    def clean_body(self):
        if not self.cleaned_data['body']:
            raise forms.ValidationError(_('Note body is empty'))
        return self.cleaned_data['body']
