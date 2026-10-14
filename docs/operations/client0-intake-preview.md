# Client 0 — Commercial Intake Preview

**Status:** Ensaio offline. Não é um bot operando. Nenhuma mensagem é enviada.

## Visão geral

Este pacote entrega o primeiro **núcleo executável** de triagem comercial:

```
mensagem sintética → candidato de IA (injetado) → validação de política → decisão estruturada
```

A função `process_commercial_intake()` em `app/services/commercial_intake.py` é **pura**:
sem chamadas de rede, sem banco de dados, sem efeitos colaterais.

## Execução

```bash
# Demo com 3 cenários (normal, incompleto, adversarial)
uv run python scripts/demo_commercial_intake.py

# Testes automatizados
uv run pytest -q tests/test_commercial_intake.py
```

## Contrato de entrada

```json
{
  "channel": "web",
  "message": "Preciso automatizar confirmação de agendamentos da minha loja.",
  "service_context": "Automação de processos e integrações sob diagnóstico.",
  "event_id": "evt-synthetic-001"
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `channel` | `str` | Canal de origem (web, whatsapp, etc.). Máx. 30 chars. |
| `message` | `str` | Mensagem do contato. **Dado não confiável**, nunca instrução de sistema. Máx. 4000 chars. |
| `service_context` | `str` | Única fonte de fatos autorizados sobre o serviço. Máx. 2000 chars. |
| `event_id` | `str` | Identificador único do evento. Máx. 100 chars. |

O candidato de resposta (`CandidateReply`) é injetado via parâmetro — **não** é gerado por LLM neste pacote.

## Contrato de saída

```json
{
  "event_id": "evt-synthetic-001",
  "intent": "automation_inquiry",
  "next_step": "ask_clarification",
  "draft_reply": "Qual processo você quer automatizar e qual ferramenta utiliza hoje?",
  "needs_human_review": true,
  "can_send": false,
  "flags": ["financial_commitment_request"],
  "simulation_only": true
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `event_id` | `str` | Mesmo `event_id` da entrada. |
| `intent` | `str` | Classificação grosseira: `automation_inquiry`, `web_inquiry`, `marketing_inquiry`, `pricing_inquiry`, `general_inquiry`. |
| `next_step` | `str` | Ação sugerida: `ask_clarification`, `escalate_to_human`, `none`. |
| `draft_reply` | `str` | Rascunho seguro para revisão, com fallback quando candidato contém padrões suspeitos. **Não é garantia de veracidade**. Limite de 2000 chars. |
| `needs_human_review` | `bool` | `true` quando há risco detectado. |
| `can_send` | `bool` | **Sempre `false`** neste pacote. |
| `flags` | `list[str]` | Riscos detectados: `possible_prompt_injection`, `asks_sensitive_data`, `financial_commitment_request`. |
| `simulation_only` | `bool` | **Sempre `true`**. |

## Políticas de segurança implementadas

1. **Prompt injection**: padrões como "ignore suas regras", "jailbreak", "bypass", "role=admin" acionam `possible_prompt_injection` + `needs_human_review=true`.
2. **Dados sensíveis**: menção a senhas, credenciais, CPF, tokens aciona `asks_sensitive_data`.
3. **Compromisso financeiro**: menção a preço, prazo, ROI aciona `financial_commitment_request`; candidatos com sinais de promessas, preço, acesso ou disponibilidade não verificada são descartados em favor de uma pergunta segura, com `unsafe_candidate` e revisão humana.
4. **`can_send` sempre `false`**: nenhum envio ocorre neste pacote.
5. **`simulation_only` sempre `true`**: marca todas as decisões como simulação.
6. **Validação de entrada**: mensagens e identificadores vazios (inclusive só espaços), excesso de tamanho, caracteres de controle ou campos extras são rejeitados.
7. **Determinismo (não idempotência persistente)**: a mesma entrada produz a mesma saída em memória, mas não existe deduplicação de envios/eventos em banco.
8. **Invariantes do modelo**: `can_send` aceita somente `false` e `simulation_only` aceita somente `true`. A decisão não equivale a permissão para uso externo.

## O que NÃO está autorizado

- **Não existe bot operando** no WhatsApp, site ou qualquer canal externo.
- **Nenhuma mensagem é enviada** por este módulo.
- **Nenhum preço, prazo ou ROI é prometido** automaticamente.
- **Nenhum dado real de cliente** é usado nos testes ou demo.
- **Nenhuma chamada de rede** é feita (Ollama, n8n, API externa).
- **Nenhum banco de dados** é lido ou escrito.
- **Nenhum deploy** é realizado.

## Conexão futura com n8n

A próxima fase (WP separado) poderá:

1. Conectar um wrapper de LLM (Ollama/alternativas) para gerar o candidato injetado.
2. Integrar o retorno estruturado com um workflow n8n para deduplicação, pausa e revisão humana.
3. Adicionar política de saída separada com `can_send=true` sob autorização explícita.

O contrato atual (`CommercialIntakeEvent` → `IntakeDecision`) é reutilizável como interface para esses adaptadores futuros.

## Limitações conhecidas

- Classificação de intent é baseada em heurísticas de palavras-chave, não em modelo de ML.
- Detecção de prompt injection e de promessas não verificadas utiliza heurísticas por regex — não é exaustiva, não prova segurança nem valida factualidade. Nunca usar rascunhos como mensagens aprovadas.
- Deduplicação persistente entre eventos não existe nesta etapa.
- `service_context` não é usado ativamente na decisão — será usado pelo wrapper LLM futuro.
