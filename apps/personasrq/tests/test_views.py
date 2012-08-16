import datetime
import time

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from nose.tools import eq_
from pyquery import PyQuery as pq

from access.models import GroupUser
from addons.models import Persona
import amo
import amo.tests
from amo.tests import addon_factory
from devhub.models import ActivityLog
from personasrq.models import PersonaLock
from users.models import UserProfile


class PersonaReviewQueueTest(amo.tests.TestCase):
    fixtures = ['base/users', 'base/admin']

    def setUp(self):
        self.persona_count = int(amo.PERSONA_INITIAL_LOCKS * 2.5)
        for x in range(self.persona_count):
            addon_factory(type=amo.ADDON_PERSONA, status=amo.STATUS_UNREVIEWED)

    def create_and_become_reviewer(self):
        username = 'reviewer%s' % User.objects.count()
        email = username + '@mozilla.com'
        reviewer = User.objects.create(username=email, email=email,
                                       is_active=True, is_superuser=True,
                                       is_staff=True)
        user = UserProfile.objects.create(user=reviewer, email=email,
                                          username=username)
        reviewer.set_password('password')
        reviewer.save()
        user.set_password('password')
        user.save()
        GroupUser.objects.create(group_id=50002, user=user)

        self.client.login(username=email, password='password')
        return user

    def get_personas(self):
        return self.client.get(reverse('personasrq.queue')).content

    def get_and_check_personas(self, reviewer, expected_queue_length):
        doc = pq(self.get_personas())
        eq_(doc('div.persona').length, expected_queue_length)
        eq_(PersonaLock.objects.filter(reviewer=reviewer).count(),
            expected_queue_length)

    def test_basic_queue(self):
        # Have reviewers take personas from the pool and into the queue.
        self.free_personas = self.persona_count
        for i in range(self.persona_count):
            reviewer = self.create_and_become_reviewer()

            if self.free_personas > amo.PERSONA_INITIAL_LOCKS:
                expected_queue_length = amo.PERSONA_INITIAL_LOCKS
            else:
                expected_queue_length = self.free_personas
            self.free_personas -= expected_queue_length

            self.get_and_check_personas(reviewer, expected_queue_length)

    def test_top_off(self):
        # If reviewer has less than max locks, try to get more from pool.
        reviewer = self.create_and_become_reviewer()

        doc = pq(self.get_personas())
        eq_(doc('div.persona').length, amo.PERSONA_INITIAL_LOCKS)
        eq_(PersonaLock.objects.filter(reviewer=reviewer).count(),
            amo.PERSONA_INITIAL_LOCKS)

        for persona_lock in PersonaLock.objects.filter(reviewer=reviewer)[:2]:
            persona_lock.delete()

        # Add to the pool.
        for i in range(4):
            addon_factory(type=amo.ADDON_PERSONA,
                          status=amo.STATUS_UNREVIEWED)

        doc = pq(self.get_personas())
        eq_(doc('div.persona').length, amo.PERSONA_INITIAL_LOCKS)
        eq_(PersonaLock.objects.filter(reviewer=reviewer).count(),
            amo.PERSONA_INITIAL_LOCKS)

    def test_expiry(self):
        # Test that reviewers who want personas from an empty pool can steal
        # checked-out personas from other reviewers whose locks have expired.
        for i in range(3):
            reviewer = self.create_and_become_reviewer()
            self.get_personas()

        # Reviewer wants personas, but empty pool.
        reviewer = self.create_and_become_reviewer()
        self.get_personas()
        eq_(PersonaLock.objects.filter(reviewer=reviewer).count(), 0)

        # Manually expire a lock and see if it's reassigned.
        expired_persona_lock = PersonaLock.objects.all()[0]
        expired_persona_lock.expiry = datetime.datetime.now()
        expired_persona_lock.save()
        self.get_personas()
        eq_(PersonaLock.objects.filter(reviewer=reviewer).count(), 1)

    def test_expiry_update(self):
        # Test expiry is updated when reviewer reloads his queue.
        reviewer = self.create_and_become_reviewer()
        self.get_personas()
        expiry = PersonaLock.objects.filter(reviewer=reviewer)[0].expiry
        time.sleep(1)
        self.client.get(reverse('personasrq.queue'))
        eq_(PersonaLock.objects.filter(reviewer=reviewer)[0].expiry > expiry,
            True)

    def test_permissions_reviewer(self):
        slug = Persona.objects.all()[1].addon.slug

        eq_(self.client.get(reverse('personasrq.queue')).status_code, 302)
        eq_(self.client.get(reverse('personasrq.single',
                            args=[slug])).status_code, 302)
        eq_(self.client.post(reverse('personasrq.commit')).status_code, 302)
        eq_(self.client.post(reverse('personasrq.commit')).status_code, 302)
        eq_(self.client.get(reverse('personasrq.more')).status_code, 302)

        self.create_and_become_reviewer()

        eq_(self.client.get(reverse('personasrq.queue')).status_code, 200)
        eq_(self.client.get(reverse('personasrq.single',
                            args=[slug])).status_code, 200)
        eq_(self.client.get(reverse('personasrq.commit')).status_code, 405)
        eq_(self.client.get(reverse('personasrq.more')).status_code, 200)

    def test_commit(self):
        form_data = {
            'form-MAX_NUM_FORMS': '',
            'form-INITIAL_FORMS': str(Persona.objects.count()),
            'form-TOTAL_FORMS': str(Persona.objects.count() + 1),
        }
        personas = Persona.objects.all()

        # Create locks.
        reviewer = self.create_and_become_reviewer()
        for index_persona in enumerate(personas):
            index = index_persona[0]
            persona = index_persona[1]
            PersonaLock.objects.create(
                persona=persona, reviewer=reviewer,
                persona_lock_id=persona.persona_id,
                expiry=datetime.datetime.now() +
                       datetime.timedelta(minutes=amo.PERSONA_LOCK_EXPIRY))
            form_data['form-%s-persona' % index] = str(persona.persona_id)

        # moreinfo
        form_data['form-%s-action' % 0] = str(amo.ACTION_MOREINFO)
        form_data['form-%s-comment' % 0] = 'moreinfo'
        form_data['form-%s-reject_reason' % 0] = ''

        # flag
        form_data['form-%s-action' % 1] = str(amo.ACTION_FLAG)
        form_data['form-%s-comment' % 1] = 'flag'
        form_data['form-%s-reject_reason' % 1] = ''

        # duplicate
        form_data['form-%s-action' % 2] = str(amo.ACTION_DUPLICATE)
        form_data['form-%s-comment' % 2] = 'duplicate'
        form_data['form-%s-reject_reason' % 2] = ''

        # reject
        form_data['form-%s-action' % 3] = str(amo.ACTION_REJECT)
        form_data['form-%s-comment' % 3] = 'reject'
        form_data['form-%s-reject_reason' % 3] = '1'

        # approve
        form_data['form-%s-action' % 4] = str(amo.ACTION_APPROVE)
        form_data['form-%s-comment' % 4] = ''
        form_data['form-%s-reject_reason' % 4] = ''

        res = self.client.post(reverse('personasrq.commit'), form_data)

        eq_(res.status_code, 302)
        eq_(ActivityLog.objects.count(), 5)
        eq_(personas[0].addon.status, amo.STATUS_PENDING)
        eq_(personas[1].addon.status, amo.STATUS_PENDING)
        eq_(personas[2].addon.status, amo.STATUS_REJECTED)
        eq_(personas[3].addon.status, amo.STATUS_REJECTED)
        eq_(personas[4].addon.status, amo.STATUS_PUBLIC)

    def test_user_review_history(self):
        reviewer = self.create_and_become_reviewer()

        res = self.client.get(reverse('personasrq.history'))
        eq_(res.status_code, 200)
        doc = pq(res.content)
        eq_(doc('tbody tr').length, 0)

        persona = Persona.objects.all()[0]
        for x in range(3):
            amo.log(amo.LOG.PERSONA_REVIEW, persona, user=reviewer,
                    details={'action': amo.ACTION_APPROVE,
                             'comment': '', 'reject_reason': ''})

        res = self.client.get(reverse('personasrq.history'))
        eq_(res.status_code, 200)
        doc = pq(res.content)
        eq_(doc('tbody tr').length, 3)

    def test_single_basic(self):
        self.create_and_become_reviewer()
        res = self.client.get(reverse('personasrq.single',
                              args=[Persona.objects.all()[0].addon.slug]))
        eq_(res.status_code, 200)
        doc = pq(res.content)
        eq_(doc('.persona').length, 1)
