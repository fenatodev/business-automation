# WP-421 — Conversas consistentes com o cliente selecionado

Branch: `wp/421-customer-conversation-order`, base `main`.

## Entrega

Ao selecionar clientes rapidamente, uma resposta atrasada acrescentava conversas
antigas ao detalhe atual. Cada consulta agora recebe uma versão e só renderiza
se pertencer à seleção visível e sessão atuais. Voltar invalida consultas,
inclusive ao reabrir o mesmo cliente. Falhas antigas também são ignoradas.

Preservar endpoints, estado vazio e tratamento de falhas atuais. Sem mudança de
API, autorização, schema, migration ou ação externa.

## Validação

Teste Node via pytest executa os handlers entregues com DOM e promises sintéticos:
troca de cliente, retorno, reabertura do mesmo ID, mudança de sessão, respostas
invertidas, falhas antigas e resposta vazia atual. A regressão foi reproduzida
antes da correção. Executar preflight e validação de sintaxe JavaScript.

Entregar um único PR aberto ao supervisor, sem merge ou próximo WP.

## Evidência local

Preflight PASS: 3286 testes passaram, 2 warnings; compileall e diff-check
passaram. Sintaxe JavaScript e teste Node PASS. Apenas dados sintéticos;
nenhum banco operacional, migration ou serviço externo de negócio utilizado.
