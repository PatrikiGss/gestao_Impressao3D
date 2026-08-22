"""Testes do login e do redirecionamento pós-login."""

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class LoginRedirecionamentoTest(TestCase):
    def setUp(self):
        self.senha = 'senha-de-teste'
        self.usuario = get_user_model().objects.create_user('admin', password=self.senha)
        self.url = reverse('autenticacao:login')

    def credenciais(self, **extras):
        dados = {'username': 'admin', 'password': self.senha}
        dados.update(extras)
        return dados

    def test_login_sem_next_vai_para_home(self):
        resposta = self.client.post(self.url, self.credenciais())
        self.assertRedirects(resposta, reverse('core:home'))

    def test_login_respeita_o_next(self):
        """Antes o next era ignorado e o usuário perdia a página que buscava."""
        destino = reverse('core:lista_models')
        resposta = self.client.post(self.url, self.credenciais(next=destino))
        self.assertRedirects(resposta, destino)

    def test_next_para_site_externo_e_ignorado(self):
        resposta = self.client.post(
            self.url, self.credenciais(next='https://site-malicioso.example/')
        )
        self.assertRedirects(resposta, reverse('core:home'))

    def test_fluxo_completo_de_pagina_protegida(self):
        protegida = reverse('core:lista_models')

        bounce = self.client.get(protegida)
        self.assertRedirects(
            bounce, f'{self.url}?next={protegida}', fetch_redirect_response=False
        )

        formulario = self.client.get(f'{self.url}?next={protegida}')
        self.assertContains(formulario, f'value="{protegida}"')

        entrada = self.client.post(self.url, self.credenciais(next=protegida))
        self.assertRedirects(entrada, protegida)

    def test_credenciais_erradas_nao_logam(self):
        resposta = self.client.post(self.url, self.credenciais(password='errada'))
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


class EstaticosTest(TestCase):
    def test_css_do_login_e_encontrado(self):
        """Estava em autenticacao/statics/ (com "s" a mais) e nunca carregava."""
        self.assertIsNotNone(finders.find('autenticacao/css/login.css'))
