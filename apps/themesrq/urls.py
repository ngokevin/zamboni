from django.conf.urls.defaults import patterns, url

from themesrq import views


urlpatterns = patterns('',
    url('^$', views.themesrq, name='themesrq.themesrq')
)
