# WP-034 — gates para backup Restic no HDD separado e recuperação real

**Estado em 2026-10-09: PREPARADO, NÃO EXECUTADO.**
Preparação feita no GitHub e inventário local exclusivamente read-only.
**Nenhuma senha foi criada, nenhum repositório Restic foi inicializado,
nenhum dado privado foi copiado e nenhuma restauração real foi executada.**
Este arquivo não é autorização de escrita; o operador aprova cada gate
sensível de forma distinta. O objetivo é entregar proteção recuperável,
não só `restic backup` sem prova de recuperação.

## Inventário e decisão técnica já observados (WP-033)

- Ubuntu 24.04.5 LTS (`noble`), Restic APT 0.16.4 presente.
- Fonte Client 0 em SSD SATA; backup em outro HDD SATA montado em
  `/mnt/backup`, NTFS3, aproximadamente 700 GiB livres na inspeção.
- Raiz, `client0/`, `cases/`, `templates/`: diretórios 0700;
  `templates/case.md`: arquivo 0600; sem leitura de conteúdo.
- Preflight adicional read-only: a pasta proposta para o repositório
  **não existe**; sua pasta-pai também não existe. SSD da origem
  aproximadamente 68,6 GiB livres na inspeção.
- Ambos os discos estão **no mesmo computador**. Independência de mídia
  não garante resiliência contra falha do host, incêndio, furto, exclusão
  por malware ou comprometimento da conta do operador.
- NTFS3 montado com máscaras que apresentam diretórios 0755 e arquivos
  0644: **não aplicar o modelo POSIX 0700/0600 ao volume de destino**,
  não supor que permissões do NTFS isolem usuários. A confidencialidade
  dos blobs depende da criptografia Restic e da chave custodiada.

A **decisão provisória** é aproveitar o HDD sem formatação para
**ensaio delimitado de compatibilidade** e depois decidir o backup real
nessa mídia. Se incompatível, parar e propor outra mídia/filesystem
apropriado — nunca reparticionar/reformatar unilateralmente.

## A. Preflight somente leitura — já parcialmente verificado

O operador autoriza apenas coleta de **metadados fixos** para este gate.
Não enumerar o conteúdo de casos, anexos, diretórios de backup ou arquivos
do cliente. Validar o sistema e a origem com
`python3 -B scripts/ubuntu_readonly_preflight.py --check` em clone
temporário limpo com SHA de `main` conferido.

Antes de qualquer escrita: conferir novamente `mountpoint`,
`findmnt`, `lsblk`, a árvore física fonte/destino, disponibilidade
e estado `rw` do mount, ausência de symlinks nos pais/destinos,
proprietário/permissões da origem, versão do Restic, e que os destinos
ainda não existem. Se a montagem mudar, um destino for symlink,
houver outro repositório já inicializado ou o preflight for bloqueado:
**STOP**, não migrar/remontar/apagar nada.

Os resultados iniciais acima são **instantâneos**, não substituem a
revalidação imediatamente antes da execução.

## B. Ensaio NTFS3 com dados integralmente sintéticos — PENDENTE

**Requer aprovação explícita para criar e apagar somente artefatos
temporários de teste no HDD**, em pasta nova nomeada exclusivamente para
este ensaio; não reutilizar destino existente.

- Restic 0.16.4, senha **aleatória descartável**, sem interação com
  os arquivos ou segredos reais.
- Criar três arquivos fictícios 0600 em área temporária privada no SSD;
  repositório Restic sintético em **pasta nova** do HDD NTFS3.
- Validar `init`, `backup --one-file-system`, `check --read-data`,
  rejeição de senha errada e `restore` para **nova pasta isolada no SSD**,
  com igualdade byte a byte e modos corretos no destino ext4.
- Restic deve receber caminhos explícitos por argumentos e senha por
  arquivo privado temporário. Capturar saídas localmente e transmitir
  somente flags e códigos sanitizados; sem senhas/snapshot IDs/logs
  de cliente no Git ou chat.
- Ao terminar, remover **somente os diretórios temporários que este
  ensaio criou**, com verificação prévia de identidade/tipo e sem
  recursão contra caminhos fornecidos externamente. Se a limpeza
  não puder ser comprovada, STOP e relatar resíduo sem exibir detalhes.
- Nunca usar `forget`, `prune`, `unlock`, `repair`, `chmod -R`,
  `rm -rf` de caminho pré-existente, root/sudo, instalação ou upgrade.

**Aceite B:** `synthetic_ntfs_backup_restore=pass`; isso **não**
atesta segurança nem recuperação dos dados reais.

## C. Custódia de senha real — PENDENTE (decisão humana)

Antes de backup com dados reais, o operador define e confirma:

1. Senha aleatória forte, gerada **localmente**, nunca exibida em
   comando, terminal compartilhado, API, mensagem, Git ou logs.
2. Arquivo `0600` dentro de diretório privado `0700` no SSD,
   **fora** de `client0/` e de `/mnt/backup`, criado com
   `O_CREAT|O_EXCL|O_NOFOLLOW` e `umask 077`; recusar sobrescrita.
3. **Segunda cópia independente do mesmo computador**, mantida pelo
   operador em gerenciador seguro, mídia offline controlada ou equivalente.
   A simples existência da senha no SSD não atende este requisito.
4. Procedimento de reobtenção da senha em caso de perda do SSD,
   sem remeter segredo a agentes ou publicá-lo. Se houver qualquer
   dúvida sobre recuperação: **STOP** antes do backup real.

Confirmar em relatório **apenas** `recovery_copy_confirmed=true|false`,
sem valor, hash, caminho completo ou dica de senha.

## D. Backup e restauração REAIS — PENDENTE, NOVA AUTORIZAÇÃO ESPECÍFICA

**Escopo exato proposto:** só
`~/.local/share/business-automation/client0/cases/` e
`~/.local/share/business-automation/client0/templates/`.
Não incluir `client0/` inteiro, marketing, ERPNext, PostgreSQL,
`.env`, chaves, anexos não autorizados ou outros volumes. Antes
do backup, conferir *localmente* classificação dos arquivos autorizados
e ausência de conteúdo indevido; não enviar inventário privado ao Git.

**Destino proposto (novo, ainda inexistente):**
`/mnt/backup/business-automation/client0-restic-v1/`.
Não reutilizar destino ocupado e não inferir escolha só porque o
caminho consta no documento. Requer aprovação explícita do operador
para esta localização e para leitura/cópia dos dois diretórios reais.

Depois de B e C aprovados/verificados e nova conferência A:
1. Inicializar **uma vez** o repositório criptografado; se já existir,
   STOP e reconciliar, não repetir `init`.
2. Usar o binário e flags suportados pelo **Restic 0.16.4**; usar
   `--password-file` e `--repo` com caminhos fixos conferidos.
3. Capturar snapshot desses **dois** diretórios explícitos, com
   `backup --one-file-system`, preservando caminhos/modes da origem;
   confirmar código zero e escopo dos paths do snapshot localmente.
4. Executar `check --read-data` e restaurar **snapshot verificado**
   em diretório privado `0700` e **novo, vazio e fora da origem**.
   No Restic, caminhos absolutos são reconstruídos sob o target:
   comparar no target correto, nunca restaurar sobre `client0/`.
5. Validar igualdade por bytes, tipos, nomes permitidos e modos no
   **ext4 de restauração**, sem expor arquivos, conteúdos, hashes
   individuais, nomes de clientes ou logs extensos. Confirmar também
   que a cópia de senha de recuperação pode abrir o repositório,
   em operação controlada pelo humano.
6. Falha de qualquer etapa = **PARTIAL/BLOCKED**. Não registrar
   `real_backup_restore_verified=true` se a recuperação não passar.

Nenhum comando de limpeza, rotação, retenção, agendamento, cron,
`forget/prune`, upload para nuvem, publicação ou integração financeira
está autorizado neste WP.

## E. Handoff estritamente sanitizado

```text
WP034=PREPARED|PARTIAL|PASS|BLOCKED
main_sha=<sha exato utilizado>
os_noble=true|false
restic_0164_available=true|false
source_modes_safe=true|false
backup_separate_sata_disk=true|false
ntfs3_mount_ready=true|false
target_new_absent=true|false
synthetic_ntfs_backup_restore=pass|fail|not_executed
recovery_copy_confirmed=true|false
real_backup_restore_verified=true|false
customer_content_disclosed=false
repository_created=true|false
restore_on_new_isolated_target=true|false|not_executed
next_gate=<código sem dados privados>
```

**Estado inicial verificado:** preflight de metadados da máquina
compatível com preparar o ensaio; gates B/C/D não executados. O operador
deve autorizar B, depois definir C, e somente então autorizar D.
O GitHub/CI NÃO possui nem recebe dados ou senhas reais.

**Limitações:** Restic do índice não é cópia consistente da base
PostgreSQL, ERPNext, nem segunda cópia off-site. Não afirma
recuperação após falha total do equipamento. F2 permanece aberta;
prospecção, envio de propostas, operações fiscais e deploy seguem
bloqueados por seus próprios gates.

## Fontes técnicas

- Restic 0.16.x: https://restic.readthedocs.io/en/v0.16.0/
- Preparação de repositórios, senhas e perda irrecuperável de chave:
  https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html
- Verificação de integridade, backup e restauração:
  https://restic.readthedocs.io/en/stable/045_working_with_repos.html
- Discussão técnica de risco de backend/FS; nenhum backend substitui
  teste de restauração e cópia off-host:
  https://github.com/restic/restic/issues
