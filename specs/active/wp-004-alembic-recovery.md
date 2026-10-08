# WP-004 — Reparar cadeia Alembic para banco vazio e baseline legacy

Status: pronto para execução local  
Base: `origin/main` atual no início da execução  
Executor: agente local autorizado com Git, shell e Docker; Continue Agent é o executor preferido atual  
Motivo para execução local: altera migrations e precisa validar PostgreSQL 17 real descartável em dois cenários.

Esta spec é **autossuficiente**. Não carregar `AGENTS.md`, histórico de chat ou WPs anteriores.

## Objetivo observável

Reparar a cadeia Alembic com o menor conjunto de mudanças necessário para que:

1. PostgreSQL totalmente vazio execute `alembic upgrade head` com sucesso;
2. um banco legacy sintético já marcado na baseline `7c83bbc2b9f7`, contendo um lead pré-Company, também execute `upgrade head` com sucesso;
3. o lead legacy seja preservado;
4. `company_id` seja preenchido de forma determinística e segura antes de virar NOT NULL;
5. nenhuma mudança de auth, membership, API, tenant runtime ou infraestrutura seja misturada.

ADR obrigatório: `docs/architecture/adr/0002-migration-recovery.md`.

## Contexto suficiente

Defeitos conhecidos da cadeia atual:

### Defeito 1 — raiz vazia

- `7c83bbc2b9f7` é uma baseline vazia;
- `1a2fcfdc65b1` altera `leads`;
- banco vazio não possui `leads`.

A branch histórica `chore/migration-baseline-review` contém uma migration candidata `0f4bc1c903c6_bootstrap_leads_schema.py`. Ela pode ser usada **somente como referência de conteúdo**. Não fazer cherry-pick da branch.

### Defeito 2 — Company sem backfill

- `4749a8ea474b` adiciona `company_id` nullable;
- `6db09cfda379` muda a coluna para NOT NULL;
- não existe backfill;
- qualquer lead legacy existente quebra essa migration.

## Preflight Git

1. `git fetch origin main`.
2. Confirmar branch `wp/004-alembic-recovery`.
3. Confirmar `HEAD == origin/main` antes da primeira alteração.
4. Confirmar working tree limpo.
5. Se branch/base/worktree divergirem, parar e relatar; não corrigir automaticamente.
6. Não usar `git clean`, `reset --hard`, rebase ou force-push.

## Pode alterar

Somente:

- novo `migrations/versions/0f4bc1c903c6_bootstrap_leads_schema.py`;
- `migrations/versions/7c83bbc2b9f7_baseline_existing_schema.py`;
- `migrations/versions/6db09cfda379_require_company_for_leads.py`;
- `scripts/verify-alembic-postgres.sh`.

Nenhum outro arquivo.

## Implementação obrigatória

### 1. Bootstrap pré-baseline

Criar revision `0f4bc1c903c6` como nova raiz Alembic.

Ela deve criar `leads` exatamente no formato pré-baseline:

- `id` integer PK;
- `name` string(120) NOT NULL;
- `phone` string(30) NOT NULL;
- `source` string(50) NOT NULL;
- `interest` string(255) nullable;
- `status` string(30) NOT NULL.

Não incluir:

- timestamps;
- `company_id`;
- índices/constraints futuros;
- dados seed.

`down_revision = None`.

### 2. Baseline histórica

Alterar somente o encadeamento de `7c83bbc2b9f7`:

`down_revision = "0f4bc1c903c6"`

O corpo da baseline continua vazio.

### 3. Backfill antes do NOT NULL

Em `6db09cfda379_require_company_for_leads.py`, antes de `alter_column(... nullable=False)`:

1. contar leads com `company_id IS NULL`;
2. se zero:
   - não criar Company artificial;
   - seguir para NOT NULL;
3. se houver leads nulos:
   - obter IDs das Companies existentes;
4. se zero Companies:
   - criar exatamente uma Company:
     - `name = "Legacy Workspace"`;
     - `slug = "legacy-workspace"`;
   - obter seu ID;
5. se exatamente uma Company:
   - usar seu ID;
6. se mais de uma Company:
   - abortar com erro explícito;
   - não escolher Company automaticamente;
7. atualizar apenas leads com `company_id IS NULL`;
8. somente então tornar `company_id` NOT NULL.

Usar `op.get_bind()` + SQLAlchemy/SQL explícito e parametrizado.

Não usar ORM da aplicação dentro da migration.

Não criar placeholder quando não existem leads a migrar.

### 4. Downgrade

O downgrade de `6db09cfda379` continua apenas tornando `company_id` nullable.

Não tentar apagar automaticamente `Legacy Workspace` no downgrade, porque após upgrade pode haver dados novos associados a ela.

### 5. Harness

Evoluir `scripts/verify-alembic-postgres.sh`.

Manter todas as garantias já existentes:

- PostgreSQL 17;
- container único desta execução;
- nome prefixado por `business-automation-alembic-wp004-`;
- sem volume;
- porta host aleatória;
- bind somente `127.0.0.1`;
- credenciais efêmeras;
- não imprimir senha/URL completa;
- não instalar dependências;
- não ler/sourcear `.env`;
- cleanup via trap;
- não tocar containers preexistentes;
- sem `set -e`.

Use senha de admin do container também efêmera; não usar `POSTGRES_PASSWORD=postgres`.

O harness deve executar **dois cenários independentes** dentro do recurso descartável.

## Cenário A — fresh database

Em um database vazio:

1. executar `alembic upgrade head`;
2. exigir exit 0;
3. verificar `alembic current`;
4. verificar que há exatamente um head;
5. executar `alembic check`;
6. considerar erro qualquer drift inesperado;
7. verificar que nenhuma Company com slug `legacy-workspace` foi criada.

Saída inequívoca:

`FRESH_DATABASE_UPGRADE_OK`

## Cenário B — legacy baseline

Criar outro database sintético no mesmo container ou recurso igualmente isolado.

Antes de Alembic:

1. criar manualmente somente a tabela `leads` pré-baseline;
2. inserir exatamente um lead sintético com valores conhecidos;
3. não criar `companies`;
4. executar `alembic stamp 7c83bbc2b9f7` apenas neste database legacy;
5. executar `alembic upgrade head`.

Depois exigir:

- upgrade exit 0;
- mesmo `id`, `name`, `phone`, `source`, `interest` e `status` do lead;
- `created_at` e `updated_at` não nulos;
- `company_id` não nulo;
- FK aponta para Company existente;
- existe exatamente uma Company `Legacy Workspace` / `legacy-workspace`;
- `alembic current` está no head.

Saída inequívoca:

`LEGACY_BASELINE_UPGRADE_OK`

No final, após ambos:

`ALEMBIC_RECOVERY_VERIFIED`

## Teste adicional da regra ambígua

Sem criar terceiro container, usar database sintético adicional ou fixture no mesmo PostgreSQL descartável para provar:

- existem dois registros em `companies`;
- existe lead com `company_id IS NULL`;
- ao executar a revision que exige Company, a migration não escolhe silenciosamente uma delas;
- o processo falha com mensagem explícita de mapeamento ambíguo.

Este teste não precisa chegar a `head`.

Saída inequívoca:

`AMBIGUOUS_COMPANY_MAPPING_REJECTED`

## Proibições

Não alterar:

- `app/**`;
- `tests/**`;
- outras migrations;
- auth/RBAC/membership;
- Docker Compose;
- dependências;
- `.env*`;
- docs/ADRs;
- configurações do Continue/Pi;
- serviço Qwen;
- infraestrutura do host.

Também proibido:

- `Base.metadata.create_all`;
- usar banco real;
- usar `stamp` no cenário fresh;
- cherry-pick da branch histórica;
- criar migration extra além de `0f4bc1c903c6`;
- esconder falha com `|| true` fora de cleanup;
- modificar dados para fazer o teste passar sem refletir a política do ADR.

## Aceite

### A1 — cadeia

```bash
uv run alembic history
uv run alembic heads
```

Deve existir uma única cadeia/head.

### A2 — harness

```bash
bash -n scripts/verify-alembic-postgres.sh
bash scripts/verify-alembic-postgres.sh
```

Deve terminar 0 e emitir as quatro confirmações:

```text
FRESH_DATABASE_UPGRADE_OK
LEGACY_BASELINE_UPGRADE_OK
AMBIGUOUS_COMPANY_MAPPING_REJECTED
ALEMBIC_RECOVERY_VERIFIED
```

### A3 — invariantes

```bash
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
```

Suíte existente continua verde.

### A4 — cleanup

Após o harness:

```bash
docker ps -a --format '{{.Names}}' | grep '^business-automation-alembic-wp004-'
```

não retorna nada.

### A5 — escopo

```bash
git diff --name-only origin/main...HEAD
```

deve listar somente:

```text
migrations/versions/0f4bc1c903c6_bootstrap_leads_schema.py
migrations/versions/7c83bbc2b9f7_baseline_existing_schema.py
migrations/versions/6db09cfda379_require_company_for_leads.py
scripts/verify-alembic-postgres.sh
```

## Stop conditions

Parar sem expandir escopo se:

- `alembic check` revelar drift que exige outro arquivo/migration;
- a cadeia tiver mais de um head inesperadamente;
- o schema real divergir do pressuposto pré-baseline;
- a regra de Company exigir decisão de negócio diferente do ADR;
- Docker/PostgreSQL não estiver operacional;
- qualquer teste exigir banco/serviço real;
- surgir necessidade de alterar auth/tenant/app.

## Encerramento GitHub-first

Quando tudo passar:

1. revisar diff/status;
2. adicionar somente os quatro arquivos autorizados;
3. commit sugerido: `fix: repair Alembic bootstrap and legacy backfill`;
4. push somente da branch `wp/004-alembic-recovery`;
5. não fazer merge;
6. não iniciar WP seguinte;
7. parar.

ChatGPT fará review pelo GitHub.

## Economia de contexto

- ler esta spec;
- ler somente as migrations/scripts diretamente envolvidos;
- não carregar `AGENTS.md`;
- não fazer inventário amplo do repo;
- não pesquisar auth/tenant;
- não ler a branch histórica além da migration bootstrap se realmente necessário.
