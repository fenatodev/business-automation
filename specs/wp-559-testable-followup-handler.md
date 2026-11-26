# WP-559 — Sessão isolável no handler de follow-up

## Objetivo

Permitir validar diretamente o handler agendado de follow-up com o SQLite em
memória da suíte, sem depender de um banco configurado para a aplicação.

## Escopo

- Aceitar uma sessão SQLAlchemy opcional em `handle_followup_job`.
- Manter o comportamento padrão: criar e fechar `SessionLocal` quando nenhuma
  sessão for fornecida.
- Não fechar a sessão fornecida; manter commit e rollback do processamento.
- Cobrir criação, deduplicação, tenant/configuração e ciclo de vida das sessões.

## Limites

- Sem alterações de schema, migrations, API, autenticação ou integrações.
- Testes usam somente SQLite em memória e dados sintéticos.
- Não demonstra execução operacional em produção nem aciona serviços externos.

## Validação

```bash
uv run pytest tests/test_wp559_followup_job_handler.py
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
scripts/preflight.sh
```