from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from projects.forms import ProjectForm
from .forms import AddTaskForm, CommentForm, AttachmentForm
from .models import Task, TaskAssignment, Project
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Task, TaskAssignment, Comment, Attachment, Project
from .forms import AddTaskForm, TaskForm, CommentForm, AttachmentForm
from django.contrib.auth.models import User

@login_required
def tasks_list(request):
    tasks = Task.objects.filter(
        Q(created_by=request.user) |  # Task Creator
        Q(assignments__user=request.user)  # Assignee, Co-Assignee, Observer
    ).select_related('project', 'created_by', 'taken_in_progress_by').prefetch_related('assignments', 'tags').distinct()

    # Add role-based flags to each task
    tasks_with_permissions = []
    for task in tasks:
        can_take = (
            task.status == 'OPEN' and
            TaskAssignment.objects.filter(task=task, user=request.user, role='ASSIGNEE').exists()
        )
        can_edit = (
            task.created_by == request.user or
            TaskAssignment.objects.filter(task=task, user=request.user, role__in=['ASSIGNEE', 'CREATOR']).exists()
        )
        tasks_with_permissions.append({
            'task': task,
            'can_take': can_take,
            'can_edit': can_edit
        })

    # Get projects for grouping in template
    projects = Project.objects.filter(
        tasks__assignments__user=request.user
    ).distinct()

    print(f"User: {request.user}, Tasks: {[t['task'] for t in tasks_with_permissions]}")
    return render(request, 'tasks/tasks_list.html', {
        'tasks_with_permissions': tasks_with_permissions,
        'projects': projects
    })

@login_required
def tasks_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)

    # Check if user has access based on role
    has_access = (
        task.created_by == request.user or
        TaskAssignment.objects.filter(task=task, user=request.user).exists()
    )

    if not has_access:
        messages.error(request, 'У вас нет прав для просмотра этой задачи')
        return redirect('tasks_list')

    # Check if user can comment or attach files
    can_comment_or_attach = (
        task.created_by == request.user or
        TaskAssignment.objects.filter(task=task, user=request.user, role__in=['ASSIGNEE', 'CO_ASSIGNEE', 'CREATOR']).exists()
    )

    # Permission flags
    can_take = (
        task.status == 'OPEN' and
        TaskAssignment.objects.filter(task=task, user=request.user, role='ASSIGNEE').exists()
    )
    can_edit = (
        task.created_by == request.user or
        TaskAssignment.objects.filter(task=task, user=request.user, role__in=['ASSIGNEE', 'CREATOR']).exists()
    )
    can_delete = (
        task.created_by == request.user
    )

    assignments = task.assignments.filter(role__in=['ASSIGNEE', 'CO_ASSIGNEE', 'OBSERVER'])
    comments = task.comments.all().order_by('-created_at')
    attachments = task.attachments.all()

    if request.method == 'POST' and can_comment_or_attach:
        if 'delete_attachment' in request.POST:
            attachment_id = request.POST.get('delete_attachment')
            attachment = get_object_or_404(Attachment, id=attachment_id, task=task)
            if attachment.uploaded_by == request.user or task.created_by == request.user:
                attachment.delete()
                messages.success(request, 'Вложение удалено')
            else:
                messages.error(request, 'У вас нет прав для удаления этого вложения')
            return redirect('tasks_detail', pk=task.pk)
        if 'comment_submit' in request.POST:
            comment_form = CommentForm(request.POST, user=request.user, task=task)
            if comment_form.is_valid():
                comment_form.save()
                messages.success(request, 'Комментарий добавлен')
                return redirect('tasks_detail', pk=task.pk)
        elif 'attachment_submit' in request.POST:
            attachment_form = AttachmentForm(request.POST, request.FILES)
            if attachment_form.is_valid():
                attachment = attachment_form.save(commit=False)
                attachment.task = task
                attachment.uploaded_by = request.user
                attachment.save()
                messages.success(request, 'Файл прикреплен')
                return redirect('tasks_detail', pk=task.pk)
    else:
        comment_form = CommentForm() if can_comment_or_attach else None
        attachment_form = AttachmentForm() if can_comment_or_attach else None

    print(f"User: {request.user}, Task: {task}, Assignments: {list(assignments)}, Comments: {list(comments)}, Attachments: {list(attachments)}")
    return render(request, 'tasks/tasks_detail.html', {
        'task': task,
        'assignments': assignments,
        'comments': comments,
        'attachments': attachments,
        'comment_form': comment_form,
        'attachment_form': attachment_form,
        'can_take': can_take,
        'can_edit': can_edit,
        'can_delete': can_delete
    })

@login_required
def tasks_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if task.created_by == request.user:
        task.delete()
        messages.success(request, 'Задача удалена')
    else:
        messages.error(request, 'У вас нет прав для удаления этой задачи')
    return redirect('tasks_list')

@login_required
def tasks_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not (
        task.created_by == request.user or
        TaskAssignment.objects.filter(task=task, user=request.user, role__in=['ASSIGNEE', 'CREATOR']).exists()
    ):
        messages.error(request, 'У вас нет прав для редактирования этой задачи')
        return redirect('tasks_list')

    if request.method == 'POST':
        form = AddTaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Задача успешно отредактирована')
            return redirect('tasks_list')
    else:
        form = AddTaskForm(instance=task, user=request.user)

    # Все пользователи для назначения
    all_users = User.objects.all()
    # Текущие назначения
    current_assignments = task.assignments.exclude(role='CREATOR').values('user_id', 'role')

    return render(request, 'tasks/tasks_edit.html', {
        'form': form,
        'task': task,
        'all_users': all_users,
        'roles': TaskAssignment.CHOICES_ROLE,
        'current_assignments': list(current_assignments)
    })

@login_required
def add_task(request):
    if request.method == 'POST':
        form = AddTaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            form.save_m2m()
            messages.success(request, 'Задача добавлена')
            return redirect('tasks_list')
    else:
        form = AddTaskForm(user=request.user)

    # Все пользователи для назначения
    all_users = User.objects.all()

    return render(request, 'tasks/add_task.html', {
        'form': form,
        'all_users': all_users,
        'roles': TaskAssignment.CHOICES_ROLE
    })

@login_required
def take_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if (
        TaskAssignment.objects.filter(task=task, user=request.user, role='ASSIGNEE').exists() and
        task.status == 'OPEN'
    ):
        task.taken_in_progress_by = request.user
        task.status = 'IN_PROGRESS'
        task.save()
        messages.success(request, 'Задача взята в работу')
    else:
        messages.error(request, 'Вы не можете взять эту задачу')
    return redirect('tasks_detail', pk=task.id)

