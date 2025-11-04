from django.db import models
from django.utils import timezone
import os
import re

class CursoChoices(models.TextChoices):
    CIENCIA_DA_COMPUTACAO = "CC", "Ciência da Computação"
    ENGENHARIA_QUIMICA = "ENG-QUI", "Engenharia Química"
    ENGENHARIA_MECANICA = "ENG-MEC", "Engenharia Mecânica"
    GESTAO_DO_AGRO = "GEST-AGRO", "Gestão do Agronegócio"
    TECNICOS = "TECS", "Cursos Técnicos"

class ImpressorasChoice(models.TextChoices):
    ENDER_V2 = "Ender_V2", "Ender V2"
    ENDER_3_SE = "Ender_3-SE", "Ender 3 SE"
    ENDER_3_S1 = "Ender_3-S1", "Ender 3 S1"
    ENDER_5_PLUS = "Ender_5-plus", "Ender 5 Plus"

class TipoFilamento(models.TextChoices):
    PLA = "PLA", "PLA"
    ABS = "ABS", "ABS"
    PETG = "PETG", "PETG"

class Resolucao(models.TextChoices):
    BAIXO = "BAIXO", "Baixo"
    MEDIO = "MEDIO", "Médio"
    ALTO = "ALTO", "Alto"


# Função para personalizar o nome do arquivo
def rename_uploaded_file(instance, filename):
    base, ext = os.path.splitext(filename)
    nome = instance.nome.replace(" ", "_")  # evita espaços no nome
    curso = instance.curso.replace(" ", "_")
    new_filename = f"{nome}-{curso}{ext}"
    return os.path.join("arquivos", new_filename)

STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PRODUCAO', 'Em produção'),
        ('CONCLUIDO', 'Concluído'),
    ]


class Models(models.Model):
    nome = models.CharField(max_length=50)
    curso = models.CharField(max_length=20, choices=CursoChoices.choices)
    quant_de_pecas = models.IntegerField()
    cor = models.CharField(max_length=20)
    telefone = models.CharField(max_length=20)

    # arquivo ou link (apenas um obrigatório)
    arq_upload = models.FileField(upload_to=rename_uploaded_file, blank=True, null=True)
    arq_link = models.URLField(blank=True, null=True)

    data_envio = models.DateTimeField(default=timezone.now)

    # campos técnicos (opcionais)
    tipo_preenchimento = models.CharField(max_length=50, blank=True, null=True)
    porcentagem_preenchimento = models.IntegerField(blank=True, null=True)
    resolucao = models.CharField(max_length=20, choices=Resolucao.choices, blank=True, null=True)
    qual_impressora = models.CharField(max_length=20, choices=ImpressorasChoice.choices, blank=True, null=True)
    tipo_filamento = models.CharField(max_length=20, choices=TipoFilamento.choices, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)


    # --- add this method ---
    def telefone_para_whatsapp(self):
        """
        Retorna o telefone formatado para usar no link wa.me:
        - remove tudo que não for dígito
        - se já tiver '55' no início, retorna assim
        - caso contrário, adiciona o DDI do Brasil '55'
        Retorna string vazia se não houver dígitos.
        """
        if not self.telefone:
            return ''
        digits = re.sub(r'\D', '', self.telefone)  # remove tudo que não for dígito
        if not digits:
            return ''
        # remove zeros à esquerda desnecessários? aqui mantemos simples:
        if digits.startswith('55'):
            return digits
        # evita números muito curtos (ex.: apenas 9)
        return '55' + digits
    
        # Novo campo
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDENTE',
        editable=False 
    )
    
    def __str__(self):
        return f"{self.nome} - {self.curso}"