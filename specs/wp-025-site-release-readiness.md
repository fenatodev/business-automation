# WP-025 — Site institucional: pacote seguro para publicação futura (F2)

**Base:** `main@ca30f4b106fef2604bf9f7b9fecab353abaab031`  
**Branch:** `wp/025-site-release-readiness`  
**Execução:** ChatGPT/GitHub + CI; Continue/Qwen 3.5 9B somente se CI indisponível.  
**Aprovação para publicar:** **NÃO CONCEDIDA**.

## Objetivo único

Produzir **um pacote estático auditável** para a vitrine do WP-021,
contendo somente os arquivos públicos necessários, configurado para
Cloudflare Pages **Direct Upload** após autorização futura. Validar via
GitHub Actions sem ligar Desktop Commander ou acessar a máquina do usuário.

## Arquivos autorizados

- `site/_headers`: cabeçalhos declarativos Cloudflare Pages para assets estáticos.
- `site_release/__init__.py` e `site_release/prepare.py`: empacotador
  stdlib, saída apenas para diretório temporário explícito, sem deploy.
- `tests/test_site_release.py`: allowlist, symlinks, integridade, conteúdo,
  política de headers e repetibilidade usando `tmp_path`.
- `.github/workflows/validation.yml`: testar empacotamento em CI; no
  `push main`, anexar um artifact de GitHub Actions por 7 dias;
  **não** usar `deploy-pages`, `wrangler`, SSH ou secrets.
- `docs/operations/site-publication-readiness.md`: decisão de hosting,
  pré-lançamento e separação do site público da API privada.
- `site/README.md`, `docs/ROADMAP.md`,
  `docs/operations/precontact-readiness.md`: links/status.
- Este documento.

**Não tocar:** `app/`, DB, auth, migrations, Docker, ERPNext,
serviços do host, Qwen, DNS, GitHub Pages, Cloudflare account, redes
sociais, API 8788, conteúdo de cases privados ou código de negócios.

## Regras de segurança do empacotamento

- Fonte fixa: `site/`, somente `index.html`, `styles.css`,
  `favicon.svg`, `_headers`; `README.md` fica só no Git,
  **não** é publicado. Qualquer asset adicional inesperado => FAIL.
- Sem symlinks e sem arquivos/diretórios especiais; cada nome permitido
  é arquivo regular, com tamanho limitado, em UTF-8 quando textual.
- Rejeitar `script`, `form`, `iframe`, origem externa automática,
  URLs de API, domínio/IP interno, tracking e acessos a dados privados.
  Links externos de navegação manual permanecem GitHub/LinkedIn já validados.
- Não fabricar `CNAME`, `sitemap.xml`, `canonical`, domínio, política
  de rastreamento ou formulário antes da decisão efetiva.
- Cabeçalhos: CSP, `frame-ancestors 'none'`, `nosniff`,
  `Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy`.
  O `_headers` **funciona somente em hosting que o processe**
  (Cloudflare Pages, não no servidor Python local nem automaticamente no GitHub Pages).
- Produzir JSON com SHA-256, bytes e nomes **sem** imprimir conteúdo da
  página, credenciais ou paths arbitrários. Arquivos fora da allowlist
  **jamais** vão ao artifact.
- Recusar output existente/não vazio/symlink e output dentro do checkout;
  não sobrescrever/delétar destino. Sem uploads pela ferramenta Python.
- O GitHub Action mantém `permissions: contents: read`; não recebe
  permissão `pages: write` nem `id-token: write`.
- Passar em CI é **pronto para revisão**, não pronto para lançar;
  `publication_authorized=false` permanece até aprovação explícita.

## Critérios de aceite

1. `uv run pytest -q` com quantidade **real** de testes.
2. `compileall`, JS e `git diff --check`: PASS.
3. `uv run python -m site_release.prepare --output "$RUNNER_TEMP/ba-site-preview"`
   cria **exatamente 4 assets** e hashes conferíveis.
4. Testes negativos: asset secreto/inusitado, symlink, HTML com script
   ou fonte remota, output inseguro/não vazio, headers ausentes.
5. CI não executa publicação/deploy; no `main` salva artifact de
   release com retenção curta (se configuração de artifact disponível).
6. Nenhuma etapa de aprovação para divulgar identidade, domínio,
   dados ou custos é inferida.
7. Não rodar Continue local se CI confirmar tudo.

## Contrato de encerramento

`WP025_REMOTE=PASS|FAIL`, `pr`, `head`, `tests`,
`site_assets=4`, `artifact`, `deploy=false`, `bloqueios`.
Depois do merge, checar CI no `main` e artifact sem fazer upload a
Cloudflare.

**Gates humanos restantes:** revisão da marca/copy, contato, destino
Cloudflare Pages, termos de privacidade compatíveis com o provedor,
domínio/HTTPS, abertura pública, backup do back-office e dados comerciais.
