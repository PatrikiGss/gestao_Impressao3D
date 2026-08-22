import os

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ModelsForm
from .models import STATUS_CHOICES, HistoricoStatus, Models

# Fonte única dos status aceitos: derivada das choices do model, para não
# divergir se um status novo for adicionado lá.
STATUS_VALIDOS = {valor for valor, _ in STATUS_CHOICES}


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


@login_required
def download_arquivo(request, pk):
    """Entrega o arquivo enviado pelo solicitante.

    Exige login: sem isso qualquer pessoa poderia percorrer /download/1/,
    /download/2/… e baixar todos os modelos enviados ao laboratório.
    """
    item = get_object_or_404(Models, pk=pk)
    if not item.arq_upload:
        raise Http404("Arquivo não encontrado.")

    file_path = item.arq_upload.path
    if not os.path.exists(file_path):
        raise Http404("Arquivo ausente no servidor.")

    # FileResponse transmite em blocos, em vez de carregar o arquivo inteiro
    # na memória do processo.
    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=os.path.basename(file_path),
    )


@login_required
@require_POST
def excluir(request, pk):
    """Remove o cadastro e o arquivo do disco.

    Exige POST: como link GET, bastava conhecer a URL para apagar um registro,
    e qualquer prefetch de navegador ou crawler podia disparar a exclusão.
    """
    item = get_object_or_404(Models, pk=pk)
    if item.arq_upload:
        try:
            item.arq_upload.delete(save=False)
        except OSError:
            # arquivo já sumiu do disco; seguir e apagar o registro mesmo assim
            pass
    item.delete()
    return redirect('core:lista_models')


@login_required
@require_POST
def atualizar_status(request, pk, novo_status):
    """Move o pedido entre os status e registra a mudança no histórico."""
    if novo_status not in STATUS_VALIDOS:
        raise Http404("Status inválido.")

    item = get_object_or_404(Models, pk=pk)
    status_antigo = item.status

    # Sem mudança real, não suja o histórico com um registro vazio.
    if status_antigo == novo_status:
        return redirect('core:lista_models')

    item.status = novo_status
    item.save(update_fields=['status'])

    HistoricoStatus.objects.create(
        impressao=item,
        usuario=request.user,
        status_antigo=status_antigo,
        status_novo=novo_status,
    )

    return redirect('core:lista_models')
