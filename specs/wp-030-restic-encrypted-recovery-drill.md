# WP-030 — Restic encrypted synthetic recovery (F2 / D07)

**Base:** `main@47984a6bc356f8b0f1df094e936b365b7ac4d45b`.
**Branch:** `wp/030-restic-encrypted-recovery-drill`.
**Executor:** ChatGPT/GitHub Actions. **Sem DC, Continue e MXQ4K**.

## Objetivo único

Sair do teste ZIP plaintext WP-028 e provar **criptografia/restauração
verdadeiras por ferramenta madura**, usando exclusivamente dados
fictícios criados e descartados no GitHub Actions.

**Não** executar backup real, **não** instalar Restic no Ubuntu do
responsável, não ler `$HOME` ou casos de cliente, não gerar credenciais
operacionais nem criar um serviço de backup personalizado.

## Arquivos autorizados

1. `client0_workspace/restic_drill.py` — único modo
   `--synthetic-drill`; gera fixture fictícia de 3 documentos sob
   `TemporaryDirectory`, senha aleatória efêmera, inicializa repo
   Restic cifrado e verifica `backup`, `check --read-data`,
   senha incorreta rejeitada e `restore` isolado, byte-exact.
2. `tests/test_restic_drill.py` — contratos Python offline;
   teste de operação real da ferramenta opcional quando Restic
   não estiver instalado, executado obrigatoriamente em CI dedicado.
3. `.github/workflows/restic-recovery.yml` — instala pacote
   oficial Ubuntu **somente num runner descartável**, executa
   ensaio real, sem artifact, sem secrets e permissões GitHub
   `contents: read`; não publicar nada.
4. `docs/operations/client0-protected-backup.md` — compara
   alternativas maduras e define limite entre CI sintético e
   backup real, com custódia/restore/retention, mídia independente.
5. Este arquivo; links em `docs/operations/client0-private-recovery.md`,
   `docs/operations/client0-launch-decisions.md`,
   `docs/operations/precontact-readiness.md` e `docs/ROADMAP.md`.

**Não alterar** `app/`, `migrations/`, banco, ERP, Compose,
sites, marketing, finanças, hardware, DNS, impostos nem o CI
existente salvo para um ajuste comprovadamente necessário.

## Critérios exatos

- GitHub Actions geral: `uv run pytest -q`, compileall, diff,
  JS, site, Prova Social, F2 synthetic e restores WP-027/028 PASS.
- Teste Restic dedicado executa o **restic real** no GitHub:
  `init → backup → check --read-data → wrong password denied →
  snapshots → restore`, com três arquivos restaurados byte a byte.
- Pasta temporária tem permissões privadas; senha aleatória em arquivo
  0600 é removida ao fim, nunca trafega por CLI ou logs.
- Nenhum artifact contém cópia, senha, ZIP ou dados pessoais.
- Resultado: `status=pass`,
  `synthetic_encrypted_repository_verified=true`,
  `isolated_restore_verified=true`,
  `wrong_password_tested=true`; **obrigatoriamente**
  `real_workspace_accessed=false`,
  `real_backup_restore_verified=false`,
  `offsite_backup_verified=false`,
  `production_backup_authorized=false`,
  `external_action_taken=false`.
- **Teste verde não marca D07 aprovado**, porque hardware de backup,
  chave do usuário e destino independente não foram conferidos.

## Previsões de falha

- Sem Restic? CI dedicado deve instalar **somente no runner**; não
  acrescentar o executável à máquina do usuário.
- Erro de binário, senha, corrupção ou restore? **FAIL fechado**,
  não alterar casos reais nem tentar ferramentas caseiras de cifra.
- Uma falha observada => uma correção causal e novo CI; se não
  resolver, **STOP** com PR aberto e motivo.
- Só merge após ambas as validações GitHub ficarem verdes para o
  commit exato; após merge verificar `main`.

## Próximo bloqueio operacional

Após WP-030, **não abrir novos WPs sintéticos por inércia**.
Decidir D01 (prestação como PF ou empresa após revisão fiscal);
D07 exige destino protegido real e restore local com autorização;
D08 boot futuro do SD Armbian MXQ4K e publicação aprovada;
D09 prospecção somente após aprovação do responsável.

Nenhuma informação particular sobre CNPJ, débitos ou CPF entra
no GitHub público.
