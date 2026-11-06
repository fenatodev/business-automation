# WP-417 — Busca de tarefas sem respostas fora de ordem

Branch: `wp/417-task-refresh-order`, base `main`.

Somente a atualização mais recente pode aplicar resultados, contagem,
paginação, seleção, erro e fim de carregamento das tarefas internas.
Respostas e falhas antigas são ignoradas. O retry preserva filtros e página
e repete apenas GETs nos endpoints existentes.

Testar handlers reais com DOM sintético, buscas sobrepostas, sucesso/falha
da lista e contagem nas duas ordens, seleção, carregamento e recuperação.
Manter cobertura existente de resultado vazio e resposta inválida.
Sem mudança de API, schema, migrations, autenticação ou execução de tarefas.

Validar pytest, compileall, diff-check, preflight e sintaxe JavaScript.
Entregar um único PR aberto ao supervisor, sem merge ou próxima WP.

## Evidência local

`bash scripts/preflight.sh`: PASS — 3282 testes passaram, 2 warnings;
compileall e diff-check passaram. `node --check app/operator_ui/app.js`: PASS.
Testes de concorrência exercitam 16 combinações de ordem e falha com promises
controladas; nenhuma API privada ou tarefa real foi executada.
