# WP-072 — Visão de pipeline de oportunidades

Base: `origin/main` (após merge WP-065 a WP-071).
Branch: `wp/072-opportunity-pipeline`.

## Motivação

O operador não tem visão geral do pipeline de oportunidades. Sem filtro por
`next_action` nem resumo de contagens, é difícil identificar quais oportunidades
precisam de atenção, quais estão em andamento e quais foram ignoradas.

## Entrega

### Backend — Filtro e resumo

- `GET /opportunities?next_action=pending` — filtro opcional por next_action.
- `GET /opportunities/pipeline-summary` — retorna contagem de oportunidades
  por next_action, tenant-isolado.

### UI — Painel de pipeline

- Seção "Pipeline" no `/operator` mostrando contagens por status:
  pending, follow, prepare_proposal, in_progress, ignore.
- Clicar em um status filtra a lista de oportunidades.
- Atualização manual via botão "Atualizar pipeline".

## Design

- Filtro é query param opcional; sem filtro retorna todas (comportamento existente).
- Pipeline summary retorna dict simples: `{"pending": N, "follow": N, ...}`.
- Operator-only, tenant-isolado.
- Sem mudanças no schema ou modelos.

## Aceite

- Testes validam:
  - Filtro por next_action retorna apenas oportunidades correspondentes.
  - Pipeline summary retorna contagens corretas.
  - Tenant isolation em ambos os endpoints.
  - Auth obrigatória.
- Testes de contrato UI validam elementos e conexão.
- `uv run pytest`, compileall, git diff --check: PASS.

## Próximo passo

Após integração, avaliar se o pipeline precisa de drag-and-drop para mudar
status ou se o triage individual é suficiente.
