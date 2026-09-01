# AGENTS.md

Contexto permanente para agentes de IA neste repositório.

## Projeto

Business Automation API.

## Stack

Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Docker, uv, pytest e Ollama.

## Arquitetura atual

- `app/main.py` deve ficar mínimo.
- Schemas ficam em `app/schemas.py`.
- Dependências FastAPI ficam em `app/dependencies.py`.
- Routers ficam em `app/routers/`.
- Integração de IA fica em `app/services/agent.py`.
- Routers atuais: `companies`, `leads`, `customers` e `conversations`.

## Validação obrigatória

Após alterações, executar obrigatoriamente:

```bash
uv run pytest
```

Também validar:

```bash
.venv/bin/python -m compileall app tests
git diff --check
```

Atualmente existem 9 testes.

## Regras de segurança e dados

- Nunca usar ou modificar o PostgreSQL real durante testes.
- Nunca executar migrations sem solicitação explícita.
- Nunca colocar segredos ou `.env` real no Git.
- Não usar dados reais de clientes no repositório público.

## Regras de mudança

- Fazer mudanças pequenas e focadas.
- Não alterar comportamento fora do escopo solicitado.
- Não fazer commit ou push sem autorização explícita.
- Antes de grandes refatorações, analisar primeiro.

## Multi-tenancy, auth e exposição pública

- Preservar multi-tenancy como requisito futuro importante.
- Auth/RBAC e isolamento de tenant serão obrigatórios antes de exposição pública.

## Serviço de agente/Ollama

- Falha do serviço de agente deve preservar a mensagem do cliente e retornar 503 sem expor detalhes internos.
- `OLLAMA_URL` e `OLLAMA_MODEL` vêm de settings/environment.
- Modelo padrão atual do Ollama: `qwen3:8b`.

## Respostas do agente de programação

- Devem ser concisas.
- Devem mostrar testes/diff ao terminar.

## Domínio atual

As entidades principais são:

- Company
- Lead
- Customer
- Conversation
- Message

Company é a raiz lógica do tenant.
Leads, customers e conversations pertencem a uma company.

## Estratégia de testes

- A suíte normal usa SQLite em memória com StaticPool.
- PRAGMA foreign_keys=ON deve permanecer habilitado nos testes.
- Base.metadata.create_all/drop_all é usado apenas nesse banco isolado.
- Essa suíte NÃO valida compatibilidade completa com PostgreSQL nem migrations.
- Futuramente deve existir uma suíte separada com PostgreSQL descartável para validar Alembic e o schema real.
- Não codifique o número atual de testes como regra permanente; o número pode crescer. Sempre execute `uv run pytest` e use o resultado atual.

## Dívida técnica conhecida

- A cadeia atual de migrations precisa ser revisada para garantir que um PostgreSQL totalmente vazio consiga executar `alembic upgrade head`.
- A baseline do Alembic foi criada depois de parte do schema inicial existir, portanto não assumir que migrations atuais recriam todo o banco do zero.
- Não tente reparar migrations sem uma tarefa explícita e sem banco PostgreSQL descartável para validação.
- A regra Conversation possuir lead_id OU customer_id, mas não ambos, atualmente depende da aplicação e deverá futuramente ter proteção adequada no banco.

## Segurança

- A API ainda não possui autenticação/RBAC/isolamento completo de tenant.
- Não considerar a API segura para exposição pública enquanto isso não existir.
- `company_id` fornecido pelo cliente não deve futuramente ser tratado como autorização; tenant deverá vir do contexto autenticado.
- Nunca introduzir dados reais de clientes em testes ou exemplos públicos.

## Agent reply

- A mensagem customer é persistida antes da chamada ao modelo.
- AgentServiceError é convertido em HTTP 503 com mensagem genérica.
- Falhas internas do Ollama não podem ser expostas ao cliente.
- Não capturar Exception genericamente apenas para transformar qualquer bug em 503.
- Existe uma questão futura de idempotência: repetir agent-reply após falha pode criar mensagem customer duplicada. Não resolver isso fora de uma tarefa específica.

## Direção do produto

O objetivo é uma plataforma multi-tenant de automação de negócios com IA.
A API deve evoluir sem acoplar regras a um único cliente ou nicho.
Configuração de agente específica por Company será uma capacidade futura.
RAG, automações e integrações entram depois da fundação de dados, segurança e isolamento de tenant.

## Workflow dos agentes

- Ler AGENTS.md antes de mudanças.
- Inspecionar código real antes de assumir arquitetura.
- Para mudanças maiores, propor plano antes de editar.
- Preferir mudanças pequenas verificáveis.
- Nunca auto-commit ou auto-push.
- Não alterar arquivos fora do escopo apenas para “melhorar” o projeto.
- Se um teste revelar um problema de comportamento existente, explicar antes de mudar esse comportamento.

## Agent workflow and escalation

- Pi is the default operational agent for this repository.
- Normal development discussion, implementation, testing and diff review happen through Pi.
- Codex IDE is a second-review agent, not the default executor.
- Do not have Pi and Codex edit the workspace simultaneously.

Pi may implement directly when the task is small or medium, scoped and covered by existing tests.

Pi MUST stop and request a Codex review before proceeding with high-risk changes involving:
- authentication or authorization;
- RBAC;
- tenant isolation or multi-tenancy security;
- database schema changes;
- Alembic migrations;
- destructive database operations;
- security-sensitive behavior;
- major architectural refactors;
- important dependency changes;
- production/deployment configuration;
- a failing test whose proposed fix changes existing application behavior.

Pi should also recommend Codex review before a significant merge or release.

When escalation is required, Pi must explicitly say:
"Codex review required"
and briefly state what needs review.

Codex should normally review the current code/diff without editing it.
After the review, Pi remains the primary executor unless explicitly instructed otherwise.

The human user should not need to decide routinely which agent to use;
Pi is responsible for signaling when second review is appropriate.

## Local Codex review handoff

- When Pi requests "Codex review required", the review may be exchanged through:
  `.ai/codex-review.md`
- `.ai/` is local agent workspace and must never be committed.
- Codex may write ONLY `.ai/codex-review.md` when explicitly asked for a review.
- Writing this review file is not considered editing application code.
- Codex must not modify source code during review unless explicitly authorized.
- After Codex writes the review, Pi should read `.ai/codex-review.md`,
  summarize the findings to the user, and propose the next action.
- Pi must not blindly apply Codex recommendations; inspect them against the
  actual code and existing tests first.
- A new Codex review should replace the previous contents of
  `.ai/codex-review.md` to avoid stale recommendations.
