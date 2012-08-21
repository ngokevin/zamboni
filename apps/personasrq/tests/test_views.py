import datetime
import time

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from nose.tools import eq_
from pyquery import PyQuery as pq

from access.models import Group, GroupUser
from addons.models import Addon, Persona
import amo
import amo.tests
from amo.tests import addon_factory
from personasrq.models import PersonaLock
from users.models import UserProfile


class PersonaReviewQueueTest(amo.tests.TestCase):
    fixtures = ['base/users', 'base/admin']

    def setUp(self):
        amo.MAX_LOCKS = 2
        self.persona_count = 5
        for x in range(self.persona_count):
            addon_factory(type=amo.ADDON_PERSONA, status=amo.STATUS_PENDING)

    def create_and_become_reviewer(self):
        pw = ('sha512$7b5436061f8c0902088c292c057be69fdb17312e2f71607c9c51641f'
              '5d876522$08d1d370d89e2ae92755fd03464a7276ca607c431d04a52d659f7a'
              '184f3f9918073637d82fc88981c7099c7c46a1137b9fdeb675304eb98801038'
              '905a9ee0600')

        username = 'reviewer%s' % User.objects.count()
        email = username + '@mozilla.com'
        reviewer = User.objects.create(username=email, email=email,
                                       is_active=True, is_superuser=True,
                                       is_staff=True, password=pw)
        user = UserProfile.objects.create(user=reviewer, email=email,
                                          username=username, password=pw)
        user.set_password('password')
        GroupUser.objects.create(group_id=50002, user=user)

        self.client.login(username=email, password='password')
        return user

    def get_personas(self):
        # It doesn't mean what you think it means.
        return self.client.get(reverse('personasrq.personasrq')).content

    def get_and_check_personas(self, reviewer):
        doc = pq(self.get_personas())
        if self.free_personas > amo.MAX_LOCKS:
            expected_queue_length = amo.MAX_LOCKS
        else:
            expected_queue_length = self.free_personas
        self.free_personas -= expected_queue_length

        eq_(doc('.persona').length, expected_queue_length)
        eq_(PersonaLock.objects.filter(reviewer=reviewer).count(),
            expected_queue_length)

    def test_basic_queue(self):
        # Have 5 reviewers take personas from the pool and into the queue.
        self.free_personas = self.persona_count
        for i in range(5):
            reviewer = self.create_and_become_reviewer()
            self.get_and_check_personas(reviewer)

    def test_expiry(self):
        # Test that reviewers who want personas from an empty pool can steal
        # checked-out personas from other reviewers whose locks have expired.
        PersonaLock.objects.all().delete()

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
        self.client.get(reverse('personasrq.personasrq'))
        eq_(PersonaLock.objects.filter(reviewer=reviewer)[0].expiry > expiry,
            True)
