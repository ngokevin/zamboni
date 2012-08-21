from django.conf.urls.defaults import patterns, url

from personasrq import views


urlpatterns = patterns('',
    url('^$', views.personasrq, name='personasrq.personasrq'),
)
