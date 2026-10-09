# WP-033 — estado operacional verificado após execução local

**Data da conferência:** 2026-10-09.
**Estado:** **PARTIAL** — relatório sanitizado, revisto com leitura de metadados no Ubuntu via Desktop Commander, sem executar novamente o WP-033.
**Natureza:** registro datado da observação feita na conferência original, não reprodução do histórico da sessão anterior. **Há uma atualização posterior de instalação abaixo**, que substitui as linhas históricas sobre a ausência do Restic.

## Evidência verificável na conferência inicial

| Item | Estado observado | Alcance da evidência |
| --- | --- | --- |
| Diretório privado principal | `0700`, pertencente ao usuário corrente | Conferido por `stat`; `getfacl` exibiu apenas proprietário com acesso e grupo/outros sem acesso. |
| Mudança de `0775` para `0700` | **Estado final compatível com correção** | WP-032 indicava `0775`; **não é possível atribuir a alteração ao Pi/Continue** nem recuperar quem/quando a efetuou. |
| Restic como comando do sistema | **AUSENTE** | `command -v restic` não encontrou o executável. |
| Pacote Restic via DPKG | **NÃO INSTALADO/INDISPONÍVEL** | Consulta `dpkg-query` não encontrou pacote instalado. **Não** fazer inferência sobre tentativa anterior de instalação. |
| Destino de backup | **MONTADO** | `mountpoint` confirmou montagem no destino operacional previsto. |
| Destino versus HOME | **FILESYSTEMS DIFERENTES** | Comparação de IDs de filesystem. WP-032 também indicara dois discos lógicos distintos. |
| Independência física | **NÃO COMPROVADA** | Discos/partições/filesystems diferentes não provam mídias físicas independentes, políticas de retenção ou capacidade de restauração. |
| Backup e restauração reais no WP-033 | **NÃO VERIFICADOS** | Nenhum backup/restauração foi realizado nesta conferência. Não reivindicar recuperação ou backup de dados reais com base neste documento. |

## Resultado e bloqueios na conferência inicial

```text
WP033_REVIEW=PARTIAL
workspace_current=0700
workspace_owner=current_user
workspace_group_access=none
workspace_other_access=none
restic_cli=absent
restic_dpkg=not_installed
backup_mount=mounted
home_and_backup_filesystems=different
physical_independence=not_verified
prior_local_action_history=not_verified
real_backup_restore_verified=false
publication_authorized=false
```

**Bloqueios observados naquela conferência inicial (histórico):** Restic ausente à época, independência do destino não comprovada e nenhum restore real demonstrado. As evidências posteriores de 2026-10-09, descritas abaixo, substituem os estados relativos à instalação e à topologia. O índice `client0` completo não foi auditado.

## Limites do procedimento

A revisão remota executou **somente consultas de estado**; não usou `sudo`, APT, `chmod`, `chown`, backup/restauração, varreduras recursivas nem alteração da pasta operacional. Não abriu arquivos de clientes, bancos, chaves, documentos, variáveis confidenciais ou logs de agentes.

A branch **`wp/033-local-report`** já havia sido enviada pelo executor local, mas estava baseada numa revisão antiga e continha campos `NÃO VERIFICADO`. Este documento é a revisão consolidada, criada **diretamente a partir da `main` atual** para evitar incorporar histórico divergente. Nenhum dado privado ou identificador físico foi copiado daquele ambiente para o GitHub.

## Atualização posterior — instalação realizada pelo operador (2026-10-09)

**Origem da evidência:** saída textual do terminal fornecida pelo responsável nesta conversa. **Não é uma verificação independente pelo Desktop Commander**; as linhas anteriores continuam registrando corretamente a situação da conferência *antes* da instalação.

- Sistema informado pelo operador: `Ubuntu 24.04.5 LTS`, codinome `noble`.
- Instalação executada pelo operador com APT: pacote oficial `restic`, versão `0.16.4-2ubuntu0.24.04.3`, obtido de `noble-updates/universe`.
- Saída final informada: `restic 0.16.4 compiled with go1.22.2 on linux/amd64`.
- Resultado relatado pelo APT: **1 pacote novo (Restic), 0 atualizados, 0 removidos**. Não reproduzir a instalação.
- A correspondência `Ubuntu 24.04.5/noble` ↔ repositório `noble-updates` elimina a suspeita anterior de divergência de codinome **para esta instalação**. Não equivale a auditar todos os repositórios APT.
- **Restic agora reportado como instalado.** Os campos históricos `restic_cli=absent` / `restic_dpkg=not_installed` acima **foram superados** por esta evidência posterior.
- `WP033_REVIEW=PARTIAL` permanece: independência física e custódia de chave não verificadas; sem backup real e sem teste de restauração.

## Atualização — inventário local read-only (2026-10-09)

**Origem:** inspeção remota de **metadados** por Desktop Commander no Ubuntu; não é execução do Pi, backup ou autorização de escrita. O output integral de dispositivos, identificadores e diretórios não foi publicado.

| Verificação | Resultado e limite |
| --- | --- |
| Sistema e Restic | Ubuntu 24.04.5 LTS / `noble`; executável `/usr/bin/restic` reporta **0.16.4**. Confirmação remota posterior à instalação manual. |
| Unidade de origem | Sistema de arquivos raiz num **SSD SATA interno**, montado normalmente. |
| Unidade de destino | `/mnt/backup` é mountpoint ativo de **outro dispositivo SATA**, um HDD próprio e distinto do SSD de origem (verificados `lsblk`, modelo/tipo e `findmnt`). |
| Capacidade no instante da leitura | Aproximadamente **700 GiB disponíveis**; não implica integridade, durabilidade ou capacidade futura garantida. |
| Sistema de arquivos de backup | `ntfs3`, montado em leitura/escrita. Máscaras observadas permitem modos apresentados como **0755 para diretórios / 0644 para arquivos**; não presumir isolamento POSIX por `chmod` nesse volume. |
| Índice privado | Raiz de trabalho, `client0`, `cases` e `templates`: todos diretórios reais reportados como **0700** do usuário corrente. `templates/case.md` existe e reporta **0600**. Somente `stat`, sem ler conteúdos. |
| Independência | **Duas unidades SATA físicas distintas conforme inventário do SO**, não apenas partições ou letras diferentes. Inspeção visual humana do gabinete **não realizada**. |
| Continuidade contra desastre | **NÃO COMPROVADA**: ambas as unidades estão no mesmo computador. Falha do host, furto, incêndio, ransomware e exclusão do repositório permanecem riscos. |
| Backup/restore operacional | **NÃO EXECUTADOS**; senha/cópia de recuperação e retenção ainda não estabelecidas. |

**Implicações:** o requisito de destino em **outro dispositivo de bloco** está atendido pelas evidências de software. Não equiparar isso a backup externo/off-site ou a mídia desconectada. Como o destino é um HDD NTFS3 pré-existente, **não** formatar, reparticionar, remontar, forçar permissões ou alterar seus arquivos sem plano e consentimento específicos. O Restic cifra e autentica dados, mas um usuário ou software com permissão de escrita no destino ainda pode remover/corromper o repositório; a senha também precisa permanecer separada. Antes de uso operacional, validar compatibilidade e restauração **nesse sistema de arquivos**, em ensaio delimitado e aprovado.

```text
wp033_local_inspection=read_only_verified
ubuntu=24.04.5_noble
restic=installed_0.16.4
workspace_mode=0700
cases_mode=0700
templates_mode=0700
template_mode=0600
backup_mount=mounted_separate_sata_hdd_ntfs3
separate_block_device=verified
physical_visual_inspection=not_done
off_host_backup=not_verified
key_custody=not_configured
real_backup_restore_verified=false
f2_open=true
```

## Próximo gate — ainda não executado

1. **Escolher a política de armazenamento:** manter o HDD NTFS3 para um ensaio delimitado ou preparar futuramente armazenamento Linux dedicado/off-site, sem mexer nas partições existentes. Avaliar segunda cópia independente do host.
2. **Definir custódia da senha:** gerar localmente senha forte, arquivo `0600` fora da origem/destino e segunda cópia recuperável sob controle do operador; jamais enviar segredo ao GitHub/chat/logs.
3. **Aprovar explicitamente em etapa separada:** escrever um repositório Restic em pasta nova, copiar *somente* `cases/` e `templates/` autorizados, `check --read-data`, restore em diretório **novo e isolado**, comparação local sem extrair conteúdo para os logs. Em falhas, STOP; nenhum `forget`/`prune`.
4. **Depois**, tratar agendamento, retenção, cópia off-host e backups consistentes de PostgreSQL/ERPNext por procedimentos próprios.

**F2 permanece aberta.** Esta evidência não autoriza publicar o site, contatar clientes, emitir documentos fiscais, fazer deploy ou declarar operações financeiras concluídas.
