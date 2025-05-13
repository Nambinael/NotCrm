import json
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Task, TaskAssignment, Comment, Attachment, Project
from django.contrib.auth.models import User


class AddTaskForm(forms.ModelForm):
    assignments = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        model = Task
        fields = ['name', 'description', 'project', 'priority', 'status', 'deadline_time', 'tags', 'taken_in_progress_by']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'w-full border-gray-300 rounded-lg'}),
            'priority': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg'}),
            'status': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg'}),
            'deadline_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full border-gray-300 rounded-lg'}),
            'project': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg'}),
            'tags': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg'}),
            'taken_in_progress_by': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg'}),
            'name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Фильтруем проекты, где пользователь является создателем или имеет роль в задачах
            projects = Project.objects.filter(
                Q(created_by=user) |
                Q(tasks__assignments__user=user)
            ).distinct()
            self.fields['project'].queryset = projects
        # Поле taken_in_progress_by включает всех пользователей
        self.fields['taken_in_progress_by'].queryset = User.objects.all()
        self.fields['taken_in_progress_by'].required = False

    def clean_assignments(self):
        assignments_data = self.cleaned_data.get('assignments')
        if not assignments_data:
            return []
        try:
            assignments = json.loads(assignments_data)
            for assignment in assignments:
                if not isinstance(assignment, dict) or 'user_id' not in assignment or 'role' not in assignment:
                    raise forms.ValidationError("Неверный формат данных назначений")
                if assignment['role'] not in dict(TaskAssignment.CHOICES_ROLE).keys():
                    raise forms.ValidationError(f"Недопустимая роль: {assignment['role']}")
                if assignment['role'] == 'CREATOR':
                    raise forms.ValidationError("Роль 'CREATOR' назначается автоматически")
            return assignments
        except json.JSONDecodeError:
            raise forms.ValidationError("Неверный формат данных назначений")

    def save(self, commit=True):
        task = super().save(commit=False)
        if commit:
            task.save()
            self.save_m2m()  # Сохраняем теги
            # Удаляем все назначения, кроме CREATOR
            TaskAssignment.objects.filter(task=task).exclude(role='CREATOR').delete()
            # Создаем новые назначения
            assignments = self.cleaned_data.get('assignments', [])
            for assignment in assignments:
                TaskAssignment.objects.create(
                    task=task,
                    user_id=assignment['user_id'],
                    role=assignment['role']
                )
            # Автоматически добавляем роль CREATOR для created_by, если еще не существует
            if not TaskAssignment.objects.filter(task=task, role='CREATOR').exists():
                TaskAssignment.objects.create(
                    task=task,
                    user=task.created_by,
                    role='CREATOR'
                )
        return task



class TaskForm(AddTaskForm):
    class Meta(AddTaskForm.Meta):
        fields = ['name', 'description', 'project', 'priority', 'status', 'deadline_time', 'tags', 'taken_in_progress_by']


class TaskAssignmentForm(forms.ModelForm):
    class Meta:
        model = TaskAssignment
        fields = ['user', 'role']
        widgets = {
            'user': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg'}),
            'role': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full border-gray-300 rounded-lg',
                'placeholder': 'Введите ваш комментарий...',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.task = kwargs.pop('task', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.user and self.task:
            if not (self.task.created_by == self.user or
                    TaskAssignment.objects.filter(
                        task=self.task,
                        user=self.user,
                        role__in=['ASSIGNEE', 'CO_ASSIGNEE', 'CREATOR']
                    ).exists()):
                raise ValidationError("Только создатель, исполнитель или соисполнитель могут комментировать задачу")
        return cleaned_data

    def save(self, commit=True):
        comment = super().save(commit=False)
        comment.task = self.task
        comment.author = self.user
        if commit:
            comment.save()
        return comment


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'w-full border-gray-300 rounded-lg',
                'accept': '.pdf,.doc,.docx,.jpg,.png,.jpeg',
            }),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            max_size = 5 * 1024 * 1024  # 5MB
            if file.size > max_size:
                raise ValidationError("Файл слишком большой. Максимальный размер: 5MB.")
        return file