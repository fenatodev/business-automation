# WP-422 — Conversas no detalhe do lead

Branch: `wp/422-lead-detail-conversations`, base `main`.

## Entrega

O detalhe tentava ler conversas com `company` indefinida e com o helper de
rotas de oportunidades. Usar `lead.company_id` retornado pela API e o helper
existente `conversationApi`, com filtro server-side `lead_id` antes do limite
50. Assim, conversas de outros leads não consomem a primeira página.

Somente a seleção visível mais recente da mesma sessão pode preencher o
histórico. Voltar invalida a leitura, inclusive ao reabrir o mesmo lead.
Preservar estado vazio e tratamento de falhas; nenhuma escrita automática.
Sem mudança de API, autorização, schema, migrations ou ação externa.

## Validação

Teste Node via pytest executa os handlers com DOM e respostas sintéticas:
rota filtrada, troca de lead, respostas invertidas, Voltar, reabertura,
mudança de sessão, sucesso/falha antiga e resultado vazio atual.
Executar preflight e sintaxe JavaScript. Um único PR aberto ao supervisor;
sem merge ou próximo WP.

## Evidência local

Preflight PASS: 3287 testes passaram, 2 warnings; compileall e diff-check
passaram. Sintaxe JavaScript PASS. Teste direcionado também passou com lista
de oportunidades vazia. Apenas dados sintéticos e banco isolado da suíte;
nenhum serviço operacional utilizado.
