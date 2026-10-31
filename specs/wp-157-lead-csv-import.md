# WP-157 — Importação CSV de leads

## Problema

O operador só podia criar leads um por um via formulário manual. Quando recebia planilhas de eventos ou campanhas, não havia como importar em lote.

## Solução

`POST /leads/import.csv` aceita arquivo CSV com colunas: Nome, Telefone, Fonte, Interesse (opcional). Deduplica por telefone, valida cada linha e retorna contagem de importados, duplicatas e erros. Limite de 500 linhas por importação.

## Mudanças

- `app/routers/leads.py`: `POST /leads/import.csv` com UploadFile, validação de header, deduplicação, tenant isolation
- `app/operator_ui/index.html`: botão "Importar CSV" e `<input type="file" hidden>`
- `app/operator_ui/app.js`: handler de importação com FormData, feedback visual
- `tests/test_lead_csv_import.py`: 12 testes backend

## Regras

- Colunas obrigatórias: Nome, Telefone
- Deduplicação por telefone dentro da mesma empresa
- Máximo 500 linhas por importação
- UTF-8 com BOM suportado
- Source vazio default para "import"
- Status sempre "new"

## Verificação

- 2103 testes passaram (12 novos)
- `compileall` ✓, `git diff --check` ✓
