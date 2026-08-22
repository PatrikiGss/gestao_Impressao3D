"""Testes das correções de segurança do Bloco 2.

Cada teste aqui corresponde a um buraco que existia antes: acesso sem login,
ação destrutiva por GET, status arbitrário e validação que só existia no
navegador.
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .forms import TAMANHO_MAXIMO_MB, ModelsForm
from .models import HistoricoStatus, Models


def criar_pedido(**kwargs):
    dados = {
        'nome': 'Fulano',
        'curso': 'CC',
        'quant_de_pecas': 1,
        'cor': 'azul',
        'telefone': '(49) 99999-9999',
        'arq_link': 'https://exemplo.br/peca.stl',
    }
    dados.update(kwargs)
    return Models.objects.create(**dados)


class AcessoSemLoginTest(TestCase):
    """As views de gestão não podem responder a quem não fez login."""

    def setUp(self):
        self.pedido = criar_pedido()

    def test_excluir_exige_login(self):
        resposta = self.client.post(reverse('core:excluir', args=[self.pedido.pk]))
        self.assertRedirects(
            resposta,
            f"/accounts/login/?next=/excluir/{self.pedido.pk}/",
            fetch_redirect_response=False,
        )
        self.assertTrue(Models.objects.filter(pk=self.pedido.pk).exists())

    def test_download_exige_login(self):
        resposta = self.client.get(reverse('core:download_arquivo', args=[self.pedido.pk]))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/accounts/login/', resposta['Location'])

    def test_atualizar_status_exige_login(self):
        resposta = self.client.post(
            reverse('core:atualizar_status', args=[self.pedido.pk, 'CONCLUIDO'])
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/accounts/login/', resposta['Location'])
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'PENDENTE')

    def test_lista_exige_login(self):
        resposta = self.client.get(reverse('core:lista_models'))
        self.assertEqual(resposta.status_code, 302)

    def test_cadastro_continua_publico(self):
        self.assertEqual(self.client.get(reverse('core:cadastro')).status_code, 200)


class AcoesDestrutivasTest(TestCase):
    """Mesmo logado, mudar dados só por POST com token CSRF."""

    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(self.usuario)
        self.pedido = criar_pedido()

    def test_excluir_por_get_e_recusado(self):
        resposta = self.client.get(reverse('core:excluir', args=[self.pedido.pk]))
        self.assertEqual(resposta.status_code, 405)
        self.assertTrue(Models.objects.filter(pk=self.pedido.pk).exists())

    def test_excluir_por_post_funciona(self):
        resposta = self.client.post(reverse('core:excluir', args=[self.pedido.pk]))
        self.assertRedirects(resposta, reverse('core:lista_models'))
        self.assertFalse(Models.objects.filter(pk=self.pedido.pk).exists())

    def test_atualizar_status_por_get_e_recusado(self):
        resposta = self.client.get(
            reverse('core:atualizar_status', args=[self.pedido.pk, 'PRODUCAO'])
        )
        self.assertEqual(resposta.status_code, 405)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'PENDENTE')

    def test_status_invalido_e_recusado(self):
        """Antes, isto gravava a string no banco e sumia o pedido das 3 abas."""
        resposta = self.client.post(
            reverse('core:atualizar_status', args=[self.pedido.pk, 'BANANA'])
        )
        self.assertEqual(resposta.status_code, 404)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'PENDENTE')

    def test_status_valido_muda_e_registra_historico(self):
        resposta = self.client.post(
            reverse('core:atualizar_status', args=[self.pedido.pk, 'PRODUCAO'])
        )
        self.assertRedirects(resposta, reverse('core:lista_models'))

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'PRODUCAO')

        historico = HistoricoStatus.objects.get(impressao=self.pedido)
        self.assertEqual(historico.status_antigo, 'PENDENTE')
        self.assertEqual(historico.status_novo, 'PRODUCAO')
        self.assertEqual(historico.usuario, self.usuario)

    def test_status_repetido_nao_duplica_historico(self):
        self.client.post(reverse('core:atualizar_status', args=[self.pedido.pk, 'PENDENTE']))
        self.assertEqual(HistoricoStatus.objects.count(), 0)

    def test_redirect_ignora_referer_externo(self):
        """O redirect não pode mais ser guiado pelo cabeçalho Referer."""
        resposta = self.client.post(
            reverse('core:atualizar_status', args=[self.pedido.pk, 'PRODUCAO']),
            HTTP_REFERER='https://site-malicioso.example/',
        )
        self.assertEqual(resposta['Location'], reverse('core:lista_models'))


class LogoutTest(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(self.usuario)

    def test_logout_por_get_e_recusado(self):
        """Por GET, um <img src="/accounts/logout/"> deslogava o admin."""
        self.assertEqual(self.client.get(reverse('autenticacao:logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_logout_por_post_funciona(self):
        resposta = self.client.post(reverse('autenticacao:logout'))
        self.assertRedirects(resposta, reverse('core:home'))
        self.assertNotIn('_auth_user_id', self.client.session)


class ValidacaoServidorTest(TestCase):
    """Regras que antes só existiam no JavaScript e caíam com um POST direto."""

    def dados_base(self, **kwargs):
        dados = {
            'nome': 'Fulano',
            'curso': 'CC',
            'quant_de_pecas': 1,
            'cor': 'azul',
            'telefone': '(49) 99999-9999',
            'arq_link': 'https://exemplo.br/peca.stl',
        }
        dados.update(kwargs)
        return dados

    def test_dados_validos_passam(self):
        self.assertTrue(ModelsForm(data=self.dados_base()).is_valid())

    def test_telefone_invalido_e_recusado(self):
        form = ModelsForm(data=self.dados_base(telefone='abc'))
        self.assertFalse(form.is_valid())
        self.assertIn('telefone', form.errors)

    def test_telefone_sem_mascara_e_aceito(self):
        self.assertTrue(ModelsForm(data=self.dados_base(telefone='49999999999')).is_valid())

    def test_quantidade_negativa_e_recusada(self):
        form = ModelsForm(data=self.dados_base(quant_de_pecas=-5))
        self.assertFalse(form.is_valid())
        self.assertIn('quant_de_pecas', form.errors)

    def test_porcentagem_acima_de_100_e_recusada(self):
        form = ModelsForm(data=self.dados_base(porcentagem_preenchimento=150))
        self.assertFalse(form.is_valid())
        self.assertIn('porcentagem_preenchimento', form.errors)

    def test_arquivo_grande_demais_e_recusado(self):
        grande = SimpleUploadedFile(
            'peca.stl',
            b'x' * ((TAMANHO_MAXIMO_MB + 1) * 1024 * 1024),
            content_type='application/octet-stream',
        )
        form = ModelsForm(data=self.dados_base(), files={'arq_upload': grande})
        self.assertFalse(form.is_valid())
        self.assertIn('arq_upload', form.errors)

    def test_extensao_invalida_e_recusada(self):
        exe = SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream')
        form = ModelsForm(data=self.dados_base(), files={'arq_upload': exe})
        self.assertFalse(form.is_valid())
        self.assertIn('arq_upload', form.errors)

    def test_sem_arquivo_nem_link_e_recusado(self):
        dados = self.dados_base()
        dados.pop('arq_link')
        self.assertFalse(ModelsForm(data=dados).is_valid())
