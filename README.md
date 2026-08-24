# Gestão de Impressoras 3D — IFSC Campus Lages

[![Testes](https://github.com/PatrikiGss/gestao_Impressao3D/actions/workflows/testes.yml/badge.svg)](https://github.com/PatrikiGss/gestao_Impressao3D/actions/workflows/testes.yml)

Sistema para organizar a fila de impressão 3D do laboratório.

O aluno preenche um formulário público com os dados dele e o arquivo do modelo (ou um link, se preferir). A equipe do laboratório faz login, vê os pedidos separados em Pendentes, Em produção e Concluídos, baixa o arquivo, chama o aluno no WhatsApp e vai movendo o pedido entre os status. Cada mudança fica registrada com autor e data, e dá pra exportar esse histórico em PDF pelo admin do Django.

Feito em Django 5.2 com Bootstrap 5, rodando em SQLite no desenvolvimento e PostgreSQL em produção.

## Rodando

Precisa de Python 3.12.

```bash
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # Linux/macOS: cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Os valores que já vêm no `.env.example` bastam pra desenvolver: `DEBUG=True` e `DB_ENGINE=sqlite3`. Nesse modo o projeto usa uma SECRET_KEY descartável e cria o `db.sqlite3` na raiz, então não precisa instalar banco nenhum.

A home e o formulário de cadastro são públicos. A lista, a edição e o admin exigem login.

Os testes rodam com `python manage.py test`. Eles também rodam sozinhos a cada push, junto com uma conferência de migrations pendentes e o `check --deploy` — está tudo em `.github/workflows/testes.yml`.

As ferramentas de lint ficam separadas em `requirements-dev.txt`, que não é instalado em produção nem no CI.

## Configuração

Tudo fica no `.env`, que não vai pro git — o `.env.example` é o modelo.

`DEBUG` liga o modo de desenvolvimento. Com ele desligado, a `SECRET_KEY` passa a ser obrigatória e o `ALLOWED_HOSTS` precisa listar o domínio, senão toda requisição vira 400. Pra gerar uma chave:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

`DB_ENGINE` aceita `sqlite3` (padrão) ou `postgresql`. Usando Postgres, preencha também `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` e `DB_PORT`; no SQLite essas variáveis são ignoradas.

## Deploy no Render

O repositório já vem com `render.yaml` e `build.sh`. No painel do Render:
**New → Blueprint**, aponte para este repositório e confirme. Ele cria o
serviço web e o banco Postgres, liga a `DATABASE_URL` entre os dois e gera a
`SECRET_KEY` sozinho.

Prefere criar na mão? É um Web Service Python com:

- **Build Command:** `./build.sh`
- **Start Command:** `gunicorn Impressora3D.wsgi:application`
- **Environment:** `DEBUG=False`, `SECRET_KEY` (gerada), e `DATABASE_URL`
  apontando para o banco

O domínio `.onrender.com` entra sozinho em `ALLOWED_HOSTS` e em
`CSRF_TRUSTED_ORIGINS` — o settings lê a variável `RENDER_EXTERNAL_HOSTNAME`
que o Render injeta. Para domínio próprio, acrescente-o em `ALLOWED_HOSTS`.

Depois do primeiro deploy, crie o administrador pelo Shell do Render:

```bash
python manage.py createsuperuser
```

Os estáticos são servidos pelo **WhiteNoise**, dentro do próprio processo — não
há nginx na frente. O `collectstatic` roda no build e os arquivos saem com hash
no nome, o que permite cache eterno no navegador.

## ⚠️ Arquivos enviados

**No plano gratuito do Render o disco é efêmero.** Todo deploy, reinício ou
hibernação por inatividade apaga o que foi gravado em disco — inclusive os
modelos 3D que os alunos enviaram. Os registros no banco sobrevivem, mas o
arquivo some e o download passa a dar 404.

Três saídas, da mais simples à mais completa:

1. **Só aceitar link.** O formulário já permite enviar um link em vez de
   arquivo. Se a turma usa Drive ou OneDrive, dá para remover o campo de upload
   e o problema desaparece.
2. **Disco persistente do Render** (plano pago). Monte um disco, aponte
   `MEDIA_ROOT` para ele — por exemplo `/var/data/media` — e pronto. Há um
   exemplo comentado no `render.yaml`. Limitação: não funciona com mais de uma
   instância.
3. **Armazenamento de objetos** (S3, Cloudflare R2, Backblaze B2), via
   `django-storages`. É a solução que escala e a única que sobrevive a
   múltiplas instâncias. Exige uma conta no serviço e mais quatro variáveis de
   ambiente.

Enquanto nenhuma das três estiver em pé, trate o ambiente do Render como
demonstração, não como produção.

Duas outras coisas do plano gratuito: o serviço **hiberna após 15 minutos** sem
acesso, e o primeiro request depois disso demora cerca de 50 segundos; e o
banco gratuito **expira em 30 dias**.

## Produção fora do Render

Ajustes mínimos no `.env`:

```
DEBUG=False
SECRET_KEY=<chave gerada, nunca a de desenvolvimento>
ALLOWED_HOSTS=seu.dominio.br
DB_ENGINE=postgresql
DB_NAME=impressao3d
DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
```

Ou, se o provedor entregar a URL pronta, só `DATABASE_URL` — ela tem
precedência sobre as `DB_*`.

Depois é rodar `migrate` e `collectstatic --no-input`.

Vale limitar o tamanho do upload no servidor web, com `client_max_body_size`: o
limite de 25 MB que existe no formulário só é conferido depois do arquivo
chegar inteiro.

## Organização

`core` é onde está o domínio — o model `Models` é a solicitação de impressão e `HistoricoStatus` é o log de mudanças de status. `autenticacao` cuida só de login e logout. As configurações ficam em `Impressora3D/settings.py`.
