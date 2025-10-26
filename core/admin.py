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
        'tipo_filamento',
        'created_at',
    )

    list_filter = (
        'curso',
        'tipo_filamento',
        'qual_impressora',
    )

    search_fields = ('nome', 'telefone')
