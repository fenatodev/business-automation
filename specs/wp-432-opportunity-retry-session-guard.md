# WP-432 — Descartar resposta de retry após mudança de sessão

## Objetivo

Impedir que uma consulta de conversas de oportunidade iniciada numa sessão
antiga atualize a interface após desconexão ou troca de sessão.

## Escopo

- Validar a sessão junto com a oportunidade e sua versão selecionadas.
- Aplicar o mesmo guard a sucesso, falha e limpeza do estado busy.
- Testar resposta obsoleta com DOM/API sintéticos mantendo o mesmo ID selecionado.
- Sem mudanças em API, autenticação/tenant, schema, migrations ou integrações.
