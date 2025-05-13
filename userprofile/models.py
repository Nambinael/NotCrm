from django.contrib.auth.forms import UserCreationForm
from django.db import models
from django.contrib.auth.models import User

from django import forms


class Userprofile(models.Model):
    user = models.OneToOneField(User, related_name='userprofile',on_delete=models.CASCADE)
    User.add_to_class('telegram_id', models.BigIntegerField(null=True, blank=True, unique=True))

