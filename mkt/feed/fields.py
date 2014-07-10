from rest_framework import serializers

from mkt.search.serializers import ESAppSerializer
from mkt.webapps.serializers import AppSerializer


class FeedCollectionMembershipField(serializers.RelatedField):
    """
    Serializer field to be used with M2M model fields to Webapps, replacing
    instances of the Membership instances with serializations of the Webapps
    that they correspond to.
    """
    def to_native(self, qs, use_es=False):
        return AppSerializer(qs, context=self.context).data


class AppESField(serializers.Field):
    """
    Deserialize an app id using ESAppSerializer.

    (DRF data) -- app ID
    self.context['app_map'] -- mapping from app ID to app ES object
    """
    def __init__(self, *args, **kwargs):
        self.many = kwargs.pop('many', False)
        super(AppESField, self).__init__(*args, **kwargs)

    def to_native(self, app_ids):
        """App ID to serialized app."""
        if self.many:
            return ESAppSerializer(
                [self.context['app_map'][app_id] for app_id in app_ids],
                many=True)
        else:
            # App IDs here is actually only one app ID.
            return ESAppSerializer(self.context['app_map'][app_ids],
                                   context=self.context).data

    def from_native(self, data):
        if self.many:
            return [app['id'] for app in data['apps']]
        else:
            return data['id']
