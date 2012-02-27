from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('chaqinterface.views',
    # Examples:
    # url(r'^$', 'website.views.home', name='home'),
    # url(r'^website/', include('website.foo.urls')),
    
    url(r'^$', 'index', name='chaqinterface.index'),
    url(r'^logs/$', 'logs', name='chaqinterface.logs'),
    url(r'^ask/$', 'ask', name='chaqinterface.ask'),

    # static pages
    url(r'^about/$', 'about', name="chaqinterface.about"),

    # login routes
    url(r'^register/$',  'register',  name="register"),
    url(r'^logout/$', 'logout', name="logout"), 
)