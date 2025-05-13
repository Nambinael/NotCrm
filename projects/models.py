from django.db import models
from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from taggit.managers import TaggableManager


class Project(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    created_by = models.ForeignKey(
        User,
        related_name='projects',
        on_delete=models.CASCADE,
        verbose_name="Создатель"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"
