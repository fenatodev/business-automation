# WP-556 — Relógio injetável para follow-up sintético

## Objetivo

Permitir ensaios determinísticos de oportunidades estagnadas sem esperar o
relógio real, preservando o comportamento padrão do serviço.

## Escopo

- `find_stale_opportunities()` aceita `now` opcional e keyword-only.
- Sem `now`, usa o horário UTC atual como antes.
- Um `now` sem fuso é interpretado como UTC.
- O limite continua estrito: uma oportunidade exatamente em `stale_days` não
  é considerada estagnada.
- A consulta continua isolada por `company_id` e exclui oportunidades fechadas.
- Teste sintético cobre relógio fixo, limite, oportunidades fechadas e isolamento
  entre tenants.

## Fora de escopo

- Nenhuma mensagem, contato ou ação externa é enviada.
- Não altera API, autenticação, schema, migrations, scheduler ou critérios
  comerciais.
- O ensaio não conclui F2 nem comprova operação com clientes reais.

## Validação

```bash
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
```