from django.urls import path
from django.conf.urls.static import static
from NotCrm import settings
from . import views

urlpatterns =[
    path('', views.tasks_list, name='tasks_list'),
    path('add-task/', views.add_task, name='add_task'),
    path('<int:pk>/', views.tasks_detail, name='tasks_detail'),
    path('<int:pk>/delete/', views.tasks_delete, name='tasks_delete'),
    path('<int:pk>/edit/', views.tasks_edit, name='tasks_edit'),
    path('<int:task_id>/take/', views.take_task, name='take_task'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
