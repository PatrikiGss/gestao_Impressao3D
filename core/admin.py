from django.contrib import admin
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from .models import Models, HistoricoStatus


# --- Inline para mostrar histórico dentro do admin do Models ---
class HistoricoStatusInline(admin.TabularInline):
    model = HistoricoStatus
    extra = 0
    can_delete = False
    readonly_fields = ('status_antigo', 'status_novo', 'usuario', 'data_alteracao')
    ordering = ('-data_alteracao',)

    def has_add_permission(self, request, obj=None):
        return False  # histórico não deve ser adicionado manualmente


# --- Admin principal dos Cadastros ---
@admin.register(Models)
class ModelsAdmin(admin.ModelAdmin):
    list_display = ('nome', 'curso', 'status', 'data_envio', 'created_at')
    list_filter = ('curso', 'status', 'data_envio')
    search_fields = ('nome', 'curso')
    readonly_fields = ('status', 'data_envio', 'created_at')
    inlines = [HistoricoStatusInline]

    fieldsets = (
        ('Informações do solicitante', {
            'fields': ('nome', 'curso', 'telefone')
        }),
        ('Arquivo ou link', {
            'fields': ('arq_upload', 'arq_link')
        }),
        ('Detalhes técnicos', {
            'fields': (
                'quant_de_pecas', 'cor', 'tipo_preenchimento',
                'porcentagem_preenchimento', 'resolucao',
                'qual_impressora', 'tipo_filamento'
            )
        }),
        ('Status e datas', {
            'fields': ('status', 'data_envio', 'created_at')
        }),
    )


# --- Ação personalizada para exportar histórico em PDF ---
def exportar_historico_pdf(modeladmin, request, queryset):
    """
    Gera um PDF com os logs selecionados.
    """
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="historico_status.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Relatório de Histórico de Status")
    y -= 30

    p.setFont("Helvetica", 10)
    for log in queryset.order_by('-data_alteracao'):
        impressao_nome = log.impressao.nome if log.impressao else '[Impressão removida]'
        usuario_nome = log.usuario.username if log.usuario else 'Sistema/Não autenticado'
        texto = (
            f"{log.data_alteracao.strftime('%d/%m/%Y %H:%M')} - "
            f"{impressao_nome} | "
            f"{log.status_antigo or '—'} → {log.status_novo} | "
            f"Usuário: {usuario_nome}"
        )
        p.drawString(50, y, texto)
        y -= 15
        if y < 50:
            p.showPage()
            p.setFont("Helvetica", 10)
            y = height - 50

    p.save()
    return response


exportar_historico_pdf.short_description = "Exportar histórico selecionado para PDF"


@admin.register(HistoricoStatus)
class HistoricoStatusAdmin(admin.ModelAdmin):
    list_display = ('get_impressao_nome', 'status_antigo', 'status_novo', 'get_usuario_nome', 'data_alteracao')
    list_filter = ('status_novo', 'usuario', 'data_alteracao')
    search_fields = ('impressao__nome', 'usuario__username', 'status_antigo', 'status_novo')
    readonly_fields = ('impressao', 'usuario', 'status_antigo', 'status_novo', 'data_alteracao')
    ordering = ('-data_alteracao',)
    actions = [exportar_historico_pdf]

    def get_impressao_nome(self, obj):
        return obj.impressao.nome if obj.impressao else '[Impressão removida]'
    get_impressao_nome.short_description = 'Impressão'

    def get_usuario_nome(self, obj):
        return obj.usuario.username if obj.usuario else 'Sistema/Não autenticado'
    get_usuario_nome.short_description = 'Usuário'
