# WP-159 — Importação CSV de oportunidades

## Problema

O operador só podia registrar oportunidades manualmente uma por uma via formulário. Sem forma de importar planilhas de oportunidades existentes.

## Solução

`POST /opportunities/import.csv` aceita CSV com Título, Descrição, URL (opcional), Orçamento, Prazo e Requisitos. Deduplicação por external_url. Se URL não fornecida, é gerada automaticamente. `source="import"` adicionado ao OpportunityCreate Literal.

## Mudanças

- `app/routers/opportunities.py`: `POST /opportunities/import.csv` com `UploadFile`, validação de header, deduplicação por URL, tenant isolation
- `app/schemas.py`: `"import"` adicionado ao `OpportunityCreate.source` Literal
- `app/operator_ui/index.html`: botão "Importar CSV" + input file hidden
- `app/operator_ui/app.js`: handlers de click e change para import, com feedback visual
- `tests/test_opportunity_csv_import.py`: 14 testes backend
- `tests/test_manual_capture_source.py`: ajustado para aceitar `"import"` no Literal

## Regras

- Colunas obrigatórias: Título, Descrição. URL, Orçamento, Prazo, Requisitos são opcionais.
- Deduplicação por external_url dentro da mesma company.
- URL auto-gerada se não fornecida.
- Máximo 500 linhas por importação.
- `source` definido como `"import"`.
- `next_action` definido como `"pending"`.

## Verificação

- 2129 testes passaram (14 novos)
- `compileall` ✓, `git diff --check` ✓
