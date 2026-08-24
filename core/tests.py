"""Testes das correções de segurança do Bloco 2.

Cada teste aqui corresponde a um buraco que existia antes: acesso sem login,
ação destrutiva por GET, status arbitrário e validação que só existia no
navegador.
"""

import os
import re
from unittest import mock
import shutil
from pathlib import Path
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import TAMANHO_MAXIMO_MB, ModelsForm
from .templatetags.estaticos import static_v
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


class ExportacaoCsvTest(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.url = reverse('core:exportar_csv')

    def baixar(self, **filtros):
        self.client.force_login(self.usuario)
        resposta = self.client.get(self.url, filtros)
        self.assertEqual(resposta.status_code, 200)
        return resposta

    def linhas(self, resposta):
        texto = resposta.content.decode('utf-8-sig')
        return [l for l in texto.splitlines() if l.strip()]

    def test_exige_login(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/accounts/login/', resposta['Location'])

    def test_baixa_como_anexo_com_data_no_nome(self):
        resposta = self.baixar()
        self.assertIn('attachment;', resposta['Content-Disposition'])
        self.assertIn('.csv', resposta['Content-Disposition'])

    def test_comeca_com_bom_para_o_excel_nao_quebrar_acento(self):
        """Sem o BOM o Excel em português lê o arquivo como latin-1."""
        self.assertTrue(self.baixar().content.startswith(b'\xef\xbb\xbf'))

    def test_usa_ponto_e_virgula_como_separador(self):
        criar_pedido(nome='Ana')
        cabecalho = self.linhas(self.baixar())[0]
        self.assertIn(';', cabecalho)
        self.assertIn('Nome', cabecalho.split(';'))

    def test_exporta_os_pedidos(self):
        criar_pedido(nome='Ana Souza', curso='CC')
        criar_pedido(nome='Bruno Lima', curso='ENG-MEC')

        linhas = self.linhas(self.baixar())
        self.assertEqual(len(linhas), 3)  # cabeçalho + 2
        conteudo = '\n'.join(linhas)
        self.assertIn('Ana Souza', conteudo)
        self.assertIn('Bruno Lima', conteudo)

    def test_mostra_rotulo_e_nao_o_codigo_do_banco(self):
        criar_pedido(nome='Ana', curso='ENG-MEC', resolucao='MEDIO')
        conteudo = '\n'.join(self.linhas(self.baixar()))
        self.assertIn('Engenharia Mecânica', conteudo)
        self.assertIn('Médio', conteudo)
        self.assertNotIn('ENG-MEC', conteudo)

    def test_respeita_a_busca(self):
        criar_pedido(nome='Ana Souza')
        criar_pedido(nome='Bruno Lima')

        conteudo = '\n'.join(self.linhas(self.baixar(q='ana')))
        self.assertIn('Ana Souza', conteudo)
        self.assertNotIn('Bruno Lima', conteudo)

    def test_respeita_o_filtro_de_curso(self):
        criar_pedido(nome='Ana Souza', curso='CC')
        criar_pedido(nome='Bruno Lima', curso='ENG-MEC')

        conteudo = '\n'.join(self.linhas(self.baixar(curso='ENG-MEC')))
        self.assertIn('Bruno Lima', conteudo)
        self.assertNotIn('Ana Souza', conteudo)

    def test_inclui_os_tres_status(self):
        criar_pedido(nome='Pendente Um', status='PENDENTE')
        criar_pedido(nome='Producao Um', status='PRODUCAO')
        criar_pedido(nome='Concluido Um', status='CONCLUIDO')

        conteudo = '\n'.join(self.linhas(self.baixar()))
        for esperado in ('Pendente', 'Em produção', 'Concluído'):
            self.assertIn(esperado, conteudo)

    def test_campos_opcionais_vazios_nao_viram_none(self):
        criar_pedido(nome='Ana', tipo_preenchimento=None, porcentagem_preenchimento=None)
        conteudo = '\n'.join(self.linhas(self.baixar()))
        self.assertNotIn('None', conteudo)

    def test_botao_aparece_na_lista_com_os_filtros(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse('core:lista_models'), {'q': 'ana'})
        self.assertContains(resposta, f'{self.url}?q=ana')


class NumeroDoPedidoTest(TestCase):
    """O solicitante precisa sair com algo que identifique o pedido dele."""

    def dados(self):
        return {
            'nome': 'Ana Souza',
            'curso': 'CC',
            'quant_de_pecas': 1,
            'cor': 'azul',
            'telefone': '(49) 99999-9999',
            'arq_link': 'https://exemplo.br/peca.stl',
        }

    def test_sucesso_mostra_o_numero_apos_cadastrar(self):
        self.client.post(reverse('core:cadastro'), self.dados())
        pedido = Models.objects.get(nome='Ana Souza')

        resposta = self.client.get(reverse('core:sucesso'))
        self.assertContains(resposta, f'#{pedido.pk}')
        self.assertContains(resposta, 'Guarde este número')

    def test_quem_abre_a_pagina_direto_nao_ve_numero(self):
        resposta = self.client.get(reverse('core:sucesso'))
        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, 'Guarde este número')

    def test_numero_nao_vai_na_url(self):
        """Na URL, daria para percorrer /sucesso/1/, /sucesso/2/… e colher nomes."""
        resposta = self.client.post(reverse('core:cadastro'), self.dados())
        self.assertEqual(resposta['Location'], reverse('core:sucesso'))


class ArquivoOrfaoTest(TestCase):
    """Trocar o arquivo na edição não pode deixar o antigo no disco."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls.media)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls.media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(self.usuario)

    def stl(self, nome, conteudo):
        return SimpleUploadedFile(nome, conteudo, content_type='application/octet-stream')

    def dados(self, **extras):
        base = {
            'nome': 'Ana Souza',
            'curso': 'CC',
            'quant_de_pecas': 1,
            'cor': 'azul',
            'telefone': '(49) 99999-9999',
        }
        base.update(extras)
        return base

    def test_arquivo_antigo_e_apagado_ao_subir_outro(self):
        self.client.post(
            reverse('core:cadastro'),
            {**self.dados(), 'arq_upload': self.stl('primeiro.stl', b'solid um')},
        )
        pedido = Models.objects.get(nome='Ana Souza')
        antigo = pedido.arq_upload.name
        self.assertTrue(pedido.arq_upload.storage.exists(antigo))

        self.client.post(
            reverse('core:editar', args=[pedido.pk]),
            {**self.dados(), 'arq_upload': self.stl('segundo.stl', b'solid dois')},
        )
        pedido.refresh_from_db()

        self.assertNotEqual(pedido.arq_upload.name, antigo)
        self.assertFalse(pedido.arq_upload.storage.exists(antigo))
        self.assertTrue(pedido.arq_upload.storage.exists(pedido.arq_upload.name))

    def test_editar_sem_trocar_arquivo_mantem_o_atual(self):
        self.client.post(
            reverse('core:cadastro'),
            {**self.dados(), 'arq_upload': self.stl('unico.stl', b'solid um')},
        )
        pedido = Models.objects.get(nome='Ana Souza')
        arquivo = pedido.arq_upload.name

        self.client.post(reverse('core:editar', args=[pedido.pk]), self.dados(cor='verde'))
        pedido.refresh_from_db()

        self.assertEqual(pedido.arq_upload.name, arquivo)
        self.assertTrue(pedido.arq_upload.storage.exists(arquivo))
        self.assertEqual(pedido.cor, 'verde')


class RetornoDaEdicaoTest(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')
        self.client.force_login(self.usuario)
        self.pedido = criar_pedido(nome='Ana Souza')
        self.origem = '/lista/?q=ana#pendentes'

    def dados(self, **extras):
        base = {
            'nome': 'Ana Souza',
            'curso': 'CC',
            'quant_de_pecas': 1,
            'cor': 'azul',
            'telefone': '(49) 99999-9999',
            'arq_link': 'https://exemplo.br/peca.stl',
        }
        base.update(extras)
        return base

    def test_link_editar_da_lista_carrega_o_destino_de_volta(self):
        """O ? e o # precisam sair codificados, senão o navegador os leria
        como querystring e fragmento da URL de edição."""
        resposta = self.client.get(reverse('core:lista_models'), {'q': 'ana'})
        self.assertContains(resposta, 'next=/lista/%3Fq%3Dana%23pendentes')

    def test_salvar_volta_para_a_origem(self):
        resposta = self.client.post(
            reverse('core:editar', args=[self.pedido.pk]),
            self.dados(next=self.origem, cor='verde'),
        )
        self.assertEqual(resposta['Location'], self.origem)

    def test_cancelar_aponta_para_a_origem(self):
        resposta = self.client.get(
            reverse('core:editar', args=[self.pedido.pk]), {'next': self.origem}
        )
        self.assertContains(resposta, f'value="{self.origem}"')

    def test_next_externo_e_ignorado(self):
        resposta = self.client.post(
            reverse('core:editar', args=[self.pedido.pk]),
            self.dados(next='https://site-malicioso.example/'),
        )
        self.assertEqual(resposta['Location'], reverse('core:lista_models'))


class TemaEscuroTest(TestCase):
    def test_tema_e_aplicado_antes_de_pintar_a_tela(self):
        """O script fica no <head>: no fim do body haveria flash branco."""
        html = self.client.get(reverse('core:home')).content.decode()
        cabeca = html.split('</head>')[0]
        self.assertIn('data-bs-theme', cabeca)
        self.assertIn('prefers-color-scheme: dark', cabeca)

    def test_botao_de_alternar_aparece(self):
        resposta = self.client.get(reverse('core:home'))
        self.assertContains(resposta, 'id="alternar-tema"')
        self.assertContains(resposta, 'core/js/tema.js')

    def test_css_define_os_dois_temas(self):
        css = open(finders.find('core/css/base.css'), encoding='utf-8').read()
        self.assertIn(':root', css)
        self.assertIn('[data-bs-theme="dark"]', css)


class UtilitariosDeCorTest(TestCase):
    """Utilities de cor do Bootstrap que ignoram o tema.

    bg-light e bg-dark têm cor fixa: no modo escuro o painel de campos
    técnicos virava uma caixa quase branca com texto quase branco (contraste
    1.24, ilegível). O certo é usar as classes próprias, ligadas aos tokens.
    """

    PROIBIDAS = ('bg-light', 'bg-dark', 'bg-white', 'navbar-dark', 'bg-body')

    def templates(self):
        raiz = Path(settings.BASE_DIR)
        for app in ('core', 'autenticacao'):
            yield from (raiz / app / 'templates').rglob('*.html')

    def test_templates_nao_usam_utility_de_cor_fixa(self):
        encontrados = []
        for caminho in self.templates():
            html = caminho.read_text(encoding='utf-8')
            for classe in self.PROIBIDAS:
                if classe in html:
                    encontrados.append(f'{caminho.name}: {classe}')
        self.assertEqual(encontrados, [], f'usar token de tema no lugar: {encontrados}')

    def test_paleta_cobre_os_dois_temas(self):
        css = Path(finders.find('core/css/base.css')).read_text(encoding='utf-8')
        claro = css.split(':root {')[1].split('}')[0]
        escuro = css.split(':root[data-bs-theme="dark"] {')[1].split('}')[0]

        tokens = lambda bloco: {l.split(':')[0].strip() for l in bloco.splitlines()
                                if l.strip().startswith('--')}
        faltando = tokens(claro) - tokens(escuro)
        self.assertEqual(faltando, set(), f'tokens sem versão escura: {faltando}')

    def test_escala_de_superficies_e_distinta(self):
        """Página, seção e cartão precisam ser cores diferentes, senão o card
        some dentro da caixa — foi o que aconteceu no primeiro modo escuro."""
        css = Path(finders.find('core/css/base.css')).read_text(encoding='utf-8')
        for bloco_nome in (':root {', ':root[data-bs-theme="dark"] {'):
            bloco = css.split(bloco_nome)[1].split('}')[0]
            valores = {}
            for nome in ('--fundo-pagina', '--fundo-secao', '--fundo-cartao'):
                for linha in bloco.splitlines():
                    if linha.strip().startswith(nome + ':'):
                        valores[nome] = linha.split(':')[1].strip().rstrip(';')
            self.assertEqual(len(set(valores.values())), 3,
                             f'{bloco_nome} tem superfícies repetidas: {valores}')


class EstaticosVersionadosTest(TestCase):
    """CSS e JS precisam carregar com marca de versão.

    Sem ela o navegador serve o arquivo antigo depois de uma alteração: o HTML
    vem fresco do Django e a página mistura template novo com estilo velho.
    Foi assim que o cabeçalho ficou sem cor de fundo depois de trocar bg-dark
    pela classe .barra-topo.
    """

    def setUp(self):
        self.usuario = get_user_model().objects.create_user('admin', password='senha-de-teste')

    def test_tag_acrescenta_versao(self):
        url = static_v('core/css/base.css')
        self.assertIn('/static/core/css/base.css', url)
        self.assertRegex(url, r'\?v=\d+$')

    @override_settings(DEBUG=True)
    def test_versao_acompanha_a_alteracao_do_arquivo(self):
        """Só vale em desenvolvimento: com DEBUG=False a versão fica em cache
        de propósito, porque os arquivos não mudam com o processo no ar."""
        caminho = Path(finders.find('core/css/base.css'))
        antes = static_v('core/css/base.css')

        original = caminho.stat().st_mtime
        try:
            os.utime(caminho, (original + 120, original + 120))
            depois = static_v('core/css/base.css')
        finally:
            os.utime(caminho, (original, original))

        self.assertNotEqual(antes, depois, 'a URL tem de mudar quando o arquivo muda')

    def test_arquivo_inexistente_nao_quebra(self):
        self.assertNotIn('?v=', static_v('core/css/nao-existe.css'))

    def test_paginas_publicas_servem_css_versionado(self):
        for rota in ('core:home', 'core:cadastro', 'core:sucesso', 'autenticacao:login'):
            resposta = self.client.get(reverse(rota))
            self.assertContains(resposta, 'core/css/base.css?v=', msg_prefix=rota)

    def test_lista_serve_css_e_js_versionados(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse('core:lista_models'))
        for estatico in ('core/css/base.css?v=', 'core/css/lista.css?v=',
                         'core/js/tema.js?v=', 'core/js/lista.js?v='):
            self.assertContains(resposta, estatico)

    def test_nenhum_template_usa_static_sem_versao_para_css_ou_js(self):
        raiz = Path(settings.BASE_DIR)
        pendentes = []
        for app in ('core', 'autenticacao'):
            for caminho in (raiz / app / 'templates').rglob('*.html'):
                html = caminho.read_text(encoding='utf-8')
                for achado in re.findall(r'\{%\s*static\s+\'[^\']+\.(?:css|js)\'', html):
                    pendentes.append(f'{caminho.name}: {achado}')
        self.assertEqual(pendentes, [], f'usar static_v nestes casos: {pendentes}')


class ConfiguracaoDeDeployTest(TestCase):
    """Checagens da infraestrutura de deploy no Render.

    Cada uma corresponde a um erro que só apareceria com o site já no ar.
    """

    def raiz(self):
        return Path(settings.BASE_DIR)

    def test_whitenoise_esta_logo_apos_o_security_middleware(self):
        """Fora dessa posição o WhiteNoise não serve os estáticos, e com
        DEBUG=False o site sobe sem nenhum CSS."""
        middleware = settings.MIDDLEWARE
        self.assertIn('whitenoise.middleware.WhiteNoiseMiddleware', middleware)
        self.assertEqual(
            middleware.index('whitenoise.middleware.WhiteNoiseMiddleware'),
            middleware.index('django.middleware.security.SecurityMiddleware') + 1,
        )

    def test_hostname_do_render_entra_em_allowed_hosts_e_csrf(self):
        """Sem isso todo request no domínio .onrender.com vira HTTP 400, e todo
        POST quebra na verificação de CSRF."""
        import importlib

        from Impressora3D import settings as modulo

        with mock.patch.dict(os.environ, {'RENDER_EXTERNAL_HOSTNAME': 'teste.onrender.com'}):
            recarregado = importlib.reload(modulo)

        try:
            self.assertIn('teste.onrender.com', recarregado.ALLOWED_HOSTS)
            self.assertIn('https://teste.onrender.com', recarregado.CSRF_TRUSTED_ORIGINS)
            self.assertNotIn('https://localhost', recarregado.CSRF_TRUSTED_ORIGINS)
        finally:
            importlib.reload(modulo)

    def test_database_url_tem_precedencia_e_exige_ssl(self):
        import importlib

        from Impressora3D import settings as modulo

        url = 'postgresql://u:s@host.render.com:5432/banco'
        with mock.patch.dict(os.environ, {'DATABASE_URL': url, 'DEBUG': 'False', 'SECRET_KEY': 'x' * 60}):
            recarregado = importlib.reload(modulo)

        try:
            banco = recarregado.DATABASES['default']
            self.assertEqual(banco['ENGINE'], 'django.db.backends.postgresql')
            self.assertEqual(banco['NAME'], 'banco')
            self.assertEqual(banco['OPTIONS'].get('sslmode'), 'require')
            self.assertTrue(banco['CONN_MAX_AGE'])
        finally:
            importlib.reload(modulo)

    def test_build_sh_existe_e_faz_o_essencial(self):
        script = (self.raiz() / 'build.sh').read_text(encoding='utf-8')
        for passo in ('pip install -r requirements.txt',
                      'collectstatic --no-input',
                      'manage.py migrate'):
            self.assertIn(passo, script, f'build.sh sem o passo: {passo}')
        self.assertIn('set -o errexit', script,
                      'sem errexit um passo que falha publicaria versão quebrada')

    def test_build_sh_usa_fim_de_linha_lf(self):
        """Com CRLF o Linux lê o shebang como '/usr/bin/env bash\\r' e o deploy
        falha com 'bad interpreter'."""
        bruto = (self.raiz() / 'build.sh').read_bytes()
        self.assertNotIn(b'\r', bruto)

    def test_render_yaml_declara_servico_e_banco(self):
        blueprint = (self.raiz() / 'render.yaml').read_text(encoding='utf-8')
        for trecho in ('buildCommand', './build.sh', 'gunicorn Impressora3D.wsgi',
                       'DATABASE_URL', 'SECRET_KEY'):
            self.assertIn(trecho, blueprint)

    def test_requirements_traz_o_necessario_para_producao(self):
        reqs = (self.raiz() / 'requirements.txt').read_text(encoding='utf-8')
        for pacote in ('gunicorn', 'whitenoise', 'dj-database-url', 'psycopg2-binary'):
            self.assertIn(pacote, reqs)
