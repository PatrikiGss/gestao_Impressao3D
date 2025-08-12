from django.contrib import admin
from .models import Models

@admin.register(Models)
class ModelsAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'curso',
        'quant_de_pecas',
        'cor',
        'telefone',
        'qual_impressora',
        'Tipo_filamento',
        'tipo_preenchimento',
        'resolução',
        'porcentagem_preenchimento',
        'arq_upload',
        'arq_link',
    )
    list_filter = (
        'curso',
        'qual_impressora',
        'Tipo_filamento',
        'cor'
    )
    search_fields = (
        'nome',
        'telefone'
    )
