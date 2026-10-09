# WP-031 — Ubuntu: inventário read-only antes de backup real

**Objetivo único:** gerar evidência **sanitizada** do que falta para
ativar proteção do Client 0 **no Ubuntu** com o Restic já validado por
CI (WP-030), sem modificar dados do operador.

**Execução:** ChatGPT prepara e valida tudo no GitHub; **Continue com Qwen3.5-9B** executa **somente** a inspeção local indispensável, após CI verde e merge na `main`. A especificação é entregue **pelo próprio GitHub**, não por um prompt copiado de várias páginas. Desktop Commander e OpenCode permanecem desligados.

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
  resultado, gates de segurança e handoff pronto para Continue.
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

## Handoff GitHub → Continue/Qwen — um checkout descartável, um resultado

**Fonte única:** `https://github.com/fenatodev/business-automation/blob/main/specs/wp-031-ubuntu-operational-preflight.md`.
Não confiar em uma spec antiga aberta no VS Code: ler a versão do
**clone temporário do GitHub** e confirmar que é o WP-031. A fonte é
esta ficha; nenhuma informação do histórico da conversa é necessária.

**Prompt mínimo para o Continue (ChatGPT fornece SHA após merge):**

> Execute **somente** o WP-031 descrito no GitHub, arquivo
> `specs/wp-031-ubuntu-operational-preflight.md`, commit
> `<SHA_DA_MAIN_CONFIRMADO>`. Clone em `/tmp`, confira SHA e
> existência do script e execute `--check` uma vez.
> Não altere o projeto, instale software ou corrija bloqueios.
> Devolva o JSON sanitizado e o status; depois **STOP**.

**Passos operacionais permitidos**, uma vez:

1. Criar **um único diretório temporário novo** com
   `mktemp -d /tmp/ba-wp031-continue.XXXXXX`, então clonar
   `https://github.com/fenatodev/business-automation.git` com
   `git clone --quiet --single-branch --branch main <URL> <TEMP>/repo`.
   **Não usar o checkout de trabalho existente.**
2. Ler a **spec local ao clone temporário** e conferir
   `git -C <TEMP>/repo rev-parse HEAD` = `<SHA_DA_MAIN_CONFIRMADO>`.
   Conferir também `test -f <TEMP>/repo/scripts/ubuntu_readonly_preflight.py`.
   Qualquer divergência ou ausência => **STOP**, não simular
   saída e não procurar/corrigir outros caminhos.
3. Executar exatamente uma vez:
   `python3 -B <TEMP>/repo/scripts/ubuntu_readonly_preflight.py --check`.
   O script foi validado no CI com Python stdlib; **não** rodar
   `pytest`, `uv`, Restic, Docker ou outros comandos locais.

O clone temporário é **a única escrita** autorizada. Não dar
`git push`, `git clean`, `reset`, `checkout`, `stash`, executar
`sudo`, instalar ou alterar permissões. Não consultar arquivos
privados além dos metadados que o script já inspeciona; jamais
abrir `.env`, dados fiscais, credenciais, serviços, arquivos
`cases/` ou `/mnt/backup` diretamente. Não acessar MXQ4K,
rede local, roteador ou DNS; o clone GitHub é a única conexão
remota prevista.

**Anti-loop:** falhou clone/SHA/script/comando => informar código de
saída e motivo sanitizado, **sem repetir, refatorar, abrir outro
WP ou declarar PASS**. Não inferir `restic=false` de uma
falha em localizar o script. Em caso de terminal travado, interromper
o trabalho e devolver bloqueio; não explorar ferramentas ou
ambiente livremente.

**Nota:** `status=review_required` no JSON é uma coleta válida, não
significa que o backup ou a operação estejam prontos. O campo
`blocked` sinaliza condição insegura; também não se corrige aqui.

**Handoff sanitizado:** `WP031_LOCAL=PASS|BLOCKED`;
`main_sha=<...>`; `workspace=<safe|missing|blocked>`;
`backup_mounted=<true|false>`; `same_filesystem=<true|false|unknown>`;
`restic_present=<true|false>`; `write=false`;
`backup_performed=false`; `bloqueio=<...>`.
Não publicar stdout com dados não listados pelo contrato.

Após retorno, ChatGPT decide se um WP de **backup real sob aprovação
específica** é justificável. **Sem iniciar segundo WP automático.**
