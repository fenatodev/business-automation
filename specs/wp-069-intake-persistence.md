# WP-069 — Persistência do intake comercial como opportunity

Base: `origin/main` (após merge WP-063 a WP-068).
Branch: `wp/069-intake-persistence`.

## Motivação

`POST /internal/commercial-intake/evaluate` retorna uma decisão estruturada,
mas é **simulation-only**: não persiste dados, não cria opportunity, não envia
mensagens. Para a F2 (operação assistida), o operador precisa de um endpoint
que persista o intake como opportunity quando a decisão for favorável,
fechando o ciclo intake → opportunity → triage.

## Entrega

### Novo schema

- `IntakeCreate` em `app/schemas.py` — request body para persistência.
- Campos: `channel`, `message`, `event_id` (mesmo que `CommercialIntakeEvaluateRequest`).
- Validação idêntica: extra="forbid", campos imprimíveis, sem controle chars.

### Novo endpoint

- `POST /internal/commercial-intake/create` no router `commercial_intake.py`.
- Autenticado (`require_operator`), tenant-isolado.
- Fluxo:
  1. Validar request.
  2. Executar `process_commercial_intake()` para obter decisão.
  3. Se `needs_human_review` é `False` e `intent` não é `unknown`,
     criar `Opportunity` com dados derivados do intake.
  4. Se `needs_human_review` é `True`, criar `Opportunity` com
     `next_action="pending"` e `triage_note` com os flags.
  5. Retornar decisão + opportunity_id (se criada).
- Se `event_id` já existe como opportunity (deduplicação), retornar 409.

### Novo schema de resposta

- `IntakeCreateResponse` — decisão + opportunity_id opcional.
- Campos: `decision` (IntakeDecision), `opportunity_id` (int | None).

### Service layer

- `persist_intake()` em `app/services/commercial_intake.py` ou módulo adjacente.
- Recebe `db`, `company_id`, `event`, `candidate`.
- Executa decisão, cria opportunity se aplicável, retorna tupla (decision, opportunity_id).

## Design

- O endpoint não altera o comportamento de `process_commercial_intake()`.
- A decisão é sempre retornada, mesmo quando opportunity não é criada.
- Deduplicação por `event_id` no campo `external_url` da opportunity.
- Source da opportunity é `"intake"` (novo valor no Literal).
- O endpoint é operator-only, tenant-isolado, sem exposição pública.
- Não envia mensagens externas nem ativa workflows.

## Aceite

- Testes unitários validam:
  - Intake cria opportunity com dados corretos.
  - Deduplicação por event_id retorna 409.
  - needs_human_review cria opportunity com triage_note.
  - Decisão é sempre retornada.
- `uv run pytest`, compileall, git diff --check: PASS.

## Próximo passo

Após integração, avaliar o fluxo de triage do operador para oportunidades
criadas pelo intake.
