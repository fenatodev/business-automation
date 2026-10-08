# WP-006 — Backup/restore PostgreSQL descartável e runbook Client 0

Status: pronto para execução local  
Base: `origin/main` atual no início da execução  
Executor preferido: Continue Agent local  
Motivo para execução local: exige Docker/PostgreSQL real descartável e validação de backup/restore.

Esta spec é **autossuficiente**. Não carregar `AGENTS.md`, WPs anteriores ou histórico de chat.

## Objetivo observável

Demonstrar que o schema atual do Business Automation pode ser:

1. criado do zero via Alembic em PostgreSQL 17 descartável;
2. populado somente com dados sintéticos;
3. exportado por `pg_dump`;
4. restaurado em um segundo banco vazio;
5. validado após restore com dados e relacionamentos preservados;
6. operado por um runbook mínimo sem depender da máquina real, banco real ou segredos reais.

Nenhum deploy, serviço persistente, backup de dados reais ou mudança de schema faz parte deste WP.

## Pode alterar somente

- novo `scripts/verify-postgres-backup-restore.sh`;
- novo `docs/operations/client0-runbook.md`.

Nenhum outro arquivo.

## Regras de segurança

- PostgreSQL 17 em container descartável.
- Prefixo obrigatório do container:
  `business-automation-backup-wp006-`.
- Sem volumes persistentes.
- Porta host aleatória publicada **somente em 127.0.0.1**.
- Credenciais efêmeras exclusivas da execução.
- Não usar `POSTGRES_PASSWORD=postgres`.
- Não imprimir senha nem DATABASE_URL completa.
- Não instalar dependências.
- Não criar/modificar `.env`.
- Não tocar em banco real.
- Não usar dados reais.
- Cleanup remove somente recursos criados pelo próprio script.
- Arquivo temporário de backup deve ficar fora do repositório e ser removido pelo trap.
- Não usar `docker compose down`, prune ou limpeza ampla.
- Não usar `set -e`; tratar falhas explicitamente.

## Implementação do harness

Criar `scripts/verify-postgres-backup-restore.sh`.

### 1. Preflight antes do container

Confirmar somente:

- Docker disponível;
- exatamente um head Alembic;
- diretório do repositório não contém artefato de backup desta execução;
- não existe container remanescente com prefixo `business-automation-backup-wp006-`.

Se já existir container com esse prefixo, **parar e relatar**. Não removê-lo automaticamente, pois pode pertencer a outra execução.

Não criar container auxiliar para preflight.

### 2. Container único

Subir **exatamente um** PostgreSQL 17 descartável nesta execução:

- nome único começando por `business-automation-backup-wp006-`;
- usar o entrypoint/CMD padrão da imagem oficial `postgres:17`;
- **não** sobrescrever o comando da imagem com `postgres`, `pg_ctl` ou outro processo;
- bind exatamente no formato `127.0.0.1::5432`, deixando o Docker escolher a porta host;
- admin/user/password efêmeros e exclusivos da execução;
- sem volume;
- nenhum container auxiliar, inclusive para diagnóstico.

Aguardar readiness **no próprio container**, por exemplo:

```bash
docker exec "$CONTAINER_NAME" \
  pg_isready -U "$DB_ADMIN" -d postgres
```

Não usar a porta host para o teste interno de readiness.

Se o readiness falhar:

1. inspecionar `docker logs "$CONTAINER_NAME"` do mesmo container;
2. relatar a causa;
3. encerrar a execução;
4. deixar o trap remover somente esse container.

Não criar outro container para investigar.

Depois que o container estiver ready, confirmar **dentro dele**:

```bash
docker exec "$CONTAINER_NAME" pg_dump --version
docker exec "$CONTAINER_NAME" pg_restore --version
```

Se algum binário não estiver disponível, parar conforme as stop conditions.

### 3. Banco fonte

Criar banco fonte sintético.

Executar:

```bash
DATABASE_URL=<efêmera> uv run alembic upgrade head
```

Confirmar `alembic current` no head.

### 4. Fixture sintética — usar exatamente o schema atual

Não inferir nomes de tabela/coluna a partir de domínio, modelos antigos ou memória. O contrato para este WP é o schema Alembic atual em `main`.

Usar **exatamente** estas tabelas e colunas relevantes:

- `companies(id INTEGER, name VARCHAR(120), slug VARCHAR(80), created_at ...)`;
- `leads(id INTEGER, company_id INTEGER, name VARCHAR(120), phone VARCHAR(30), source VARCHAR(50), interest VARCHAR(255) NULL, status VARCHAR(30), created_at ..., updated_at ...)`;
- `customers(id INTEGER, company_id INTEGER, lead_id INTEGER NULL UNIQUE, name VARCHAR(120), phone VARCHAR(30), email VARCHAR(120) NULL, created_at ..., updated_at ...)`;
- `conversations(id INTEGER, company_id INTEGER, lead_id INTEGER NULL, customer_id INTEGER NULL, channel VARCHAR(30), status VARCHAR(30), created_at ..., updated_at ...)`;
- `messages(id INTEGER, conversation_id INTEGER, sender_type VARCHAR(20), content TEXT/VARCHAR, created_at ...)`.

Todos os IDs usados na fixture são **inteiros**, não strings.

Fixture obrigatória:

- Company:
  - `id = 101`
  - `name = 'WP006 Synthetic Company'`
  - `slug = 'wp006-synthetic-company'`
- Lead:
  - `id = 201`
  - `company_id = 101`
  - `name = 'WP006 Synthetic Lead'`
  - `phone = '11000000000'`
  - `source = 'wp006-test'`
  - `interest = 'backup-restore'`
  - `status = 'new'`
- Customer:
  - `id = 301`
  - `company_id = 101`
  - `lead_id = 201`
  - `name = 'WP006 Synthetic Customer'`
  - `phone = '11000000001'`
  - `email = 'wp006@example.invalid'`
- Conversation:
  - `id = 401`
  - `company_id = 101`
  - `lead_id = NULL`
  - `customer_id = 301`
  - `channel = 'web'`
  - `status = 'open'`
- Messages:
  - `id = 501`, `conversation_id = 401`, `sender_type = 'customer'`, `content = 'WP006 synthetic customer message'`
  - `id = 502`, `conversation_id = 401`, `sender_type = 'agent'`, `content = 'WP006 synthetic agent message'`

Deixar timestamps para os defaults do banco quando possível.

Inserir diretamente no PostgreSQL, sem ORM e sem API externa.

Não usar tabelas singulares como `company`, `lead`, `customer`, `conversation` ou `message`.

Não adicionar colunas inexistentes como `subject`, `is_from_customer`, `messages.company_id`, `messages.customer_id` ou `messages.lead_id`.

Não desabilitar foreign keys/constraints.

### 5. Backup

Criar backup lógico em formato custom do PostgreSQL usando o `pg_dump` **do mesmo container**.

Fluxo esperado:

```bash
docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
  pg_dump -U "$DB_ADMIN" -d "$SOURCE_DB" -Fc > "$BACKUP_FILE"
```

Não usar `--verbose` redirecionando stdout e stderr juntos para o arquivo de backup. O dump custom deve receber **somente stdout binário**. Se quiser capturar diagnóstico, redirecionar stderr separadamente para variável/arquivo temporário de texto fora do repo.

O arquivo deve ficar no host em caminho temporário único fora do repositório, por exemplo `/tmp/business-automation-wp006-...`.

Não exigir `pg_dump` instalado no host.

Validar:

- comando terminou com sucesso;
- arquivo existe;
- arquivo tem tamanho > 0.

Não imprimir conteúdo binário.

### 6. Restore

Criar um segundo banco vazio **no mesmo container**.

Restaurar usando o `pg_restore` do mesmo container, alimentado pelo arquivo temporário do host pela entrada padrão, por exemplo:

```bash
docker exec -i -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
  pg_restore -U "$DB_ADMIN" -d "$RESTORE_DB" < "$BACKUP_FILE"
```

Não passar `"$BACKUP_FILE"` como caminho para `pg_restore` dentro do container; esse caminho existe no host, não dentro do container.

Não exigir `pg_restore` instalado no host.

Não executar migrations no banco restaurado antes do restore.

### 7. Validação pós-restore

No banco restaurado, verificar:

- Alembic version restaurada corresponde ao head;
- exatamente 1 Company sintética;
- exatamente 1 Lead;
- exatamente 1 Customer;
- exatamente 1 Conversation;
- exatamente 2 Messages;
- `leads.company_id = customers.company_id = conversations.company_id = 101`;
- `customers.lead_id = 201`;
- `conversations.customer_id = 301` e `conversations.lead_id IS NULL`;
- as duas rows de `messages` têm `conversation_id = 401`;
- conteúdos, nomes, slug, telefone, source, interest, status e email da fixture obrigatória foram preservados.

Emitir:

```text
POSTGRES_BACKUP_CREATED_OK
POSTGRES_RESTORE_OK
POSTGRES_RESTORE_DATA_VERIFIED
BACKUP_RESTORE_VERIFIED
```

### 8. Cleanup

Ao terminar, com sucesso ou falha:

- remover somente o container desta execução;
- remover somente o backup temporário desta execução;
- deixar zero containers com prefixo WP-006 desta execução;
- não deixar arquivo de dump no repo.

## Runbook

Criar `docs/operations/client0-runbook.md`.

Deve ser curto e operacional, com:

### Estado atual

- piloto privado somente;
- API não autorizada para exposição pública;
- acesso por Bearer conforme ADR 0003;
- PostgreSQL é fonte operacional do core;
- ERP/financeiro continuam fontes autoritativas onde já definido.

### Startup privado

Documentar apenas regras, sem inventar infraestrutura:

- bind privado/loopback ou rede privada autorizada;
- nunca `0.0.0.0` sem gate posterior;
- segredos fora do Git;
- health check `GET /`;
- como confirmar que API não está exposta publicamente.

Não criar systemd/deploy neste WP.

### Backup

Explicar:

- backup lógico PostgreSQL;
- arquivo protegido fora do repo;
- registro de data/ambiente;
- verificação de exit code e tamanho;
- nunca considerar backup válido sem restore drill periódico.

### Restore

Procedimento genérico para restaurar em banco novo/isolado primeiro.

Proibir restore destrutivo sobre banco ativo sem procedimento próprio futuro.

### Incidente mínimo

Checklist:

1. parar escrita/efeitos externos quando aplicável;
2. preservar evidências/logs;
3. identificar último backup conhecido;
4. restaurar em ambiente isolado;
5. validar schema + dados;
6. só promover retorno após revisão humana.

### Segredos

Nunca registrar token Bearer, token hash, password, DATABASE_URL completa ou dados reais no Git/logs de exemplo.

## Validação obrigatória

Executar e registrar os resultados:

```bash
bash -n scripts/verify-postgres-backup-restore.sh
bash scripts/verify-postgres-backup-restore.sh
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
```

Acceptance:

- harness sai 0;
- quatro markers presentes;
- testes existentes continuam verdes;
- compileall passa;
- diff check passa;
- nenhum container da execução atual permanece;
- nenhum container auxiliar foi criado;
- nenhum dump ficou no repositório;
- diff contém somente os dois arquivos autorizados.

## Stop conditions

Parar e relatar se:

- Alembic não chegar ao head no banco fonte;
- schema atual não permitir fixture coerente sem mudança de schema;
- `pg_dump` ou `pg_restore` não estiver disponível dentro do único container PostgreSQL 17;
- já existir container remanescente com prefixo WP-006 antes da execução;
- restore exigir migration extra;
- surgir necessidade de volume persistente;
- surgir necessidade de banco real;
- qualquer mudança fora dos dois arquivos autorizados for necessária.

Não corrigir schema, auth, migrations ou aplicação neste WP.

## Git

Branch:

`wp/006-postgres-backup-restore`

Commit sugerido:

`ops: verify PostgreSQL backup and restore`

Push somente da branch do WP.

Não mergear.

Após push, parar e informar branch + commit.
