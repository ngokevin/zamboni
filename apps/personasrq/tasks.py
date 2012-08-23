from celeryutils import task

from amo.utils import send_mail_jinja


@task
def send_mail(subject, template, context, recipient_list):
    from django.conf import settings
    settings.SEND_REAL_EMAIL = True
    send_mail_jinja(subject, template, context,
                    recipient_list=recipient_list)
