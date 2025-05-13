from django.conf.urls.static import static

from NotCrm import settings
from dashboard import urls
from django.contrib import admin
from django.urls import path, include
from core.views import index
from userprofile.views import signup
from django.contrib.auth import views

urlpatterns = [
    path('', index, name='index'),
    path('admin/', admin.site.urls),
    path('signup/', signup, name='signup'),
    path('log-in/', views.LoginView.as_view(template_name="userprofile/login.html"), name="login"),
    path ('log-out/', views.LogoutView.as_view(), name="logout"),
    path ('dashboard/tasks/', include('tasks.urls')),
    path ('dashboard/', include('dashboard.urls')),
    path('dashboard/projects/', include('projects.urls')),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
