# WP-025 — Prontidão de publicação do site FenatoDev (sem deploy)

**Status:** pacote estático candidato à revisão, preparado no
GitHub Actions. **Não há site publicado, domínio contratado, conta de
hospedagem configurada ou autorização de lançamento.**
**WP-026:** por decisão do responsável, a hospedagem futura poderá ser
um [TV Box MXQ4K ainda não avaliado](mxq4k-hosting-deferred.md).
A opção gerenciada Cloudflare fica como **fallback**, não obrigação.

## 1. Escolha técnica inicial: Cloudflare Pages Direct Upload

O site [WP-021](../../site/README.md) usa somente HTML, CSS e SVG.
**Não precisa de banco, API, Node.js, build frontend, formulário ou
infraestrutura própria.** Hospedar a aplicação FastAPI `127.0.0.1:8788`
junto com a vitrine seria um erro de arquitetura e segurança.

| Alternativa | Adequação | Ressalva |
| --- | --- | --- |
| **Cloudflare Pages — Direct Upload** | Preferida **para primeiro lançamento manual**, somente após aprovação. Suporta upload de pasta/ZIP de assets estáticos e arquivo `_headers` com CSP, `frame-ancestors` e políticas adicionais. Plano Free é opção para site pequeno. | Após criar projeto no modo Direct Upload, **não é possível convertê-lo em Git integration** no mesmo projeto. Deploy é público; não usar para prévia privada. Exige validar os termos/custos e a conta antes de escolher. |
| GitHub Pages — GitHub Actions | Alternativa sem backend, integrada ao repositório público; deploy controlado por workflow. | Exige configuração explícita de Pages e permissões de implantação. A configuração de headers HTTP não corresponde automaticamente ao arquivo Cloudflare `_headers`. Não habilitar neste WP. |
| VPS + servidor próprio | Controle avançado de HTTP e deploy. | Injustificável para quatro arquivos; amplia custo e manutenção. **Não recomendado**. |

**Decisão técnica do WP:** preparar somente um pacote **compatível com
Cloudflare Pages Direct Upload**; **não** selecionar formalmente a
hospedagem em nome do responsável, registrar domínio, aceitar termos ou
criar serviço. O responsável poderá preferir GitHub Pages posteriormente;
se escolher, deve haver revisão própria de headers e publicação.

Referências oficiais para a revisão de lançamento:
- [Cloudflare Pages: Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/).
- [Cloudflare Pages: cabeçalhos `_headers`](https://developers.cloudflare.com/pages/configuration/headers/).
- [Cloudflare Pages: limites atuais](https://developers.cloudflare.com/pages/platform/limits/).
- [GitHub Pages: fonte de publicação](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## 2. Release candidate: lista fechada de quatro arquivos

O empacotador [`site_release.prepare`](../../site_release/prepare.py)
lê somente a pasta `site/` e cria em **um diretório novo, externo ao
checkout**:

| Arquivo de saída | Finalidade |
| --- | --- |
| `index.html` | Página institucional, sem JS |
| `styles.css` | Estilo local e responsivo |
| `favicon.svg` | Ícone SVG local |
| `_headers` | Configuração de headers **somente para Cloudflare Pages** |

**Não acompanha:** `site/README.md`, `.env`, dados comerciais, documentos
de cliente, `app/`, SQL, migrations, modelos locais, prompts, testes,
tokens, `AGENTS.md`, API privada ou outros arquivos do repositório.

A auditoria falha diante de arquivo extra inesperado, symlink, asset
não regular, HTML ativo, dependência remota, script, formulário,
tracking, rota privada, links externos não previstos, política CSP
incompleta ou destino de saída já existente. Em caso de falha,
**não ignorar a validação nem publicar o diretório bruto**.

### Gerar candidato offline (fora do repositório)

O GitHub Actions executa automaticamente em PR e no `main`:

```bash
uv run python -m site_release.prepare --output "$RUNNER_TEMP/ba-site-candidate"
```

O output JSON mostra nomes, tamanhos, SHA-256 e flags:

```text
status=ready_for_human_review
site_asset_count=4
publication_authorized=false
deploy_performed=false
api_exposed=false
domain_configured=false
```

O SHA-256 detecta alteração de bytes; **não comprova autoria, autorização
de publicação, identidade de titular ou licença de terceiros**.

Depois de CI verde no `main`, o workflow **apenas salva um artefato**
`fenatodev-site-candidate-<sha>` no GitHub Actions por sete dias.
Isto **não** cria site, ativação do GitHub Pages, deploy Cloudflare,
DNS ou URL pública. O repositório Git já é público, mas isso é distinto
de servir os arquivos como site institucional.

### Variante portátil para um servidor estático futuro (WP-026)

Além do pacote de quatro arquivos específico para Cloudflare, há um
segundo target gerado pelo mesmo empacotador:

```bash
uv run python -m site_release.prepare \
  --target portable-static --output /tmp/site-portatil-novo
```

Ele contém **exatamente três arquivos**: `index.html`,
`styles.css` e `favicon.svg`; `_headers` é intencionalmente
excluído. O arquivo Cloudflare `_headers` **não ativa políticas
HTTP em servidores genéricos** e pode ser servido como arquivo comum.
O webserver efetivo deverá configurar e comprovar CSP e demais
headers separadamente, depois de uma escolha e autorização humanas.
O GitHub Actions guarda `fenatodev-portable-static-<sha>` por sete dias
no `main`; não há deploy nem servidor automaticamente configurado.

**MXQ4K permanece em espera.** Modelo/SoC real, flash, compatibilidade
Linux, alimentação, disponibilidade e exposição segura devem ser
avaliados em sessão futura; não criar firmware, configuração de
roteador ou serviço agora. Consultar
[restrições do hosting adiado](mxq4k-hosting-deferred.md).

## 3. Headers e privacidade: verificar resposta do hosting

O arquivo `site/_headers` declara:

- `Content-Security-Policy`: `default-src 'none'`, sem script,
  fonte/CDN remoto, `connect-src 'none'`, `form-action 'none'`,
  `frame-ancestors 'none'`; CSS e ícone apenas da própria origem.
- `X-Content-Type-Options: nosniff`.
- `Referrer-Policy: strict-origin-when-cross-origin`.
- `X-Frame-Options: DENY`.
- `Permissions-Policy`: câmera, microfone, geolocalização e pagamento
  desabilitados pela página.

A CSP via `meta` no HTML é **defesa adicional**, mas não suporta
`frame-ancestors`; o header real deve ser validado por HTTP depois
do deploy **aprovado**. `_headers` é configuração de Cloudflare
Pages; não funciona automaticamente com servidor Python local ou
GitHub Pages. A hospedagem pode ter registros operacionais, cookies
ou telemetria próprios. A ausência de cookies ou analytics **no código**
não promete ausência de tratamento de dados pelo provedor.

**Não habilitar** Web Analytics, pixels, formulários, rastreamento,
Cloudflare Functions, Workers, domínios ou integradores externos
sem outra decisão explícita, avaliação de privacidade e finalidade.

## 4. Aprovações indispensáveis, antes da primeira URL pública

| Gate | Evidência/decisão necessária | Estado |
| --- | --- | --- |
| Identidade e marca | Confirmar **FenatoDev**, uso comercial da marca e autor/titular do conteúdo | Pendente |
| Conteúdo | Revisar oferta, limite da demo fictícia, repositórios, links e textos | Pendente |
| Contato | Confirmar LinkedIn como canal comercial público e se deseja outro | Pendente |
| Direitos | Confirmar uso de imagens, fontes, logotipo, resultados e marcas; não há depoimentos de clientes | Pendente |
| Hospedagem | Escolher Cloudflare Pages, GitHub Pages ou outra; revisar conta, plano e termos | Pendente |
| Custos | Aprovar eventual compra de domínio/plano; **nenhuma compra realizada** | Pendente |
| Privacidade | Verificar dados do provedor, tratamento de logs e informação de rodapé | Pendente |
| Publicação | Autorizar **explicitamente** destino e versão SHA do pacote | **NÃO AUTORIZADA** |

**Domínio próprio não é requisito para um lançamento inicial tecnicamente
funcional** (o provedor pode disponibilizar subdomínio gratuito).
Não inventar agora `CNAME`, `canonical`, `og:url`,
`sitemap.xml` ou endereço de domínio. Defini-los somente quando
houver URL final aprovada. DNS/HTTPS/HSTS dependem do destino efetivo.

### Após autorização futura — procedimento manual sugerido

1. Baixar o artefato do workflow **verde do commit aprovado** no GitHub
   Actions; verificar que a pasta contém **somente os quatro arquivos**.
2. Após decisão expressa sobre provedor e conta, usar no painel do
   Cloudflare Pages a opção de Direct Upload (arrastar pasta/ZIP)
   para criar o site. **Esse passo publica na internet:** não fazer
   como teste sem autorização.
3. Conferir HTTPS, origem/caminho, headers HTTP efetivos, responsividade
   móvel, teclado, favicon, navegação e links externos. Não conectar a
   UI administrativa ou o PostgreSQL.
4. Somente depois de revisar URL definitiva e privacidade, atualizar
   SEO/canonical/sitemap em WP separado, se necessário.
5. Guardar o SHA do commit e asset release aprovado, responsável, data,
   destino e evidência de publicação; manter possibilidade de retirada.

## 5. Resultado e sequência da F2

**WP-025/026 preparam publicação portável, mas não a executam.** Conclusão por CI
não remove os bloqueios humanos da tabela acima nem fecha F2.
Continuam pendentes validação do back-office real, prova de restore do
índice privado e ciclo de oportunidade → recebimento com cliente real.

Próxima decisão: revisar identidade, canal e hospedagem com o
responsável **antes** de publicar. Não começar prospecção nem integrar
captura de leads como efeito deste documento.
