# WP-035 — Núcleo de triagem comercial autônoma (ensaio offline)

**Status:** ficha pronta para execução pelo **Junie**, sem implementação neste PR.  
**Referência:** `fenatodev/business-automation` em `main` após integração desta ficha.  
**Missão:** entregar um primeiro **fluxo executável** de entrada comercial
(`mensagem sintética → sugestão da IA simulada → validação de política →
decisão estruturada`). Serve como núcleo testável da futura automação com
n8n e providers reais, **não é um bot público nem um envio**.

## 1. Contexto real confirmado

- API privada FastAPI, Python 3.12, pytest e `uv`.
- `app/services/agent.py` possui `generate_agent_reply()`, atualmente
  acoplado ao Ollama, sem retorno estruturado. **Não alterar nesta ficha**.
- `app/routers/conversations.py` persiste mensagens e chama o agente;
  tem risco conhecido de duplicidade após falhas. **Não utilizar, alterar nem
  disparar esta rota para o ensaio**.
- O núcleo `Opportunity` é para captação de projetos do 99Freelas:
  `app/routers/opportunities.py`. **Não misturar** com atendimento inbound.
- n8n self-hosted existe, mas a execução do Junie **não recebe** permissão
  para alterar workflows/credenciais da instância real.
- A VPS OCI A1 tem agendamento separado e não é dependência deste WP.
- `AGENTS.md` na raiz estabelece testes, branches, proteção de dados
  e estratégia GitHub-first.

## 2. Contrato de entrada e saída (100% sintético)

Propor e implementar `app/services/commercial_intake.py` com **função pura
e testável**, recebendo um evento de entrada e uma proposta textual
de agente **injetada via parâmetro**, sem chamar Ollama nem qualquer rede.

Entrada exemplar (nomes exatos a documentar no código e testes):

```json
{
  "channel": "web",
  "message": "Preciso automatizar confirmação de agendamentos da minha loja.",
  "service_context": "Automação de processos e integrações sob diagnóstico.",
  "event_id": "evt-synthetic-001"
}
```

A `service_context` é a única fonte de fatos autorizados sobre o
serviço. `message` é **dado não confiável**, nunca instrução de sistema.
O gerador (futuro LLM) fornece apenas um **candidato** de resposta;
não concede permissão, canal, identidade, aprovação ou acesso a dados.

Retorno de decisão validada, formato/nomes definidos e testados:

```json
{
  "event_id": "evt-synthetic-001",
  "intent": "automation_inquiry",
  "next_step": "ask_clarification",
  "draft_reply": "Qual processo você quer automatizar e qual ferramenta utiliza hoje?",
  "needs_human_review": true,
  "can_send": false,
  "flags": [],
  "simulation_only": true
}
```

O núcleo **nunca** envia mensagens, cobra, aprova ofertas nem escreve em
banco. `can_send` é **sempre false** neste pacote; um futuro adaptador
necessita política de saída separada e decisão de autorização. Não
prometer preço, prazo, ROI, disponibilidade ou suporte não presentes em
contexto confiável. Mensagens que pedirem credenciais, contornarem
instruções, tentarem aprovar gasto ou exigirem exceções devem produzir
`needs_human_review=true`, `can_send=false` e uma flag de risco.

Prever entradas inválidas (mensagem vazia, comprimento excessivo,
`event_id` vazio, payload malformado), respostas candidatas vazias e
falha do gerador com **parada explícita e sem efeito externo**. Limitar
comprimento do draft e do contexto. Não tratar texto da LLM como JSON
arbitrário a ser executado ou código. Sem dependências novas, migrations,
modelos ORM, novos endpoints ou alteração das rotas existentes.

**Idempotência nesta etapa:** a função pura deve emitir resultado
determinístico para a mesma entrada/candidato e preservar o `event_id`.
A deduplicação persistente entre eventos será uma etapa separada
(`n8n` ou banco + autorização), não alegar que existe.

## 3. Implementação solicitada ao Junie

Arquivos do pacote (não adicionar extras sem causa comprovada):

1. `app/services/commercial_intake.py` — modelos/validação mínimos e
   política de decisão pura. Pode usar Pydantic já instalado.
2. `tests/test_commercial_intake.py` — dados sintéticos, nenhum HTTP,
   banco ou provider real. Cobrir no mínimo:
   - caso comercial legítimo → draft estruturado, sem envio;
   - pedido incompleto → pergunta de esclarecimento;
   - prompt injection ("ignore suas regras...") → marca risco e não envia;
   - pedido de preço/prazo sem fatos verificados → não inventa;
   - entrada vazia/longa/evento inválido → validação falha;
   - candidato vazio/erro de gerador → falha fechada;
   - repetição com mesmos inputs → saída idêntica;
   - qualquer caso → `simulation_only=true`, `can_send=false`.
3. `scripts/demo_commercial_intake.py` — CLI totalmente offline, com
   **3 cenários falsos** (normal, incompleto, adversarial) que imprime
   JSON sintético sem PII, sem acessar recursos locais reais.
4. `docs/operations/client0-intake-preview.md` — execução, campos,
   limitações, conexão futura com o n8n e lista clara do que não está
   autorizado. Não afirmar que existe bot operando no WhatsApp/site.

Usar o mínimo de lógica específica de nicho. Preferir interfaces simples
a frameworks de múltiplos agentes. Não introduzir multiagentes, Redis,
Celery, broker, filas, workflows ativos, scraping, WhatsApp, webhooks,
prospecção ou n8n API neste WP. A próxima fase poderá conectar o
retorno estruturado à orquestração n8n após comprovar utilidade.

## 4. Verificações obrigatórias e regras de execução

- Antes de codificar, conferir `AGENTS.md`, esta ficha e os símbolos
  existentes em `app/services/agent.py` e `app/routers/conversations.py`.
  Se o contrato real divergir, **STOP** e informar; não adivinhar.
- Trabalhar em branch `wp/035-commercial-intake-preview`, derivada
  de `main` atualizada. Não sobrescrever alterações locais do usuário.
  Se o checkout estiver sujo, usar clone/worktree descartável novo.
- Não ler `.env`, credenciais, dados reais, SQLite/PG persistente,
  artefatos de produção ou serviços OCI/n8n. Não usar rede nem provider
  real para gerar respostas de teste.
- Testes:
  `uv run pytest -q tests/test_commercial_intake.py`,
  `uv run pytest -q`,
  `uv run python -m compileall -q app/services tests scripts`,
  `git diff --check`,
  `uv run python scripts/demo_commercial_intake.py`.
- Se falhar, diagnosticar uma vez e corrigir a causa; sem ciclos
  infinitos. Jamais falsear saída de testes.
- Fazer commit/push **somente da branch WP**, abrindo PR para `main`
  se autenticado e autorizado pelo GitHub. **Não fazer merge**, deploy,
  publicar site, criar VM, alterar n8n, emitir cobrança, enviar mensagem,
  prospectar ou mudar permissões/segredos.

## 5. Critérios de aceite e handoff

Aprovado quando: (a) script mostra 3 saídas estruturadas reais,
(b) testes completos passam, (c) nenhuma operação externa ocorre,
(d) teste adversarial força revisão, (e) contrato é reutilizável para
adapter n8n/LLM futuro.

Relatório final conciso: `PASS|FAIL`, branch, commit, PR, contagem
real de testes, saída resumida do demo e bloqueio se houver.
**STOP após este pacote.** Não iniciar integração n8n automaticamente.

## 6. Próximas etapas — não autorizadas por este WP

- WP seguinte: wrapper privado de LLM (Ollama/DeepSeek/alternativas)
  com saída estruturada e fake de rede, controlado pelo mesmo guard.
- WP seguinte: n8n self-hosted para receber evento autenticado,
  deduplicar, pausar e revisar; criação/importação desativada por
  padrão, sem conectar canal externo.
- WP seguinte: validação de atendimento real e só então canal externo,
  consentimento, opt-out, limites financeiros e governança de envio.

**Prova de valor desejada:** IA realiza análise/rascunho automaticamente,
supervisor só entra em exceções e efeitos financeiros/externos. Esta
primeira ficha é a base de segurança testável, não a automação completa.
