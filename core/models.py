from django.db import models

class CursoChoices(models.TextChoices):
    CIENCIA_DA_COMPUTACAO = "CC", "Ciência da Computação"
    ENGENHARIA_QUIMICA = "ENG-QUI", "Engenharia Química"
    ENGENHARIA_MECANICA = "ENG-MEC", "Engenharia Mecânica"
    GESTAO_DO_AGRO = "GEST-AGRO", "Gestão do Agronegocio"
    TECNICOS = "TECS", "Cursos Técnicos"
    
class ImpressorasChoice(models.TextChoices):
    
    ENDER_V2 = "Ender_V2", "Ender V2"
    ENDER_3_SE = "Ender_3-SE", "Ender 3 SE"
    ENDER_3_S1 = "Ender_3-S1", "Ender 3 S1"
    ENDER_5_PLUS = "Ender_5-plus", "Ender 5 Plus"
    
class Tipo_filamento(models.TextChoices):
    PLA="PLA","pla"
    ABS="ABS","abs"
    PETG="PETG","petg"

class Models(models.Model):
    nome = models.CharField(max_length=50)
    curso = models.CharField(
        max_length=20,
        choices=CursoChoices.choices,
        default=CursoChoices.CIENCIA_DA_COMPUTACAO
    )
    quant_de_pecas = models.IntegerField()
    cor=models.CharField(max_length=20)
    telefone=models.IntegerField(unique=True)
    arq_upload=models.FileField(upload_to="arquivos/", blank=True,null=True)
    arq_link=models.URLField(blank=True,null=True)
    #abaixo os campos apenas para quem possui conhecimento tecnico
    tipo_preenchimento=models.CharField(max_length=50, blank=True, null=True)
    resolução=models.IntegerField(blank=True, null=True)
    porcentagem_preenchimento=models.IntegerField(blank=True, null=True)
    qual_impressora = models.CharField(
        max_length=20,
        choices=ImpressorasChoice.choices,
        default=ImpressorasChoice.ENDER_V2,
        blank=True,
        null=True
    )
    porcentagem_preenchimento=models.IntegerField()
    Tipo_filamento = models.CharField(
        max_length=20,
        choices=Tipo_filamento.choices,
        default=Tipo_filamento.PLA,
        blank=True,
        null=True
    )
    
 
    
    def __str__(self):
        return f"{self.nome} - {self.curso}"