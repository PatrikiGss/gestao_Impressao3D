from django.db import models
from django.utils import timezone

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

class Models(models.Model):
    nome = models.CharField(max_length=50)
    curso = models.CharField(max_length=20, choices=CursoChoices.choices)
    quant_de_pecas = models.IntegerField()
    cor = models.CharField(max_length=20)
    telefone = models.IntegerField(unique=True)

    # arquivos
    arq_upload = models.FileField(upload_to="arquivos/", blank=True, null=True)
    arq_link = models.URLField(blank=True, null=True)
    data_envio = models.DateTimeField(default=timezone.now)

    # campos técnicos (opcionais)
    tipo_preenchimento = models.CharField(max_length=50, blank=True, null=True)
    porcentagem_preenchimento = models.IntegerField(blank=True, null=True)
    resolucao = models.CharField(max_length=20, choices=Resolucao.choices, blank=True, null=True)
    qual_impressora = models.CharField(max_length=20, choices=ImpressorasChoice.choices, blank=True, null=True)
    tipo_filamento = models.CharField(max_length=20, choices=TipoFilamento.choices, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} - {self.curso}"
