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
- Routers atuais: `companies`, `leads`, `customers`, `conversations` e `opportunities`.

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

Use sempre a contagem real retornada por `uv run pytest`; não mantenha contagem fixa de testes neste arquivo.

## Regras de segurança e dados

- Nunca usar ou modificar o PostgreSQL real durante testes.
- Nunca executar migrations sem solicitação explícita.
- Nunca colocar segredos ou `.env` real no Git.
- Não usar dados reais de clientes no repositório público.

## Regras de mudança

- Fazer mudanças pequenas e focadas.
- Não alterar comportamento fora do escopo solicitado.
- Para work packages autorizados, usar o fluxo GitHub-first descrito abaixo; isso inclui commit e push da branch do WP sem nova confirmação.
- Antes de grandes refatorações, analisar primeiro.

## Multi-tenancy, auth e exposição pública

- Company é a raiz de tenant e o isolamento existente deve ser preservado.
- Auth Bearer mínima e isolamento tenant estão implementados para o piloto privado.
- `company_id` fornecido pelo cliente nunca substitui o tenant derivado da identidade autenticada.
- A API continua não autorizada para exposição pública; qualquer ampliação exige gate próprio.

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
- Opportunity
- ProposalBrief
- Lead
- Customer
- Conversation
- Message

Company é a raiz lógica do tenant.
Opportunity pertence diretamente a uma Company.
ProposalBrief herda o tenant exclusivamente da Opportunity.
Leads, customers e conversations pertencem a uma Company.

## Estratégia de testes

- A suíte normal usa SQLite em memória com StaticPool.
- PRAGMA foreign_keys=ON deve permanecer habilitado nos testes.
- Base.metadata.create_all/drop_all é usado apenas nesse banco isolado.
- Essa suíte NÃO substitui a validação PostgreSQL/Alembic.
- O repositório já possui harness separado com PostgreSQL descartável para validar Alembic e schema real.
- Mudança de migration/schema deve executar esse harness e receber segunda revisão.
- Não codifique o número atual de testes como regra permanente; o número pode crescer. Sempre execute `uv run pytest` e use o resultado atual.

## Dívida técnica conhecida

- A cadeia Alembic atual já foi recuperada e validada em PostgreSQL descartável; preservar um único head.
- Não alterar migrations históricas fora de tarefa explícita.
- Toda nova migration/schema continua high-risk e exige PostgreSQL descartável + segunda revisão.
- A regra Conversation possuir lead_id OU customer_id, mas não ambos, atualmente depende da aplicação e deverá futuramente ter proteção adequada no banco.

## Segurança

- A API possui autenticação Bearer mínima e isolamento tenant para o piloto privado.
- Admin não recebe acesso implícito a dados tenant.
- Tenant vem do contexto autenticado; `company_id` enviado pelo cliente nunca concede autoridade.
- Cross-tenant por ID deve permanecer oculto conforme os contratos existentes.
- A API continua não autorizada para exposição pública.
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

## Prioridade de execução

A ordem padrão de execução é:

1. **ChatGPT/GitHub primeiro** para tudo que puder ser resolvido apenas com o repositório remoto: análise, arquitetura, documentação, revisão, criação/edição de arquivos, branches, commits, PRs e merges autorizados.
2. **Pi/local somente quando houver dependência local real**, como executar testes/comandos, acessar runtime/serviços locais, hardware, arquivos não versionados, ambiente privado, containers ou outra evidência que não esteja disponível pelo GitHub.
3. Não criar work package para Pi apenas para delegar trabalho que pode ser concluído integralmente pelo GitHub.
4. Quando Pi for necessário, ChatGPT prepara um WP pequeno e autossuficiente; Pi executa localmente e faz handoff pela branch remota conforme as regras abaixo.

O objetivo é minimizar tool calls remotas e trabalho local sem perder rastreabilidade, testes ou gates de segurança.

## Contrato de handoff para Continue / Qwen 3.5 9B

O **ChatGPT prepara, implementa e revisa no GitHub** o que não depende do
computador. O **Continue com Qwen 3.5 9B** recebe apenas o **passo local mínimo
já definido**, não a arquitetura inteira, e **não** inicia novo WP sozinho.

**O GitHub é também o meio de entrega das specs ao Continue.** Manter o
handoff integral em `specs/wp-NNN-*.md` versionado na branch correta,
validado remotamente e, quando aplicável, integrado na `main`. No chat,
enviar **apenas** referência do GitHub, SHA exato, ação local mínima e
STOP. O Continue lê a spec no **clone temporário verificado**, não precisa
que o usuário cole blocos longos nem pode confiar em um checkout antigo.
Se faltar GitHub, o arquivo, a revisão ou o SHA não conferir => **STOP**
e relatório de falha, nunca inventar sucesso nem implementar substituto.

**Ao preparar uma ficha local:**
1. Limitar a **uma tarefa, um checkout, um resultado observável**. Preferir
   até **3 comandos verificáveis**; se não couber, dividir antes do handoff.
2. Incluir **branch exata, repositório GitHub completo, paths literais,
   pré-condições, comandos prontos, saída esperada, proibições e STOP**.
3. Não exigir que Qwen deduza diretórios, versões, URLs, stack, permissões
   ou regras consultando histórico de chats; copiar só o contrato essencial.
4. Se código e testes já foram escritos/revisados remotamente, Qwen apenas
   **valida**, sem refatorar, corrigir ou implementar itens adjacentes.
5. Não passar caminhos de projeto genéricos (ex.: `/workspace`,
   `/home/pi`) sem evidência de que existem no host autorizado.

**Preflight e Git imutável para validação local:**
- **Nunca** executar `git stash`, `git restore`, `git clean`,
  `rm`, `git checkout` ou `git reset` num checkout de usuário
  para "limpar" os testes. Encontrou alteração inesperada? **STOP**.
- Clonar em diretório temporário **novo**, usar URL **completa** do
  repositório: `https://github.com/fenatodev/business-automation.git`.
  `origin/wp/...` é **ref Git, nunca URL de `git clone`**.
- Preferir clone normal (não raso) do **único branch do WP**; fazer
  `git fetch origin main` se precisar do `merge-base`.
  O checkout operacional, `.env`, Postgres, API e ERPNext ficam intocados.
- Rodar só testes com fixtures sintéticas/isoladas. Não executar
  migration real, Docker, deploy, Git merge ou push como efeito da validação.

**Tratamento de erro / anti-loop (obrigatório):**
- Inspecionar **código de saída real e stderr**, não confiar apenas no
  indicador `tool succeeded` que informa somente que o comando foi
  executado. Ex.: `fatal`/exit 128 é **falha**, mesmo com chamada aceita.
- **Nunca repetir comando idêntico após falha.** Identificar causa e
  permitir **no máximo uma tentativa corrigida**, com mudança explícita;
  falhou novamente => **STOP**, sem investigação ilimitada.
- Não apagar testes não versionados ou arquivos do usuário para fazer
  `pytest` passar. Se o ambiente estiver contaminado, trocar para um
  novo clone descartável **sem modificar o original**.
- Não reexecutar uma operação com efeitos colaterais quando o resultado
  é incerto. Verificar estado antes de qualquer reenvio/duplicação.
- Se o passo depender de credencial, autorização adicional, caminho
  desconhecido ou ação fora do escopo: **STOP** com motivo, não adivinhar.
- Finalizar explicitamente com **PASS** ou **FAIL**, sem carregar
  automaticamente a próxima tarefa.

**Handoff curto e estável:** `WP`, `branch/commit`, `PASS|FAIL`,
`testes (contagem real)`, `verificações`, `bloqueio (se houver)`.
Sem segredos, logs integrais, dados reais nem explicações prolixas.

## Workflow dos agentes

- Ler AGENTS.md antes de mudanças.
- Inspecionar código real antes de assumir arquitetura.
- Para mudanças maiores, propor plano antes de editar.
- Preferir mudanças pequenas verificáveis.
- Em work packages autorizados, criar checkpoint e push da branch do WP conforme `GitHub-first handoff` e `GitHub progress checkpoints`.
- Não alterar arquivos fora do escopo apenas para “melhorar” o projeto.
- Se um teste revelar um problema de comportamento existente, explicar antes de mudar esse comportamento.

## GitHub-first handoff

Para reduzir dependência de acesso remoto ao computador, GitHub é o canal padrão de
handoff, evidência e revisão entre Pi e ChatGPT.

Para cada work package autorizado:

1. trabalhar em uma branch própria no formato `wp/<id>-<descricao-curta>`;
2. se a sessão começar em `main`, criar a branch antes da primeira alteração;
3. executar somente um WP por sessão;
4. não carregar nem executar automaticamente o WP seguinte;
5. validar o trabalho conforme este AGENTS.md;
6. criar commit apenas com arquivos pertencentes ao WP;
7. fazer push somente da branch do WP para `origin`;
8. encerrar após o push e informar branch + commit.

O estado remoto da branch deve ser suficiente para revisão por GitHub. Não depender
de copiar saída da CLI nem de acesso por Desktop Commander para o handoff normal.

Se já existirem alterações locais do usuário ou de outro WP, não misturá-las.
Interromper e relatar o conflito de escopo.

### Restrições permanentes

- Nunca fazer push direto em `main` durante execução de WP.
- Nunca fazer merge automaticamente.
- Nunca fazer force-push ou reescrever histórico publicado.
- Nunca apagar branches remotas sem autorização explícita.
- Nunca publicar/deployar como consequência de um WP sem autorização específica.
- Para WPs normais e escopados, o usuário autoriza ChatGPT a fazer merge em `main` após revisão bem-sucedida, sem nova confirmação. Release, deploy, operação destrutiva ou mudança ambígua continuam exigindo autorização específica.
- Um push de branch não implica aprovação, merge ou release.
- Se o push falhar, preservar o commit local e relatar o erro.

## GitHub progress checkpoints

The user permanently authorizes Pi to create Git commits and push them to
GitHub as progress checkpoints under the rules below.

### When to checkpoint

Pi MUST create a checkpoint after every meaningful completed development task
or milestone when:

- the requested task is complete;
- relevant tests pass;
- compileall passes when applicable;
- `git diff --check` passes;
- no known broken behavior is being intentionally committed;
- no Codex review required by AGENTS.md is still pending.

For longer or risky work, Pi should also make sure a safe checkpoint exists
BEFORE beginning the risky change.

### Checkpoint procedure

Before committing:

1. inspect `git status`;
2. inspect the relevant diff;
3. run the required validation from AGENTS.md;
4. confirm no secrets, `.env`, real client data, credentials, `.ai/`, temporary
   files or unrelated changes are being included.

Then:

1. create a concise conventional-style commit describing the completed work;
2. push the CURRENT working branch to `origin`;
3. verify that the push succeeded;
4. report the commit hash and branch to the user.

Example:

```bash
git add <only relevant files>
git commit -m "fix: preserve customer message on agent failure"
git push origin <current-branch>
```

### Important restrictions

- Never use `git add .` blindly when unrelated or unknown files exist.
- Never commit secrets, credentials, `.env`, real customer data or `.ai/`.
- Never force-push.
- Never rewrite published history unless explicitly authorized.
- Never automatically merge branches.
- Never automatically push directly to `main` as part of a merge/release
  operation unless that workflow was explicitly authorized.
- Normal progress checkpoints should be pushed to the current development
  branch.
- Do not create checkpoint commits when tests are failing unless the user
  explicitly requests saving a known-broken experimental state.
- Do not commit a Codex review file from `.ai/`.
- If GitHub push fails, keep the local commit and clearly notify the user.
- If there are unrelated user changes in the working tree, do not include them
  in the checkpoint; ask if their ownership or relevance is ambiguous.

### User interaction

The user does NOT need to approve each normal progress checkpoint individually.

Pi should simply report after a successful checkpoint:

```text
CHECKPOINT SAVED
Branch: <branch>
Commit: <hash> <message>
GitHub push: successful
```

Normal WP merges reviewed by ChatGPT are pre-authorized by the user. Releases, deploys, destructive Git operations, force pushes, history rewrites or ambiguous changes still require explicit user approval.

## Agent workflow and escalation

- ChatGPT/GitHub é o executor padrão para trabalho que não dependa do ambiente local.
- Pi é o executor local para tarefas que realmente exigem comandos, testes, runtime, hardware, arquivos locais ou serviços privados.
- Codex/Astra pode ser usado para arquitetura ou segunda revisão de mudanças de maior risco/complexidade.
- Não permitir que dois agentes editem simultaneamente o mesmo workspace/branch.

Quando uma tarefa precisar de Pi, ela deve chegar como um WP pequeno, autocontido e limitado ao necessário. Pi não deve inventar arquitetura adjacente nem puxar automaticamente o próximo WP.

Mudanças de alto risco exigem segunda revisão antes da execução/aplicação quando envolverem:
- authentication ou authorization;
- RBAC;
- tenant isolation ou multi-tenancy security;
- database schema changes;
- Alembic migrations;
- destructive database operations;
- security-sensitive behavior;
- major architectural refactors;
- important dependency changes;
- production/deployment configuration;
- correção de teste que altere comportamento existente da aplicação.

Quando a dependência local for inevitável, Pi deve produzir evidência pela branch remota e parar. ChatGPT revisa pelo GitHub antes do próximo pacote. Se o WP estiver correto, o merge normal está pré-autorizado; release/deploy e operações sensíveis continuam dependendo de autorização específica.

## Product context

Before making product, roadmap or commercial assumptions, read:

- `docs/PRODUCT.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`

Do not invent answers for open product/commercial decisions.
If implementation depends on an unresolved business decision, ask the user.

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
