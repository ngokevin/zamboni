from django.db import models

from users.models import UserForeignKey


class PersonaLock(models.Model):
    persona = models.OneToOneField('addons.Persona')
    persona_lock_id = models.PositiveIntegerField(db_index=True)
    reviewer = UserForeignKey()
    expiry = models.DateTimeField()

    class Meta:
        db_table = 'persona_locks'
