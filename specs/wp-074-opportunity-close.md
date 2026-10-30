# WP-074 — Fechar oportunidades como concluída ou perdida

Base: `origin/main`.
Branch: `wp/074-opportunity-close`.

## Motivação

O ciclo comercial F2 estava incompleto: após `in_progress`, o operador não podia
fechar a oportunidade. Não havia estado final para registrar que o trabalho foi
concluído com sucesso (`done`) ou que a oportunidade foi perdida (`lost`).

## Entrega

### Backend

- `done` e `lost` adicionados ao `OpportunityTriageUpdate.next_action` em
  `app/schemas.py`.
- `in_progress` também adicionado (com WP-073) para completar a cadeia de estados.
- O endpoint `PATCH /opportunities/{id}/triage` aceita os novos estados sem
  mudanças adicionais (router já delega ao schema).
- `done` e `lost` bloqueiam a criação de proposal brief (comportamento
  existente para estados ≠ `prepare_proposal`).

### UI

- Opções "Concluída" e "Perdida" adicionadas ao `<select id="next-action">` no
  formulário de triagem.
- `in_progress`, `done` e `lost` adicionados ao `actionLabels` para exibição.

## Design

- Sem mudanças no router, modelo ou migração.
- Tenant isolation e auth preservados pelo endpoint existente.
- Estados finais não impedem reabertura via triagem para outro estado.

## Aceite

- Testes validam:
  - Triagem para `done` e `lost` com e sem nota.
  - `done` e `lost` bloqueiam proposal brief.
  - Reflexo na listagem.
  - Auth obrigatória e tenant isolation.
- Testes de contrato UI validam elementos e conexão.
- `uv run pytest`: **1146 passed**, compileall ✓, git diff --check ✓.

## Próximo passo

Avaliar se é necessário um endpoint dedicado de fechamento com campos adicionais
(razão da perda, valor final, data de conclusão) ou se o triage com nota é
suficiente para o piloto.
