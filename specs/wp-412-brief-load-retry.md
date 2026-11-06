# WP-412 — Recuperação da lista de briefs

Branch: `wp/412-brief-load-retry`, base `main`.

Preservar lista, contagem, paginação e seleção quando lista ou contagem
falhar. Mostrar aviso genérico, carregamento acessível e Tentar novamente.
Retry mantém filtros, ordem e página e repete apenas consultas existentes.
Limpar seleção somente após sucesso; ignorar respostas antigas e limpar
feedback ao desconectar. Sem API nova, schema, migrations ou ações externas.

Validar handlers JavaScript com APIs e DOM sintéticos, preflight, compileall
e diff-check. Deixar um único PR aberto para revisão pelo supervisor.
