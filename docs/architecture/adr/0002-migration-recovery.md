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

## Evidência após WP-003

O WP-003 foi concluído e mergeado pelo PR #16. O harness PostgreSQL 17 isolado comprovou de forma reproduzível que um banco vazio falha em `1a2fcfdc65b1` porque a tabela `leads` não existe.

Durante a revisão da cadeia foi identificado um segundo defeito de compatibilidade legacy:

- `4749a8ea474b` adiciona `company_id` como nullable;
- `6db09cfda379` torna `company_id` obrigatório;
- não existe backfill entre essas revisions;
- portanto qualquer banco legacy com leads existentes falha ao tentar tornar `company_id` NOT NULL.

Esse segundo defeito precisa ser tratado no mesmo pacote de recuperação da cadeia, porque uma correção que funciona apenas para banco vazio não satisfaz a compatibilidade com a baseline histórica.

## Decisão

A estratégia aprovada é **inserir uma migration de bootstrap antes da baseline histórica**, preservando os IDs das revisions posteriores, e adicionar um backfill explícito antes de tornar `leads.company_id` obrigatório.

Objetivo:

- banco vazio: executar bootstrap → baseline → cadeia existente → head;
- banco legado que já está marcado na baseline ou revision posterior: continuar a partir da revision registrada sem recriar `leads`;
- nenhum banco real é usado para descobrir ou validar a correção.

A implementação candidata pode reutilizar o conteúdo conceitual de `0f4bc1c903c6`, mas deve ser revisada contra o schema atual antes de entrar em `main`.

### Política de backfill legacy para Company

No momento em que `6db09cfda379` for tornar `company_id` obrigatório:

1. se não houver leads com `company_id IS NULL`, não criar nenhuma Company artificial;
2. se houver leads sem Company e a tabela `companies` estiver vazia, criar uma única Company de migração:
   - name: `Legacy Workspace`;
   - slug: `legacy-workspace`;
3. se houver exatamente uma Company existente, associar os leads legacy sem Company a ela;
4. se houver mais de uma Company existente, **não inferir ownership**: interromper a migration com erro claro para exigir mapeamento explícito;
5. somente depois do backfill tornar `leads.company_id` NOT NULL.

Racional:

- o schema pré-Company era single-tenant e não continha informação suficiente para reconstruir ownership múltiplo;
- criar um placeholder apenas quando não existe nenhuma Company preserva dados sem inventar múltiplos vínculos;
- escolher automaticamente entre várias Companies seria uma inferência de autorização/tenant e é proibido.

O placeholder é um artefato de migração e pode ser renomeado/reconciliado posteriormente por operação humana.

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
- nenhuma tabela `companies` pré-existente;
- marcar/stamp na revision histórica `7c83bbc2b9f7` sem fingir execução das migrations anteriores.

Depois:

- executar upgrade até head;
- preservar id/nome/telefone/source/interest/status da linha;
- verificar `created_at` e `updated_at`;
- verificar `company_id` não nulo e FK válida;
- verificar a criação de exatamente um `Legacy Workspace` para o caso zero-Company;
- verificar `alembic current` no head;
- nenhuma tabela/dado real é copiado.

O objetivo é provar compatibilidade com a premissa que originou a baseline vazia e com a introdução posterior de tenancy.

## Regras de implementação

- não usar `Base.metadata.create_all` para “preparar” o teste Alembic;
- não usar `stamp` para esconder falha em banco vazio;
- não editar revisions posteriores fora de `6db09cfda379`, que está explicitamente incluída nesta recuperação por causa do backfill ausente;
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
2. a falha original da cadeia em banco vazio foi reproduzida com segurança;
3. a migration de bootstrap foi inserida antes da baseline;
4. banco vazio executa `upgrade head` com sucesso;
5. fixture legacy com lead existente executa `upgrade head` preservando dados e recebendo Company válida conforme a política acima;
6. `alembic current`/head e drift relevante são verificados;
7. nenhuma mudança de auth, membership, tenant API ou infraestrutura é misturada neste reparo.
