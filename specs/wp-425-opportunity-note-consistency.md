# WP-425 — Salvamento de nota da oportunidade selecionada

Branch: `wp/425-opportunity-note-consistency`, base `main`.

## Problema e entrega

Uma resposta atrasada ao salvar a nota de uma oportunidade usava a seleção
atual para substituir o registro na lista, os dois editores e o aviso.
Trocar a seleção durante a gravação podia mostrar a nota da oportunidade
anterior e substituir o registro atual em memória.

Capturar ID, versão da seleção e sessão antes do PATCH existente. Aplicar
resultado e feedback somente enquanto os três ainda correspondem à seleção.
Respostas antigas de sucesso ou falha são ignoradas, inclusive ao reabrir o
mesmo ID ou conectar outra sessão. A escrita já enviada não é cancelada;
selecionar novamente consulta o estado pelo fluxo existente.

Sem alteração de API, autenticação, schema, migration ou serviço externo.
Sem mudança nos outros formulários de edição ou no contrato de triagem.

## Validação

Teste Node via pytest executa o listener real com promises sintéticas:
troca de ID, reabertura, fechamento e sessão; sucesso e falha antigos antes
e depois da gravação atual; atualização dos editores e registro correto;
falha atual preserva rascunho para retry; nota vazia mantém envio nulo.
Executar `scripts/preflight.sh` e `node --check app/operator_ui/app.js`.
Entregar uma PR aberta, sem merge.

## Evidência local

`scripts/preflight.sh` PASS: 3290 testes passaram, 2 warnings;
compileall e diff-check passaram. Sintaxe JavaScript e 14 testes
direcionados passaram. O bug foi reproduzido no listener de `origin/main`
com respostas sintéticas, sem editar o checkout base. Nenhum banco real,
serviço operacional, migration ou envio externo foi utilizado.
