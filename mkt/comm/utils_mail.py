import base64
import logging
import urllib2
from email import message_from_string
from email.utils import parseaddr

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import translation

import waffle
from email_reply_parser import EmailReplyParser

import amo
from amo.utils import to_language

from mkt.access import acl
from mkt.access.models import Group
from mkt.comm.models import CommunicationThreadToken, user_has_perm_thread
from mkt.constants import comm
from mkt.site.helpers import absolutify
from mkt.site.mail import send_mail_jinja
from mkt.users.models import UserProfile
from mkt.webapps.models import Webapp


log = logging.getLogger('z.comm')


def send_mail_comm(note):
    """
    Email utility used globally by the Communication Dashboard to send emails.
    Given a note (its actions and permissions), recipients are determined and
    emails are sent to appropriate people.
    """
    if not waffle.switch_is_active('comm-dashboard'):
        return
    log.info(u'Sending emails for %s' % note.thread.addon)

    if note.note_type == comm.ESCALATION:
        # Email senior reviewers on escalations.
        recipients = (Group.objects.get(name='Senior App Reviewers')
                                   .values_list('id', 'email'))
        email_recipients(recipients, note,
                         template='escalation_senior_reviewer')

        # Email developers on escalations.
        recipients = note.thread.addon.authors.values_list('id', 'email')
        email_recipients(recipients, note,
                         template='escalation_developer')
    else:
        email_recipients(get_recipients(note), note)


def get_recipients(note):
    """
    Determine email recipients.
    Chooses reviewers that have participated in the thread, the app developers,
    and the Mozilla contact.
    Returns user_id/user_email tuples.
    """
    thread = note.thread
    developers = list(thread.addon.authors.values_list('id', 'email'))

    # Reviewers that have participated.
    recipients = list(thread.notes.filter(author__isnull=False).values_list(
        'author__id', 'author__email'))

    # Developers.
    recipients += developers

    # Mozilla contact.
    mozilla_contact = thread.addon.mozilla_contact
    for email in thread.addon.get_mozilla_contacts():
        try:
            mozilla_contact = UserProfile.objects.get(email=email)
        except UserProfile.DoesNotExist:
            continue
        recipients += (mozilla_contact.id, mozilla_contact.email)

    # Exclusions.
    excludes = []
    if not note.read_permission_developer:
        # Exclude developer.
        excludes += developers
    if note.author:
        # Exclude note author.
        excludes.append((note.author.id, note.author.email))

    return [r for r in set(recipients) if r not in excludes]


def tokenize_recipients(recipients, thread):
    """[(user_id, user_email)] -> [(user_email, token)]."""
    recipients = []
    for user_id, user_email in recipients:
        tok = get_reply_token(thread, user_id)
        recipients.append((user_email, tok.uuid))
    return recipients


def email_recipients(recipients, note, template=None):
    """
    Given a list of tuple of user_id/user_email, email bunch of people.
    note -- commbadge note, the note type determines which email to use.
    template -- override which template we use.
    """
    subject = '%s: %s' % (unicode(comm.NOTE_TYPES[note.note_type]),
                          note.thread.addon.name)

    for email, tok in tokenize_recipients(recipients, note.thread):
        reply_to = '{0}{1}@{2}'.format(comm.REPLY_TO_PREFIX, tok,
                                       settings.POSTFIX_DOMAIN)

        # Get the appropriate mail template.
        mail_template = template or comm.COMM_MAIL_MAP.get(note.note_type,
                                                           'generic')

        # Send mail.
        send_mail_jinja(subject, 'comm/emails/%s.html' % mail_template,
                        get_mail_context(note), recipient_list=[email],
                        from_email=settings.MKT_REVIEWERS_EMAIL,
                        perm_setting='app_reviewed',
                        headers={'reply_to': reply_to})


def get_mail_context(note):
    """
    Get context data for comm emails, specifically for review action emails.
    """
    app = note.thread.addon

    if app.name.locale != app.default_locale:
        # We need to display the name in some language that is relevant to the
        # recipient(s) instead of using the reviewer's. addon.default_locale
        # should work.
        lang = to_language(app.default_locale)
        with translation.override(lang):
            app = Webapp.objects.get(id=app.id)

    return {
        'amo': amo,
        'app': app,
        'comm': comm,
        'note': note,
        'review_url': absolutify(reverse('reviewers.apps.review',
                                 args=[app.app_slug], add_prefix=False)),
        'settings': settings
    }


class CommEmailParser(object):
    """Utility to parse email replies."""
    address_prefix = comm.REPLY_TO_PREFIX

    def __init__(self, email_text):
        """Decode base64 email and turn it into a Django email object."""
        try:
            log.info('CommEmailParser received email: ' + email_text)
            email_text = base64.standard_b64decode(
                urllib2.unquote(email_text.rstrip()))
        except TypeError:
            # Corrupt or invalid base 64.
            self.decode_error = True
            log.info('Decoding error for CommEmailParser')
            return

        self.email = message_from_string(email_text)

        payload = self.email.get_payload()  # If not multipart, it's a string.
        if isinstance(payload, list):
            # If multipart, get the plaintext part.
            for part in payload:
                if part.get_content_type() == 'text/plain':
                    payload = part.get_payload()
                    break

        self.reply_text = EmailReplyParser.read(payload).reply

    def _get_address_line(self):
        return parseaddr(self.email['to'])

    def get_uuid(self):
        name, addr = self._get_address_line()

        if addr.startswith(self.address_prefix):
            # Strip everything between "reply+" and the "@" sign.
            uuid = addr[len(self.address_prefix):].split('@')[0]
        else:
            log.info('TO: address missing or not related to comm. (%s)'
                      % unicode(self.email).strip())
            return False

        return uuid

    def get_body(self):
        return self.reply_text


def save_from_email_reply(reply_text):
    from mkt.comm.utils import create_comm_note

    log.debug("Saving from email reply")

    parser = CommEmailParser(reply_text)
    if hasattr(parser, 'decode_error'):
        return False

    uuid = parser.get_uuid()

    if not uuid:
        return False
    try:
        tok = CommunicationThreadToken.objects.get(uuid=uuid)
    except CommunicationThreadToken.DoesNotExist:
        log.error('An email was skipped with non-existing uuid %s.' % uuid)
        return False

    if user_has_perm_thread(tok.thread, tok.user) and tok.is_valid():
        # Deduce an appropriate note type.
        note_type = comm.NO_ACTION
        if (tok.user.addonuser_set.filter(addon=tok.thread.addon).exists()):
            note_type = comm.DEVELOPER_COMMENT
        elif acl.action_allowed_user(tok.user, 'Apps', 'Review'):
            note_type = comm.REVIEWER_COMMENT

        t, note = create_comm_note(tok.thread.addon, tok.thread.version,
                                   tok.user, parser.get_body(),
                                   note_type=note_type)
        log.info('A new note has been created (from %s using tokenid %s).'
                 % (tok.user.id, uuid))
        return note
    elif tok.is_valid():
        log.error('%s did not have perms to reply to comm email thread %s.'
                  % (tok.user.email, tok.thread.id))
    else:
        log.error('%s tried to use an invalid comm token for thread %s.'
                  % (tok.user.email, tok.thread.id))

    return False


def get_reply_token(thread, user_id):
    tok, created = CommunicationThreadToken.objects.get_or_create(
        thread=thread, user_id=user_id)

    # We expire a token after it has been used for a maximum number of times.
    # This is usually to prevent overusing a single token to spam to threads.
    # Since we're re-using tokens, we need to make sure they are valid for
    # replying to new notes so we reset their `use_count`.
    if not created:
        tok.update(use_count=0)
    else:
        log.info('Created token with UUID %s for user_id: %s.' %
                 (tok.uuid, user_id))
    return tok
