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

## Produção

O mínimo no `.env`:

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

Depois é rodar `migrate` e `collectstatic --noinput`.

Com `DEBUG=False` o Django para de servir `MEDIA_ROOT` e `STATIC_ROOT` — quem faz isso passa a ser o nginx (ou o WhiteNoise). Vale também limitar o tamanho do upload lá no servidor web, com `client_max_body_size`: o limite de 25 MB que existe no formulário só é conferido depois do arquivo chegar inteiro.

## Organização

`core` é onde está o domínio — o model `Models` é a solicitação de impressão e `HistoricoStatus` é o log de mudanças de status. `autenticacao` cuida só de login e logout. As configurações ficam em `Impressora3D/settings.py`.
