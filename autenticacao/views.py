from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    # se já autenticado, redireciona para home
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # redireciona para home conforme opção 3
            return redirect('core:home')
    else:
        form = AuthenticationForm()

    return render(request, 'autenticacao/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('core:home')
