# WP-073 — Triagem manual para "em andamento"

Base: `origin/main` (após merge WP-065 a WP-072).
Branch: `wp/073-triage-in-progress`.

## Motivação

O operador não podia marcar uma oportunidade como "em andamento" manualmente
via triagem. O único caminho para `in_progress` era o fluxo de aprovação do
proposal brief (WP-071), o que exigia criar e aprovar um brief mesmo quando
o trabalho já estava em andamento por outro canal.

## Entrega

### Backend

- `in_progress` adicionado ao `OpportunityTriageUpdate.next_action` em
  `app/schemas.py`.
- O endpoint `PATCH /opportunities/{id}/triage` aceita `in_progress` sem
  mudanças adicionais (router já delega ao schema).

### UI

- Opção "Em andamento" adicionada ao `<select id="next-action">` no
  formulário de triagem.
- `in_progress` já estava presente no `actionLabels` (WP-072).

## Design

- Sem mudanças no router, modelo ou migração.
- `in_progress` bloqueia a criação de proposal brief (comportamento
  existente para estados ≠ `prepare_proposal`).
- Tenant isolation e auth preservados pelo endpoint existente.

## Aceite

- Testes validam:
  - Triagem para `in_progress` com e sem nota.
  - `in_progress` bloqueia proposal brief.
  - Tenant isolation e auth obrigatória.
  - Reflexo na listagem e filtro por `next_action`.
- Testes de contrato UI validam elemento e conexão.
- `uv run pytest`, compileall, git diff --check: PASS.

## Próximo passo

Avaliar se o pipeline precisa de drag-and-drop para mudar status ou se o
triage individual é suficiente.
