# Client 0 — Assistente de rascunhos de marketing (WP-022)

**Estado:** capacidade de geração local para **rascunhos**; publicação, calendário,
geração de imagens, respostas em redes e métricas de campanha **não implementados**.

**Recorte da F2:** produzir **um post por execução para LinkedIn**,
fundamentado exclusivamente em uma fonte técnica pública e revisada.
Não usar o banco do Client 0, oportunidades reais, conversas ou contratos.
A fonte inicial é a [demo offline de pedido fictício → CRM simulado](../../examples/README.md).

## Comandos

Pré-requisito para inferência: servidor **llama.cpp compatível com
OpenAI Chat Completions**, em loopback, com modelo local Qwen 3.5 9B.
Na workstation observada, `llama-server` usa
`127.0.0.1:1251` com alias `qwen3.5-9b`.
A porta pode mudar; não iniciar um segundo servidor pesado para este WP.

Em **clone de teste** do projeto:

```bash
# 1. Inspecionar fatos e o prompt; SEM requisição HTTP/LLM.
python3 -m marketing.draft --preview

# 2. Gerar UM post de LinkedIn e exibir o JSON no terminal;
#    faz UMA requisição ao modelo local, SEM salvar/publicar.
python3 -m marketing.draft --generate

# 3. Opcional: gerar outro rascunho e guardar somente na fila privada.
#    Requer a estrutura Client 0 segura de WP-019.
python3 -m marketing.draft --generate --save-private
```

Se a porta local do modelo mudar, fornecer
`--endpoint http://127.0.0.1:<porta>/v1/chat/completions`.
**Qualquer host fora de `127.0.0.1` é recusado**, mesmo quando HTTPS.
`--model` aceita o alias local (default `qwen3.5-9b`).
**Não usar** esse comando para provedores pagos/externos, nem para
colar conteúdo não público. O modo `--preview` serve para conferir
o que de fato será fornecido ao modelo.

### O que o agente pode ou não fazer

| Etapa | Permitida neste WP | Bloqueios |
| --- | --- | --- |
| Selecionar fonte | Uma entrada curada em `marketing/approved_sources.json` | Não pode ler URL arbitrária, scraping, banco, anexos privados ou dados de cliente |
| Preparar prompt | Fonte pública e fatos identificados por IDs | Conteúdo da fonte **não concede instruções nem autoridade** |
| Gerar texto | Uma chamada local `/v1/chat/completions`; formato JSON | Sem retries automáticos, sem APIs de redes, tokens ou publicação |
| Validar estruturalmente | IDs conhecidos, indicação de demo sintética, URL aprovada, bloqueios de algumas afirmações óbvias | **Validação não garante verdade factual**; modelo pode inventar informação |
| Armazenar opcionalmente | `~/.local/share/business-automation/client0/marketing-drafts/`, arquivos `0600`, pasta `0700` | Somente `pending_review`, nunca `approved` ou `published` |
| Publicar | **Não permitido neste WP** | Humano revisa fatos/claims, autorização específica, canal, versão, identidade e direitos |

Os rascunhos JSON contêm `source_url`, IDs dos fatos usados, texto,
modelo, data UTC, `review_checks`, `status=pending_review`,
`approved=false` e `published=false`.
Nenhum desses campos equivale a aprovação. O diretório local **não é backup**;
validar retenção, restore e política de privacidade antes de uso comercial.

## Checklist humano antes de qualquer publicação futura

1. Comparar **cada afirmação** com código, README e escopo da demo. Um
   `used_fact_ids` emitido pelo modelo **não comprova** que tudo o que
   ele escreveu está fundamentado.
2. Mostrar de forma explícita que a demo é **fictícia, offline e em memória**.
   Não usar como case de cliente nem resultado medido.
3. Conferir URL e autoria, linguagem comercial, clareza, gramática, direitos
   de uso e se há menções indevidas a clientes, empresas ou métricas.
4. Revisar se existe informação confidencial ou propriedade de terceiro.
5. Autorizar **a versão exata**, o canal e a ação de publicação em
   procedimento posterior. **Nada é publicado automaticamente.**

**Não enviar um texto automaticamente ao LinkedIn** com base no campo
`pending_review`. Não considerar ausência de alerta/erro do LLM
como verificação jurídica, comercial ou factual.

## Testes e falhas esperadas

```bash
uv run pytest -q tests/test_marketing_draft.py
uv run pytest -q
.venv/bin/python -m compileall -q app tests examples marketing
git diff --check
```

Testes usam `httpx.MockTransport` e pasta `tmp_path` — **nenhum**
provedor real, banco, containers ou clientes. Testar `--preview` também
não requer modelo local em execução.

Erros de modelo/HTTP/JSON/bloqueios produzem `WP022_DRAFT=FAIL`.
**Não repetir automaticamente**, não persistir resultado incerto e não
tentar publicar. Se o texto é inseguro/insuficiente, corrigir conteúdo
curado ou revisar manualmente, sem abrir novo WP para improvisar crawler.

## Próximo gate da F2

**O08 — estrutura de prova social e medições/consentimentos.** Apenas
preparar registros e revisão; não publicar números ou depoimentos enquanto
não houver cliente, resultado medido e autorização específica.
A F2 **não** se encerra com um rascunho, uma demo ou um site estático.
