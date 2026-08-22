# Gestão de Impressoras 3D — IFSC Campus Lages

Sistema web para gerenciar as solicitações de impressão 3D do laboratório.

- **Aluno** preenche um formulário público com seus dados, o arquivo do modelo (ou um link) e, opcionalmente, os parâmetros técnicos da impressão.
- **Administrador** faz login e acompanha as solicitações em três abas — *Pendentes*, *Em produção* e *Concluídos* —, baixa o arquivo enviado, entra em contato pelo WhatsApp e move o pedido entre os status.
- Toda mudança de status fica registrada num **histórico auditável** (quem mudou, de qual status para qual, quando), exportável em PDF pelo admin do Django.

Stack: Django 5.2 · Bootstrap 5 · SQLite (dev) / PostgreSQL (produção).

---

## Rodando localmente

Pré-requisito: **Python 3.12**.

### 1. Clonar e entrar na pasta

```bash
git clone <url-do-repo> && cd gestao_Impressao3D
```

### 2. Criar e ativar o ambiente virtual

Windows (PowerShell):

```bash
python -m venv venv; .\venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python3 -m venv venv && source venv/bin/activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar o ambiente

```bash
copy .env.example .env
```

No Linux/macOS use `cp .env.example .env`.

Os valores padrão do `.env.example` já bastam para desenvolvimento: `DEBUG=True` e `DB_ENGINE=sqlite3`. Nesse modo o projeto usa uma `SECRET_KEY` descartável e cria um `db.sqlite3` na raiz — não é preciso instalar banco nenhum.

### 5. Criar o banco

```bash
python manage.py migrate
```

### 6. Criar o usuário administrador

```bash
python manage.py createsuperuser
```

### 7. Subir o servidor

```bash
python manage.py runserver
```

| Rota | O quê | Acesso |
|---|---|---|
| `/` | Home | Público |
| `/cadastro/` | Formulário de solicitação | Público |
| `/lista/` | Painel de gerenciamento | Requer login |
| `/admin/` | Admin do Django e histórico | Requer login |
| `/accounts/login/` | Login | Público |

---

## Variáveis de ambiente

Todas ficam no `.env` (que **não** é versionado). O `.env.example` é o modelo.

| Variável | Padrão | Descrição |
|---|---|---|
| `DEBUG` | `False` | `True` em desenvolvimento. Nunca `True` em produção. |
| `SECRET_KEY` | *(vazio)* | Obrigatória quando `DEBUG=False`. Com `DEBUG=True` o projeto usa uma chave descartável. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Domínios permitidos, separados por vírgula. |
| `DB_ENGINE` | `sqlite3` | `sqlite3` ou `postgresql`. |
| `DB_NAME` | — | Só lida se `DB_ENGINE` não for `sqlite3`. |
| `DB_USER` | — | idem |
| `DB_PASSWORD` | — | idem |
| `DB_HOST` | `localhost` | idem |
| `DB_PORT` | `5432` | idem |

Para gerar uma `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Produção

Ajustes mínimos no `.env`:

```
DEBUG=False
SECRET_KEY=<chave gerada, nunca a de desenvolvimento>
ALLOWED_HOSTS=seu.dominio.br
DB_ENGINE=postgresql
DB_NAME=impressao3d
DB_USER=postgres
DB_PASSWORD=<senha>
DB_HOST=localhost
DB_PORT=5432
```

Depois:

```bash
python manage.py migrate && python manage.py collectstatic --noinput
```

Com `DEBUG=False` o Django deixa de servir os arquivos de `MEDIA_ROOT` e de `STATIC_ROOT` — isso passa a ser responsabilidade do servidor web (nginx, Apache) ou do WhiteNoise.

---

## Estrutura

```
gestao_Impressao3D/
├── Impressora3D/       # settings, urls e wsgi do projeto
├── core/               # solicitações de impressão: models, form, lista, histórico
├── autenticacao/       # login e logout
├── staticfiles/        # saída do collectstatic
└── manage.py
```

O app `core` concentra o domínio: `Models` é a solicitação de impressão e `HistoricoStatus` é o log de mudanças de status.
