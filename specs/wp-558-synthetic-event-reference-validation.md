# WP-558 — Validar referências sintéticas em eventos

## Objetivo

Rejeitar entradas inválidas nos campos de tenant e oportunidade antes de
usá-los para procurar o subject no ensaio offline WP-557.

## Escopo

- Exigir que `tenant_ref` e `opportunity_ref` de cada evento sejam strings no
  formato reservado `SYN-*`.
- Retornar `SimulationInputError` com código estável para referências inválidas,
  inclusive valores não hashable, como listas e objetos.
- Cobrir strings não sintéticas e tipos não textuais com testes parametrizados.

## Limites

- Mudança exclusiva no validador e testes do simulador offline.
- Não altera API, regras de produção, banco de dados, autenticação, n8n ou
  provedores externos.
- Não usa dados reais nem representa enforcement em produção.

## Validação

O preflight completo precisa passar antes de publicar a branch.

```bash
uv run pytest tests/test_wp557_synthetic_dual_path.py
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
scripts/preflight.sh
```