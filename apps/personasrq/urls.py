from django.conf.urls.defaults import patterns, url

from personasrq import views


urlpatterns = patterns('',
    url('^$', views.queue, name='personasrq.queue'),
    url('^commit/$', views.commit, name='personasrq.commit'),
    url('^more/$', views.more, name='personasrq.more'),
    url('^history/$', views.history, name='personasrq.history'),
    url('^(?P<slug>[^ /]+)/$', views.single, name='personasrq.single'),
)
