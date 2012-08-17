import jingo

import amo
from amo.decorators import json_view
from addons.models import Persona
from personasrq.models import PersonaLocked


def personasrq(request):
    reviewer = request.amo_user
    reviewer_personas_locked = PersonaLocked.objects.filter(reviewer=reviewer)
    if not reviewer_personas_locked:
        personas_to_review = (Persona.objects
            .filter(addon__status=amo.STATUS_PENDING)
            [:amo.MAX_LOCKED])
    else:
        pass

    personas_to_review = Persona.objects.filter(id__gte=2000, id__lte=2003)
    return jingo.render(request, 'personasrq/index.html', {
        'personas': personas_to_review
    })


@json_view
def approve(request):
    pass


@json_view
def reject(request):
    pass
