"""Testes das correções de segurança do Bloco 2.

Cada teste aqui corresponde a um buraco que existia antes: acesso sem login,
ação destrutiva por GET, status arbitrário e validação que só existia no
navegador.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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


class EdicaoTest(TestCase):
    """Antes não existia edição: corrigir um telefone exigia apagar e refazer."""

    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.pedido = criar_pedido()
        self.url = reverse('core:editar', args=[self.pedido.pk])

    def dados_edicao(self, **kwargs):
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

    def test_editar_exige_login(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/accounts/login/', resposta['Location'])

    def test_get_mostra_formulario_preenchido(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['form'].instance.pk, self.pedido.pk)

    def test_post_salva_alteracoes(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(self.url, self.dados_edicao(telefone='(49) 98888-7777'))
        self.assertRedirects(resposta, reverse('core:lista_models'))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.telefone, '(49) 98888-7777')

    def test_post_invalido_nao_salva(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(self.url, self.dados_edicao(telefone='xxx'))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('telefone', resposta.context['form'].errors)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.telefone, '(49) 99999-9999')

    def test_edicao_nao_mexe_no_status(self):
        self.pedido.status = 'PRODUCAO'
        self.pedido.save()
        self.client.force_login(self.usuario)
        self.client.post(self.url, self.dados_edicao(cor='verde'))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'PRODUCAO')
        self.assertEqual(self.pedido.cor, 'verde')


class BuscaEFiltroTest(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(self.usuario)
        criar_pedido(nome='Ana Souza', curso='CC', cor='azul')
        criar_pedido(nome='Bruno Lima', curso='ENG-MEC', cor='vermelho')

    def nomes_pendentes(self, resposta):
        return sorted(p.nome for p in resposta.context['pendentes'])

    def test_sem_filtro_traz_todos(self):
        resposta = self.client.get(reverse('core:lista_models'))
        self.assertEqual(self.nomes_pendentes(resposta), ['Ana Souza', 'Bruno Lima'])

    def test_busca_por_nome(self):
        resposta = self.client.get(reverse('core:lista_models'), {'q': 'ana'})
        self.assertEqual(self.nomes_pendentes(resposta), ['Ana Souza'])

    def test_busca_por_cor(self):
        resposta = self.client.get(reverse('core:lista_models'), {'q': 'vermelho'})
        self.assertEqual(self.nomes_pendentes(resposta), ['Bruno Lima'])

    def test_filtro_por_curso(self):
        resposta = self.client.get(reverse('core:lista_models'), {'curso': 'ENG-MEC'})
        self.assertEqual(self.nomes_pendentes(resposta), ['Bruno Lima'])

    def test_paginacao_por_aba(self):
        from .views import PEDIDOS_POR_PAGINA
        for i in range(PEDIDOS_POR_PAGINA + 3):
            criar_pedido(nome=f'Extra {i}')

        primeira = self.client.get(reverse('core:lista_models'))
        self.assertEqual(len(primeira.context['pendentes']), PEDIDOS_POR_PAGINA)
        self.assertTrue(primeira.context['pendentes'].has_next())

        segunda = self.client.get(reverse('core:lista_models'), {'pend': 2})
        self.assertEqual(segunda.context['pendentes'].number, 2)

    def test_paginacao_de_uma_aba_nao_afeta_a_outra(self):
        resposta = self.client.get(reverse('core:lista_models'), {'pend': 2})
        self.assertEqual(resposta.context['producao'].number, 1)


class InterfaceListaTest(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(self.usuario)
        self.pedido = criar_pedido(resolucao='MEDIO', qual_impressora='Ender_3-SE')

    def test_modal_mostra_rotulo_e_nao_o_codigo_do_banco(self):
        resposta = self.client.get(reverse('core:lista_models'))
        self.assertContains(resposta, 'Médio')
        self.assertContains(resposta, 'Ender 3 SE')

    def test_historico_aparece_na_lista(self):
        HistoricoStatus.objects.create(
            impressao=self.pedido, usuario=self.usuario,
            status_antigo='PENDENTE', status_novo='PRODUCAO',
        )
        resposta = self.client.get(reverse('core:lista_models'))
        self.assertContains(resposta, 'Histórico de status')

    def test_lista_tem_botao_de_editar(self):
        resposta = self.client.get(reverse('core:lista_models'))
        self.assertContains(resposta, reverse('core:editar', args=[self.pedido.pk]))


class MensagensTest(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(self.usuario)
        self.pedido = criar_pedido()

    def texto_das_mensagens(self, resposta):
        return [str(m) for m in resposta.context['messages']]

    def test_mudanca_de_status_avisa_o_usuario(self):
        resposta = self.client.post(
            reverse('core:atualizar_status', args=[self.pedido.pk, 'PRODUCAO']), follow=True
        )
        self.assertTrue(any('Em produção' in m for m in self.texto_das_mensagens(resposta)))

    def test_exclusao_avisa_o_usuario(self):
        resposta = self.client.post(reverse('core:excluir', args=[self.pedido.pk]), follow=True)
        self.assertTrue(any('excluído' in m for m in self.texto_das_mensagens(resposta)))


class PaginaSucessoTest(TestCase):
    def test_anonimo_nao_recebe_link_para_area_restrita(self):
        """O botão "Ver lista" só levava o solicitante à tela de login."""
        resposta = self.client.get(reverse('core:sucesso'))
        self.assertNotContains(resposta, reverse('core:lista_models'))
        self.assertContains(resposta, 'Voltar ao início')

    def test_logado_continua_vendo_o_link(self):
        usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(usuario)
        resposta = self.client.get(reverse('core:sucesso'))
        self.assertContains(resposta, reverse('core:lista_models'))


class OrdemDaFilaTest(TestCase):
    """A fila deve ser atendida por ordem de chegada."""

    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(self.usuario)

    def criar_em(self, nome, dias_atras, status='PENDENTE'):
        pedido = criar_pedido(nome=nome, status=status)
        Models.objects.filter(pk=pedido.pk).update(
            created_at=timezone.now() - timedelta(days=dias_atras)
        )
        return pedido

    def test_pendentes_vem_do_mais_antigo_para_o_mais_novo(self):
        self.criar_em('Recente', 1)
        self.criar_em('Antigo', 30)
        self.criar_em('Meio', 10)

        resposta = self.client.get(reverse('core:lista_models'))
        self.assertEqual(
            [p.nome for p in resposta.context['pendentes']],
            ['Antigo', 'Meio', 'Recente'],
        )

    def test_concluidos_vem_do_mais_recente_para_o_mais_antigo(self):
        self.criar_em('Antigo', 30, status='CONCLUIDO')
        self.criar_em('Recente', 1, status='CONCLUIDO')

        resposta = self.client.get(reverse('core:lista_models'))
        self.assertEqual(
            [p.nome for p in resposta.context['concluidos']],
            ['Recente', 'Antigo'],
        )


class TempoDeEsperaTest(TestCase):
    def pedido_com_idade(self, dias):
        pedido = criar_pedido()
        Models.objects.filter(pk=pedido.pk).update(
            created_at=timezone.now() - timedelta(days=dias)
        )
        return Models.objects.get(pk=pedido.pk)

    def test_conta_os_dias_de_espera(self):
        self.assertEqual(self.pedido_com_idade(0).dias_de_espera, 0)
        self.assertEqual(self.pedido_com_idade(5).dias_de_espera, 5)

    def test_niveis_de_espera(self):
        self.assertEqual(self.pedido_com_idade(0).nivel_espera, 'normal')
        self.assertEqual(self.pedido_com_idade(2).nivel_espera, 'normal')
        self.assertEqual(self.pedido_com_idade(3).nivel_espera, 'atencao')
        self.assertEqual(self.pedido_com_idade(6).nivel_espera, 'atencao')
        self.assertEqual(self.pedido_com_idade(7).nivel_espera, 'urgente')
        self.assertEqual(self.pedido_com_idade(60).nivel_espera, 'urgente')

    def test_badge_aparece_na_lista(self):
        usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(usuario)
        self.pedido_com_idade(9)
        resposta = self.client.get(reverse('core:lista_models'))
        self.assertContains(resposta, 'há 9 dias')
        self.assertContains(resposta, 'bg-danger')


class MensagemWhatsappTest(TestCase):
    def test_texto_muda_conforme_o_status(self):
        pedido = criar_pedido(nome='Ana')
        self.assertIn('Recebemos sua solicitação', pedido.mensagem_whatsapp())

        pedido.status = 'PRODUCAO'
        self.assertIn('entrou em produção', pedido.mensagem_whatsapp())

        pedido.status = 'CONCLUIDO'
        self.assertIn('pronta para retirada', pedido.mensagem_whatsapp())

    def test_link_da_lista_leva_a_mensagem_pronta(self):
        """Antes o link abria uma conversa em branco."""
        usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(usuario)
        criar_pedido(nome='Ana')
        resposta = self.client.get(reverse('core:lista_models'))
        self.assertContains(resposta, 'wa.me/5549999999999?text=')
        self.assertContains(resposta, 'Ol%C3%A1%20Ana')


class RetornoAposAcaoTest(TestCase):
    """As ações devem devolver o usuário para a aba, página e filtro de origem."""

    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(self.usuario)
        self.pedido = criar_pedido(status='CONCLUIDO')
        self.origem = '/lista/?q=fulano&conc=2#concluidos'

    def test_mudanca_de_status_volta_para_a_origem(self):
        resposta = self.client.post(
            reverse('core:atualizar_status', args=[self.pedido.pk, 'PRODUCAO']),
            {'next': self.origem},
        )
        self.assertEqual(resposta['Location'], self.origem)

    def test_exclusao_volta_para_a_origem(self):
        resposta = self.client.post(
            reverse('core:excluir', args=[self.pedido.pk]), {'next': self.origem}
        )
        self.assertEqual(resposta['Location'], self.origem)

    def test_status_repetido_tambem_volta_para_a_origem(self):
        resposta = self.client.post(
            reverse('core:atualizar_status', args=[self.pedido.pk, 'CONCLUIDO']),
            {'next': self.origem},
        )
        self.assertEqual(resposta['Location'], self.origem)

    def test_next_para_fora_do_site_e_ignorado(self):
        resposta = self.client.post(
            reverse('core:atualizar_status', args=[self.pedido.pk, 'PRODUCAO']),
            {'next': 'https://site-malicioso.example/'},
        )
        self.assertEqual(resposta['Location'], reverse('core:lista_models'))

    def test_sem_next_cai_na_lista(self):
        resposta = self.client.post(
            reverse('core:atualizar_status', args=[self.pedido.pk, 'PRODUCAO'])
        )
        self.assertEqual(resposta['Location'], reverse('core:lista_models'))

    def test_formulario_da_lista_carrega_o_next_com_aba_e_filtro(self):
        resposta = self.client.get(reverse('core:lista_models'), {'q': 'fulano'})
        self.assertContains(resposta, 'name="next" value="/lista/?q=fulano#concluidos"')
