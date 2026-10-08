# ADR 0002 — Recuperação da cadeia Alembic

Data: 2026-10-08  
Status: Accepted  
Escopo: tornar a cadeia de migrations reproduzível sem assumir banco existente e sem usar PostgreSQL real de operação.

## Evidência atual

Na `main`:

- `7c83bbc2b9f7_baseline_existing_schema.py` é a raiz e não cria tabelas;
- `1a2fcfdc65b1_add_lead_timestamps.py` vem em seguida e executa `add_column` em `leads`;
- não existe migration anterior em `main` que crie `leads`;
- portanto um PostgreSQL vazio não possui pré-condição para executar a cadeia atual até `head`.

A branch histórica `chore/migration-baseline-review` contém uma correção candidata isolável:

- `0f4bc1c903c6_bootstrap_leads_schema.py` cria a tabela `leads` no formato pré-baseline;
- a baseline `7c83bbc2b9f7` passa a declarar `0f4bc1c903c6` como `down_revision`.

O restante daquela branch contém auth, tenant, configuração de agente e outras mudanças fora deste ADR e não deve ser importado em bloco.

## Decisão

A estratégia aprovada para avaliação é **inserir uma migration de bootstrap antes da baseline histórica**, preservando os IDs das revisions posteriores.

Objetivo:

- banco vazio: executar bootstrap → baseline → cadeia existente → head;
- banco legado que já está marcado na baseline ou revision posterior: continuar a partir da revision registrada sem recriar `leads`;
- nenhum banco real é usado para descobrir ou validar a correção.

A implementação candidata pode reutilizar o conteúdo conceitual de `0f4bc1c903c6`, mas deve ser revisada contra o schema atual antes de entrar em `main`.

## Gate obrigatório: PostgreSQL descartável

Antes de alterar a cadeia em `main`, criar um harness local descartável que:

1. cria um PostgreSQL 17 exclusivo para a validação;
2. usa nome, credencial e porta próprios;
3. não lê `.env` real nem reutiliza volume de projeto;
4. recusa URL que não aponte explicitamente ao recurso descartável;
5. remove somente o recurso que ele próprio criou;
6. não publica a porta além de `127.0.0.1`.

O harness não deve alterar migrations. Sua primeira função é provar de forma reproduzível o estado atual e servir de ambiente seguro para a correção seguinte.

## Cenários de validação

### A. Fresh database

Em PostgreSQL vazio:

- `alembic upgrade head` deve completar após a correção;
- `alembic current` deve indicar o head esperado;
- `alembic check` não deve apontar drift inesperado para o schema coberto.

Antes da correção, o harness deve demonstrar de forma controlada a falha atual relacionada à ausência de `leads`.

### B. Legacy baseline

Criar fixture sintética que represente o estado pré-Alembic relevante:

- tabela `leads` com colunas pré-baseline;
- pelo menos uma linha sintética;
- marcar/stamp na revision histórica apropriada sem fingir execução de migrations anteriores.

Depois:

- executar upgrade até head;
- preservar a linha;
- verificar timestamps, Company e demais evoluções posteriores aplicáveis;
- nenhuma tabela/dado real é copiado.

O objetivo é provar compatibilidade com a premissa que originou a baseline vazia.

## Regras de implementação

- não usar `Base.metadata.create_all` para “preparar” o teste Alembic;
- não usar `stamp` para esconder falha em banco vazio;
- não editar revisions posteriores para acomodar o teste sem review específico;
- não cherry-pickar a branch histórica inteira;
- não combinar esta correção com auth, XOR, tenant, config de agente ou refatoração;
- não executar downgrade destrutivo em banco real;
- não considerar SQLite evidência de compatibilidade Alembic/PostgreSQL.

## Rollback e segurança

O primeiro pacote local cria somente o harness; não muda schema nem migrations.

A correção da cadeia será um pacote posterior e separado. Se o harness não conseguir provar isolamento do banco descartável, a execução deve parar antes de qualquer `alembic upgrade`.

## Critério de saída deste ADR

Este ADR está satisfeito quando:

1. existe harness descartável aprovado;
2. a falha da cadeia atual em banco vazio foi reproduzida com segurança;
3. a fixture legacy foi definida;
4. somente então uma spec separada autoriza a alteração mínima da cadeia.
