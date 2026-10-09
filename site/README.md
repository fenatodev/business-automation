# FenatoDev — site institucional estático (WP-021)

**Estado:** código de vitrine disponível para revisão local; **não publicado**.
Esta pasta é um **artefato público independente** do core Business Automation
e de seu PostgreSQL. O site não é um portal de clientes nem o operador `/operator`.

## Executar um preview privado

Em um clone de teste, com Python 3 instalado:

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
```

Abrir `http://127.0.0.1:8000/` **somente na máquina local**.
Encerrar com Ctrl+C. Este é um servidor estático temporário, não um deploy.

Arquivos publicados **separadamente**, caso haja aprovação:

- `index.html`: oferta, processo, referências públicas e contato por links.
- `styles.css`: layout responsivo, contraste, foco visível e redução de movimento.
- `favicon.svg`: ícone local.

Não há JavaScript, cookies definidos pelo código, fontes/CDNs externos,
formulário, analytics, banco de dados nem requisições de API.
Links externos **só navegam após clique**. A CSP em `index.html` impede
scripts, formulários e requisições remotas iniciadas pela página,
mas a política de cabeçalhos HTTP pertence ao **hosting**, quando escolhido.

### Identidade e alegações aprovadas para o rascunho

- Nome institucional de trabalho: **FenatoDev**, associado aos perfis públicos
  `github.com/fenatodev` e `linkedin.com/in/fenatodev`.
  A identidade final, uso comercial/marca e política de contatos ainda
  exigem revisão humana **antes de publicar**.
- Oferta: diagnóstico técnico, implantação de **um fluxo** de automação/
  integração e documentação/suporte **segundo contrato**, não um serviço
  ilimitado nem sistema ERP implantado.
- Portfólio: demonstração totalmente sintética
  `examples/order_to_crm.py`, e repositórios técnicos públicos
  `ai-coding-evaluation` e `lai-harness`, conferidos no GitHub.
- Nenhuma referência a cliente real, depoimento, receita, equipe,
  resultado financeiro, número de entregas, SLA, prazo ou economia medida.
- A demonstração é marcada **SIMULAÇÃO / DADOS FICTÍCIOS** e não é integrada
  a plataformas ou CRMs de terceiros.
- Contato por **links externos**, sem mensagem ou captura automática.
  Não publicar um e-mail particular sem decisão explícita.

## Segurança e privacidade

Antes de qualquer publicação:

1. Revisar texto, identidade/marca, endereço público/domínio, canal de
   contato e termos aplicáveis; validar links e autorização para qualquer
   marca, logotipo, depoimento, screenshot ou métrica futura.
2. Publicar **exclusivamente a pasta `site/`**, em hospedagem estática
   separada, sem `app/`, `migrations/`, `.env`, volume, logs ou
   dados privados. Manter a API `127.0.0.1:8788` sem exposição pública.
3. Usar HTTPS. Configurar cabeçalhos HTTP no host quando disponíveis:
   `Content-Security-Policy` coerente com o conteúdo sem script;
   `X-Content-Type-Options: nosniff`;
   `Referrer-Policy: strict-origin-when-cross-origin`;
   `X-Frame-Options: DENY` ou `frame-ancestors 'none'` via **header**
   (não via `meta`). HSTS apenas após confirmar HTTPS do domínio.
4. Confirmar se o **provedor de hospedagem** adiciona cookies/telemetria,
   termos de privacidade ou coleta além do código. A afirmação do rodapé
   refere-se **somente à página**, não a serviços externos.
5. Após definir domínio, revisar canonical, OG image/licenças,
   `robots.txt`/`sitemap.xml` e política de navegação/privacidade
   proporcional ao ambiente efetivo. **Não inventar** domínio agora.
6. Validar em dispositivos e navegadores móveis/desktop, acessibilidade
   e carregamento em hospedagem de teste antes do lançamento.

## Validação automatizada

```bash
uv run pytest -q tests/test_site_static.py
uv run pytest -q
.venv/bin/python -m compileall -q app tests examples
git diff --check
```

Teste visual adicional: Chrome/headless em **servidor local temporário**
de clone isolado, inspeção de console e screenshots responsivas, sem rede
externa. Browser QA não substitui avaliação editorial humana.

## Gate final do WP-021

**Código testado e revisado ≠ site publicado.** O WP termina com arquivos
revisados e, se apropriado, merge em `main`, mantendo o site fora do ar.
Publicação, escolha de domínio, DNS, custo de hosting, política de
privacidade final e abertura de canal de contato são **ações distintas**,
dependentes da autorização do responsável.

**Próximo passo da fila F2:** assistente para **rascunhos de marketing**
fundamentados no material público revisado. Sem publicação automática,
captação de leads ou case inventado.
