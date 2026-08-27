#!/usr/bin/env bash
# Executado pelo Render a cada deploy, antes de subir o processo web.
# set -o errexit: qualquer passo que falhe aborta o deploy em vez de publicar
# uma versão quebrada.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Reúne CSS e JS em STATIC_ROOT. Sem isto o site sobe sem estilo nenhum, já que
# com DEBUG=False o Django não serve estáticos a partir das pastas dos apps.
python manage.py collectstatic --no-input

# Aplica migrations pendentes. É idempotente: se não houver nada novo, não faz
# nada.
python manage.py migrate

# Cria o primeiro administrador a partir de ADMIN_USERNAME e ADMIN_PASSWORD.
# O plano gratuito do Render não dá acesso a shell, então esta é a única forma
# de criar o superusuário. Não faz nada se ele já existir ou se as variáveis
# não estiverem definidas.
python manage.py criar_admin
