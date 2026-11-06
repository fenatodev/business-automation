# WP-424 — Notas consistentes com a conversa selecionada

Branch: `wp/424-conversation-note-consistency`, base `main`.

## Problema e entrega

Ao trocar de conversa, o editor conservava a nota anterior enquanto aguardava
as mensagens e a leitura da nota. Uma falha atrasada apagava a nota atual;
reabrir o mesmo ID também permitia aplicar resultados antigos. O operador
podia salvar texto da conversa anterior na seleção nova.

Iniciar a leitura e limpar/bloquear o editor imediatamente na seleção.
Vincular resultados de leitura e feedback de salvamento à versão da seleção,
ID e sessão. Só permitir salvar após leitura bem-sucedida; bloquear duplicação
durante o salvamento. Falha de leitura mantém editor bloqueado e orienta
reselecionar a conversa. Falha de gravação conserva o rascunho para nova tentativa.
Confirmação de gravação permanece visível até próxima leitura/gravação.

Reutilizar GET /conversations/{id}/note e PATCH /conversations/{id} existentes.
Sem mudança de API, schema, migration, autorização, envio de mensagem ou serviço.

## Validação

Teste Node via pytest executa seleção, leitura e listener de salvar reais com
DOM e promises sintéticos: troca de ID, reabertura, sessão, fechamento,
sucesso/falha antiga antes/depois da resposta atual, mensagens pendentes,
nota vazia, bloqueio durante leitura, erro de leitura com recuperação,
gravação duplicada e retry com rascunho preservado. Testes existentes de
notas cobrem persistência via API e contratos de acesso.

Executar scripts/preflight.sh e node --check app/operator_ui/app.js.
Entregar um único PR aberto para CI e supervisor; não fazer merge.

## Evidência local

Preflight PASS: 3289 testes passaram, 2 warnings; compileall e diff-check
passaram. Sintaxe JavaScript e teste Node direcionado PASS. Somente respostas
sintéticas e SQLite isolado da suíte; nenhum serviço operacional utilizado.
