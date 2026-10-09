# WP-026 — Portable static release; hardware deferred

**Base:** `main@6ecc762239b11e8ae8908cdcb44b049d2a4344bd`.  
**Branch:** `wp/026-portable-static-site`.  
**Fase:** F2 / complementa WP-025 sem lançar site.  
**Executor:** GitHub + Actions; **não ligar DC nem acionar Continue**.
**MXQ4K:** reservado para verificação em etapa futura, sem flash/configuração.

## Recorte único

Adicionar `portable-static` ao empacotador existente,
preservando `cloudflare-pages` como default. Os dois targets
leem exatamente a mesma source `site/` sob auditoria de
conteúdo, symlink, links externos, CSP e privacidade.

- `cloudflare-pages`: pacote atual com **4** assets, incluindo
  `_headers` processado somente pela Cloudflare Pages.
- `portable-static`: pacote novo com **3** assets — `index.html`,
  `styles.css`, `favicon.svg`; **excluir `_headers`**.
- Ambos: `publication_authorized=false`, `deploy_performed=false`,
  `api_exposed=false`, `http_headers_verified=false`,
  `hosting_selected_by_operator=false`.
- Nunca embutir webserver, rede, segredo, cliente, API privada,
  cert/TLS, SoC presumido, imagem Android/Linux, flash ou shell
  para provisionar host.
- No `main`: reter pacote portátil como artifact GitHub de 7 dias,
  tal como WP-025; **nenhum deployment**.

## Arquivos permitidos

- `site_release/prepare.py`: parâmetro `--target`;
- `tests/test_site_portable.py`: testes offline de ambos os targets,
  allowlists, hashes, defaults, sem output externo;
- `.github/workflows/validation.yml`: validação de ambos e upload
  de artifact portátil apenas no main;
- `docs/operations/mxq4k-hosting-deferred.md`: hardware
  desconhecido, inventário read-only futuro e gates;
- `docs/operations/site-publication-readiness.md`,
  `site/README.md`, `docs/operations/precontact-readiness.md`
  e `docs/ROADMAP.md`: escopo do host neutro e pendências;
- Esta spec.

Não tocar `app/`, migrations, PostgreSQL, ERP, o provedor
de marketing, drivers, firmware, contas, rede nem arquivos locais.

## Critério de aceite

1. `uv run pytest -q` no GitHub Actions, contagem real.
2. `compileall`, JS, `git diff --check`, prova social e
   simulador de F2 em PASS.
3. Release Cloudflare padrão mantém **4 arquivos**; portátil gera
   **exatamente 3** e nenhum `_headers`, README ou `.env`.
4. Artifacts são somente arquivos estáticos com hash, sem tokens,
   upload externo ou autorização de publicação.
5. Nenhuma ação na MXQ4K ou na máquina do usuário.
6. CI verde no SHA do PR antes de merge, e CI verde no merge main
   confirmando artifact; sem rodar Continue para duplicar testes.

**Anti-loop:** erro de CI => localizar primeira falha, fazer no
máximo uma correção dirigida e testar novamente; depois STOP.
Não transformar isso em instalação de Linux no box.

**Próximo bloqueio real do roadmap:** prontidão operacional F2/O02
(back-office, índice privado, backup/restore), separado do
futuro WP de hospedagem após o usuário autorizar.
