# WP-030 — Restic: backup criptografado e restore isolado sintéticos

**Base:** `main@47984a6bc356f8b0f1df094e936b365b7ac4d45b`
**Branch:** `wp/030-restic-recovery-readiness`
**F2/D07:** preparar *ferramenta real de backup criptografado*,
sem copiar ou acessar qualquer dado real.

## Escopo único

- Criar `client0_workspace/restic_drill.py` com **somente**
  `--synthetic-drill`. Ele usa Restic externo verdadeiro com
  `TemporaryDirectory`, fontes fictícias, senha randômica sintética
  em arquivo 0600, repositório isolado, `init`, `backup`,
  `snapshots --json`, `check --read-data`, restore isolado
  e comparação exata de bytes/0600. Testar recusa de senha errada.
- Criar `tests/test_client0_restic_drill.py`: erro sanitizado,
  argumentos de produção rejeitados, código seguro e teste funcional
  quando Restic estiver disponível.
- CI: **somente no runner Ubuntu do GitHub**, instalar Restic
  via apt quando ausente, executar suíte e teste do CLI com flags
  de bloqueio `real_backup_restore_verified=false`,
  `real_workspace_accessed=false`, `production_repository_created=false`,
  `external_action_taken=false`.
- Documentar fluxo operacional **futuro** com destino independente,
  custódia de senha fora da origem e Git, revisão de escopo, dados,
  restore em diretório novo, separação do banco PostgreSQL:
  `docs/operations/client0-restic-recovery.md`.
- Atualizar `docs/operations/client0-private-recovery.md`,
  `docs/operations/client0-launch-decisions.md`,
  `docs/operations/precontact-readiness.md` e `docs/ROADMAP.md`
  com links e **sem declarar restore de produção validado**.

## Proibições expressas

**Nada local**: não ligar DC, Continue, Open Interpreter ou MXQ4K,
não instalar Restic no Ubuntu do usuário, não pesquisar conteúdo de
`client0/cases`, PostgreSQL, Docker, .env, chaves, backup ou GitHub
privado, não criar snapshot de dado pessoal nem anexar repositório
Restic/senha ao GitHub Actions artifact. Não fazer deploy, fiscal,
proposta, contato ou cobrança.

A ferramenta **não** aceita `--backup`, `--restore`, `--source`,
`--repository`, não opera `Path.home()` e não cria task agendada.
Nunca usar ZIP plaintext WP-028 para dados reais, não declarar que
SHA-256 é criptografia ou que um teste CI equivale a backup
independente/seguro no host.

## Aceite

1. Github Actions verde no HEAD exato do PR: suíte Pytest com
   contagem real, compileall, JS, guardrails, `git diff --check`.
2. Binário Restic real no CI (apt só no runner); snapshot criptografado
   temporário, `check --read-data`, senha inválida rejeitada,
   restauração isolada de 3 arquivos 0600 idênticos aos originais.
3. A saída JSON informa explicitamente todas as limitações e
   `publication_authorized=false`; sem caminhos reais ou chaves.
4. Sem artifact Restic e sem acesso a volume ou credencial privada;
   artifacts existentes apenas do site estático no `main`.
5. Os passos locais com dados reais dependem de aprovação específica
   posterior para seleção de destino independente e custódia da senha.

**Depois:** não iniciar novo WP sintético automaticamente. A próxima
execução que realmente avance o negócio deverá comprovar prontidão
operacional local ou resolver decisões humanas de lançamento. A F2
só é encerrada depois de ciclo comercial verdadeiro com recebimento.
