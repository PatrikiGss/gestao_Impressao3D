from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .forms import ModelsForm
from .models import Models
from django.http import HttpResponse, Http404
from django.conf import settings
import os
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, 'core/home.html')



def cadastro(request):
    if request.method == "POST":
        form = ModelsForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('core:sucesso')
        # se inválido, renderiza com errors (status 200) — template mostrará os erros
    else:
        form = ModelsForm()

    return render(request, 'core/cadastro.html', {'form': form})

def sucesso(request):
    return render(request, 'core/sucesso.html')

@login_required
def lista_models(request):
    items = Models.objects.order_by('-created_at')
    return render(request, 'core/lista.html', {'items': items})

def download_arquivo(request, pk):
    item = get_object_or_404(Models, pk=pk)
    if not item.arq_upload:
        raise Http404("Arquivo não encontrado.")
    file_path = item.arq_upload.path
    if not os.path.exists(file_path):
        raise Http404("Arquivo ausente no servidor.")
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response

def excluir(request, pk):
    item = get_object_or_404(Models, pk=pk)
    # remove arquivo do disco se existir
    if item.arq_upload:
        try:
            item.arq_upload.delete(save=False)
        except Exception:
            pass
    item.delete()
    return redirect('core:lista_models')

