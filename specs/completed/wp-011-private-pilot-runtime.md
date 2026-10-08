# WP-011 — Runtime privado canônico do Client 0

Status: concluído  
Fase: F2 — operação assistida / preparação do piloto real  
Base: `origin/main` atual no início da execução

## Problema

A fundação F1 validou bind privado, auth, restore e lifecycle, mas o repositório ainda contém configuração legada incompatível com esse contrato:

- `docker-compose.yml` publica PostgreSQL em `0.0.0.0:5432`;
- `.env.example` contém `postgres/postgres`;
- README/AGENTS ainda descrevem auth, tenant isolation e Alembic como não implementados/futuros.

Antes de inserir dados reais no piloto, a configuração canônica do repositório precisa refletir o estado validado.

## Objetivo observável

1. PostgreSQL do Compose local publica somente em loopback;
2. credenciais não possuem default fraco;
3. senha é obrigatória;
4. porta do host é explícita e configurável;
5. volume persistente continua existindo para o piloto;
6. healthcheck do PostgreSQL existe;
7. configuração pode ser validada com credenciais sintéticas;
8. documentação não afirma dívida já resolvida;
9. nenhum recurso de validação permanece após o harness.

## Arquivos autorizados

Somente:

- `docker-compose.yml`;
- `.env.example`;
- novo `scripts/verify-private-compose.sh`;
- `docs/operations/client0-runbook.md`;
- `README.md`;
- `AGENTS.md`.

Nenhum código de aplicação, migration ou teste Python.

## docker-compose.yml

Manter apenas o serviço PostgreSQL existente e o volume persistente.

Contrato obrigatório:

- imagem `postgres:17`;
- remover `container_name` global fixo;
- `restart: unless-stopped` pode permanecer;
- exigir:
  - `POSTGRES_DB`;
  - `POSTGRES_USER`;
  - `POSTGRES_PASSWORD`;
  - `POSTGRES_PORT`;
- usar sintaxe Compose de variável obrigatória, sem defaults fracos;
- publicar exatamente:
  `127.0.0.1:${POSTGRES_PORT}:5432`;
- não publicar `0.0.0.0`;
- manter volume nomeado em `/var/lib/postgresql/data`;
- adicionar healthcheck com `pg_isready` usando as variáveis internas do container;
- não adicionar API, ERP, Ollama ou outro serviço ao Compose neste WP.

## .env.example

Deve ser seguro para copiar como template.

Pode incluir:

- `POSTGRES_PORT=55432`;
- `POSTGRES_DB=business_automation`;
- `POSTGRES_USER=business_automation`;
- `POSTGRES_PASSWORD=` vazio com comentário explícito para gerar segredo forte;
- `DATABASE_URL=` vazio, a ser preenchido coerentemente;
- `BA_ACCESS_IDENTITIES_JSON=[]` como default fail-closed;
- configuração Ollama existente pode permanecer.

Não incluir:

- `postgres:postgres`;
- token real;
- hash real;
- senha utilizável como default.

Incluir exemplo de geração **somente como comentário**, por exemplo:

`openssl rand -hex 32`

Não colocar o segredo gerado no comando documentado.

## Harness

Novo:

`scripts/verify-private-compose.sh`

Regras:

- não usar dados reais;
- não ler `.env`;
- criar arquivo env sintético único em `/tmp`;
- password aleatório de alta entropia;
- escolher porta loopback livre para a execução;
- usar project name Compose único com prefixo:
  `business-automation-wp011-`;
- executar `docker compose config`;
- subir somente `postgres`;
- esperar `pg_isready`;
- verificar via `docker inspect` que `5432/tcp` possui:
  - `HostIp = 127.0.0.1`;
  - `HostPort = porta sintética escolhida`;
- verificar que não existe bind `0.0.0.0` ou `::` para esse container;
- não executar migrations;
- não usar banco real;
- cleanup com:
  `docker compose -p <projeto-da-execucao> ... down -v --remove-orphans`;
- cleanup deve afetar apenas o projeto Compose da execução;
- remover env temporário;
- confirmar que nenhum container/volume/rede da execução permanece.

Não usar prune nem cleanup amplo.

Markers:

```text
PRIVATE_COMPOSE_CONFIG_OK
PRIVATE_COMPOSE_BIND_OK
PRIVATE_COMPOSE_POSTGRES_OK
PRIVATE_COMPOSE_CLEANUP_OK
PRIVATE_COMPOSE_VERIFIED
```

## Runbook

Adicionar seção curta "Runtime local persistente do piloto":

1. copiar `.env.example` para `.env` local não versionado;
2. gerar password forte;
3. preencher `POSTGRES_PASSWORD`;
4. preencher `DATABASE_URL` coerente com porta/user/db;
5. configurar `BA_ACCESS_IDENTITIES_JSON` fora do Git antes de dados reais;
6. executar `docker compose up -d postgres`;
7. confirmar health;
8. executar `uv run alembic upgrade head` somente contra esse DB explicitamente identificado;
9. iniciar Uvicorn em `127.0.0.1`;
10. confirmar health/auth antes de operar.

Deixar explícito:

- volume é persistente;
- `docker compose down -v` é destrutivo e não faz parte do shutdown normal do piloto;
- backup verificado precede qualquer operação destrutiva;
- API continua fora do Compose neste WP.

## README

Atualizar apenas o estado factual:

- migrations/recovery já validados;
- auth + tenant isolation implementados para piloto privado;
- backup/restore, lifecycle e startup privado validados;
- Opportunity e ProposalBrief agora fazem parte do domínio;
- API continua não autorizada para exposição pública;
- ERPNext ainda não integrado.

Não transformar README em changelog.

## AGENTS.md

Reconciliar apenas instruções obsoletas:

- entidades atuais incluem Opportunity e ProposalBrief;
- auth/tenant isolation existem e devem ser preservados;
- PostgreSQL/Alembic harness já existe;
- migrations continuam high-risk e exigem PostgreSQL descartável + segunda revisão;
- API continua não autorizada para exposição pública.

Não reescrever o arquivo inteiro.

## Validação obrigatória

```bash
bash -n scripts/verify-private-compose.sh
bash scripts/verify-private-compose.sh
uv run pytest
.venv/bin/python -m compileall app tests migrations
git diff --check
```

Acceptance:

- cinco markers aparecem;
- suíte Python atual inteira passa;
- compileall passa;
- diff check passa;
- nenhum recurso WP-011 permanece;
- diff limitado aos seis arquivos autorizados.

## Segunda revisão obrigatória

Este WP altera configuração operacional/deployment-like. Revisão independente deve verificar:

- bind somente loopback;
- nenhuma senha/default fraco;
- Compose exige password;
- harness não toca projeto/volume alheio;
- `down -v` ocorre somente no project name sintético da execução;
- `.env.example` permanece sem segredo;
- runbook não incentiva `down -v` no shutdown normal;
- nenhuma afirmação de exposição pública/produção.

## Não objetivos

Não:

- iniciar o runtime real;
- criar `.env` real;
- criar volume real do Client 0;
- inserir dados reais;
- instalar ERPNext;
- adicionar API ao Compose;
- systemd;
- reverse proxy;
- TLS;
- cloud;
- deploy público.

## Git

Branch:

`wp/011-private-pilot-runtime`

Commit sugerido:

`ops: harden private pilot runtime config`

Não mergear localmente.


## Resultado

Concluído em 2026-10-08.

- branch: `wp/011-private-pilot-runtime`;
- PR: #41;
- merge commit: `0d1981fc6837c32f0711b40b9e6f2fca53f91e56`;
- PostgreSQL Compose passou a publicar somente em `127.0.0.1`;
- `POSTGRES_PASSWORD` tornou-se obrigatório, sem default fraco;
- `.env.example` passou a ser fail-closed e sem segredo utilizável;
- volume persistente do piloto foi preservado;
- healthcheck PostgreSQL adicionado;
- harness Compose sintético e isolado validou config, bind, readiness e cleanup;
- runbook documenta startup/shutdown persistente e proíbe `down -v` como rotina normal;
- README/AGENTS foram reconciliados com auth, tenant isolation e Alembic já validados;
- `bash -n`: OK;
- harness Compose: todos os cinco markers presentes;
- `uv run pytest`: 25 passed;
- compileall e diff check passaram;
- nenhum container, volume, network ou arquivo temporário WP-011 permaneceu;
- segunda revisão independente: sem blockers e `OK_TO_MERGE: yes`.
