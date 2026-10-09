# WP-028 — Client 0: ensaio isolado de recuperação do índice privado

**Fase:** F2/O02, continuidade após WP-027.
**Base:** `main@32295ff387a0d790c1956e495976a5709265e089`.
**Branch:** `wp/028-synthetic-index-recovery`.
**Executor:** GitHub-first + Actions; **não ligar DC nem Continue** se CI verde.

## Objetivo único

Demonstrar o **backup e restore estrutural de três arquivos fictícios**
(índice de serviço, placeholder de prova social, modelo público)
num diretório temporário descartável. Falhar em symlink, caminho de
fuga, corrupção, documento extra, permissão incorreta e sobrescrita.

**Contrato de segurança:** isto NÃO é backup criptografado de dados
reais. Criar somente ZIP **plaintext** temporário com dados sintéticos
para testar restauração isolada. Não oferecer CLI para qualquer
`--source`/`--backup`/`--restore` real. Nunca afirmar que o
Client 0 privado foi recuperado ou protegido. O ZIP não deve ser
anexado a um artefato Actions e não deve entrar no Git.

## Arquivos autorizados

- `client0_workspace/recovery.py`: teste de arquivo bounded somente
  em `TemporaryDirectory`; ZIP sintético com manifest/checksum,
  formato restrito e restauração em destino inexistente.
- `tests/test_client0_recovery.py`: testes positivos e negativos
  com arquivos criados em `tmp_path` (nunca `Path.home()`).
- `docs/operations/client0-private-recovery.md`: segurança,
  diferenciação PostgreSQL × índice, restore real pendente.
- `docs/operations/client0-private-workspace.md`,
  `docs/operations/precontact-readiness.md`, `docs/ROADMAP.md`:
  referenciar gate e limitação.
- `.github/workflows/validation.yml`: adicionar **somente**
  `uv run python -m client0_workspace.recovery --synthetic-drill`
  no CI, com asserts de `archive_encrypted=false`,
  `real_workspace_accessed=false`,
  `real_backup_restore_verified=false`,
  `production_backup_authorized=false`.
- Esta spec.

**Não tocar:** `app/`, `migrations/`, Docker, banco,
ERPNext, MXQ4K, rede, backups atuais, `.env`, `cases/` do usuário,
firmware, Cloudflare, site, serviços, chaves ou dados comerciais.

## Aceite no GitHub Actions

1. `uv run pytest -q`: contagem real, incluindo ataque a arquivo ZIP,
   links simbólicos e manifesto adulterado.
2. `compileall`, syntax JS, site bundle 3/4, proof-social checklist e
   simulação F2 seguem verdes no SHA exato do PR.
3. Simulação em diretório temporário cria 3 arquivos 0600,
   diretórios 0700, snapshot ZIP plaintext 0600, verifica SHA-256
   e restaura em local novo; relatório resume só contagens/flags.
4. Nenhum backup/restore de dados reais nem saída para GitHub Actions
   artifacts; sem HTTP, subprocess, banco ou modelo.
5. **Não declarar conclusão da F2**, pagamento, produção, segurança
   de chave ou `real_backup_restore_verified=true`.

## Handoff para Qwen/Continue (não executar sem motivo)

Este WP é totalmente testável no GitHub: **Continue não recebe tarefa**.
Se CI falhar, identificar o erro por log do Actions, realizar uma
correção causal pequena e revalidar. No máximo uma tentativa corrigida;
sem sucesso, parar e reportar, não repetir comandos nem modificar
checkouts locais. Para operações futuras envolvendo dados reais,
abrir WP autônomo de criptografia/backups com aprovação separada.

**Entrega:** PR, SHA, testes reais, resultado CI, flags de bloqueio,
pendências para uma solução madura de backup criptografado.
