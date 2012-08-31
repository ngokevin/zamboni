from django.db import models

import amo
from users.models import UserForeignKey


class PersonaLock(models.Model):
    persona = models.OneToOneField('addons.Persona')
    persona_lock_id = models.PositiveIntegerField(db_index=True)
    reviewer = UserForeignKey()
    expiry = models.DateTimeField()

    class Meta:
        db_table = 'persona_locks'


class PersonaReview(amo.models.ModelBase):
    """
    Review history.
    """
    reviewer = UserForeignKey()
    persona = models.ForeignKey('addons.Persona')
    action = models.PositiveIntegerField(choices=amo.REVIEW_ACTIONS.items())
    reject_reason = models.PositiveIntegerField(
        choices=amo.PERSONA_REJECT_REASONS.items() + [('duplicate', '')],
        null=True)
    comment = models.CharField(null=True, max_length=500)

    class Meta:
        db_table = 'persona_reviews'
