# WP-031 — Ubuntu: inventário read-only antes de backup real

**Objetivo único:** gerar evidência **sanitizada** do que falta para
ativar proteção do Client 0 **no Ubuntu** com o Restic já validado por
CI (WP-030), sem modificar dados do operador.

**Execução:** código, testes e PR primeiro no GitHub; **OpenCode** é
executor da leitura local *apenas depois do CI e merge da main*.
Desktop Commander permanece desligado.

## Limites de escopo

Arquivos autorizados:
- `scripts/ubuntu_readonly_preflight.py`: Python stdlib,
  CLI obrigatoriamente `--check`, inspeciona **metadados
  exclusivamente** das pastas fixas
  `~/.local/share/business-automation/client0/` e
  `/mnt/backup`, disponibilidade de `restic`, `git`, `uv`,
  `opencode`, arquitetura e `/proc/self/mountinfo`.
- `tests/test_ubuntu_readonly_preflight.py`: fixtures temporárias
  para ausência, modos, symlink, arquivos de cliente ignorados,
  mount simulado, argumentos não autorizados e output.
- `docs/operations/client0-ubuntu-preflight.md`: interpretação de
  resultado, gates de segurança e handoff pronto para OpenCode.
- `docs/operations/client0-launch-decisions.md`,
  `docs/operations/precontact-readiness.md`, `docs/ROADMAP.md`:
  indicar **inventário local pendente**, sem confundir CI com operação.
- `.github/workflows/validation.yml`: compilar script e rodar testes
  sintéticos junto da suíte existente.
- Este documento.

**Não autoriza:** `--bootstrap-empty`, Restic `init/backup/restore`
no Ubuntu, escrita em `cases`, `chmod/chown`, instalação,
`sudo`, login, acesso PostgreSQL/ERPNext/Docker, inspeção de
conteúdo/nomes de casos, montagem/partição de mídia, reboot,
MXQ4K/SSH, portas/túneis/domínio/deploy, proposta ou prospecção.

## Critério técnico

1. GitHub Actions verde no **HEAD exato** do PR: testes e
   `compileall`, diff, JS e guardrails inalterados.
2. Testes de preflight só rodam em `tmp_path`; **CI não inspeciona
   nenhum dado real do operador**.
3. CLI `--check`: imprime JSON sem nomes de pessoas, paths de
   documentos, mount devices, CNPJ, secrets ou dados empresariais.
4. Se um componente é symlink ou tem permissões inseguras,
   retorna `blocked`; o executor só informa, **não corrige**.
5. Volume montado e filesystem diferente **não provam**
   mídia fisicamente independente. Campo
   `physical_independence_verified=false` sempre.
6. `user_files_modified=false`, `backup_executed=false`,
   `restore_executed=false`, `mxq4k_accessed=false`,
   `publication_authorized=false` sempre.
7. **Não rodar CLI local antes de CI/merge.**

## Contrato OpenCode — um checkout descartável, um resultado

Depois do merge, ChatGPT informa SHA completo de `main`.
Executar **uma vez**, com OpenCode, dentro de clone temporário novo.
Somente os três comandos permitidos dentro de um script shell
`set -e` são:

1. `git clone --quiet --single-branch --branch main
   https://github.com/fenatodev/business-automation.git
   <novo_tmp>/repo` (nunca checkout local existente).
2. `git -C <novo_tmp>/repo rev-parse HEAD` e comparar o SHA aprovado;
   divergência => **STOP**, não rodar Python.
3. `python3 -B <novo_tmp>/repo/scripts/ubuntu_readonly_preflight.py --check`
   (stdlib, sem `uv`, sem ferramentas externas de manutenção).

Não consultar/ler diretórios privados além dos metadados que o
script acessa. Não abrir .env, dados fiscais, credenciais, banco,
serviços, cases ou `/mnt/backup` diretamente. Não dar acesso
irreversível ou amplo ao agente; se um comando pedir confirmação
de ação fora dos três, **STOP**.

**Handoff sanitizado:** `WP031_LOCAL=PASS|BLOCKED`;
`main_sha=<...>`; `workspace=<safe|missing|blocked>`;
`backup_mounted=<true|false>`; `same_filesystem=<true|false|unknown>`;
`restic_present=<true|false>`; `write=false`;
`backup_performed=false`; `bloqueio=<...>`.
Não publicar stdout com dados não listados pelo contrato.

Após retorno, ChatGPT decide se um WP de **backup real sob aprovação
específica** é justificável. **Sem iniciar segundo WP automático.**
