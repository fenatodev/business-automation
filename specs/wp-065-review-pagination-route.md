# WP-065 — corrigir conexão da fila paginada

Base: WP-064 integrada pelo PR #147, `b249266`.
Branch: `wp/065-review-pagination-route`.

## Falha reproduzida

WP-062 introduziu `/review-queue/?limit=50&offset=0`, mas a allowlist da UI
aceitava somente `/review-queue/`. A conexão solicitava essa página, lançava
erro antes do fetch e desconectava o operador. Testes de texto não detectavam.

## Correção focada

Aceitar a query gerada com limit 1–100 e offset decimal não negativo, na ordem
exata. Preservar rota sem query e demais rotas existentes. Rejeitar controles,
URLs externas, parâmetros extras/duplicados e fragmentos antes do fetch.
Nenhuma política backend, persistência de Bearer ou ação externa foi alterada.

## Reprodução

`uv run pytest tests/test_review_pagination_runtime.py` executa Node.js com DOM
sintético construído dos IDs do HTML real, fetch sintético e app.js entregue.
Comprova conexão, offsets 0→50→0 e parâmetros rejeitados sem chamada de rede.
Não equivale a ensaio visual de navegador ou autenticação de serviço real.
Node.js é necessário; já usado no CI para sintaxe do painel.

Validação: suíte completa, compileall, diff-check e `node --check app/operator_ui/app.js`.
Segunda revisão antes de integração. Próxima WP: painel das tarefas internas.
