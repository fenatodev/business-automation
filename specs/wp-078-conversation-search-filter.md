# WP-078 — Busca e filtro de conversas no operador

Base: `origin/main`.
Branch: `wp/078-conversation-search-filter`.

## Motivação

O operador não pode filtrar conversas por canal, status ou buscar por keywords.
Com o crescimento das conversas, a lista sem filtros torna-se difícil de navegar.
WP-077 unificou as seções de conversas, mas a filtragem permanece pendente.

## Entrega

### Backend (conversations.py)

- `GET /companies/{company_id}/conversations` aceita parâmetros opcionais:
  - `channel`: filtra por canal (whatsapp, instagram, web, telegram, email).
  - `status`: filtra por status (open, closed, etc.).
  - `q`: busca keywords no conteúdo das mensagens (LIKE case-insensitive).
- Quando `q` é fornecido, o endpoint retorna apenas conversas que contêm
  mensagens com o termo buscado, usando JOIN com Message.
- Tenant isolation preservada: todos os filtros aplicam company_id.

### UI (index.html)

- Seção "06 / COMUNICAÇÃO" com controles de filtro:
  - Dropdown de canal (`#conv-filter-channel`) com opção "Todos os canais".
  - Dropdown de status (`#conv-filter-status`) com opção "Todos os status".
  - Campo de busca por keywords (`#conv-search-q`).
  - Botão "Buscar" (`#conv-search-btn`) e botão "Limpar" (`#conv-clear-filter`).
- Filtros aplicam-se automaticamente ao carregar a lista.

### JavaScript (app.js)

- `conversationApi()` atualizada para aceitar query params nos filtros.
- `applyConversationFilters()` constrói a URL com os parâmetros ativos.
- `refreshConversations()` usa os filtros atuais.
- `clearConversationFilters()` reseta os controles e recarrega.
- `onChannelFilterChange()`, `onStatusFilterChange()` aplicam filtro imediato.
- `onSearchSubmit()` executa busca por keywords.

### CSS (styles.css)

- `.conv-filters` container flex para os controles de filtro.
- `.conv-filter-group` com label e select/input.
- Estilos consistentes com o tema escuro do operador.

## Design

- Sem mudanças de schema ou migração.
- Filtros são opcionais; sem filtros retorna todas as conversas (comportamento existente).
- Busca por keywords usa LIKE com %wildcard% para parcial match.
- Tenant isolation mantida em todas as consultas.

## Aceite

- Testes backend validam cada filtro individualmente e combinados.
- Testes de contrato UI validam elementos, funções e integração.
- `uv run pytest`: todos os testes passam.
- compileall ✓, git diff --check ✓.

## Próximo passo

Avaliar se é necessário paginar as conversas quando há muitas ou adicionar
ordenamento por data/última mensagem.
