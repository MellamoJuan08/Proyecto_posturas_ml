from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import LoginForm, RegisterForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('detector:dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'detector:dashboard')
            messages.success(request, f'¡Bienvenido de vuelta, {user.first_name or user.username}!')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = LoginForm(request)

    return render(request, 'accounts/login.html', {'form': form, 'page_title': 'Iniciar sesión'})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('detector:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Cuenta creada exitosamente! Bienvenido, {user.first_name or user.username}.')
            return redirect('detector:dashboard')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form, 'page_title': 'Crear cuenta'})


def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    from detector.models import UserStats
    stats, _ = UserStats.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {
        'stats': stats,
        'page_title': 'Mi perfil',
    })
