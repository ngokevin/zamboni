# Using 'personas' instead of 'themes' in the backend code to be consistent
# with old code, but they're actually themes now.
import datetime

import jingo

import amo
from amo.decorators import json_view
from addons.models import Persona
from personasrq.models import PersonaLock


def personasrq(request):
    # from users.models import UserProfile
    # reviewer = UserProfile.objects.get(username='kngo')
    reviewer = request.amo_user
    persona_locks = PersonaLock.objects.filter(reviewer=reviewer)

    if not persona_locks:
        # Check out personas from the pool if none checked out.
        personas = (Persona.objects
            .filter(addon__status=amo.STATUS_PENDING)
            [:amo.MAX_LOCKS])

        # Set a lock on the checked-out personas
        for persona in personas:
            PersonaLock.objects.create(persona=persona, reviewer=reviewer,
                                       expiry=datetime.datetime.now() +
                                       datetime.timedelta(minutes=30),
                                       persona_lock_id=persona.persona_id)
            persona.addon.status = amo.STATUS_BEING_REVIEWED
            persona.addon.save()

        # Empty pool? Go look for some expired locks.
        if not personas:
            expired_locks = (PersonaLock.objects
                .filter(expiry__lte=datetime.datetime.now())
                [:amo.MAX_LOCKS])
            # Steal expired locks.
            for persona_lock in expired_locks:
                persona_lock.reviewer = reviewer
                persona_lock.expiry = (datetime.datetime.now() +
                                       datetime.timedelta(minutes=30))
                persona_lock.save()
                personas = [persona_lock.persona for persona_lock
                            in expired_locks]
    else:
        # Update the expiry on currently checked-out personas.
        persona_locks.update(
            expiry=datetime.datetime.now() + datetime.timedelta(minutes=30))
        personas = [persona_lock.persona for persona_lock in persona_locks]

    return jingo.render(request, 'personasrq/index.html', {
        'personas': personas
    })


@json_view
def approve(request):
    pass


@json_view
def reject(request):
    pass
