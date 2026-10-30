# Continuidade do desenvolvimento — Codex ou Junie

## Ponto de partida

- Repositório: `fenatodev/business-automation`, branch base `main`.
- Fonte de verdade: GitHub (`AGENTS.md`, `specs/`, `docs/operations/`, CI e PRs).
- A implantação privada de n8n e PostgreSQL **não é** o GitHub; não inferir estado dos serviços de relatórios históricos.
- Codex é opcional e temporário; **Junie deve continuar sem acesso à sessão ou memória do Codex**.
- A aplicação comercial permanece sob gate explícito: não ativar workflows, publicar API nem enviar mensagens sem autorização.

## Primeira sessão de qualquer agente

1. Verificar branch e árvore de trabalho; usar novo worktree da `main` para não sobrescrever trabalho anterior.
2. Ler `AGENTS.md`, os specs das WPs e os PRs abertos antes de implementar.
3. Uma tarefa focada por branch e PR; não desenvolver arquitetura paralela.
4. `uv sync --frozen` em venv próprio do agente, sem assumir que `.venv` do worktree seja válido.
5. Executar `uv run pytest -q`, `uv run python -m compileall -q app tests`, `git diff --check origin/main...HEAD`. Para migrações e concorrência, também testar PostgreSQL descartável.
6. Apresentar evidência com contagem real, riscos, commits e próxima ação; não afirmar E2E PASS com testes unitários.
7. Merge apenas após CI e autorização. Nunca mesclar pelo Junie sem instrução específica.

## Estado técnico no início desta WP

- Pipeline sintético n8n → FastAPI → PostgreSQL validado em ambiente descartável (WP-058); operação real não ativada.
- `/operator` implementa triagem e revisão; resumo e alertas 24h integrados na `main` (WP-059/060).
- WP-061 adicionou contrato de handoff e exclusões de contexto para build Docker. O build sem rede não terminou porque faltava buscar `uv`; validação de build conectado continua separada.
- Codex CLI 0.165.0 instalado no Ubuntu em inspeção anterior; Context Mode bloqueou um toolcall sob aprovação `never` e AgentMemory não teve uso comprovado. **Nenhum deles é dependência do produto**.
- WP-062 (PR deste arquivo): decisão condicional atômica e fila paginada; testes de aplicação aprovados. Concurrency race em PostgreSQL descartável continua sendo gate recomendado antes de exposição real.

## Pontos operacionais obrigatórios antes de ativar clientes

- Revisar backups e restauração do banco real n8n, incluindo chave de criptografia; snapshot não substitui drill.
- Validar autenticação/tenancy no ambiente de destino e revisão humana antes de qualquer saída.
- Confirmar que retries, dedupe e falhas recuperáveis não geram mensagens duplicadas.
- Definir política de retenção, LGPD, métricas e alertas sem PII.
- Não usar API paga, VPS ou exposição pública por inferência; exigir aprovação específica.

## Handoff de cada PR

Registrar objetivo, arquivos, estado (PASS/BLOCKED), comandos e resultados, comportamento em PostgreSQL quando aplicável, riscos, dependências locais, próximo passo concreto e o que **não foi** validado.
