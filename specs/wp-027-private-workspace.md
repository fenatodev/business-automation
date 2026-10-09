# WP-027 — O02: private workspace preflight + blank-template bootstrap

**Base:** `main@45744c9af42756c6239f7469761096dbb413b888`
**Branch:** `wp/027-private-client0-workspace`
**Executor:** ChatGPT/GitHub Actions; **DC permanece desligado**.
**Dispositivo:** MXQ4K tem Armbian preparado em SD, informado pelo
responsável, mas **boot ainda não verificado** e nenhum acesso permitido.

## Resultado único

Transformar o modelo privado Client 0 de WP-019 em uma ferramenta
**segura e verificável** que apenas:

1. Audita existência, proprietário e modos sem ler dados (`--preflight`).
2. Cria **somente** pastas privadas vazias e cópia de modelo público,
   sem sobrescrever arquivos (`--bootstrap-empty`).
3. Demonstra idempotência e isolamento no CI (`--synthetic-drill`).

**Não realiza backup, restore, autenticação ERP, fiscal, postagem, envio
de proposta ou avaliação do hardware.** `backup_restore_verified=false`
em todos os relatórios.

## Arquivos permitidos

Criar `client0_workspace/__init__.py`,
`client0_workspace/workspace.py`, `tests/test_client0_workspace.py`,
`docs/operations/client0-private-workspace.md`, este documento.
Atualizar somente `.github/workflows/validation.yml`,
`docs/operations/mxq4k-hosting-deferred.md`,
`docs/operations/precontact-readiness.md` e `docs/ROADMAP.md`.

Sem acesso a `app/`, `migrations/`, `docker-compose.yml`,
tokens, banco PostgreSQL real, Uvicorn, ERPNext, TV Box, roteador,
Cloudflare Pages ou arquivos reais de cliente.

## Aceite via GitHub Actions

- `uv run pytest -q`: contagem real, testes de permissões, symlinks,
  modelo preexistente, não sobrescrever, preflight sem escrita.
- `compileall` inclui `client0_workspace`.
- `uv run python -m client0_workspace.workspace --synthetic-drill`
  retorna `status=pass`, `real_workspace_accessed=false`,
  `backup_restore_verified=false`, `external_action_taken=false`.
- Testes, diff, JS, releases do site, provas sociais e simulação
  comercial permanecem verdes.
- Nenhum CLI `--bootstrap-empty` ou `--preflight` de **HOME real**
  é executado pelo GitHub Actions.
- CI verde no **HEAD exato do PR** antes de merge. No main,
  repetir CI e não dar deploy nem criar infraestrutura.

## Contrato anti-loop para Continue/Qwen 3.5 9B

Não precisar de Continue para o teste em CI. Se for necessário ativar
o diretório privado após merge, delegar **só o comando CLI já
testado**, em checkout confiável, primeiro `--preflight`, depois
`--bootstrap-empty` apenas quando o status for `missing`, por fim
`--preflight`. Nunca ler casos existentes, mover arquivos, corrigir
modos manualmente, fazer `chmod -R`, `sudo`, migrar, apagar, subir
serviços, ligar o MXQ4K ou tocar banco.

Uma falha => registrar motivo, sem repetir mecanicamente; no
máximo uma correção causal **via novo PR**, não no host do usuário.
Ação de armazenamento real/backup exige gate específico posterior.

**Encerramento:** `WP027_REMOTE=PASS` somente com CI de todos
os testes verde; `WP027_LOCAL` fica **NOT_RUN**, salvo execução
explícita. F2 permanece aberta até ciclo real e retorno financeiro
confirmado. Próxima etapa de back-office: desenho/validação de
recuperação protegida sem perder dados, em WP separado.
