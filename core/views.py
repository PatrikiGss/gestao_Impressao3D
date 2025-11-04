from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .forms import ModelsForm
from .models import Models
from django.http import HttpResponse, Http404
from django.conf import settings
import os
from django.contrib.auth.decorators import login_required
from .models import Models, HistoricoStatus

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
    pendentes = Models.objects.filter(status='PENDENTE').order_by('-created_at')
    producao = Models.objects.filter(status='PRODUCAO').order_by('-created_at')
    concluidos = Models.objects.filter(status='CONCLUIDO').order_by('-created_at')

    return render(request, 'core/lista.html', {
        'pendentes': pendentes,
        'producao': producao,
        'concluidos': concluidos,
    })

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

@login_required
def atualizar_status(request, pk, novo_status):
    item = get_object_or_404(Models, pk=pk)
    if novo_status in ['PENDENTE', 'PRODUCAO', 'CONCLUIDO']:
        item.status = novo_status
        item.save()
    return redirect('core:lista_models')

@login_required
def atualizar_status(request, pk, novo_status):
    # buscar o objeto
    item = get_object_or_404(Models, pk=pk)
    status_antigo = item.status if hasattr(item, 'status') else None

    # atualiza o status
    item.status = novo_status
    item.save()

    # registra o histórico
    HistoricoStatus.objects.create(
        impressao=item,
        usuario=request.user if request.user.is_authenticated else None,
        status_antigo=status_antigo,
        status_novo=novo_status
    )

    # redireciona de volta para a lista
    return redirect(request.META.get('HTTP_REFERER', 'core:lista'))