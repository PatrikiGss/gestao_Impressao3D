# Gestão de Impressoras 3D — IFSC Campus Lages

[![Testes](https://github.com/PatrikiGss/gestao_Impressao3D/actions/workflows/testes.yml/badge.svg)](https://github.com/PatrikiGss/gestao_Impressao3D/actions/workflows/testes.yml)

**Acesse:** [Gestão de Impressões 3D](https://gestao-impressao3d.onrender.com)

Sistema web desenvolvido para organizar e gerenciar a fila de solicitações de impressão 3D do laboratório do **IFSC — Campus Lages**.

O aluno pode realizar uma solicitação por meio de um formulário público, informando seus dados e enviando o arquivo do modelo 3D ou um link para ele. A equipe responsável pelo laboratório possui acesso autenticado ao sistema para acompanhar e gerenciar as solicitações.

Cada solicitação pode ser acompanhada pelos seguintes status:

* **Pendente**
* **Em produção**
* **Concluído**

A equipe pode baixar os arquivos enviados, entrar em contato com o aluno pelo WhatsApp e atualizar o status da solicitação. Cada alteração de status é registrada com o responsável e a data da alteração.

O histórico das solicitações também pode ser consultado e exportado em PDF por meio do painel administrativo do Django.

## Tecnologias

* **Python 3.12**
* **Django 5.2**
* **Bootstrap 5**
* **SQLite** para desenvolvimento
* **PostgreSQL** para produção
* **WhiteNoise** para arquivos estáticos
* **Render** para hospedagem da aplicação
* **Neon** para o banco de dados PostgreSQL

## Executando localmente

### Requisitos

É necessário ter o **Python 3.12** instalado.

### Instalação

Clone o repositório e entre na pasta do projeto:

```bash
git clone https://github.com/PatrikiGss/gestao_Impressao3D.git
cd gestao_Impressao3D
```

Crie e ative um ambiente virtual:

```bash
python -m venv venv
```

No Windows:

```powershell
venv\Scripts\activate
```

No Linux/macOS:

```bash
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie o arquivo `.env` a partir do modelo:

```powershell
copy .env.example .env
```

No Linux/macOS:

```bash
cp .env.example .env
```

Execute as migrations:

```bash
python manage.py migrate
```

Crie um usuário administrador:

```bash
python manage.py createsuperuser
```

Inicie o servidor:

```bash
python manage.py runserver
```

O sistema estará disponível em:

```text
http://127.0.0.1:8000/
```

### Desenvolvimento

Os valores presentes no `.env.example` são suficientes para executar o projeto localmente.

Por padrão:

```env
DEBUG=True
DB_ENGINE=sqlite3
```

Nesse modo, o projeto utiliza SQLite e cria automaticamente o arquivo `db.sqlite3` na raiz do projeto. Não é necessário instalar ou configurar um servidor de banco de dados.

### Acesso

As seguintes áreas são públicas:

* Página inicial
* Formulário de solicitação de impressão

As seguintes áreas exigem autenticação:

* Lista de solicitações
* Edição de solicitações
* Painel administrativo

## Testes

Os testes podem ser executados com:

```bash
python manage.py test
```

O projeto também possui integração contínua configurada no GitHub Actions.

A cada push, o workflow executa:

* Testes automatizados
* Verificação de migrations pendentes
* `check --deploy`

A configuração está disponível em:

```text
.github/workflows/testes.yml
```

As ferramentas de lint e desenvolvimento ficam separadas em `requirements-dev.txt` e não são instaladas no ambiente de produção.

## Configuração

As configurações específicas do ambiente ficam no arquivo `.env`.

O arquivo `.env` não deve ser versionado no Git. O arquivo `.env.example` serve como modelo para configuração do ambiente.

### Variáveis principais

`DEBUG` controla o modo de desenvolvimento. Em produção, deve permanecer desativado:

```env
DEBUG=False
```

Quando `DEBUG=False`, a `SECRET_KEY` precisa estar configurada e o domínio utilizado pela aplicação deve estar presente em `ALLOWED_HOSTS`.

Uma nova `SECRET_KEY` pode ser gerada com:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Banco de dados

O banco pode ser configurado de duas formas.

Se `DATABASE_URL` estiver definida, ela terá prioridade. Esse é o formato utilizado por serviços como Neon e Render.

Caso contrário, o banco pode ser configurado individualmente utilizando:

```env
DB_ENGINE=postgresql
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
```

Para desenvolvimento, basta utilizar:

```env
DB_ENGINE=sqlite3
```

## Deploy

A aplicação está hospedada no **Render**, enquanto o banco de dados PostgreSQL está hospedado no **Neon**.

O arquivo `render.yaml` descreve a configuração do serviço e o `build.sh` é executado durante o processo de deploy.

O processo de build realiza:

1. Instalação das dependências
2. Coleta dos arquivos estáticos
3. Aplicação das migrations

Caso alguma etapa apresente erro, o deploy é interrompido.

### Render

O domínio `.onrender.com` é adicionado automaticamente ao `ALLOWED_HOSTS` e ao `CSRF_TRUSTED_ORIGINS` por meio da variável `RENDER_EXTERNAL_HOSTNAME`, disponibilizada pelo próprio Render.

Para utilizar um domínio próprio, ele deve ser adicionado à configuração de `ALLOWED_HOSTS` e, quando necessário, de `CSRF_TRUSTED_ORIGINS`.

A aplicação não utiliza nginx. Os arquivos estáticos são servidos pelo **WhiteNoise** diretamente pela aplicação Django.

Em produção, os arquivos estáticos são armazenados com hash nos nomes, permitindo que o navegador utilize cache de longa duração.

### Neon

Para o PostgreSQL do Neon, é recomendado utilizar a connection string do endpoint com `-pooler` no host.

Esse endpoint utiliza o PgBouncer em modo transaction. O projeto identifica esse tipo de conexão e desativa os cursores no servidor, que não são compatíveis com esse modo de operação.

O banco pode entrar em estado de suspensão após um período de inatividade. A aplicação utiliza verificação da conexão para descartar conexões que tenham sido encerradas antes de reutilizá-las.

## Arquivos enviados

Existe uma limitação importante no ambiente gratuito do Render: o armazenamento local é **efêmero**.

Isso significa que arquivos gravados no disco da aplicação podem ser apagados durante:

* Novo deploy
* Reinicialização da aplicação
* Hibernação
* Outras operações de infraestrutura

No caso deste projeto, isso afeta diretamente os arquivos de modelos 3D enviados pelos alunos.

O registro da solicitação permanece no PostgreSQL, mas o arquivo armazenado localmente pode desaparecer. Nesse caso, o download do modelo deixará de funcionar.

### Alternativas

Existem três opções principais para resolver esse problema:

**1. Utilizar apenas links**

O formulário já permite informar um link para o arquivo. Serviços como Google Drive e OneDrive podem ser utilizados para armazenar os modelos.

É a alternativa mais simples e não exige alterações significativas no projeto.

**2. Utilizar Persistent Disk do Render**

O Render oferece armazenamento persistente em planos pagos.

Nesse cenário, o `MEDIA_ROOT` pode ser direcionado para o disco persistente.

Essa solução possui limitações relacionadas à execução de múltiplas instâncias da aplicação.

**3. Utilizar armazenamento de objetos**

Serviços como:

* Amazon S3
* Cloudflare R2
* Backblaze B2

podem ser utilizados em conjunto com `django-storages`.

Essa é a solução mais adequada para uma aplicação que precise escalar ou executar múltiplas instâncias, embora exija configuração adicional.

Enquanto uma dessas soluções não estiver implementada, o ambiente hospedado no Render deve ser considerado **demonstração**, e não um ambiente de produção confiável para armazenamento dos arquivos enviados.

### Limite de upload

O formulário possui um limite de **25 MB** para arquivos enviados.

Esse limite é validado pela aplicação depois que o arquivo chega ao servidor. Portanto, ele não impede que um arquivo maior seja transferido até a aplicação antes de ser rejeitado.

Em uma infraestrutura que utilize nginx ou outro servidor web reverso, também é recomendável configurar um limite de tamanho de requisição no próprio servidor.

## Estrutura do projeto

A aplicação é organizada principalmente em duas aplicações Django:

```text
core/
└── Lógica principal do sistema
    ├── Models
    └── HistoricoStatus

autenticacao/
└── Autenticação
    ├── Login
    └── Logout

Impressora3D/
└── Configurações do projeto
    └── settings.py
```

O app `core` concentra as regras relacionadas às solicitações de impressão.

O model `Models` representa uma solicitação de impressão, enquanto `HistoricoStatus` registra as alterações de status realizadas durante o processamento.

O app `autenticacao` concentra as funcionalidades de login e logout.

As configurações gerais do Django ficam em:

```text
Impressora3D/settings.py
```

## Licença

Este projeto está disponível sob a licença definida no arquivo [`LICENSE`](LICENSE).
