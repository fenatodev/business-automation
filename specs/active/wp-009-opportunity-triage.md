# WP-009 — Opportunity capture e triagem mínima

Status: pronto para implementação  
Fase: F2 — primeiro ciclo Client 0 assistido  
Base: `origin/main` atual no início da execução

## Problema

O modelo atual de `Lead` exige nome e telefone e representa um contato já identificável. A primeira fonte do Client 0, 99Freelas, começa antes disso: existe uma oportunidade pública que precisa ser registrada, triada e decidida sem inventar pessoa/telefone.

Não reutilizar `Lead` para preencher dados falsos.

## Objetivo observável

Adicionar uma entidade `Opportunity` tenant-scoped capaz de registrar manualmente uma oportunidade de 99Freelas e sua próxima ação de triagem.

O operador deve conseguir:

1. capturar uma oportunidade manual;
2. listar apenas oportunidades da própria Company;
3. consultar por ID somente dentro do próprio tenant;
4. atualizar a decisão de triagem;
5. receber 409 ao tentar capturar novamente a mesma URL na mesma Company.

Nenhum scraping, envio de proposta ou criação automática de Lead.

## Schema

Nova tabela `opportunities`:

- `id INTEGER PK`;
- `company_id INTEGER NOT NULL FK companies.id`;
- `source VARCHAR(50) NOT NULL`;
- `external_url VARCHAR(1000) NOT NULL`;
- `title VARCHAR(200) NOT NULL`;
- `description TEXT NOT NULL`;
- `budget VARCHAR(120) NULL`;
- `deadline VARCHAR(120) NULL`;
- `requirements TEXT NULL`;
- `captured_at TIMESTAMP WITH TIME ZONE NOT NULL`;
- `next_action VARCHAR(30) NOT NULL DEFAULT 'pending'`;
- `triage_note TEXT NULL`;
- `created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()`;
- `updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()`.

Constraint:

```text
UNIQUE(company_id, external_url)
```

com nome explícito:

`uq_opportunities_company_external_url`

Criar índice de `company_id`.

Não adicionar relação com Lead neste WP.

## Contrato API

### POST /opportunities

Operator only.

Payload:

```json
{
  "source": "99freelas",
  "external_url": "https://example.invalid/project/123",
  "title": "Automação de processo",
  "description": "Descrição sintética",
  "budget": "R$ 1.000 - R$ 2.000",
  "deadline": "7 dias",
  "requirements": "Python, API",
  "captured_at": "2026-10-08T12:00:00-03:00"
}
```

Regras:

- payload **não contém `company_id`**;
- tenant vem somente da identidade operator;
- `source` aceito neste WP: somente `99freelas`;
- Company autenticada precisa existir;
- `next_action` inicial = `pending`;
- mesma `external_url` na mesma Company => 409 genérico `Opportunity already captured`;
- a mesma URL em outra Company é permitida.

### GET /opportunities

Operator only.

Lista apenas a própria Company, ordenada por `id`.

### GET /opportunities/{opportunity_id}

Operator only.

Busca por `(id, identity.company_id)`.

ID de outro tenant deve responder 404 `Opportunity not found`.

### PATCH /opportunities/{opportunity_id}/triage

Operator only.

Payload:

```json
{
  "next_action": "prepare_proposal",
  "triage_note": "Bom fit técnico; revisar escopo e prazo."
}
```

`next_action` permitido:

- `pending`;
- `ignore`;
- `follow`;
- `prepare_proposal`.

Não criar scoring estruturado ainda. O primeiro ciclo deve mostrar quais critérios realmente merecem campos próprios.

## Auth / tenant

- admin não ganha acesso implícito;
- operator só opera própria Company;
- nenhuma rota aceita `company_id` do cliente;
- list/get/patch sempre filtram pelo tenant autenticado;
- cross-tenant por ID => 404;
- auth ausente/inválida mantém 401 do contrato atual;
- admin nessas rotas => 403.

## Migration

Criar uma nova migration linear após o head atual.

Ela deve:

- criar somente `opportunities`, índice e constraint definidos;
- não alterar tabelas existentes;
- downgrade remover somente a nova tabela/índice implícito pela tabela;
- preservar um único Alembic head.

Não editar migrations históricas.

## Arquivos esperados

Pode alterar somente:

- `app/models.py`;
- `app/schemas.py`;
- `app/main.py`;
- novo `app/routers/opportunities.py`;
- nova migration em `migrations/versions/`;
- `tests/test_api.py`.

Não alterar auth/dependencies existentes salvo stop condition.

## Testes obrigatórios

Adicionar testes para:

1. operator cria oportunidade e Company vem da identidade;
2. source diferente de `99freelas` é rejeitada pela validação;
3. duplicate URL na mesma Company => 409;
4. mesma URL em Company diferente => permitido;
5. operator A lista somente A;
6. operator A GET de B => 404;
7. operator A PATCH de B => 404;
8. triage atualiza `next_action` e `triage_note`;
9. admin GET/POST/PATCH => 403;
10. rota sem credencial continua 401.

Não reduzir testes anteriores.

## Validação obrigatória

```bash
uv run pytest
.venv/bin/python -m compileall app tests migrations
uv run alembic heads
bash scripts/verify-alembic-postgres.sh
git diff --check
```

Acceptance:

- suíte completa verde;
- exatamente um Alembic head;
- harness PostgreSQL existente passa com o novo head;
- nenhum container de validação sobra;
- diff limitado aos seis grupos de arquivos autorizados.

## Segunda revisão obrigatória

Como o WP altera schema e adiciona nova superfície tenant-scoped, antes do merge executar revisão independente focada em:

- migration/reversibilidade;
- isolamento por Company;
- duplicate constraint;
- semântica 401/403/404/409;
- ausência de `company_id` client-controlled;
- ausência de bypass admin.

Review pode ser feita pelo Qwen local/Continue em modo somente leitura após a implementação e antes do merge.

## Não objetivos

Não implementar:

- scraper;
- browser automation;
- integração com 99Freelas;
- envio de proposta;
- Opportunity -> Lead;
- scoring por IA;
- budget numérico/moeda normalizada;
- catálogo/oferta;
- ERP adapter;
- frontend;
- jobs;
- webhooks;
- dados reais nos testes.

## Stop conditions

Parar se:

- migration existente precisar ser reescrita;
- auth/dependencies precisarem de mudança para suportar o contrato;
- for necessário expor Company via payload;
- o harness PostgreSQL revelar drift não causado pela nova migration;
- o recorte exigir Lead/Customer/ERP para funcionar.

## Git

Branch:

`wp/009-opportunity-triage`

Commit sugerido:

`feat: add tenant scoped opportunity triage`

Não mergear localmente.
