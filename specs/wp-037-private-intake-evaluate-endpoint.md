# WP-037 — Endpoint privado de avaliação comercial para futura orquestração n8n

**Estado:** especificação para Junie; nenhum runtime externo é alterado por esta ficha.
**Base:** `main` após merge do WP-036 (`a87df52c7bcb3a7ac051c0da81319de41188dc85`).

## Objetivo

Expor o núcleo WP-035 + gerador WP-036 por um **endpoint privado, autenticado,
sem persistência e sem efeitos externos**, para que o n8n possa chamá-lo
futuramente sem duplicar lógica de negócio.

Fluxo:
```text
POST /internal/commercial-intake/evaluate
  -> autenticação operator existente
  -> compõe CommercialIntakeEvent com service_context do servidor
  -> gerador configurado (static por padrão; ollama apenas opt-in local)
  -> evaluate_intake()
  -> IntakeDecision
```

O endpoint **não envia mensagem, não grava banco, não cria lead/oportunidade,
não chama n8n e não publica nada**.

## Contratos já existentes

- `app/services/commercial_intake.py`: event/decision e guard;
  `can_send=False`, `simulation_only=True`.
- `app/services/intake_candidate_generator.py`: porta de gerador,
  `StaticCandidateGenerator`, `OllamaCandidateGenerator`,
  `evaluate_intake()`; Ollama é HTTP loopback-only.
- `app/dependencies.py`: autenticação Bearer e `require_operator`.
- `app/database.py`: `Settings` com Ollama atual.
- `app/main.py`: composição dos routers.
- API permanece autorizada apenas para uso privado.

## Escopo de implementação

Até 6 arquivos, sem migration/schema:

1. **`app/schemas.py`**
   - adicionar `CommercialIntakeEvaluateRequest` com somente:
     `channel`, `message`, `event_id`.
   - **não aceitar `service_context`, company_id, model, base_url,
     can_send, flags, prompt ou configuração do provider pelo request**.
   - `extra="forbid"`, limites coerentes com WP-035.

2. **`app/database.py`**
   - settings novos:
     - `intake_generator: Literal["static","ollama"] = "static"`
       via env `BA_INTAKE_GENERATOR`;
     - `intake_service_context`: texto operador, default sintético
       "Automação de processos e integrações sob diagnóstico."
       via `BA_INTAKE_SERVICE_CONTEXT`.
   - não adicionar secrets; não alterar DATABASE_URL.
   - `static` deve ser default para impedir chamada de LLM por acidente.

3. **`app/dependencies.py`**
   - criar dependency pequena para gerador:
     - `static`: `StaticCandidateGenerator`;
     - `ollama`: construir `httpx.Client(follow_redirects=False)`
       e `OllamaCandidateGenerator` usando apenas
       `settings.ollama_url` e `settings.ollama_model`;
     - modo inválido/configuração insegura => HTTP 503 genérico,
       sem expor URL/model/erro.
   - se usar `yield`, fechar o client no finally/context manager.
   - não fazer chamada de rede nesta dependency; rede só acontece
     quando `generate()` é invocado.
   - URL pública continua bloqueada pelo WP-036.

4. **novo `app/routers/commercial_intake.py`**
   - `POST /internal/commercial-intake/evaluate`.
   - `include_in_schema=False`.
   - exige `require_operator`; admin não recebe acesso implícito.
   - compor `CommercialIntakeEvent` usando request +
     `settings.intake_service_context` do servidor.
   - chamar `evaluate_intake`.
   - retornar somente `IntakeDecision`.
   - nenhuma Session/DB; nenhum commit; nenhum background task.
   - erros inesperados do provider não podem vazar detalhes.
   - `event_id` é correlação funcional, **não** prova deduplicação persistente.

5. **`app/main.py`**
   - incluir somente o novo router.

6. **`tests/test_commercial_intake_endpoint.py`**
   Cobrir com TestClient e dependency override/fake:
   - sem Bearer => 401;
   - admin => 403;
   - operator válido => 200;
   - `service_context` no payload => 422;
   - `company_id`, `model`, `base_url`, `can_send` => 422;
   - saída mantém `can_send=false`, `simulation_only=true`;
   - event_id preservado;
   - prompt injection => revisão/sem envio;
   - candidato financeiro perigoso é sanitizado pelo guard;
   - provider indisponível => decisão segura, não 500;
   - default static não abre rede;
   - modo ollama em teste usa somente MockTransport/dependency fake,
     nunca socket real;
   - configuração Ollama não-loopback => 503 sanitizado;
   - nenhuma escrita SQL/DB é necessária para a rota.

## Regras arquiteturais

- `service_context` é **trusted server configuration**, nunca conteúdo
  do cliente.
- Request não pode escolher modelo/provider/URL.
- Conteúdo recebido continua dado não confiável.
- IA só produz candidato; autorização continua fora do modelo.
- Sem preço/prazo/ROI/garantia automáticos.
- Não introduzir webhook público, CORS, API key nova, JWT, HMAC ou
  autenticação paralela neste WP.
- Não implementar rate limiting, dedupe persistente ou fila ainda;
  registrar como pré-condições do workflow n8n futuro.
- Não alterar rotas existentes de conversations/opportunities.
- Não ler `.env` real ou banco real nos testes.
- Não iniciar Ollama, n8n, Docker ou Oracle.

## Validação

Branch:
`wp/037-private-intake-endpoint`

Executar:
```bash
uv run pytest -q tests/test_commercial_intake_endpoint.py
uv run pytest -q
uv run python -m compileall -q app tests
git diff --check
```

Fazer commit/push e abrir PR. **Não fazer merge.**

Relatório: PASS/FAIL, branch, SHA, PR, contagem real de testes e limitações.
STOP após WP-037.

## Próximo passo — fora deste WP

WP-038 deverá preparar um workflow n8n **desativado por padrão**, com
entrada autenticada interna, deduplicação persistente, limite de frequência
e fila/revisão antes de qualquer canal externo. Nenhuma mensagem real será
enviada sem gate específico.
