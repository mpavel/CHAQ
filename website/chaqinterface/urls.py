from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('chaqinterface.views',
    # Examples:
    # url(r'^$', 'website.views.home', name='home'),
    # url(r'^website/', include('website.foo.urls')),
    
    url(r'^$', 'index'),
    url(r'^logs/$', 'logs'),
    url(r'^ask/$', 'ask'),
)