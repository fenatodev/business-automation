# WP-481 — Proteger edição de template ao sair da página

## Objetivo

Evitar que atualização ou fechamento da página descarte silenciosamente
alterações não salvas feitas ao editar um template de resposta.

## Escopo

- Acionar o aviso nativo de saída somente enquanto um template está em edição
  e nome ou conteúdo diferem do original.
- Não bloquear saída em formulário novo, edição intacta ou após cancelar/salvar.
- Cobrir os estados com DOM e evento `beforeunload` sintéticos.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
