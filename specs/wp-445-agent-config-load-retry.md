# WP-445 — Retry ao carregar configuração do agente

## Objetivo

Informar o operador quando a configuração do agente não puder ser carregada e
permitir nova tentativa na própria seção.

## Escopo

- Anunciar carregamento e falha com mensagem genérica acessível.
- Exibir retry somente após falha; ocultá-lo durante carregamento e após sucesso.
- Preservar os campos existentes em caso de falha e ignorar respostas obsoletas.
- Testar o handler real com API e DOM sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
