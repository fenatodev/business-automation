# WP-022 — Qwen local produz rascunho de LinkedIn, sem publicar

**Status:** desenvolvimento GitHub-first; revisão e validação obrigatórias.
**Base:** `main@c4295734a71b7fd7285c030475e7077e017a3099`.
**Branch:** `wp/022-marketing-draft-assistant`.
**Fase:** F2, quinto gate da matriz pré-contato, depois do site WP-021.

## Único resultado deste WP

Gerar e revisar estruturalmente **um rascunho** de post em pt-BR usando
somente uma fonte pública curada sobre `examples/order_to_crm.py`.
A saída sempre é `pending_review`, nunca `approved`/`published`.
Opcionalmente salvar uma cópia em pasta privada fora do Git.

### Contrato completo para um Qwen 3.5 9B

- Entrada: **`marketing/approved_sources.json`**, única entrada
  `synthetic-order-crm`, classe `public_synthetic`; fatos `demo_offline`,
  `demo_safety`, `demo_tests`, `demo_limit` e URL pública canônica.
  Nenhum acesso a `.env`, banco, 99Freelas, prompt privado ou scraper.
- Modelo de geração: **Qwen 3.5 9B local**, OpenAI-compatible
  `http://127.0.0.1:1251/v1/chat/completions`, alias `qwen3.5-9b`;
  1 chamada por comando com JSON e timeout. Não usar modelo de cloud
  como fallback nem retentar cegamente.
- Saída de IA: JSON estrito `{"post": "…", "used_fact_ids": ["demo_offline", "demo_limit"]}`.
  Validação verifica formato, IDs autorizados, ausência de alguns sinais
  óbvios de exagero e URLs. **A revisão factual completa é humana**.
- Saída do assistente: JSON marcado `pending_review`, `approved=false`,
  `published=false`, canal `linkedin`, URL/IDs da fonte, checklist.
- Opção de salvar: somente em
  `~/.local/share/business-automation/client0/marketing-drafts/`
  (diretório `0700`, arquivo novo `0600`, sem sobrescrever).
- Falha: `WP022_DRAFT=FAIL`, sem retry, sem arquivo parcial de rascunho
  se modelo falha e sem interação com redes.
- Prioridade: implementação e revisão no GitHub; testes somente em clone
  descartável. **Continue não implementa**, não refatora, não cria WP
  seguinte e não toca o checkout com trabalho de outros agentes.

## Arquivos permitidos

Criar apenas:
`marketing/__init__.py`, `marketing/approved_sources.json`,
`marketing/draft.py`, `tests/test_marketing_draft.py`,
`docs/operations/client0-marketing-drafts.md`, este documento.

Atualizar somente `docs/operations/precontact-readiness.md` e, se
necessário, o link do `docs/ROADMAP.md`. Não alterar `app/`, schema,
migrations, `docker-compose.yml`, auth, chaves, sites, provider atual
do core, banco real ou comportamento operacional.

## Critérios de aceite

1. `uv run python -m marketing.draft --preview` não chama modelo e mostra
   somente fatos públicos curados.
2. Um `httpx.MockTransport` confirma **uma** chamada ao endpoint
   loopback, JSON e saída com revisão obrigatória.
3. Endpoints remotos, redirecionamento externo, falha HTTP/timeout,
   retorno inválido, IDs falsos e afirmações comercialmente suspeitas
   falham sem retry/publicação.
4. `--save-private` só grava quando `--generate` foi solicitado,
   com permissões verificáveis e `O_EXCL`; symlinks/permissões
   inadequadas impedem escrita.
5. Testes não usam redes, oportunidades reais, token, providers, Docker
   ou PostgreSQL. Nenhuma publicação ou postagem sai do WP.

## Testar em clone isolado — sem dar tarefas de arquitetura ao Qwen

```bash
set -euo pipefail
tmp="$(mktemp -d /tmp/ba-wp022-check.XXXXXX)"
git clone --quiet --single-branch --branch wp/022-marketing-draft-assistant \
  https://github.com/fenatodev/business-automation.git "$tmp/repo"
cd "$tmp/repo"
test ! -e .env
git fetch --quiet origin main:refs/remotes/origin/main
git diff --check origin/main...HEAD
uv run pytest -q
.venv/bin/python -m compileall -q app tests examples marketing
uv run python -m marketing.draft --preview >/dev/null
test -z "$(git status --porcelain)"
printf 'WP022_LOCAL=PASS\n'
```

**STOP obrigatório:** nenhuma repetição de comando idêntico que falhou;
no máximo **uma** tentativa corrigida com causa explicada, depois
`WP022_LOCAL=FAIL` com exit code real. Não executar `git restore`,
`stash`, `clean`, `reset`, `rm` em checkout de usuário. Nunca
ler `.env`, reiniciar a API, acessar PostgreSQL, criar commits/push
no lugar do ChatGPT ou enviar post ao LinkedIn.

**Gate após PASS:** revisão GitHub e merge do PR de código; posterior
smoke **único** opcional com o modelo local pode gerar rascunho
de demonstração público, mas não publica. WP seguinte só em outra etapa:
**O08 prova social com consentimento e métricas**.
