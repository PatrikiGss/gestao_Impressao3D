"""Cria o primeiro administrador a partir de variáveis de ambiente.

Existe porque o plano gratuito do Render não dá acesso a shell: sem isto não
haveria como criar o superusuário depois do deploy.

Roda no fim do build.sh e é idempotente — se o usuário já existe, não faz nada
e não falha, então deploys seguintes passam batido. Se as variáveis não
estiverem definidas, também não faz nada: o build de quem não precisa disso
segue normal.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Cria um superusuário a partir de ADMIN_USERNAME, ADMIN_EMAIL e ADMIN_PASSWORD.'

    def handle(self, *args, **options):
        usuario = os.environ.get('ADMIN_USERNAME')
        senha = os.environ.get('ADMIN_PASSWORD')
        email = os.environ.get('ADMIN_EMAIL', '')

        if not usuario or not senha:
            self.stdout.write(
                'ADMIN_USERNAME e ADMIN_PASSWORD não definidas; nenhum administrador criado.'
            )
            return

        Usuario = get_user_model()

        if Usuario.objects.filter(username=usuario).exists():
            self.stdout.write(f'Administrador "{usuario}" já existe; nada a fazer.')
            return

        Usuario.objects.create_superuser(username=usuario, email=email, password=senha)
        self.stdout.write(self.style.SUCCESS(f'Administrador "{usuario}" criado.'))
