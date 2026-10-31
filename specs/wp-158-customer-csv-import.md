# WP-158 — Importação CSV de customers

## Problema

O operador só podia criar customers manualmente um por um via formulário. Sem forma de importar planilhas de customers existentes.

## Solução

`POST /customers/import.csv` aceita CSV com Nome, Telefone e E-mail (opcional). Deduplicação por telefone dentro da mesma company. Limite de 500 linhas por importação. Suporte a UTF-8 BOM.

## Mudanças

- `app/routers/customers.py`: `POST /customers/import.csv` com `UploadFile`, validação de header, deduplicação por telefone, tenant isolation
- `app/operator_ui/index.html`: botão "Importar CSV" + input file hidden
- `app/operator_ui/app.js`: handlers de click e change para import, com feedback visual
- `app/operator_ui/app.js`: `customerApi()` allowlist atualizada para incluir `/customers/export.csv`
- `tests/test_customer_csv_import.py`: 12 testes backend

## Regras

- Colunas obrigatórias: Nome, Telefone. E-mail é opcional.
- Deduplicação por telefone dentro da mesma company.
- Máximo 500 linhas por importação.
- Tenant isolation: customers importados pertencem à company do operador autenticado.
- Sem migration necessária.

## Verificação

- 2115 testes passaram (12 novos)
- `compileall` ✓, `git diff --check` ✓
