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
        'tipo_filamento',  # <- nome correto
    )

    list_filter = (
        'curso',
        'tipo_filamento',  # <- nome correto
        'qual_impressora',
    )

    search_fields = ('nome', 'telefone')
