# WP-557 — Ensaio sintético de duas rotas por 72 horas

## Objetivo

Criar um protótipo offline e repetível para exercitar recuperação de propostas
e qualificação inbound usando apenas dados inventados, relógio controlado e
falhas injetadas.

## Escopo

- Fixture com oito oportunidades sintéticas, em dois tenants e duas rotas:
  recuperação e inbound.
- Avanço determinístico por 72 horas, com checkpoint serializado no meio e
  comparação da retomada com uma execução contínua.
- Cenários de permissão ausente, opt-out, encaminhamento humano, limite de
  contato por oportunidade/canal, duplicação de eventos e falha transitória com retry.
- Deduplicação de eventos por tenant; transições de estado com registro de
  auditoria e instante derivado do relógio sintético.
- Relatório CLI sanitizado com contagens, sem conteúdo de mensagens.

## Limites e interpretação

- O simulador não chama a API, serviços da aplicação, banco de dados, n8n ou
  provedores externos; não envia mensagens nem faz chamadas pagas.
- O limite de contato por oportunidade/canal é um parâmetro exclusivo da
  fixture, não uma política aprovada para operação real.
- A saída mede apenas esta simulação de referência. Não comprova enforcement
  em produção, prontidão comercial, sucesso real ou conclusão da F2.
- Nenhuma alteração em schema, migration, autenticação ou fluxo de produção.

## Validação

```bash
uv run pytest tests/test_wp557_synthetic_dual_path.py
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
scripts/preflight.sh
```