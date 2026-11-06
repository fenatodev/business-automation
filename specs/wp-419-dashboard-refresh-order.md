# WP-419 — Dashboard com atualização consistente

Branch: `wp/419-dashboard-refresh-order`, base `main`.

## Problema e entrega

Consultas concorrentes do dashboard podiam terminar fora de ordem e substituir
os totais atuais por um snapshot antigo. Uma resposta pendente também podia
atualizar a tela depois de interromper o polling ou encerrar a sessão.

Somente a consulta mais recente da sessão atual pode renderizar o dashboard.
Interromper o polling invalida consultas pendentes. Verificar a validade tanto
após os headers quanto após a leitura assíncrona do JSON. Respostas 403 antigas
não desconectam a sessão atual; respostas 403 atuais preservam o tratamento
existente. Falhas de rede mantêm o comportamento existente e permitem novo poll.

Sem alteração de API, autenticação, schema, migrations ou serviços externos.

## Validação

Teste executável em Node via pytest com fetch sintético e promises controladas:
ordens de conclusão, respostas 200/403/503 antigas, JSON atrasado, interrupção,
mudança de sessão, 403 atual e recuperação após falha de rede. O cenário de
respostas invertidas reproduziu a regressão antes da correção.

Executar `bash scripts/preflight.sh` e `node --check app/operator_ui/app.js`.
Entregar um único PR aberto ao supervisor, sem merge ou próximo WP.

## Evidência local

`bash scripts/preflight.sh`: PASS — 3284 testes passaram, 2 warnings;
compileall e diff-check passaram. Sintaxe JavaScript: PASS.
Sem PostgreSQL real, migration, credencial ou chamada externa de negócio.
