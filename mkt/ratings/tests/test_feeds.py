# -*- coding: utf-8 -*-
import mock

from mkt.ratings.feeds import RatingsRss
from reviews.tests.test_feeds import FeedTest
from translations.models import Translation


class RatingsFeedTest(FeedTest):

    def setUp(self):
        self.feed = RatingsRss()
        self.u = u'Ελληνικά'
        self.wut = Translation(localized_string=self.u, locale='el')

        self.addon = mock.Mock()
        self.addon.name = self.wut

        self.user = mock.Mock()
        self.user.name = self.u

        self.review = mock.Mock()
        self.review.title = self.wut
        self.review.rating = 4
        self.review.user = self.user
