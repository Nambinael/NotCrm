import json
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from tasks.models import  Project
from django.contrib.auth.models import User

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full border-gray-300 rounded-lg',
                'placeholder': 'Введите название проекта'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full border-gray-300 rounded-lg',
                'placeholder': 'Введите описание проекта (необязательно)'
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError("Название проекта обязательно")
        return name