import datetime

from django.conf import settings

from celeryutils import task
from tower import ugettext_lazy as _

import amo
from amo.utils import send_mail_jinja


@task
def send_mail(cleaned_data, persona, persona_lock):
    """
    Send emails out for respective review actions taken on themes.
    """
    action = cleaned_data['action']
    reject_reason = cleaned_data['reject_reason']
    reason = None
    if reject_reason:
        reason = amo.PERSONA_REJECT_REASONS[reject_reason]
    comment = cleaned_data['comment']

    emails = set(persona.addon.authors.values_list('email', flat=True))
    context = {
        'persona': persona,
        'base_url': settings.SITE_URL,
        'reason': reason,
        'comment': comment
    }

    subject = None
    if action == amo.ACTION_APPROVE:
        subject = _('Thanks for submitting your Theme')
        template = 'personasrq/emails/approve.html'
        persona.addon.update(status=amo.STATUS_PUBLIC)

    elif action == amo.ACTION_REJECT:
        subject = _('A problem with your Theme submission')
        template = 'personasrq/emails/reject.html'
        persona.addon.update(status=amo.STATUS_REJECTED)
        reason = (amo.PERSONA_REJECT_REASONS[reject_reason])

    elif action == amo.ACTION_DUPLICATE:
        subject = _('A problem with your Theme submission')
        template = 'personasrq/emails/reject.html'
        persona.addon.update(status=amo.STATUS_REJECTED)
        reason = 'Duplicate'

    elif action == amo.ACTION_FLAG:
        subject = ('Theme Submission Flagged for Review: %s'
                   % persona.addon.name)
        template = 'personasrq/emails/flag.html'
        emails = [settings.SENIOR_EDITORS_EMAIL]
        persona.addon.update(status=amo.STATUS_PENDING)

    elif action == amo.ACTION_MOREINFO:
        subject = _('A question about your Theme submission')
        template = 'personasrq/emails/moreinfo.html'
        context['reviewer_email'] = persona_lock.reviewer.email
        persona.addon.update(status=amo.STATUS_PENDING)

    amo.log(amo.LOG.PERSONA_REVIEW, persona, details={
        'action': action,
        'reject_reason': reject_reason,
        'comment': comment}, user=persona_lock.reviewer)

    persona.approve = datetime.datetime.now()
    persona.save()

    if subject is not None:
        send_mail_jinja(subject, template, context,
                        recipient_list=emails,
                        headers={'Reply-To': persona_lock.reviewer.email})
