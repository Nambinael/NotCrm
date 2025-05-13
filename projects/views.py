from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from tasks.models import Project  # Или projects.models.Project
from .forms import ProjectForm

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(
            Q(created_by=user) |
            Q(tasks__assignments__user=user)
        ).distinct()

class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(
            Q(created_by=user) |
            Q(tasks__assignments__user=user)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks'] = self.object.tasks.all()
        return context

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('projects:project_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Проект успешно создан!")
        return super().form_valid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('projects:project_list')

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(created_by=user)

    def form_valid(self, form):
        messages.success(self.request, "Проект успешно обновлен!")
        return super().form_valid(form)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'projects/project_confirm_delete.html'
    success_url = reverse_lazy('projects:project_list')

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(created_by=user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Проект успешно удален!")
        return super().delete(request, *args, **kwargs)