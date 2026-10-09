# WP-032 — causa do bloqueio no Ubuntu (diagnóstico mínimo)

**Base GitHub:** `abbf77e0ca5782c4833d3b5fc9362c846447ca38` (WP-031 já aprovado).  
**Status:** implementação e CI apenas com fixtures sintéticas. **Ubuntu não foi alterado.**

## Evidência recebida

A execução local do WP-031 informou:

- `workspace_metadata.business-automation=blocked`. A checagem exige
  diretório real do próprio usuário com permissões exatas `0700`.
  **Não** podemos assumir se o motivo é dono, modo, symlink ou tipo.
- `restic=false`: instalação poderá ser necessária, mas **não autorizada**.
- `/mnt/backup` aparentemente montado e com filesystem diferente
  de `HOME`; isso **não comprova unidade física independente**.
- O `kind` citado pelo agente como `client0_ubuntu_readonly_prelight`
  não coincide com o literal do código WP-031:
  `client0_ubuntu_readonly_preflight`. O resumo pode ter sido transcrito
  incorretamente; não tratá-lo como saída bruta verificada.

**Não ajustar permissões por hipótese.** O diretório pai pode ser
usado por outras aplicações. `chmod -R`, `chown -R` ou migração
automática não são soluções aceitáveis para essa incerteza.

## O que o WP-032 fornece

Novo CLI read-only, Python stdlib:
`scripts/ubuntu_blocker_diagnosis.py --check`.

1. `Path.lstat()` **somente** na pasta exata
   `~/.local/share/business-automation`. Não lista diretórios ou abre
   arquivos. Produz **somente** `state`, modo octal e booleano de
   propriedade (`safe`, `missing`, `different_owner`,
   `private_mode_mismatch`, `symlink`, `not_directory`,
   `inaccessible`).
2. Executa **uma vez, sem privilégio**, `lsblk --json --output
   NAME,TYPE,MOUNTPOINTS` (somente leitura). Compara o disco ancestral
   da montagem do HOME e de `/mnt/backup` **apenas** para topologia
   simples `disk -> part`. Retorna `same_block_disk`,
   `different_block_disks` ou `indeterminate`, sem imprimir
   identificadores, serial, UUID, label ou paths privados. Em casos
   complexos (LVM, LUKS, RAID, rede, montagem duplicada), **não infere**.
3. Independentemente da resposta: `physical_independence_verified=false`,
   `real_backup_restore_verified=false`,
   `permission_change_authorized=false`,
   `restic_installation_authorized=false`.

A existência de discos distintos por topologia **ainda não confirma**
dois dispositivos independentes adequados para backup (falha conjunta,
armazenamento em bridge, mesmo hardware/controlador ou disponibilidade).
Uma revisão física/operacional posterior é obrigatória.

## Proibições

- Sem `sudo`, `apt`, `chmod`, `chown`, `mkdir` na pasta
  privada, mudança de ACL, desmontagem, reparo, snapshots ou limpeza.
- Não abrir `.env`, casos, documentos, contratos, contas fiscais,
  PostgreSQL, ERPNext, backups nem variáveis de ambiente.
- Não acessar MXQ4K, rede doméstica, volumes de clientes, servidor
  público, credenciais, chaves ou conteúdo de `/mnt/backup`.
- Não rodar Restic, teste de escrita em disco, deploy, propostas ou
  qualquer ação comercial.

## Aceite GitHub

- Adicionar `scripts/ubuntu_blocker_diagnosis.py` e
  `tests/test_ubuntu_blocker_diagnosis.py` com fixtures totalmente
  sintéticas; não consultar o `HOME` real no runner.
- CI Pytest e `compileall`, demais guardrails sem regressão,
  `git diff --check` verde no SHA exato.
- Documentar a leitura do resultado e entregar ao Continue por
  **especificação no GitHub + SHA de `main`**.
- Não executar OpenCode, Desktop Commander nem computador do usuário.
- Integrar PR normal apenas após CI verde; o WP-032 não permite
  corrigir as causas encontradas automaticamente.

## Execução futura com Continue: único handoff local

**Não usar o checkout de desenvolvimento existente.** Após o merge,
o ChatGPT fornecerá o SHA final `main`. O Continue deverá:

1. Criar uma pasta temporária nova usando `mktemp -d` e clonar
   `https://github.com/fenatodev/business-automation.git` apenas
   na subpasta `repo`.
2. Conferir `git -C <tmp>/repo rev-parse HEAD` com o SHA exato
   fornecido e `test -f <tmp>/repo/scripts/ubuntu_blocker_diagnosis.py`.
   Falha => STOP, sem tentar outros caminhos.
3. Executar **uma vez**:
   `python3 -B <tmp>/repo/scripts/ubuntu_blocker_diagnosis.py --check`.
   A ferramenta pode consultar `lsblk`, mas não usa privilégio
   ou comandos de manutenção.

**Retorno obrigatório:** colar stdout JSON original **sem reescrever**
e o exit code real; confirmar literalmente
`kind=client0_ubuntu_blocker_diagnosis`. Sem um JSON válido e
literal, considerar o diagnóstico **não verificado**.

**STOP após o JSON**, independentemente do estado. Não instalar,
corrigir ou acionar outra tarefa por consequência desse retorno.

## Próxima decisão após o diagnóstico

A causa exata será tratada separadamente: se `0700` for inadequado por
ser uma pasta compartilhada, avaliar isolamento de um índice próprio,
**não enfraquecer as checagens do sistema**. Se disco de backup não for
fisicamente separado, escolher outro destino antes de ativar o Restic.
A instalação do Restic e o primeiro backup/restore real exigem
autorização humana distinta. F2, prospecção e publicação seguem pendentes.
