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
        return reviewer

    def get_and_check_personas(self):
        doc = pq(self.client.get(reverse('personasrq.personasrq')).content)
        if self.free_personas > amo.MAX_LOCKS:
            expected_queue_length = amo.MAX_LOCKS
        else:
            expected_queue_length = self.free_personas
        eq_(doc('.persona').length, expected_queue_length)
        self.free_personas -= expected_queue_length

    def test_one_reviewer_filled_queue(self):
        self.free_personas = self.persona_count
        reviewer = self.create_and_become_reviewer()
        self.get_and_check_personas()

    def test_multi_reviewers_filled_queue(self):
        self.free_personas = self.persona_count
        for i in range(2):
            reviewer = self.create_and_become_reviewer()
            self.get_and_check_personas()

    def test_multi_reviewers_part_queue(self):
        self.free_personas = self.persona_count
        for i in range(3):
            reviewer = self.create_and_become_reviewer()
            self.get_and_check_personas()

    def test_multi_reviewers_empty_queue(self):
        self.free_personas = self.persona_count
        for i in range(4):
            reviewer = self.create_and_become_reviewer()
            self.get_and_check_personas()
