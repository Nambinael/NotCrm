from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('add/', views.ProjectCreateView.as_view(), name='project_create'),
    path('<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
]