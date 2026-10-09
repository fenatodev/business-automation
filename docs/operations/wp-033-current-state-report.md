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

**Bloqueios ainda ativos:** instalação do Restic **não confirmada e ausente no estado atual**; independência física e operacional do destino não comprovada; nenhum restore real de dados privados demonstrado. O índice `client0` completo ainda não foi validado neste relatório.

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

## Próximo gate — ainda não executado

1. Confirmar fisicamente o volume de destino e sua disponibilidade **fora do disco de origem**, antes de afirmar independência.
2. Conferir separadamente existência/modos de `client0/cases` e `templates`; não inspecionar conteúdo.
3. **Somente com autorização específica posterior:** custódia de senha local, backup criptografado real e restauração isolada com integridade comprovada.

**F2 permanece aberta.** Esta evidência não autoriza publicar o site, contatar clientes, emitir documentos fiscais, fazer deploy ou declarar operações financeiras concluídas.
