from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()  # Сохраняет пользователя и создаёт Userprofile
            return redirect('login')  # Замените на ваш URL для перенаправления
    else:
        form = CustomUserCreationForm()

    return render(request, 'userprofile/signup.html', {
        'form': form,
    })