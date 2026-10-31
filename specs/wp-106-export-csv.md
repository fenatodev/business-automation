# WP-106 — Exportação CSV de dados do operador

**Status:** Concluída
**Branch:** `wp/106-export-csv`
**Depende de:** WP-105 (PR #188)

## Problema

O operador não podia exportar os dados de oportunidades, leads e customers para análise externa (planilhas, relatórios, etc.).

## Solução

Três endpoints `GET /export.csv` tenant-isolados, um por tipo de entidade. Cada endpoint retorna um arquivo CSV com cabeçalhos em português e `Content-Disposition: attachment`.

## Changes

### Backend

- **`app/routers/opportunities.py`**: `GET /opportunities/export.csv` — exporta todas as oportunidades do tenant com campos: ID, Título, Descrição, Status, Orçamento, Prazo, Requisitos, URL, Fonte, Nota triagem, Capturada em.
- **`app/routers/leads.py`**: `GET /leads/export.csv` — exporta todos os leads do tenant com campos: ID, Nome, Telefone, E-mail, Fonte, Interesse, Status, Criado em.
- **`app/routers/customers.py`**: `GET /customers/export.csv` — exporta todos os customers do tenant com campos: ID, Nome, Telefone, E-mail, Lead origem, Criado em.

### UI

- **`app/operator_ui/index.html`**: Botão "Exportar CSV" nas seções de oportunidades, leads e customers.
- **`app/operator_ui/app.js`**: `downloadCsv()` helper; listeners nos três botões de exportação.
- **`app/operator_ui/styles.css`**: `.panel-actions` para agrupar botões na toolbar.

### Testes

- **`tests/test_export_csv.py`**: 15 testes (5 por entidade: básico, vazio, tenant isolation, auth, campos completos).

## Segurança

- Todos os endpoints exigem autenticação Bearer operator.
- Exportação é tenant-isolada: cada operador vê apenas os dados da sua company.
- Nenhum dado sensível extra é exposto; os campos seguem o schema existente.

## Verificação

- 1587 testes passaram, 2 warnings preexistentes.
- `compileall` ✓, `git diff --check` ✓.
