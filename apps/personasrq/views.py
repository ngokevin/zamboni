# Using 'personas' instead of 'themes' in the backend code to be consistent
# with old code, but they're actually themes now.
import datetime

from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.forms.formsets import formset_factory
from django.utils.datastructures import MultiValueDictKeyError

import jingo
from tower import ugettext_lazy as _

import amo
from amo.decorators import json_view, post_required
from addons.models import Persona
from personasrq.forms import PersonaReviewForm
from personasrq.models import PersonaLock


def personasrq(request):
    reviewer = request.amo_user
    persona_locks = PersonaLock.objects.filter(reviewer=reviewer)
    persona_locks_count = persona_locks.count()

    if persona_locks_count < amo.INITIAL_LOCKS:
        personas = get_personas(reviewer, persona_locks, persona_locks_count)
        # Combine currently checked-out personas with newly checked-out ones by
        # re-evaluating persona_locks.
        personas = [persona_lock.persona for persona_lock in persona_locks]
    else:
        # Update the expiry on currently checked-out personas.
        persona_locks.update(
            expiry=datetime.datetime.now() + datetime.timedelta(minutes=30))
        personas = [persona_lock.persona for persona_lock in persona_locks]

    PersonaReviewFormset = formset_factory(PersonaReviewForm)
    formset = PersonaReviewFormset(
        initial=[{'persona': persona.persona_id} for persona in personas])

    return jingo.render(request, 'personasrq/index.html', {
        'formset': formset,
        'persona_formset': zip(personas, formset),
        'reject_reasons': amo.PERSONA_REJECT_REASONS.items(),
        'persona_count': len(personas),
        'max_locks': amo.MAX_LOCKS,
        'more_url': reverse('personasrq.more')
    })


def get_personas(reviewer, persona_locks, persona_locks_count):
    # Check out personas from the pool if none or not enough checked out.
    personas = list(Persona.objects
        .filter(addon__status=amo.STATUS_UNREVIEWED)
        [:amo.INITIAL_LOCKS - persona_locks_count])

    # Set a lock on the checked-out personas
    for persona in personas:
        PersonaLock.objects.create(persona=persona, reviewer=reviewer,
                                   expiry=datetime.datetime.now() +
                                   datetime.timedelta(minutes=30),
                                   persona_lock_id=persona.persona_id)
        persona.addon.set_status(amo.STATUS_PENDING)

    # Empty pool? Go look for some expired locks.
    if not personas:
        expired_locks = (PersonaLock.objects
            .filter(expiry__lte=datetime.datetime.now())
            [:amo.INITIAL_LOCKS])
        # Steal expired locks.
        for persona_lock in expired_locks:
            persona_lock.reviewer = reviewer
            persona_lock.expiry = (datetime.datetime.now() +
                                   datetime.timedelta(minutes=30))
            persona_lock.save()
            personas = [persona_lock.persona for persona_lock
                        in expired_locks]
    return personas


@post_required
def commit(request):
    reviewer = request.amo_user
    PersonaReviewFormset = formset_factory(PersonaReviewForm)
    formset = PersonaReviewFormset(request.POST)

    for form in formset:
        if form.is_valid() and form.cleaned_data:
            form.save()
        else:
            # If invalid data somehow got past client-side validation,
            # ignore the offending review and discard the lock.
            try:
                persona_lock = PersonaLock.objects.filter(
                    persona=form.data[form.prefix + '-persona'],
                    reviewer=reviewer)
                if persona_lock:
                    persona_lock.delete()
            except MultiValueDictKeyError:
                # Django's formset metadata off-by-one, ignore extra form.
                pass
    return redirect(reverse('personasrq.queue'))


@json_view
def more(request):
    reviewer = request.amo_user
    persona_locks = PersonaLock.objects.filter(reviewer=reviewer)
    persona_locks_count = persona_locks.count()

    # Maximum number of locks.
    if (persona_locks_count >= amo.MAX_LOCKS):
        return {
            'personas': [],
            'message': _('You have reached the maximum number of personas to '
                         'review at once. Please commit your outstanding '
                         'reviews.')}

    # Adapt the third argument of get_personas to not take over than the max
    # number of locks.
    if persona_locks_count > amo.MAX_LOCKS - amo.INITIAL_LOCKS:
        wanted_locks = amo.MAX_LOCKS - persona_locks_count
    else:
        wanted_locks = amo.INITIAL_LOCKS
    personas = get_personas(reviewer, persona_locks,
                            amo.INITIAL_LOCKS - wanted_locks)

    # Create forms, which will need to be manipulated to fit with the currently
    # existing forms.
    PersonaReviewFormset = formset_factory(PersonaReviewForm)
    formset = PersonaReviewFormset(
        initial=[{'persona': persona.persona_id} for persona in personas])

    html = jingo.render(request, 'personasrq/personas.html', {
        'persona_formset': zip(personas, formset)
    }).content

    return {'html': html,
            'count': PersonaLock.objects.filter(reviewer=reviewer).count()}


def single(request, persona_id):
    """
    Like a detail page, manually review a single persona if it is pending
    and isn't locked.
    """
    reviewer = request.amo_user
    error = False
    msg = None

    # Don't review an already reviewed theme.
    persona = get_object_or_404(Persona, persona_id=persona_id)
    if persona.addon.status not in [amo.STATUS_UNREVIEWED, amo.STATUS_PENDING]:
        error = True
        msg = _('This theme has already been reviewed.')

    # Don't review a locked theme (that's not locked to self).
    persona_lock = (PersonaLock.objects.filter(persona=persona)
                    .exclude(reviewer=reviewer))
    if persona_lock and persona_lock[0].expiry > datetime.datetime.now():
        error = True
        msg = _('This theme is currently being reviewed.')

    if error:
        return jingo.render(request, 'personasrq/error.html', {
            'persona': persona,
            'error': msg
        })

    # Create lock if not created.
    if persona_lock == []:  # Passes on 'if not persona_lock' for some reason.
        PersonaLock.objects.create(persona=persona, reviewer=reviewer,
                                   expiry=datetime.datetime.now() +
                                   datetime.timedelta(minutes=30),
                                   persona_lock_id=persona.persona_id)
        persona.addon.set_status(amo.STATUS_PENDING)

    PersonaReviewFormset = formset_factory(PersonaReviewForm)
    formset = PersonaReviewFormset(
        initial=[{'persona': persona.persona_id}])

    return jingo.render(request, 'personasrq/single.html', {
        'formset': formset,
        'persona': persona,
        'persona_formset': zip([persona, ], formset),
        'reject_reasons': amo.PERSONA_REJECT_REASONS.items(),
        'max_locks': 0,
    })
