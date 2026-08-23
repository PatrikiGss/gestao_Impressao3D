from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.utils import timezone
import os
import re
from django.conf import settings

# A máscara do formulário é só conveniência no navegador; um POST direto passa
# qualquer coisa. Este validador é o que realmente vale.
validar_telefone = RegexValidator(
    regex=r'^\(?\d{2}\)?[\s-]?\d{4,5}-?\d{4}$',
    message='Informe um telefone válido com DDD. Ex.: (49) 99999-9999',
)

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

# A partir de quantos dias na fila um pedido passa a ser destacado.
DIAS_PARA_ATENCAO = 3
DIAS_PARA_URGENCIA = 7


class Models(models.Model):
    nome = models.CharField(max_length=50)
    curso = models.CharField(max_length=20, choices=CursoChoices.choices)
    quant_de_pecas = models.IntegerField(validators=[MinValueValidator(1)])
    cor = models.CharField(max_length=20)
    telefone = models.CharField(max_length=20, validators=[validar_telefone])

    # arquivo ou link (apenas um obrigatório)
    arq_upload = models.FileField(upload_to=rename_uploaded_file, blank=True, null=True)
    arq_link = models.URLField(blank=True, null=True)

    data_envio = models.DateTimeField(default=timezone.now)

    # campos técnicos (opcionais)
    tipo_preenchimento = models.CharField(max_length=50, blank=True, null=True)
    porcentagem_preenchimento = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    resolucao = models.CharField(max_length=20, choices=Resolucao.choices, blank=True, null=True)
    qual_impressora = models.CharField(max_length=20, choices=ImpressorasChoice.choices, blank=True, null=True)
    tipo_filamento = models.CharField(max_length=20, choices=TipoFilamento.choices, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # Não editável no formulário: só muda pela view atualizar_status, que
    # registra cada troca em HistoricoStatus.
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDENTE',
        editable=False,
    )

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
        if digits.startswith('55'):
            return digits
        return '55' + digits

    def mensagem_whatsapp(self):
        """Texto já pronto para abrir a conversa no WhatsApp.

        Sem isto o link abre um chat em branco e a equipe redigita a mesma
        mensagem a cada pedido.
        """
        if self.status == 'CONCLUIDO':
            return (
                f'Olá {self.nome}! Sua impressão 3D está pronta para retirada '
                f'no laboratório do IFSC Lages.'
            )
        if self.status == 'PRODUCAO':
            return (
                f'Olá {self.nome}! Sua impressão 3D entrou em produção. '
                f'Avisamos assim que estiver pronta.'
            )
        return f'Olá {self.nome}! Recebemos sua solicitação de impressão 3D.'

    @property
    def dias_de_espera(self):
        """Dias inteiros desde o cadastro."""
        if not self.created_at:
            return 0
        return (timezone.now() - self.created_at).days

    @property
    def nivel_espera(self):
        """Quanto o pedido já esperou, para destacar quem está encalhado."""
        if self.dias_de_espera >= DIAS_PARA_URGENCIA:
            return 'urgente'
        if self.dias_de_espera >= DIAS_PARA_ATENCAO:
            return 'atencao'
        return 'normal'

    def __str__(self):
        return f"{self.nome} - {self.curso}"

class HistoricoStatus(models.Model):
    """
    Registra alterações de status de um pedido (Models).
    Armazena: qual pedido, quem fez a mudança (User), status antigo, status novo e timestamp.
    """
    impressao = models.ForeignKey(
        Models,
        on_delete=models.SET_NULL,  # mantém o histórico mesmo se o cadastro for apagado
        null=True,
        blank=True,
        related_name='historico_status'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status_antigo = models.CharField(max_length=50, blank=True, null=True)
    status_novo = models.CharField(max_length=50)
    data_alteracao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_alteracao']
        verbose_name = 'Histórico de status'
        verbose_name_plural = 'Históricos de status'

    def __str__(self):
        usuario = self.usuario.username if self.usuario else 'Sistema/Não autenticado'
        impressao_nome = self.impressao.nome if self.impressao else '[Impressão removida]'
        return f"{impressao_nome} — {self.status_antigo or '—'} → {self.status_novo} ({usuario})"
