from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from . import views


fleetpatterns = [
    url(r'^raw/wings/$', views.fleet_json_wings),
    url(r'^raw/members/$', views.fleet_json_members),
    url(r'^raw/$', views.fleet_json),
    url(r'^settings/$', views.fleet_settings),
    url(r'^$', views.fleet),
]


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^logout/', auth_views.logout, {'next_page': '/'}, name='logout'),
    url(r'^fleet/$', views.parse_url),
    url(r'^fleet/(?P<fleet_id>\d+)/', include(fleetpatterns)),
    url(r'^', include('social.apps.django_app.urls', namespace='social')),
    url(r'^$', views.home),
]
