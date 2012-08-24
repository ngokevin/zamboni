from django.conf.urls.defaults import patterns, url

from personasrq import views


urlpatterns = patterns('',
    url('^$', views.personasrq, name='personasrq.queue'),
    url('^commit/$', views.commit, name='personasrq.commit'),
    url('^more/$', views.more, name='personasrq.more'),
)
