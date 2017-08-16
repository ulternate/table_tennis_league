from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from rankings.views import RegisterView

urlpatterns = [
    url(r'', include('rankings.urls')),
    url(r'^login/$', auth_views.login, {'template_name': 'app/login.html'}, name='ranking_login'),
    url(r'^logout/$', auth_views.logout, {'next_page': '/'}, name='ranking_logout'),
    url(r'^register/$', RegisterView.as_view(), name='ranking_register'),
    url(r'^admin/', admin.site.urls),
]
