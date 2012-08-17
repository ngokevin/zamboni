from django.db import models

from users.models import UserForeignKey


class PersonaLocked(models.Model):
    persona_locked_id = models.PositiveIntegerField(db_index=True)
    persona = models.OneToOneField('addons.Persona')
    reviewer = UserForeignKey()
    expiry = models.DateTimeField()

    class Meta:
        db_table = 'personas_locked'
