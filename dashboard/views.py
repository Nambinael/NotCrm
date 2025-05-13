from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count
from tasks.models import Task

@login_required
def dashboard(request):
    # Собираем данные для дашборда
    tasks_by_status = Task.objects.values('status').annotate(count=Count('id'))
    tasks_by_priority = Task.objects.values('priority').annotate(count=Count('id'))
    total_tasks = Task.objects.count()
    tasks_in_progress_by_user = Task.objects.filter(taken_in_progress_by=request.user).count()

    # Передаем данные в шаблон
    return render(request, 'dashboard/dashboard.html', {
        'tasks_by_status': tasks_by_status,
        'tasks_by_priority': tasks_by_priority,
        'total_tasks': total_tasks,
        'tasks_in_progress_by_user': tasks_in_progress_by_user,
    })