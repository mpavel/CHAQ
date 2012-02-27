from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template
from django.contrib.auth.views import login, logout

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^$', direct_to_template, {'template': 'interface/index.html'}, name='index'),

    # routing for the chaqinterface
    url(r'^chat/', include('chaqinterface.urls')),

    url(r'logout/$', logout, name="logout"),
    url(r'login/$', login, name="login"),
    # url(r'activate/$', activate, name="activate"),
)
