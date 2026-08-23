from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.http import require_POST

from core.utils import destino_seguro


def login_view(request):
    # se já autenticado, redireciona para home
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.get_username()}!')
            # O @login_required anexa ?next=... ao barrar o acesso; assim o
            # usuário volta para a página que tentou abrir, e não para a home.
            return redirect(destino_seguro(request, settings.LOGIN_REDIRECT_URL))
    else:
        form = AuthenticationForm()

    return render(request, 'autenticacao/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


@require_POST
def logout_view(request):
    # Exige POST: por GET, um simples <img src="/accounts/logout/"> em qualquer
    # página deslogava o administrador.
    logout(request)
    messages.info(request, 'Você saiu da sua conta.')
    return redirect('core:home')
