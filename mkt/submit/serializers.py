import json

from django.core.urlresolvers import reverse

from rest_framework import serializers

import mkt
from mkt.access import acl
from mkt.api.fields import ReverseChoiceField
from mkt.files.models import FileUpload
from mkt.webapps.models import Preview, Webapp


class AppStatusSerializer(serializers.ModelSerializer):
    status = ReverseChoiceField(choices_dict=mkt.STATUS_CHOICES_API,
                                required=False)
    disabled_by_user = serializers.BooleanField(required=False)

    allowed_statuses = {
        # You can push to the pending queue.
        mkt.STATUS_NULL: [mkt.STATUS_PENDING],
        # Approved apps can be public or unlisted.
        mkt.STATUS_APPROVED: [mkt.STATUS_PUBLIC, mkt.STATUS_UNLISTED],
        # Public apps can choose to become private (APPROVED) or unlisted.
        mkt.STATUS_PUBLIC: [mkt.STATUS_APPROVED, mkt.STATUS_UNLISTED],
        # Unlisted apps can become private or public.
        mkt.STATUS_UNLISTED: [mkt.STATUS_APPROVED, mkt.STATUS_PUBLIC],
    }

    class Meta:
        model = Webapp
        fields = ('status', 'disabled_by_user')

    def validate_status(self, attrs, source):
        if not self.object:
            raise serializers.ValidationError(u'Error getting app.')

        if source not in attrs:
            return attrs

        # Admins can change any status, skip validation for them.
        # It's dangerous, but with great powers comes great responsability.
        if ('request' in self.context and self.context['request'].user and
                acl.action_allowed(self.context['request'], 'Admin', '%')):
            return attrs

        # An incomplete app's status can not be changed.
        if not self.object.is_fully_complete():
            raise serializers.ValidationError(
                self.object.completion_error_msgs())

        # Only some specific changes are possible depending on the app current
        # status.
        if (self.object.status not in self.allowed_statuses or
                attrs[source] not in
                self.allowed_statuses[self.object.status]):
            raise serializers.ValidationError(
                'App status can not be changed to the one you specified.')

        return attrs


class FileUploadSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='pk', read_only=True)
    processed = serializers.BooleanField(read_only=True)

    class Meta:
        model = FileUpload
        fields = ('id', 'processed', 'valid', 'validation')

    def transform_validation(self, obj, value):
        return json.loads(value) if value else value


class PreviewSerializer(serializers.ModelSerializer):
    filetype = serializers.CharField()
    id = serializers.IntegerField(source='pk')
    image_url = serializers.CharField(read_only=True)
    resource_uri = serializers.SerializerMethodField('get_resource_uri')
    thumbnail_url = serializers.CharField(read_only=True)

    class Meta:
        model = Preview
        fields = ['filetype', 'image_url', 'id', 'resource_uri',
                  'thumbnail_url']

    def get_resource_uri(self, obj):
        if obj:
            return reverse('app-preview-detail', kwargs={'pk': obj})


class SimplePreviewSerializer(PreviewSerializer):
    class Meta(PreviewSerializer.Meta):
        fields = ['filetype', 'id', 'image_url', 'thumbnail_url']


class FeedPreviewESSerializer(PreviewSerializer):
    """
    Preview serializer for feed where we want to know the image orientation to
    scale feed app tiles appropriately.
    """
    id = serializers.IntegerField(source='id')
    image_size = serializers.Field(source='image_size')
    thumbnail_size = serializers.Field(source='thumbnail_size')

    class Meta(PreviewSerializer.Meta):
        fields = ['id', 'image_size', 'image_url', 'thumbnail_size',
                  'thumbnail_url']
