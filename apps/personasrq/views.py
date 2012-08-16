# Using 'personas' instead of 'themes' in the backend code to be consistent
# with old code, but they're actually themes now.
import datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.forms.formsets import formset_factory
from django.utils.datastructures import MultiValueDictKeyError

import jingo
from tower import ugettext_lazy as _

import amo
from amo.decorators import json_view, post_required
import amo.utils
from addons.models import Persona
from editors.views import reviewer_required
from personasrq.forms import PersonaReviewForm
from personasrq.models import PersonaLock, PersonaReview


@reviewer_required('persona')
def queue(request):
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
            expiry=datetime.datetime.now() +
            datetime.timedelta(minutes=amo.LOCK_EXPIRY))
        personas = [persona_lock.persona for persona_lock in persona_locks]

    PersonaReviewFormset = formset_factory(PersonaReviewForm)
    formset = PersonaReviewFormset(
        initial=[{'persona': persona.persona_id} for persona in personas])

    request.session['persona_redirect_url'] = reverse('personasrq.queue')

    return jingo.render(request, 'personasrq/queue.html', {
        'formset': formset,
        'persona_formset': zip(personas, formset),
        'reject_reasons': amo.PERSONA_REJECT_REASONS.items(),
        'persona_count': len(personas),
        'max_locks': amo.MAX_LOCKS,
        'more_url': reverse('personasrq.more'),
        'actions': amo.REVIEW_ACTIONS,
        'reviewable': True,
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
                                   datetime.timedelta(minutes=amo.LOCK_EXPIRY),
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
                                   datetime.timedelta(minutes=amo.LOCK_EXPIRY))
            persona_lock.save()
            personas = [persona_lock.persona for persona_lock
                        in expired_locks]
    return personas


@post_required
@reviewer_required('persona')
def commit(request):
    reviewer = request.amo_user
    PersonaReviewFormset = formset_factory(PersonaReviewForm)
    formset = PersonaReviewFormset(request.POST)

    for form in formset:
        try:
            persona_lock = PersonaLock.objects.filter(
                persona__persona_id=form.data[form.prefix + '-persona'],
                reviewer=reviewer)
            if persona_lock and form.is_valid() and form.cleaned_data:
                form.save()
        except MultiValueDictKeyError:
            # Address off-by-one error caused by management form.
            continue

    if 'persona_redirect_url' in request.session:
        return redirect(request.session['persona_redirect_url'])
    else:
        return redirect(reverse('personasrq.queue'))


@json_view
@reviewer_required('persona')
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
        'persona_formset': zip(personas, formset),
        'max_locks': amo.MAX_LOCKS
    }).content

    return {'html': html,
            'count': PersonaLock.objects.filter(reviewer=reviewer).count()}


@reviewer_required('persona')
def single(request, slug):
    """
    Like a detail page, manually review a single persona if it is pending
    and isn't locked.
    """
    reviewer = request.amo_user
    reviewable = True

    # Don't review an already reviewed theme.
    persona = get_object_or_404(Persona, addon__slug=slug)
    if (persona.addon.status not in
        [amo.STATUS_UNREVIEWED, amo.STATUS_PENDING, amo.STATUS_REJECTED]):
        reviewable = False

    # Don't review a locked theme (that's not locked to self).
    persona_lock = (PersonaLock.objects.filter(persona=persona)
                    .exclude(reviewer=reviewer))
    if persona_lock and persona_lock[0].expiry > datetime.datetime.now():
        reviewable = False

    if reviewable:
        # Create lock if not created or steal expired one.
        persona_lock = PersonaLock.objects.filter(persona=persona)
        if persona_lock:
            persona_lock.update(reviewer=reviewer,
                expiry=datetime.datetime.now() +
                datetime.timedelta(minutes=amo.LOCK_EXPIRY)
            )
        else:
            PersonaLock.objects.create(persona=persona, reviewer=reviewer,
                expiry=datetime.datetime.now() +
                datetime.timedelta(minutes=amo.LOCK_EXPIRY),
                persona_lock_id=persona.persona_id)
            persona.addon.set_status(amo.STATUS_PENDING)

    PersonaReviewFormset = formset_factory(PersonaReviewForm)
    formset = PersonaReviewFormset(
        initial=[{'persona': persona.persona_id}])

    request.session['persona_redirect_url'] = reverse('personasrq.single',
        args=[persona.addon.slug])

    pager = amo.utils.paginate(request,
        PersonaReview.objects.filter(persona=persona)
        .order_by('-created'), 20)

    return jingo.render(request, 'personasrq/single.html', {
        'formset': formset,
        'persona': persona,
        'persona_formset': zip([persona, ], formset),
        'pager': pager,
        'persona_reviews': pager.object_list,
        'reject_reasons': amo.PERSONA_REJECT_REASONS.items(),
        'max_locks': 0,
        'actions': amo.REVIEW_ACTIONS,
        'reasons': amo.PERSONA_REJECT_REASONS,
        'persona_count': 1,
        'reviewable': reviewable,
    })


@reviewer_required('persona')
def history(request):
    pager = amo.utils.paginate(request,
        PersonaReview.objects.filter(
        reviewer=request.amo_user).order_by('-created'), 20)

    return jingo.render(request, 'personasrq/history.html', {
        'persona_reviews': pager.object_list,
        'pager': pager,
        'user_history': True,
        'actions': amo.REVIEW_ACTIONS,
        'reasons': amo.PERSONA_REJECT_REASONS,
        'base_url': settings.SITE_URL
    })
