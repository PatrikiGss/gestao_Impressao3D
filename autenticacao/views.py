from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


def _destino_seguro(request):
    """Para onde mandar o usuário depois do login.

    O @login_required já anexa ?next=... ao redirecionar; antes essa
    informação era ignorada e todo mundo caía na home, perdendo a página que
    tentou acessar. A URL é validada para não virar um open redirect.
    """
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(
        url=destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return destino
    return settings.LOGIN_REDIRECT_URL


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
            return redirect(_destino_seguro(request))
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
