# WP-036 — Gerador de candidato comercial com LLM local e transporte simulado

**Estado:** especificação para Junie; nenhum código implementado por esta ficha.
**Repositório:** `fenatodev/business-automation`. Executar sobre `main`
atualizada depois do PR #100, que implementou o WP-035.

## Objetivo — capacidade real, sem custos ou canais externos

Transformar o núcleo offline WP-035 em um fluxo que **possa** usar um modelo
Ollama local, mas que rode com **fakes** nos testes e na demonstração.
A implementação não deve iniciar Ollama, baixar modelos, fazer uma chamada
remota, gastar tokens, enviar mensagens, alterar n8n, Oracle, produção,
segredos nem banco.

Arquitetura mínima:
```text
CommercialIntakeEvent
    -> CandidateGenerator (porta pequena e substituível)
    -> candidato LLM / erro classificado
    -> process_commercial_intake() do WP-035
    -> IntakeDecision {can_send:false, simulation_only:true}
```
**Regra essencial:** modelo gera **texto candidato**, mas **não** decide
autorização, canal, aprovação, preço, envio ou ações externas. O guard
do WP-035 é sempre executado, inclusive em erro.

## Estado confirmado do código

- `app/services/commercial_intake.py`: `CommercialIntakeEvent`,
  `CandidateReply`, `IntakeDecision`, `process_commercial_intake`.
  O output é imutável e sua política mantém `can_send=False`.
- `app/services/agent.py` é fluxo Ollama legado de conversas, com
  `httpx.post` e `settings.ollama_url`; **não alterar** nesta tarefa.
- `app/routers/conversations.py` tem escrita real e risco conhecido
  de duplicação de mensagem após falha; **não alterar/chamar**.
- `scripts/demo_commercial_intake.py` já existe com três cenários.
- A API é privada; n8n instalado em máquina local, mas ainda não integrado.
- AGENTS.md exige testes isolados, revisão e proíbe mudanças fora de WP.

## Escopo para Junie — até quatro arquivos

1. Criar `app/services/intake_candidate_generator.py` contendo:
   - Porta `CandidateGenerator` (Protocol ou interface simples) para
     `generate(event: CommercialIntakeEvent) -> CandidateReply`.
   - `StaticCandidateGenerator` determinístico e sem rede, usando
     pergunta de esclarecimento, para demo e testes.
   - `OllamaCandidateGenerator`, **injetando `httpx.Client`** e
     `model` fixado pelo operador, nunca vindo do texto do cliente.
     Por padrão, endpoint **somente loopback** `http://127.0.0.1:11434`
     (ou `localhost` / IPv6 loopback), `/api/chat`, resposta sem streaming,
     timeout explícito e `follow_redirects=False`. Rejeitar URL pública,
     IP não loopback, credenciais embutidas, query string, fragment,
     ou endpoint fornecido por evento. Não adicionar acesso a provider
     externo, nem a OpenRouter/DeepSeek nesta etapa.
   - Prompts: política confiável no papel `system`, `event.message`
     somente em `user` (conteúdo não confiável), `service_context`
     marcado como confiável **apenas se configurado pelo operador**.
     Modelo não deve inventar preços, prazos ou garantias e só deve
     solicitar dados para qualificação. Não transformar saída do modelo
     em JSON arbitrário executável, nem copiar dados sensíveis para logs.
   - Validar estrutura Ollama `{"message":{"content":"..."}}`, limites
     de tamanho, texto vazio e status HTTP. Definir
     `CandidateGenerationError` estável/sanitizado; não vazar response
     body, prompt, texto do cliente, `Authorization` ou stack interna.
   - `evaluate_intake(event, generator)` que chama geração e depois
     obrigatoriamente `process_commercial_intake`. Em falha de
     geração, retornar decisão segura, com `needs_human_review=True`,
     flag `provider_unavailable`, rascunho padrão sem dado inventado,
     `can_send=False` e `simulation_only=True`.
     Não mutar `IntakeDecision` diretamente (modelo congelado).

2. Criar `tests/test_intake_candidate_generator.py` com testes fake HTTP
   (por exemplo `httpx.MockTransport`), sem abrir sockets, para:
   resposta válida, indisponibilidade/timeout, HTTP 4xx/5xx, JSON
   inválido, `message` ausente, `content` não-string, string vazia,
   corpo enorme, endereço não loopback, redirect, método/rota correta,
   separação system/user, injeção no texto do cliente, candidato
   financeiro perigoso filtrado pelo guard, saída estruturada em
   falha com revisão, flags e invariantes de não envio.
   Verificar que `httpx.MockTransport` **nunca** recebe host externo.

3. Criar `scripts/demo_intake_candidate_generator.py`, sem rede,
   com pelo menos três entradas fictícias: normal, adversarial e
   gerador indisponível. Deve usar só `StaticCandidateGenerator`/
   fake e imprimir JSON estruturado. Nenhum live endpoint.

4. Criar `docs/operations/client0-llm-preview.md` com contrato de
   porta, execução totalmente offline, requisitos para eventual
   uso local Ollama, riscos, diferença candidato vs autorização,
   caminhos futuros: n8n interno com deduplicação/revisão e
   provedores externos **somente após aprovação específica de custos**.

## Restrições e pré-condições

- Não reescrever o WP-035; se descobrir bloqueio real no contrato,
  documentar e STOP antes de mudar regras de negócio.
- Não tocar em auth, ORM, schema, migrations, banco real, Docker,
  n8n ativo, Oracle, variáveis GitHub, servidor ou máquina de cliente.
- Não usar LLM remoto pago, nem chamar o próprio Ollama durante testes.
- Não introduzir dependência se `httpx` e Pydantic já resolvem.
- Não usar mensagens nem contextos de clientes reais nos testes ou docs.
- Não adicionar endpoint público, envio de mensagem nem agendamento.
- Não afirmar que uma proposta de modelo foi revisada ou enviada.
- Diferenciar **idempotência funcional** de deduplicação persistente
  (esta última ainda não existe).
- Se algum erro for imprevisível, falhar fechado, sem retry automático
  que possa causar chamadas indesejadas.

## Execução e aceitação

Ler `AGENTS.md` e os arquivos reais antes da edição. Usar branch
`wp/036-local-llm-candidate` criada a partir da `main` recente.
Não trabalhar sobre checkout sujo; preferir clone temporário isolado.

Comandos obrigatórios:
```bash
uv run pytest -q tests/test_intake_candidate_generator.py
uv run pytest -q
uv run python -m compileall -q app/services tests scripts
git diff --check
uv run python scripts/demo_intake_candidate_generator.py
```

Fazer commit e push somente da branch; abrir PR para `main` se possível.
**Não fazer merge.** Reportar PASS/FAIL, branch, SHA, PR, contagem
real de testes, demonstração e limitações. STOP após WP-036.

**Próximo passo, ainda não autorizado:** conectar ao n8n por canal
interno com autenticação, deduplicação, limites e aprovação de saída.
