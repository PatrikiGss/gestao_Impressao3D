# Gestão de Impressoras 3D — IFSC Campus Lages

[![Testes](https://github.com/PatrikiGss/gestao_Impressao3D/actions/workflows/testes.yml/badge.svg)](https://github.com/PatrikiGss/gestao_Impressao3D/actions/workflows/testes.yml)
**Acesse:** [Impressão3D](https://gestao-impressao3d.onrender.com)
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

O banco é escolhido em três níveis. Se existir `DATABASE_URL`, ela vence — é o formato que Neon, Render e a maioria dos serviços entregam. Senão vale `DB_ENGINE`, que aceita `sqlite3` (padrão) ou `postgresql` com as variáveis `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` e `DB_PORT`.

## Deploy

A aplicação roda no Render e o banco fica no Neon. O `render.yaml` descreve o serviço web e o `build.sh` é o que o Render executa a cada deploy: instala as dependências, roda o `collectstatic` e aplica as migrations, abortando no primeiro erro em vez de publicar uma versão quebrada.

O domínio `.onrender.com` entra sozinho no `ALLOWED_HOSTS` e no `CSRF_TRUSTED_ORIGINS`, porque o settings lê a variável `RENDER_EXTERNAL_HOSTNAME` que o Render injeta. Pra domínio próprio, acrescente ele no `ALLOWED_HOSTS`.

Não há nginx na frente do Django: quem serve CSS e JS é o WhiteNoise, dentro do próprio processo. Em produção os arquivos saem com hash no nome, o que permite cache eterno no navegador.

Do lado do Neon, use a connection string do endpoint com `-pooler` no host. Ele passa por PgBouncer em modo transaction, e o settings detecta isso pelo nome e desliga os cursores no servidor, que esse modo não suporta. O banco hiberna depois de alguns minutos ocioso; a conexão é reaproveitada entre requests com verificação de saúde, então a conexão morta é descartada em vez de estourar no meio de uma tela.

## Arquivos enviados

No plano gratuito do Render o disco é efêmero. Todo deploy, reinício ou hibernação apaga o que foi gravado — inclusive os modelos 3D que os alunos enviaram. O registro no banco sobrevive, mas o arquivo some e o download passa a dar 404.

Três saídas. A mais simples é aceitar só link: o formulário já permite, e se a turma usa Drive ou OneDrive dá pra remover o campo de upload. A segunda é o disco persistente do Render, que é plano pago — monte o disco, aponte o `MEDIA_ROOT` pra ele e pronto, com a limitação de não funcionar com mais de uma instância. A terceira é armazenamento de objetos (S3, Cloudflare R2, Backblaze B2) via `django-storages`, que escala e é a única que sobrevive a múltiplas instâncias, mas exige conta no serviço e mais configuração.

Enquanto nenhuma delas estiver em pé, trate o ambiente do Render como demonstração, não como produção.

Vale também limitar o tamanho do upload no servidor web, com `client_max_body_size`: o limite de 25 MB que existe no formulário só é conferido depois do arquivo chegar inteiro.

## Organização

`core` é onde está o domínio — o model `Models` é a solicitação de impressão e `HistoricoStatus` é o log de mudanças de status. `autenticacao` cuida só de login e logout. As configurações ficam em `Impressora3D/settings.py`.
