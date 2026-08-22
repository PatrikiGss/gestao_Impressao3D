import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import TAMANHO_MAXIMO_MB, ModelsForm
from .models import STATUS_CHOICES, CursoChoices, HistoricoStatus, Models

# Fonte única dos status aceitos: derivada das choices do model, para não
# divergir se um status novo for adicionado lá.
STATUS_VALIDOS = {valor for valor, _ in STATUS_CHOICES}

PEDIDOS_POR_PAGINA = 9

# Rótulo legível de cada status, para as mensagens de confirmação.
ROTULO_STATUS = dict(STATUS_CHOICES)


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

    return render(request, 'core/cadastro.html', {
        'form': form,
        'tamanho_maximo_mb': TAMANHO_MAXIMO_MB,
    })


def sucesso(request):
    return render(request, 'core/sucesso.html')


def _paginar(request, queryset, parametro):
    """Pagina uma aba. Cada aba usa seu próprio parâmetro na querystring
    (?pend=2, ?prod=2, ?conc=2) para que paginar uma não mexa nas outras."""
    return Paginator(queryset, PEDIDOS_POR_PAGINA).get_page(request.GET.get(parametro))


@login_required
def lista_models(request):
    busca = request.GET.get('q', '').strip()
    curso = request.GET.get('curso', '').strip()

    pedidos = Models.objects.prefetch_related('historico_status__usuario')

    if busca:
        pedidos = pedidos.filter(
            Q(nome__icontains=busca) | Q(cor__icontains=busca) | Q(telefone__icontains=busca)
        )
    if curso:
        pedidos = pedidos.filter(curso=curso)

    def por_status(status):
        return pedidos.filter(status=status).order_by('-created_at')

    # Querystring sem os parâmetros de página, para os links de paginação
    # preservarem a busca e o filtro de curso.
    filtros = request.GET.copy()
    for parametro in ('pend', 'prod', 'conc'):
        filtros.pop(parametro, None)

    return render(request, 'core/lista.html', {
        'pendentes': _paginar(request, por_status('PENDENTE'), 'pend'),
        'producao': _paginar(request, por_status('PRODUCAO'), 'prod'),
        'concluidos': _paginar(request, por_status('CONCLUIDO'), 'conc'),
        'busca': busca,
        'curso_selecionado': curso,
        'cursos': CursoChoices.choices,
        'filtros': filtros.urlencode(),
        'tem_filtro': bool(busca or curso),
    })


@login_required
def editar(request, pk):
    """Corrige os dados de um pedido já cadastrado.

    Sem isto, um telefone digitado errado só podia ser resolvido apagando o
    cadastro e pedindo para o solicitante preencher tudo de novo.
    """
    item = get_object_or_404(Models, pk=pk)

    if request.method == 'POST':
        form = ModelsForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cadastro de {item.nome} atualizado.')
            return redirect('core:lista_models')
        messages.error(request, 'Corrija os campos destacados abaixo.')
    else:
        form = ModelsForm(instance=item)

    return render(request, 'core/editar.html', {
        'form': form,
        'item': item,
        'tamanho_maximo_mb': TAMANHO_MAXIMO_MB,
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
    nome = item.nome
    item.delete()
    messages.success(request, f'Cadastro de {nome} excluído.')
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

    messages.success(
        request,
        f'{item.nome}: {ROTULO_STATUS[status_antigo]} → {ROTULO_STATUS[novo_status]}.',
    )
    return redirect('core:lista_models')
