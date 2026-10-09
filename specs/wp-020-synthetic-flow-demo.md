# WP-020 — Demonstração técnica sintética de um fluxo (F2)

**Status:** código preparado no GitHub; validar antes de integrar.  
**Base canônica:** `main@a3ce2178ee860c3a3f9f0c503048fbd3ee9e9552`.  
**Branch:** `wp/020-synthetic-order-crm-demo`.  
**Executor remoto:** ChatGPT + GitHub. **Executor local eventual:** Continue/Qwen 3.5 9B **apenas para validar**.  
**Objetivo:** executar offline **um** fluxo de aviso de pedido fictício para CRM em memória, com validação, chave de deduplicação, conflito e tratamento de timeout ambíguo, para servir como demonstração técnica honesta no futuro site.

## 1. Contrato e fronteira

**Estado anterior:** existe oferta `client0-integration-flow-v1`, processo G0–G10 e core privado de oportunidades; **não** há conector real de e-commerce/CRM nem case comercial medido. Esta entrega não toca esses componentes.

**Entrada fictícia:** dicionário com **exatamente** `order_ref` (`ORD-101`) e `customer_ref` (`CUST-001`). Dados adicionais ou formato diferente => `rejected`.

**Saída:** `created`, `duplicate`, `conflict`, `rejected`, `unknown` ou `blocked`. Se houve timeout antes ou após eventual gravação, **não repetir** a escrita; bloquear a mesma chave até `reconcile` obter read-back positivo **do mesmo payload**. Read-back ausente ou diferente => `unresolved`.

**Unidade e limites:** apenas a demonstração `examples/order_to_crm.py`, testes isolados e documentação. **Nenhuma** rede, credentials, .env, SQL, Docker, ERPNext, providers, edição do core, tentativa em clientes, postagem pública ou atualização da API `127.0.0.1:8788`. Fake em memória **não é prova** de idempotência distribuída nem ERP integrado.

## 2. Arquivos da implementação remota

| Caminho | Função |
| --- | --- |
| `examples/order_to_crm.py` | Código stdlib com fake de CRM e CLI JSON determinístico |
| `tests/test_demo_order_to_crm.py` | Testes de eventos, negativos, timeout antes/depois, bloqueio e reconciliação |
| `examples/README.md` | Instruções reproduzíveis e limites para portfólio |
| `AGENTS.md` | Contrato permanente de handoff para Qwen/Continue |
| Este arquivo | Entrada mínima do WP e validação segura |

**Não modificar** `app/`, `migrations/`, `docker-compose.yml`, `uv.lock`, outros testes, checkout operacional ou `.env`.

## 3. Preflight do agente local: regras sem interpretação

O Continue **não precisa escrever código, commitar, fazer push ou checkout
do projeto existente**. Somente validar o estado remoto usando **um
diretório descartável novo**, **sem reusar** `/home/fenatodev/dev/projects/business-automation`
(esse checkout tem trabalho não versionado do usuário).

### Uma única sequência de comandos (não adicionar etapas)

Em terminal limpo, **somente depois de confirmado que a branch existe**:

```bash
set -euo pipefail
tmp="$(mktemp -d /tmp/ba-wp020-qwen.XXXXXX)"
git clone --quiet --single-branch --branch wp/020-synthetic-order-crm-demo \
  https://github.com/fenatodev/business-automation.git "$tmp/repo"
cd "$tmp/repo"
test ! -e .env
git fetch --quiet origin main:refs/remotes/origin/main
git diff --check origin/main...HEAD
uv run pytest -q
.venv/bin/python -m compileall -q app tests examples
node --check app/operator_ui/app.js
python3 -m examples.order_to_crm
test -z "$(git status --porcelain)"
printf 'WP020_LOCAL=PASS\n'
```

Se qualquer comando falhar, **não** continuar nem declarar PASS.
Informar **o primeiro erro, comando e exit code**; no máximo **uma**
tentativa corrigida com mudança justificada; **nunca repetir o mesmo
comando que falhou**. Não usar `git clone origin/...` (é ref, não URL),
`git stash`, `git restore`, `git clean`, `rm`, `git reset`
ou editar arquivos existentes. Erros de teste não autorizam exclusões
de arquivos do checkout de outro WP.

## 4. Aceite observável

1. CLI imprime JSON com `kind=synthetic_offline_demonstration` e zero erro.
2. `created` grava apenas uma vez, replay vira `duplicate`, chave alterada vira `conflict` sem alterar o registro; entrada inválida vira `rejected`.
3. Timeout depois de escrita gera `unknown` e bloqueia repetição; read-back coincidente gera `reconciled`; nova tentativa vira `duplicate`, não recriação.
4. Timeout antes da escrita gera `unknown`; read-back vazio permanece `unresolved` e bloqueado. Outra chave continua operando.
5. Testes não acessam Postgres, arquivos operacionais, credenciais, APIs, Docker ou ambiente real; a suíte existente permanece verde.
6. Nenhuma afirmação falsa de case/cliente real, ROI, dados financeiros, exactly-once nem automação externa implementada.

## 5. Encerramento do Qwen — formato obrigatório

Responder **somente**:

```text
WP020_LOCAL=PASS|FAIL
branch=<nome>
commit=<sha curta>
pytest=<quantidade real aprovada ou erro>
compileall=PASS|FAIL|NOT_RUN
js_check=PASS|FAIL|NOT_RUN
diff_check=PASS|FAIL|NOT_RUN
demo_cli=PASS|FAIL|NOT_RUN
bloqueio=<none | primeiro erro e comando>
```

O ChatGPT faz revisão GitHub e merge após PASS. Não passar outro WP
ao Qwen nesta sessão. Publicação de site e comunicação externa exigem
gates próprios.
