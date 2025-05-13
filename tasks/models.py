from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from taggit.managers import TaggableManager

from projects.models import Project


def validate_deadline(value):
    if value and value < timezone.now():
        raise ValidationError("Дедлайн не может быть в прошлом.")


class Task(models.Model):
    PRIORITY_CHOICES = (
        ('LOW', 'Низкий'),
        ('MEDIUM', 'Средний'),
        ('HIGH', 'Высокий'),
    )
    STATUS_CHOICES = (
        ('OPEN', 'Открыта'),
        ('IN_PROGRESS', 'В процессе'),
        ('COMPLETED', 'Завершена'),
        ('BLOCKED', 'Заблокирована'),
    )

    name = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', verbose_name="Проект")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM', verbose_name="Приоритет")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', verbose_name="Статус")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tasks',
        verbose_name="Создатель"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    deadline_time = models.DateTimeField(
        null=True,
        blank=True,
        validators=[validate_deadline],
        verbose_name="Дедлайн"
    )
    tags = TaggableManager(blank=True, verbose_name="Теги")
    taken_in_progress_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks_in_progress',
        verbose_name="Взял в работу"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"


class TaskAssignment(models.Model):
    CREATOR = 'CREATOR'
    ASSIGNEE = 'ASSIGNEE'
    CO_ASSIGNEE = 'CO_ASSIGNEE'
    OBSERVER = 'OBSERVER'

    CHOICES_ROLE = (
        (CREATOR, 'Создатель'),
        (ASSIGNEE, 'Исполнитель'),
        (CO_ASSIGNEE, 'Соисполнитель'),
        (OBSERVER, 'Наблюдатель'),
    )

    task = models.ForeignKey(
        Task,
        related_name='assignments',
        on_delete=models.CASCADE,
        verbose_name="Задача"
    )
    user = models.ForeignKey(
        User,
        related_name='task_assignments',
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    role = models.CharField(
        max_length=20,
        choices=CHOICES_ROLE,
        verbose_name="Роль"
    )

    def __str__(self):
        return f"{self.user} - {self.get_role_display()} в {self.task}"

    class Meta:
        unique_together = ('task', 'user')
        verbose_name = "Назначение задачи"
        verbose_name_plural = "Назначения задач"


class Comment(models.Model):
    task = models.ForeignKey(
        Task,
        related_name='comments',
        on_delete=models.CASCADE,
        verbose_name="Задача"
    )
    author = models.ForeignKey(
        User,
        related_name='comments',
        on_delete=models.CASCADE,
        verbose_name="Автор"
    )
    content = models.TextField(verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Комментарий от {self.author} к {self.task}"

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"


class Attachment(models.Model):
    task = models.ForeignKey(
        Task,
        related_name='attachments',
        on_delete=models.CASCADE,
        verbose_name="Задача"
    )
    file = models.FileField(
        upload_to='task_attachments/%Y/%m/%d/',
        verbose_name="Файл"
    )
    uploaded_by = models.ForeignKey(
        User,
        related_name='attachments',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Загрузил"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    def __str__(self):
        return f"Вложение к {self.task}"

    class Meta:
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"