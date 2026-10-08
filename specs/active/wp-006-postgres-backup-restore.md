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

### 1. Preflight

Confirmar:

- Docker disponível;
- exatamente um head Alembic;
- `pg_dump` e `pg_restore` disponíveis no container PostgreSQL 17;
- diretório do repositório não recebe artefato de backup.

### 2. Container

Subir um único PostgreSQL 17 descartável:

- nome único com prefixo WP-006;
- bind `127.0.0.1::5432`;
- admin/user/password efêmeros;
- sem volume.

Aguardar `pg_isready`.

### 3. Banco fonte

Criar banco fonte sintético.

Executar:

```bash
DATABASE_URL=<efêmera> uv run alembic upgrade head
```

Confirmar `alembic current` no head.

### 4. Fixture sintética

Inserir diretamente no PostgreSQL, sem ORM e sem API externa, uma fixture mínima coerente contendo:

- 1 Company;
- 1 Lead da Company;
- 1 Customer da mesma Company vinculado ao Lead quando o schema permitir;
- 1 Conversation da mesma Company vinculada ao Customer ou Lead conforme o schema;
- 2 Messages na Conversation.

Usar valores claramente sintéticos.

Não desabilitar foreign keys/constraints.

### 5. Backup

Criar backup lógico em formato custom do PostgreSQL:

`pg_dump -Fc`.

O arquivo deve ficar em caminho temporário único, por exemplo `/tmp/business-automation-wp006-...`.

Validar:

- comando terminou com sucesso;
- arquivo existe;
- arquivo tem tamanho > 0.

Não imprimir conteúdo binário.

### 6. Restore

Criar um segundo banco vazio no mesmo container.

Restaurar o backup usando `pg_restore`.

Não executar migrations no banco restaurado antes do restore.

### 7. Validação pós-restore

No banco restaurado, verificar:

- Alembic version restaurada corresponde ao head;
- exatamente 1 Company sintética;
- exatamente 1 Lead;
- exatamente 1 Customer;
- exatamente 1 Conversation;
- exatamente 2 Messages;
- `company_id` permanece coerente em Lead/Customer/Conversation;
- Customer/Lead linkage, se existente na fixture, foi preservado;
- Messages apontam para a Conversation correta;
- dados textuais sintéticos esperados foram preservados.

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
- zero containers WP-006 remanescentes;
- nenhum dump ficou no repositório;
- diff contém somente os dois arquivos autorizados.

## Stop conditions

Parar e relatar se:

- Alembic não chegar ao head no banco fonte;
- schema atual não permitir fixture coerente sem mudança de schema;
- `pg_dump` ou `pg_restore` não estiver disponível no PostgreSQL 17;
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
