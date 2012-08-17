from django.db import models

from users.models import UserForeignKey


class PersonaLock(models.Model):
    persona_lock_id = models.PositiveIntegerField(db_index=True)
    persona = models.OneToOneField('addons.Persona')
    reviewer = UserForeignKey()
    expiry = models.DateTimeField()

    class Meta:
        db_table = 'persona_locks'
