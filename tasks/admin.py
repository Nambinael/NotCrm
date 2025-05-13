from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.html import format_html
from .models import Project, Task, TaskAssignment, Comment, Attachment


class TaskAssignmentInline(admin.TabularInline):
    model = TaskAssignment
    extra = 1
    autocomplete_fields = ['user']
    can_delete = True


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1
    autocomplete_fields = ['author']
    readonly_fields = ['created_at']
    can_delete = True


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 1
    autocomplete_fields = ['uploaded_by']
    readonly_fields = ['uploaded_at']
    can_delete = True


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'task_count']
    list_filter = ['created_at', 'created_by']
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def task_count(self, obj):
        return obj.tasks.count()
    task_count.short_description = 'Задач'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(
                tasks__assignments__user=request.user
            ).distinct()
        return qs


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'priority', 'status', 'created_by', 'deadline_time', 'taken_in_progress_by', 'assignment_count']
    list_filter = ['priority', 'status', 'created_at', 'project']
    search_fields = ['name', 'description']
    autocomplete_fields = ['project', 'created_by', 'taken_in_progress_by']
    inlines = [TaskAssignmentInline, CommentInline, AttachmentInline]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_select_related = ['project', 'created_by', 'taken_in_progress_by']

    def assignment_count(self, obj):
        return obj.assignments.count()
    assignment_count.short_description = 'Назначений'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(
                Q(created_by=request.user) |
                Q(assignments__user=request.user)
            ).distinct()
        return qs


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'role']
    list_filter = ['role']
    search_fields = ['task__name', 'user__username']
    autocomplete_fields = ['task', 'user']
    ordering = ['task']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(user=request.user).distinct()
        return qs


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'author', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['task__name', 'author__username', 'content']
    autocomplete_fields = ['task', 'author']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def content_preview(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    content_preview.short_description = 'Комментарий'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(
                task__assignments__user=request.user
            ).distinct()
        return qs


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['task', 'file_link', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['task__name', 'file']
    autocomplete_fields = ['task', 'uploaded_by']
    date_hierarchy = 'uploaded_at'
    ordering = ['-uploaded_at']

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">Открыть</a>', obj.file.url)
        return '-'
    file_link.short_description = 'Файл'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(
                task__assignments__user=request.user
            ).distinct()
        return qs