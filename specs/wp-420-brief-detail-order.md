# WP-420 — Detalhe de brief consistente com a seleção

Branch: `wp/420-brief-detail-order`, base `main`.

## Problema e entrega

Ao selecionar A e depois B, uma resposta atrasada de A podia substituir os
campos e conversas sob o título de B. Erros antigos também apagavam o detalhe
atual. Cada seleção recebe uma versão; somente a seleção visível mais recente
da mesma sessão pode renderizar sucesso ou falha. Fechar por toggle ou Voltar
invalida o resultado, inclusive ao reabrir o mesmo brief.

Preservar endpoints, tratamento de erros atuais e conversas opcionais.
Sem schema, migrations, alteração de autorização ou ação externa.

## Validação

Teste Node executa os handlers entregues com DOM e promises sintéticos:
seleções invertidas, sucesso/falha antiga antes/depois da atual, toggle,
Voltar, reabertura do mesmo ID, mudança de sessão e falha atual.
A corrida reproduziu a regressão antes da correção.
Executar `bash scripts/preflight.sh` e `node --check app/operator_ui/app.js`.
Um único PR aberto para o supervisor; sem merge ou próximo WP.

## Evidência local

Preflight PASS: 3285 testes passaram, 2 warnings; compileall e diff-check
passaram. Sintaxe JavaScript PASS. Somente fixtures isoladas e respostas
sintéticas; nenhum serviço operacional foi usado.
