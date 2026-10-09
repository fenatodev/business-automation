# WP-021 — site-vitrine estático e seguro do Client 0

**Fase:** F2 — preparo pré-contato, depois do WP-020.  
**Base:** `main@c231e1fdb49a28c83818631c1eaf383cd4fc108b`.  
**Branch:** `wp/021-institutional-static-site`.  
**Executor de desenvolvimento:** ChatGPT via GitHub.  
**Continue/Qwen 3.5 9B:** **não implementa** este WP; usar apenas se
for indispensável um teste local já delimitado. O responsável aprova
separadamente qualquer publicação/hospedagem.

## Entrega e por que ela existe

Criar a primeira vitrine institucional **estática** FenatoDev que demonstre
prontidão técnica sem afirmar resultados comerciais inexistentes. A página
explica serviço realista, método, código executável e perfil público.
Não antecipar IA de marketing, prova social, CRM público ou ERP.

A fonte para serviços é `docs/operations/client0-offer-v1.md`;
o portfólio técnico verificável é `examples/README.md`
e os repositórios públicos `fenatodev/ai-coding-evaluation`
e `fenatodev/lai-harness`.

## Escopo fechado

**Adicionar:** `site/index.html`, `site/styles.css`,
`site/favicon.svg`, `site/README.md`, `tests/test_site_static.py`.  
**Atualizar:** `docs/operations/precontact-readiness.md` com status
de site codificado, revisão/publicação **ainda pendentes**.
**Não tocar:** `app/`, `migrations/`, `docker-compose.yml`,
`pyproject.toml`, credenciais, repositórios externos, Postgres, API
privada, processos operacionais, cliente real ou outras fases.

## Contratos explícitos

- Conteúdo em **pt-BR**, nome de trabalho **FenatoDev**.
- Primeiro serviço: diagnóstico e implantação de **um fluxo** de
  automação/integração, com critérios de aceite; suporte separado
  conforme o contrato. Preço e prazo **não definidos**.
- Demonstração `pedido → CRM fake`: **offline, sintética e em memória**,
  com controles de duplicação, conflito e timeout. Não atribuir a cliente.
- A identidade e contato usam perfis públicos já existentes; links
  clicáveis manualmente, **sem enviar mensagem automaticamente**.
- Não publicar métricas inventadas, clientes, marcas alheias, resultados,
  cases, depoimentos ou tempo de experiência não comprovado no contexto.
- Sem JS, tracking, coleta, formulário, backend, SQL, imagem remota,
  CDN ou fontes remotas; CSP via `meta` para recursos da página.
- `site/` autocontido e separado; HTML sem caminho/porta da API privada
  ou dados reais. Página funciona em caminho relativo.
- Layout responsivo, foco de teclado visível, link para pular ao
  conteúdo, contraste legível e respeito a `prefers-reduced-motion`.
- **Nenhuma publicação de fato:** arquivos em GitHub público não implicam
  domínio/hosting disponível. Deploy externo requer outro gate.

## Pré-condições e aceite observável

1. `AGENTS.md` vigente existe e demanda isolamento GitHub/local e STOP
   por repetição. Nenhum Continue precisa ler a baseline inteira.
2. `examples/order_to_crm.py`, `examples/README.md` e a oferta v1
   existem no commit-base.
3. `uv run pytest -q` passa com os testes anteriores mais os novos
   testes estáticos; contagem **real** no resultado. Sem DB real.
4. `.venv/bin/python -m compileall -q app tests examples` passa;
   `git diff --check origin/main...HEAD` passa.
5. Navegação interna leva a IDs existentes; links externos seguem somente
   HTTPS com `rel=noopener noreferrer`; recursos usam paths locais.
6. Prévia em Chrome local com resoluções 1440x900, 768x1024 e
   390x844: sem overflow horizontal, console sem erros, CSS/favicon
   carregando, links internos funcionais e site sem requisições de
   provedores terceiros.
7. Revisão humana de copy/branding e hosting **não** está compreendida
   no aceite técnico; portanto não declarar site publicado.

## Recorte local mínimo — anti-loop

Se for necessário usar **Continue/Qwen** para testar no Ubuntu,
enviar somente uma sequência fechada e não delegar design/implementação:

```bash
set -euo pipefail
tmp="$(mktemp -d /tmp/ba-wp021-qwen.XXXXXX)"
git clone --quiet --single-branch --branch wp/021-institutional-static-site \
  https://github.com/fenatodev/business-automation.git "$tmp/repo"
cd "$tmp/repo"
test ! -e .env
uv run pytest -q
.venv/bin/python -m compileall -q app tests examples
git diff --check
printf 'WP021_LOCAL=PASS\n'
```

No último comando, `git diff --check` **sem ref** só verifica mudanças
não commitadas; para conferir o PR, usar `git fetch origin main`
e `git diff --check origin/main...HEAD`. Não repetir comandos cegamente.
No máximo **uma tentativa corrigida** quando falhar; em novo erro:
`WP021_LOCAL=FAIL` + primeiro comando, exit code e stderr resumidos.
Nunca atuar em checkout de usuário, executar `git stash`, `restore`,
`clean`, `rm`, editar artefatos, rodar serviço real, publicar,
commitar, fazer push ou avançar automaticamente ao WP seguinte.

## Encerramento

Entregar `PR`, commit, lista restrita de arquivos, contagem real de
testes, resultado de browser, limites e gates ainda pendentes. Nenhuma
solicitação de aprovação para tarefas ordinárias de GitHub/teste.
Aprovação de **publicação, domínio, hospedagem ou custo** continua
separada. O F2 termina somente com ciclo comercial real rastreável.
