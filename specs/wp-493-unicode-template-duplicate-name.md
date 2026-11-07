# WP-493 — Evitar nomes repetidos ao duplicar templates

## Objetivo

Sugerir um nome disponível ao duplicar um template de resposta, mantendo o
limite de 100 pontos de código aceito pelo formulário e pela API.

## Escopo

- Usar “(cópia)” para a primeira cópia e numerar sugestões seguintes quando o
  nome normalizado já existir na lista da empresa.
- Truncar o nome original para preservar o limite de 100 pontos de código.
- Preservar a possibilidade de o operador editar ou cancelar a sugestão.
- Cobrir colisões, lista atualizada e cancelamento em teste sintético.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
