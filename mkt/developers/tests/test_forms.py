# -*- coding: utf8 -*-
import json
import os
import shutil

from django import forms as django_forms
from django.conf import settings
from django.core.files.storage import default_storage as storage
from django.core.files.uploadedfile import SimpleUploadedFile

import mock
from nose.tools import eq_
from test_utils import RequestFactory

import amo
import amo.tests
from amo.tests import app_factory, version_factory
from amo.tests.test_helpers import get_image_path
from addons.models import Addon, AddonCategory, Category
from files.helpers import copyfileobj
from tags.models import Tag
from translations.models import Translation
from users.models import UserProfile

import mkt
from mkt.developers import forms
from mkt.developers.tests.test_views_edit import TestAdmin
from mkt.site.fixtures import fixture
from mkt.webapps.models import AddonExcludedRegion, IARCInfo, Webapp


class TestPreviewForm(amo.tests.TestCase):
    fixtures = ['base/addon_3615']

    def setUp(self):
        self.addon = Addon.objects.get(pk=3615)
        self.dest = os.path.join(settings.TMP_PATH, 'preview')
        if not os.path.exists(self.dest):
            os.makedirs(self.dest)

    @mock.patch('amo.models.ModelBase.update')
    def test_preview_modified(self, update_mock):
        name = 'transparent.png'
        form = forms.PreviewForm({'upload_hash': name,
                                  'position': 1})
        shutil.copyfile(get_image_path(name), os.path.join(self.dest, name))
        assert form.is_valid(), form.errors
        form.save(self.addon)
        assert update_mock.called

    def test_preview_size(self):
        name = 'non-animated.gif'
        form = forms.PreviewForm({'upload_hash': name,
                                  'position': 1})
        with storage.open(os.path.join(self.dest, name), 'wb') as f:
            copyfileobj(open(get_image_path(name)), f)
        assert form.is_valid(), form.errors
        form.save(self.addon)
        eq_(self.addon.previews.all()[0].sizes,
            {u'image': [250, 297], u'thumbnail': [180, 214]})

    def check_file_type(self, type_):
        form = forms.PreviewForm({'upload_hash': type_,
                                  'position': 1})
        assert form.is_valid(), form.errors
        form.save(self.addon)
        return self.addon.previews.all()[0].filetype

    @mock.patch('lib.video.tasks.resize_video')
    def test_preview_good_file_type(self, resize_video):
        eq_(self.check_file_type('x.video-webm'), 'video/webm')

    def test_preview_other_file_type(self):
        eq_(self.check_file_type('x'), 'image/png')

    def test_preview_bad_file_type(self):
        eq_(self.check_file_type('x.foo'), 'image/png')


class TestCategoryForm(amo.tests.WebappTestCase):
    fixtures = fixture('user_999', 'webapp_337141')

    def setUp(self):
        super(TestCategoryForm, self).setUp()
        self.user = UserProfile.objects.get(username='regularuser')
        self.app = Webapp.objects.get(pk=337141)
        self.request = RequestFactory()
        self.request.user = self.user
        self.request.groups = ()

        self.cat = Category.objects.create(type=amo.ADDON_WEBAPP)

    def _make_form(self, data=None):
        self.form = forms.CategoryForm(
            data, product=self.app, request=self.request)

    def _cat_count(self):
        return self.form.fields['categories'].queryset.count()

    def test_has_no_cats(self):
        self._make_form()
        eq_(self._cat_count(), 1)
        eq_(self.form.max_categories(), 2)

    def test_save_cats(self):
        self._make_form({'categories':
            map(str, Category.objects.filter(type=amo.ADDON_WEBAPP)
                                     .values_list('id', flat=True))})
        assert self.form.is_valid(), self.form.errors
        self.form.save()
        eq_(AddonCategory.objects.filter(addon=self.app).count(),
            Category.objects.count())
        eq_(self.form.max_categories(), 2)


class TestRegionForm(amo.tests.WebappTestCase):
    fixtures = fixture('webapp_337141')

    def setUp(self):
        super(TestRegionForm, self).setUp()
        self.request = RequestFactory()
        self.kwargs = {'product': self.app}

    def test_initial_empty(self):
        form = forms.RegionForm(data=None, **self.kwargs)
        self.assertSetEqual(form.initial['regions'],
            set(mkt.regions.ALL_REGION_IDS) -
            set(mkt.regions.SPECIAL_REGION_IDS))
        eq_(form.initial['enable_new_regions'], False)

    def test_initial_excluded_in_region(self):
        self.app.addonexcludedregion.create(region=mkt.regions.BR.id)

        # Everything except Brazil.
        regions = set(mkt.regions.ALL_REGION_IDS)
        regions.remove(mkt.regions.BR.id)
        self.assertSetEqual(self.get_app().get_region_ids(restofworld=True),
            regions)

        form = forms.RegionForm(data=None, **self.kwargs)

        # Everything except Brazil and China.
        self.assertSetEqual(form.initial['regions'],
            regions - set(mkt.regions.SPECIAL_REGION_IDS))
        eq_(form.initial['enable_new_regions'], False)

    def test_initial_excluded_in_regions_and_future_regions(self):
        regions = [mkt.regions.BR, mkt.regions.UK, mkt.regions.RESTOFWORLD]
        for region in regions:
            self.app.addonexcludedregion.create(region=region.id)

        regions = set(mkt.regions.ALL_REGION_IDS)
        regions.remove(mkt.regions.BR.id)
        regions.remove(mkt.regions.UK.id)
        regions.remove(mkt.regions.RESTOFWORLD.id)

        self.assertSetEqual(self.get_app().get_region_ids(),
            regions)

        form = forms.RegionForm(data=None, **self.kwargs)
        self.assertSetEqual(form.initial['regions'],
            regions - set(mkt.regions.SPECIAL_REGION_IDS))
        eq_(form.initial['enable_new_regions'], False)

    def test_restofworld_only(self):
        form = forms.RegionForm({'regions': [mkt.regions.RESTOFWORLD.id]},
                                **self.kwargs)
        assert form.is_valid(), form.errors

    def test_no_regions(self):
        form = forms.RegionForm({'enable_new_regions': True}, **self.kwargs)
        assert not form.is_valid(), 'Form should be invalid'
        eq_(form.errors,
            {'regions': ['You must select at least one region.']})

    def test_exclude_each_region(self):
        """Test that it's possible to exclude each region."""

        for region_id in mkt.regions.ALL_REGION_IDS:
            to_exclude = list(mkt.regions.ALL_REGION_IDS)
            to_exclude.remove(region_id)

            form = forms.RegionForm({'regions': to_exclude,
                                     'restricted': '1',
                                     'enable_new_regions': True},
                                    **self.kwargs)
            assert form.is_valid(), form.errors
            form.save()

            r_id = mkt.regions.REGIONS_CHOICES_ID_DICT[region_id]
            eq_(self.app.reload().get_region_ids(True), to_exclude,
                'Failed for %s' % r_id)

    def test_unrated_games_excluded(self):
        games = Category.objects.create(type=amo.ADDON_WEBAPP, slug='games')
        self.app.addoncategory_set.create(category=games)

        form = forms.RegionForm({'regions': mkt.regions.REGION_IDS,
                                 'restricted': '1',
                                 'enable_new_regions': True},
                                **self.kwargs)

        # Developers should still be able to save form OK, even
        # if they pass a bad region. Think of the grandfathered developers.
        assert form.is_valid(), form.errors
        form.save()

        # No matter what the developer tells us, still exclude Brazilian
        # and German games.
        form = forms.RegionForm(data=None, **self.kwargs)
        assert mkt.regions.BR.id not in form.initial['regions']
        assert mkt.regions.DE.id not in form.initial['regions']
        eq_(form.initial['enable_new_regions'], True)

    def test_unrated_games_already_excluded(self):
        regions = [x.id for x in
                   mkt.regions.ALL_REGIONS_WITH_CONTENT_RATINGS()]
        for region in regions:
            self.app.addonexcludedregion.create(region=region)

        games = Category.objects.create(type=amo.ADDON_WEBAPP, slug='games')
        self.app.addoncategory_set.create(category=games)

        form = forms.RegionForm({'regions': mkt.regions.REGION_IDS,
                                 'restricted': '1',
                                 'enable_new_regions': True},
                                **self.kwargs)

        assert form.is_valid(), form.errors
        form.save()

        form = forms.RegionForm(data=None, **self.kwargs)
        self.assertSetEqual(form.initial['regions'],
            set(mkt.regions.REGION_IDS) -
            set(mkt.regions.SPECIAL_REGION_IDS) -
            set(regions + [mkt.regions.RESTOFWORLD.id]))
        eq_(form.initial['enable_new_regions'], True)

    def test_rated_games_with_content_rating(self):
        # This game has a government content rating!
        for body in mkt.ratingsbodies.RATINGS_BODIES.keys():
            self.app.content_ratings.create(ratings_body=body, rating=0)

        games = Category.objects.create(type=amo.ADDON_WEBAPP, slug='games')
        self.app.addoncategory_set.create(category=games)

        form = forms.RegionForm({'regions': mkt.regions.ALL_REGION_IDS,
                                 'enable_new_regions': True},
                                **self.kwargs)
        assert form.is_valid(), form.errors
        form.save()

        eq_(self.app.get_region_ids(True), mkt.regions.ALL_REGION_IDS)

    def test_exclude_restofworld(self):
        form = forms.RegionForm({'regions': mkt.regions.REGION_IDS,
                                 'restricted': '1',
                                 'enable_new_regions': False}, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save()
        eq_(self.app.get_region_ids(True), mkt.regions.REGION_IDS)

    def test_reinclude_region(self):
        self.app.addonexcludedregion.create(region=mkt.regions.BR.id)

        form = forms.RegionForm({'regions': mkt.regions.ALL_REGION_IDS,
                                 'enable_new_regions': True}, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save()
        eq_(self.app.get_region_ids(True), mkt.regions.ALL_REGION_IDS)

    def test_reinclude_restofworld(self):
        self.app.addonexcludedregion.create(
                region=mkt.regions.RESTOFWORLD.id)

        form = forms.RegionForm({'regions': mkt.regions.ALL_REGION_IDS},
                                **self.kwargs)
        assert form.is_valid(), form.errors
        form.save()
        eq_(self.app.get_region_ids(True), mkt.regions.ALL_REGION_IDS)

    def test_restofworld_valid_choice_paid(self):
        self.app.update(premium_type=amo.ADDON_PREMIUM)
        form = forms.RegionForm(
            {'regions': [mkt.regions.RESTOFWORLD.id]}, **self.kwargs)
        assert form.is_valid(), form.errors

    def test_restofworld_valid_choice_free(self):
        form = forms.RegionForm(
            {'regions': [mkt.regions.RESTOFWORLD.id]}, **self.kwargs)
        assert form.is_valid(), form.errors

    def test_china_initially_excluded_if_null(self):
        self.create_flag('special-regions')
        form = forms.RegionForm(None, **self.kwargs)
        cn = mkt.regions.CN.id
        assert cn not in form.initial['regions']
        assert cn in dict(form.fields['regions'].choices).keys()

    def _test_china_excluded_if_pending_or_rejected(self):
        self.create_flag('special-regions')

        # Mark app as pending/rejected in China.
        for status in (amo.STATUS_PENDING, amo.STATUS_REJECTED):
            self.app.geodata.set_status(mkt.regions.CN, status, save=True)
            eq_(self.app.geodata.get_status(mkt.regions.CN), status)

            # Post the form.
            form = forms.RegionForm({'regions': mkt.regions.ALL_REGION_IDS,
                                     'special_regions': [mkt.regions.CN.id]},
                                    **self.kwargs)

            # China should be checked if it's pending and
            # unchecked if rejected.
            cn = mkt.regions.CN.id
            if status == amo.STATUS_PENDING:
                assert cn in form.initial['regions'], (
                    status, form.initial['regions'])
            else:
                assert cn not in form.initial['regions'], (
                    status, form.initial['regions'])
            choices = dict(form.fields['regions'].choices).keys()
            assert cn in choices, (status, choices)

            eq_(form.disabled_regions, [])
            assert form.is_valid(), form.errors
            form.save()

            # App should be unlisted in China and always pending after
            # requesting China.
            self.app = self.app.reload()
            eq_(self.app.listed_in(mkt.regions.CN), False)
            eq_(self.app.geodata.get_status(mkt.regions.CN),
                amo.STATUS_PENDING)

    def test_china_excluded_if_pending_or_rejected(self):
        self._test_china_excluded_if_pending_or_rejected()

    def test_china_already_excluded_and_pending_or_rejected(self):
        cn = mkt.regions.CN.id
        self.app.addonexcludedregion.create(region=cn)

        # If the app was already excluded in China, the checkbox should still
        # be checked if the app's been requested for approval in China now.
        self._test_china_excluded_if_pending_or_rejected()

    def test_china_excluded_if_pending_cancelled(self):
        """
        If the developer already requested to be in China,
        and a reviewer hasn't reviewed it for China yet,
        keep the region exclusion and the status as pending.

        """

        self.create_flag('special-regions')

        # Mark app as pending in China.
        status = amo.STATUS_PENDING
        self.app.geodata.set_status(mkt.regions.CN, status, save=True)
        eq_(self.app.geodata.get_status(mkt.regions.CN), status)

        # Post the form.
        form = forms.RegionForm({'regions': mkt.regions.ALL_REGION_IDS},
                                **self.kwargs)

        # China should be checked if it's pending.
        cn = mkt.regions.CN.id
        assert cn in form.initial['regions']
        assert cn in dict(form.fields['regions'].choices).keys()

        eq_(form.disabled_regions, [])
        assert form.is_valid(), form.errors
        form.save()

        # App should be unlisted in China and now null.
        self.app = self.app.reload()
        eq_(self.app.listed_in(mkt.regions.CN), False)
        eq_(self.app.geodata.get_status(mkt.regions.CN), amo.STATUS_NULL)

    def test_china_included_if_approved_but_unchecked(self):
        self.create_flag('special-regions')

        # Mark app as public in China.
        status = amo.STATUS_PUBLIC
        self.app.geodata.set_status(mkt.regions.CN, status, save=True)
        eq_(self.app.geodata.get_status(mkt.regions.CN), status)

        # Post the form.
        form = forms.RegionForm({'regions': mkt.regions.ALL_REGION_IDS},
                                **self.kwargs)

        # China should be checked if it's public.
        cn = mkt.regions.CN.id
        assert cn in form.initial['regions']
        assert cn in dict(form.fields['regions'].choices).keys()

        eq_(form.disabled_regions, [])
        assert form.is_valid(), form.errors
        form.save()

        # App should be unlisted in China and now null.
        self.app = self.app.reload()
        eq_(self.app.listed_in(mkt.regions.CN), False)
        eq_(self.app.geodata.get_status(mkt.regions.CN), amo.STATUS_NULL)

    def test_china_included_if_approved_and_checked(self):
        self.create_flag('special-regions')

        # Mark app as public in China.
        status = amo.STATUS_PUBLIC
        self.app.geodata.set_status(mkt.regions.CN, status, save=True)
        eq_(self.app.geodata.get_status(mkt.regions.CN), status)

        # Post the form.
        form = forms.RegionForm({'regions': mkt.regions.ALL_REGION_IDS,
                                 'special_regions': [mkt.regions.CN.id]},
                                **self.kwargs)
        eq_(form.disabled_regions, [])
        assert form.is_valid(), form.errors
        form.save()

        # App should still be listed in China and still public.
        self.app = self.app.reload()
        eq_(self.app.listed_in(mkt.regions.CN), True)
        eq_(self.app.geodata.get_status(mkt.regions.CN), status)


class TestNewManifestForm(amo.tests.TestCase):

    @mock.patch('mkt.developers.forms.verify_app_domain')
    def test_normal_validator(self, _verify_app_domain):
        form = forms.NewManifestForm({'manifest': 'http://omg.org/yes.webapp'},
            is_standalone=False)
        assert form.is_valid()
        assert _verify_app_domain.called

    @mock.patch('mkt.developers.forms.verify_app_domain')
    def test_standalone_validator(self, _verify_app_domain):
        form = forms.NewManifestForm({'manifest': 'http://omg.org/yes.webapp'},
            is_standalone=True)
        assert form.is_valid()
        assert not _verify_app_domain.called


class TestPackagedAppForm(amo.tests.AMOPaths, amo.tests.WebappTestCase):

    def setUp(self):
        super(TestPackagedAppForm, self).setUp()
        path = self.packaged_app_path('mozball.zip')
        self.files = {'upload': SimpleUploadedFile('mozball.zip',
                                                   open(path).read())}

    def test_not_there(self):
        form = forms.NewPackagedAppForm({}, {})
        assert not form.is_valid()
        eq_(form.errors['upload'], [u'This field is required.'])
        eq_(form.file_upload, None)

    def test_right_size(self):
        form = forms.NewPackagedAppForm({}, self.files)
        assert form.is_valid(), form.errors
        assert form.file_upload

    def test_too_big(self):
        form = forms.NewPackagedAppForm({}, self.files, max_size=5)
        assert not form.is_valid()
        validation = json.loads(form.file_upload.validation)
        assert 'messages' in validation, 'No messages in validation.'
        eq_(validation['messages'][0]['message'],
            u'Packaged app too large for submission. Packages must be smaller '
            u'than 5 bytes.')

    def test_origin_exists(self):
        self.app.update(app_domain='app://hy.fr')
        form = forms.NewPackagedAppForm({}, self.files)
        assert not form.is_valid()
        validation = json.loads(form.file_upload.validation)
        eq_(validation['messages'][0]['message'],
            'An app already exists on this domain; only one app per domain is '
            'allowed.')


class TestTransactionFilterForm(amo.tests.TestCase):

    def setUp(self):
        (app_factory(), app_factory())
        # Need queryset to initialize form.
        self.apps = Webapp.objects.all()
        self.data = {
            'app': self.apps[0].id,
            'transaction_type': 1,
            'transaction_id': 1,
            'date_from_day': '1',
            'date_from_month': '1',
            'date_from_year': '2012',
            'date_to_day': '1',
            'date_to_month': '1',
            'date_to_year': '2013',
        }

    def test_basic(self):
        """Test the form doesn't crap out."""
        form = forms.TransactionFilterForm(self.data, apps=self.apps)
        assert form.is_valid(), form.errors

    def test_app_choices(self):
        """Test app choices."""
        form = forms.TransactionFilterForm(self.data, apps=self.apps)
        for app in self.apps:
            assertion = (app.id, app.name) in form.fields['app'].choices
            assert assertion, '(%s, %s) not in choices' % (app.id, app.name)


class TestAppFormBasic(amo.tests.TestCase):

    def setUp(self):
        self.data = {
            'slug': 'yolo',
            'manifest_url': 'https://omg.org/yes.webapp',
            'description': 'You Only Live Once'
        }
        self.request = mock.Mock()
        self.request.groups = ()

    def post(self):
        self.form = forms.AppFormBasic(
            self.data, instance=Webapp.objects.create(app_slug='yolo'),
            request=self.request)

    def test_success(self):
        self.post()
        eq_(self.form.is_valid(), True, self.form.errors)
        eq_(self.form.errors, {})

    def test_slug_invalid(self):
        Webapp.objects.create(app_slug='yolo')
        self.post()
        eq_(self.form.is_valid(), False)
        eq_(self.form.errors,
            {'slug': ['This slug is already in use. Please choose another.']})


class TestAppVersionForm(amo.tests.TestCase):

    def setUp(self):
        self.request = mock.Mock()
        self.app = app_factory(make_public=amo.PUBLIC_IMMEDIATELY,
                               version_kw={'version': '1.0',
                                           'created': self.days_ago(5)})
        version_factory(addon=self.app, version='2.0',
                        file_kw=dict(status=amo.STATUS_PENDING))
        self.app.reload()

    def get_form(self, version, data=None):
        return forms.AppVersionForm(data, instance=version)

    def test_get_publish(self):
        form = self.get_form(self.app.latest_version)
        eq_(form.fields['publish_immediately'].initial, True)

        self.app.update(make_public=amo.PUBLIC_WAIT)
        self.app.reload()
        form = self.get_form(self.app.latest_version)
        eq_(form.fields['publish_immediately'].initial, False)

    def test_post_publish(self):
        # Using the latest_version, which is pending.
        form = self.get_form(self.app.latest_version,
                             data={'publish_immediately': True})
        eq_(form.is_valid(), True)
        form.save()
        self.app.reload()
        eq_(self.app.make_public, amo.PUBLIC_IMMEDIATELY)

        form = self.get_form(self.app.latest_version,
                             data={'publish_immediately': False})
        eq_(form.is_valid(), True)
        form.save()
        self.app.reload()
        eq_(self.app.make_public, amo.PUBLIC_WAIT)

    def test_post_publish_not_pending(self):
        # Using the current_version, which is public.
        form = self.get_form(self.app.current_version,
                             data={'publish_immediately': False})
        eq_(form.is_valid(), True)
        form.save()
        self.app.reload()
        eq_(self.app.make_public, amo.PUBLIC_IMMEDIATELY)


class TestAdminSettingsForm(TestAdmin):

    def setUp(self):
        super(TestAdminSettingsForm, self).setUp()
        self.data = {'position': 1}
        self.user = UserProfile.objects.get(username='admin')
        self.request = RequestFactory()
        self.request.user = self.user
        self.request.groups = ()
        self.kwargs = {'instance': self.webapp, 'request': self.request}
        self.create_switch('iarc')

    @mock.patch('mkt.developers.forms.index_webapps.delay')
    def test_reindexed(self, index_webapps_mock):
        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save(self.webapp)
        index_webapps_mock.assert_called_with([self.webapp.id])

    def test_reinclude_rated_games(self):
        """
        Adding a content rating for a game in a region should remove the
        regional exclusion for that region.
        """
        # List it in the Games category.
        cat = Category.objects.create(type=amo.ADDON_WEBAPP, slug='games')
        self.webapp.addoncategory_set.create(category=cat)

        self.log_in_with('Apps:Configure')

        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save(self.webapp)

        excluded_regions = [
            x.id for x in mkt.regions.ALL_REGIONS_WITH_CONTENT_RATINGS()
        ]

        # After the form was saved, it should be excluded in Brazil.
        self.assertSetEqual(
            self.webapp.addonexcludedregion.values_list('region', flat=True),
            excluded_regions)

        # Add Brazil content rating.
        rb_br = mkt.regions.BR.ratingsbody
        br_0_idx = mkt.ratingsbodies.ALL_RATINGS().index(rb_br.ratings[0])
        self.data['app_ratings'] = [br_0_idx]

        # Post the form again.
        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save(self.webapp)

        # Notice the Brazilian region exclusion is now gone.
        excluded_regions.remove(mkt.regions.BR.id)
        eq_(len(self.webapp.content_ratings_in(region=mkt.regions.DE)), 0)
        eq_(len(self.webapp.content_ratings_in(region=mkt.regions.BR)), 1)

        self.assertSetEqual(
            self.webapp.addonexcludedregion.values_list('region', flat=True),
            excluded_regions)

    def test_exclude_unrated_games_when_removing_content_rating(self):
        """
        Removing a content rating for a game in Brazil should exclude that
        game in Brazil only.
        """
        self.log_in_with('Apps:Configure')
        rb_br = mkt.regions.BR.ratingsbody
        self.webapp.content_ratings.create(ratings_body=rb_br.id,
                                           rating=rb_br.ratings[0].id)

        rb_de = mkt.regions.DE.ratingsbody
        self.webapp.content_ratings.create(ratings_body=rb_de.id,
                                           rating=rb_de.ratings[0].id)

        games = Category.objects.create(type=amo.ADDON_WEBAPP, slug='games')
        AddonCategory.objects.create(addon=self.webapp, category=games)

        # Remove Brazil but keep Germany.
        de_0_idx = mkt.ratingsbodies.ALL_RATINGS().index(rb_de.ratings[0])
        self.data['app_ratings'] = [de_0_idx]

        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save(self.webapp)

        regions = self.webapp.get_region_ids()
        assert mkt.regions.BR.id not in regions
        assert mkt.regions.DE.id in regions

    def test_exclude_unrated_games_with_waffle(self):
        """
        Removing a content rating for a game in Brazil should exclude that
        game in Brazil only. Include all ratings bodies in the form choices.
        """
        self.create_switch('iarc')
        self.log_in_with('Apps:Configure')

        rb_br = mkt.regions.BR.ratingsbody
        self.webapp.content_ratings.create(ratings_body=rb_br.id,
                                          rating=rb_br.ratings[0].id)

        rb_de = mkt.regions.DE.ratingsbody
        self.webapp.content_ratings.create(ratings_body=rb_de.id,
                                           rating=rb_de.ratings[0].id)

        games = Category.objects.create(type=amo.ADDON_WEBAPP, slug='games')
        AddonCategory.objects.create(addon=self.webapp, category=games)

        # Remove Brazil but keep Germany.
        de_0_idx = mkt.ratingsbodies.ALL_RATINGS().index(rb_de.ratings[0])
        self.data['app_ratings'] = [de_0_idx]

        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save(self.webapp)

        regions = self.webapp.get_region_ids()
        assert mkt.regions.BR.id not in regions
        assert mkt.regions.DE.id in regions

    def test_update_content_rating(self):
        """
        Test changing the content rating of a rating body to a different
        rating.
        """
        self.create_switch('iarc')
        self.log_in_with('Apps:Configure')

        self.webapp.set_content_ratings({
            mkt.ratingsbodies.CLASSIND: mkt.ratingsbodies.CLASSIND_L
        })

        # Change CLASSIND rating from L to 18.
        classind_18_idx = mkt.ratingsbodies.ALL_RATINGS().index(
            mkt.ratingsbodies.CLASSIND_18)
        self.data['app_ratings'] = [classind_18_idx]

        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save(self.webapp)

        eq_(
            self.webapp.content_ratings.get(
                ratings_body=mkt.ratingsbodies.CLASSIND.id).rating,
            mkt.ratingsbodies.CLASSIND_18.id)

    def test_adding_tags(self):
        self.data.update({'tags': 'tag one, tag two'})
        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save(self.webapp)

        eq_(self.webapp.tags.count(), 2)
        self.assertSetEqual(
            self.webapp.tags.values_list('tag_text', flat=True),
            ['tag one', 'tag two'])

    def test_removing_tags(self):
        Tag(tag_text='tag one').save_tag(self.webapp)
        eq_(self.webapp.tags.count(), 1)

        self.data.update({'tags': 'tag two, tag three'})
        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save(self.webapp)

        eq_(self.webapp.tags.count(), 2)
        self.assertSetEqual(
            self.webapp.tags.values_list('tag_text', flat=True),
            ['tag two', 'tag three'])

    def test_banner_message(self):
        self.data.update({
            'banner_message_en-us': u'Oh Hai.',
            'banner_message_es': u'¿Dónde está la biblioteca?',
        })
        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert form.is_valid(), form.errors
        form.save(self.webapp)

        geodata = self.webapp.geodata.reload()
        trans_id = geodata.banner_message_id
        eq_(geodata.banner_message, self.data['banner_message_en-us'])
        eq_(unicode(Translation.objects.get(id=trans_id, locale='es')),
            self.data['banner_message_es'])
        eq_(unicode(Translation.objects.get(id=trans_id, locale='en-us')),
           self.data['banner_message_en-us'])

    def test_banner_regions_garbage(self):
        self.data.update({
            'banner_regions': ['LOL']
        })
        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert not form.is_valid(), form.errors

    def test_banner_regions_valid(self):  # Use strings
        self.data.update({
            'banner_regions': [unicode(mkt.regions.BR.id),
                               mkt.regions.SPAIN.id]
        })
        self.webapp.geodata.update(banner_regions=[mkt.regions.RS.id])
        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        eq_(form.initial['banner_regions'], [mkt.regions.RS.id])
        assert form.is_valid(), form.errors
        eq_(form.cleaned_data['banner_regions'], [mkt.regions.BR.id,
                                                  mkt.regions.SPAIN.id])
        form.save(self.webapp)
        geodata = self.webapp.geodata.reload()
        eq_(geodata.banner_regions, [mkt.regions.BR.id, mkt.regions.SPAIN.id])

    def test_banner_regions_initial(self):
        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        eq_(self.webapp.geodata.banner_regions, None)
        eq_(form.initial['banner_regions'], [])

        self.webapp.geodata.update(banner_regions=[])
        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        eq_(form.initial['banner_regions'], [])

    def test_banner_regions_disabled(self):
        self.data.update({
            'banner_regions': [mkt.regions.BR.id]
        })
        AddonExcludedRegion.objects.create(addon=self.webapp,
                                           region=mkt.regions.BR.id)
        form = forms.AdminSettingsForm(self.data, **self.kwargs)
        assert not form.is_valid(), form.errors
        assert 'banner_regions' in form.errors


class TestIARCGetAppInfoForm(amo.tests.WebappTestCase):

    def test_good(self):
        with self.assertRaises(IARCInfo.DoesNotExist):
            self.app.iarc_info

        self.app.addonexcludedregion.create(region=mkt.regions.BR.id,
                                            is_iarc_excluded=True)

        form = forms.IARCGetAppInfoForm({'submission_id': 1,
                                         'security_code': 'a'})
        assert form.is_valid(), form.errors
        form.save(self.app)

        iarc_info = self.app.iarc_info
        eq_(iarc_info.submission_id, 1)
        eq_(iarc_info.security_code, 'a')

        assert not self.app.addonexcludedregion.exists()

    def test_allow_subm(self):
        form = forms.IARCGetAppInfoForm({'submission_id': 'subm-1231',
                                         'security_code': 'a'})
        assert form.is_valid(), form.errors
        form.save(self.app)

        iarc_info = self.app.iarc_info
        eq_(iarc_info.submission_id, 1231)
        eq_(iarc_info.security_code, 'a')

    def test_bad_submission_id(self):
        form = forms.IARCGetAppInfoForm({'submission_id': 'subwayeatfresh-133',
                                         'security_code': 'jksubwaysux'})
        assert not form.is_valid()

    def test_incomplete(self):
        form = forms.IARCGetAppInfoForm({'submission_id': 1})
        assert not form.is_valid(), 'Form was expected to be invalid.'

    @mock.patch('lib.iarc.utils.IARC_XML_Parser.parse_string')
    def test_rating_not_found(self, _mock):
        _mock.return_value = {'rows': [
            {'ActionStatus': 'No records found. Please try another criteria.'}
        ]}
        form = forms.IARCGetAppInfoForm({'submission_id': 1,
                                         'security_code': 'a'})
        assert form.is_valid(), form.errors
        with self.assertRaises(django_forms.ValidationError):
            form.save('app')  # Just pass string to avoid making a Webapp obj.
