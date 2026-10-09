# WP-023 — O08: preparo de prova social, sem publicação

**Fase:** F2; sexto gate do checklist pré-contato.
**Base:** `main@bc8db51b1b0811c04c9129ffe8b3df94775fbb03`.
**Branch:** `wp/023-proof-social-readiness`.
**Propriedade:** desenvolvimento no GitHub; Continue/Qwen 3.5 9B faz **somente
validação local sintética**, quando solicitado.
**Status:** pendente de validação. Este WP não cria um case real.

## Contrato mínimo

O Client 0 já possui modelo de serviço G0–G10, demonstração técnica
**sintética**, site **não publicado** e assistente de rascunhos LinkedIn.
Falta definir o que é uma **evidência de resultado comercial publicável**
e como impedir que simulação/depoimento não autorizado vire case.

**Entregas limitadas:**

- `docs/operations/templates/client0-proof-social.template.json`:
  metadados privados por case, com **permissões negadas por padrão**.
- `docs/operations/client0-proof-social.md`: metodologia antes/depois,
  escopo de consentimento e revisão editorial.
- `proof_social/checklist.py`: verificador **somente de leitura**,
  sem rede/banco, com relatório de bloqueios sanitizado.
- `proof_social/__init__.py` e `tests/test_proof_social_checklist.py`:
  testes exclusivamente sintéticos.
- Atualizar o status do gate O08 no roadmap/readiness, **sem** marcar
  F2 como concluída.

**Não alterar:** `app/`, PostgreSQL real, Alembic, Docker, API privada,
site, `marketing/`, serviço do Qwen, credenciais, sistema financeiro,
arquivos privados do cliente ou qualquer publicação.

## Decisões irrevogáveis deste recorte

- Case real e fonte externa **não** podem ser inferidos de dados
  recuperados, de `company_id`, de hashes ou de flags no JSON.
- Métricas têm valor **observado** antes/depois, duas fontes, períodos,
  método, revisão de comparabilidade e limites documentados.
- Consentimentos são **separados** por uso, canal e SHA-256 da versão
  sanitizada: `metrics`, `identity`, `logo`, `testimonial` ou `image`.
- Revogação, expiração, desconhecido, outra versão ou canal bloqueiam.
- Mesmo que o checker retorne `human_review_required`, ele **sempre**
  devolve `publication_authorized=false` e nunca publica.
- `--template-check` avalia exclusivamente o modelo público e
  **deve retornar `status=blocked`**; exit 0 significa somente que
  o teste do template foi executado, não que publicação foi liberada.
- Arquivo real, quando algum dia existir, fica em
  `~/.local/share/business-automation/client0/cases/<case_ref>/proof-social.json`
  (diretórios 0700, arquivo 0600, fora do Git), mas este WP **não**
  autoriza criá-lo ou preenchê-lo com dados reais.

## Aceite sintético

1. Modelo público continua sem consentimentos, métricas confirmadas
   ou permissão de publicação.
2. Testes mostram `blocked` quando faltam aceites, medições, fontes,
   revisão de privacidade, escopo de uso/canal, prazo ou grant.
3. Valores não numéricos, períodos sobrepostos/futuros, estimativas,
   referências duplicadas, chaves JSON duplicadas e caminhos/symlinks/
   permissões inseguros são rejeitados.
4. Mesmo o exemplo **fictício** com todos os metadados simulados retorna
   `human_review_required` e `publication_authorized=false`.
5. Nenhum arquivo real de clientes, segredo ou mensagem é lido,
   alterado, publicado ou incluído no repositório.
6. Suíte normal e compilação passam em um clone descartável; sem
   servidor local, modelo, Docker, DB, login ou token.

## Handoff único para Continue/Qwen 3.5 9B (somente testes)

**Uma execução; não implementar, refatorar, commitar ou publicar.**

```bash
set -euo pipefail
tmp="$(mktemp -d /tmp/ba-wp023-qwen.XXXXXX)"
git clone --quiet --single-branch --branch wp/023-proof-social-readiness \
  https://github.com/fenatodev/business-automation.git "$tmp/repo"
cd "$tmp/repo"
test ! -e .env
git fetch --quiet origin main:refs/remotes/origin/main
git diff --check origin/main...HEAD
uv run pytest -q
.venv/bin/python -m compileall -q app tests examples marketing proof_social
uv run python -m proof_social.checklist --template-check
test -z "$(git status --porcelain)"
printf 'WP023_LOCAL=PASS\n'
```

Revisar no JSON final: `status=blocked`,
`publication_authorized=false`,
`external_action_taken=false`.

**STOP obrigatório:** primeiro comando com exit code diferente de zero
interrompe o bloco; ler a causa, tentar **no máximo uma correção
justificada e diferente**; sem segundo sucesso, relatar FAIL.
Nunca repetir comando que falhou, nem usar `git stash`, `reset`,
`restore`, `clean`, `rm` ou checkout de usuário. Não acessar dados
reais ou arquivos `~/.local/share/business-automation/client0/cases/`.
Não fazer merge/push, não executar o próximo WP.

**Resposta obrigatória, curta:**

```text
WP023_LOCAL=PASS|FAIL
head=<sha>
pytest=<contagem real ou erro>
diff_check=PASS|FAIL|NOT_RUN
compileall=PASS|FAIL|NOT_RUN
template_check=blocked, publication_authorized=false | FAIL
bloqueio=<nenhum | primeiro comando, erro e exit code>
```

Após `PASS`: ChatGPT revisa a PR no GitHub e faz merge normal.
Próximo WP, **em outra sessão:** ensaio de prontidão F2 com dados
inteiramente sintéticos, sem encerrar F2 nem retomar prospecção.
