# Client 0 — WP-030: backup criptografado com Restic, preparado para validação local

**Estado:** escolha técnica e recuperação criptografada **validadas somente
em ambiente sintético no GitHub Actions**. Backup real do usuário,
restauração real, chave de recuperação, destino independente e
agendamento **não executados ou aprovados**.

## Decisão: não desenvolver criptografia ou outro motor de backup

Adotar **Restic** (open source, repositório criptografado e snapshots
deduplicados) para o **índice documental privado Client 0**. Não criar
criptografia própria, ZIP em claro de produção, adapter de nuvem,
cron, systemd timer ou integração com o MXQ4K neste WP.

O piloto anterior WP-028 validou um ZIP temporário **sem criptografia**;
o WP-030 usa o **binário Restic real**, gerando um repositório
criptografado com senha aleatória fictícia, salvando três arquivos
sintéticos, validando `restic check --read-data`, rejeitando senha
incorreta, restaurando em pasta isolada e comparando bytes/permissões.
Tudo ocorre em diretório temporário descartável, sem acessar o
`$HOME` real, rede, dados de cliente ou dispositivos de backup.

O GitHub Actions roda:

```bash
uv run python -m client0_workspace.restic_drill --synthetic-drill
```

Esse comando **não aceita** opções `--backup`, `--restore`,
`--source`, `--repository`, `--apply` ou caminho arbitrário de
operador. Ele é um teste de integração com Restic, **não é a interface
para fazer backup de produção**. O CI instala/restaura o binário Restic
**no runner GitHub**, não no computador do usuário.

### Evidência produzida sem dados privados

```json
{
  "kind": "client0_restic_encrypted_recovery_drill",
  "status": "pass",
  "backup_engine": "restic",
  "synthetic_file_count": 3,
  "verified_file_count": 3,
  "repository_check_read_data": true,
  "wrong_password_rejected": true,
  "restore_byte_exact": true,
  "restore_isolated": true,
  "repository_encrypted_by_restic": true,
  "real_workspace_accessed": false,
  "real_backup_restore_verified": false,
  "production_repository_created": false,
  "key_recovery_proven": false,
  "external_action_taken": false,
  "publication_authorized": false
}
```

**Os flags não são afirmações de segurança absoluta.** A confiança no
código criptográfico depende da segurança e versão do Restic; o teste
simples verifica somente funcionalidades de backup e recuperação no
runner. A senha é descartável, gerada dentro do CI e **nunca exibida**.
Nenhum repositório de backup ou chave é salvo como artifact.

## Próximo gate LOCAL obrigatório — ainda NÃO EXECUTAR

Antes de qualquer uso com dados reais, o operador precisa:

1. **Escolher destino independente e confirmar o dispositivo:** SSD,
   HD externo ou outro armazenamento sob controle legítimo. Um caminho
   como `/mnt/backup` **não prova** independência física; verificar
   efetivamente volume, montagem, capacidade e acesso. Não usar MXQ4K
   público como armazenamento de documentos privados.
2. **Delimitar exatamente o escopo:** inicialmente só
   `~/.local/share/business-automation/client0/cases/` e
   `templates/`, **não** todo o `client0/`, que poderá conter
   rascunhos privados de marketing, dados externos e futuras
   credenciais. Confirmar que ambos existem, que não são symlinks, que
   têm modo `0700` e que cada arquivo incluído pode estar no backup.
   Nenhum anexo não autorizado deve ser incorporado implicitamente.
3. **Definir custódia da senha:** chave longa **gerada localmente**,
   armazenada em arquivo privado `0600` **fora da pasta de origem
   e fora do repositório de backup**, com segunda cópia segura e
   recuperação controlada. Não digitar senha em comando, chat, Git,
   URL ou variável que termine em log. Se perder a senha, os dados
   Restic podem ficar irrecuperáveis.
4. **Executar backup e restore de ensaio local:** com aprovação
   específica para acessar os dois diretórios e gravar no destino,
   inicializar repositório Restic, capturar snapshot, verificar
   `check --read-data`, restaurar **em diretório novo externo ao
   índice ativo**, comparar conteúdo e permissões localmente **sem
   emitir os dados no chat**. Em caso de falha, STOP; jamais restaurar
   por cima da pasta operacional nem executar `forget/prune`.
5. **Validar política operacional:** agendamento, retenção,
   armazenamento externo, verificação periódica e segundo dispositivo
   são decisões separadas após prova da primeira recuperação.
   A rotina só é considerada confiável após **restauração periódica**,
   e o controle de chaves deverá ser testado separadamente.
6. **Recuperação PostgreSQL e back-office:** precisam de
   rotinas/evidências **distintas**. Restic do índice não é backup
   consistente do PostgreSQL ou do ERPNext, e não comprova emissão
   fiscal, faturamento ou pagamentos.

### Sequência técnica de referência — não executar em produção sem gate

Em local **aprovado** e com Restic instalado:
- `restic --repo <DESTINO-INDEPENDENTE> --password-file <CHAVE-0600> init`
  cria o repositório uma única vez; **não repetir init** se existir.
- `restic --repo <DESTINO-INDEPENDENTE> --password-file <CHAVE-0600> backup
  --one-file-system <ORIGEM-CASES> <ORIGEM-TEMPLATES>` salva só os
  dois caminhos revisados.
- `restic --repo <DESTINO-INDEPENDENTE> --password-file <CHAVE-0600>
  check --read-data` verifica todos os blobs do repositório.
- `restic --repo <DESTINO-INDEPENDENTE> --password-file <CHAVE-0600>
  snapshots` consulta as revisões.
- `restic --repo <DESTINO-INDEPENDENTE> --password-file <CHAVE-0600>
  restore <ID-CONFERIDO> --target <DIRETORIO-NOVO-ISOLADO>`
  **restaura caminhos absolutos abaixo de target**. Verificar em
  `target/<caminho absoluto sem barra inicial>/...`, não supor
  `target/cases/`. Os caminhos apresentados no output do Restic
  podem revelar detalhes privados: não colar logs integrais no chat.

**Não tornar esses comandos automáticos ainda.** Evitar colar caminhos
reais e identificadores privados em documentação pública. Gerar ficha
local curta com `--preflight` e evidência sanitizada **depois** de
autorização e identificação efetiva do dispositivo.

## Decisão de produto

Com Restic pronto para execução operacional controlada, **não precisamos
de mais um módulo** de backup. O próximo avanço real é acertar os gates
comerciais pendentes, validar destino/restore no Ubuntu e concluir a
hospedagem do site no MXQ4K **somente após checar o Armbian**.
Prospeção, deploy e exposição da API continuam sem autorização.

Referências oficiais:
- [Restic: inicialização e senha do repositório](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html).
- [Restic: backup e sistemas de arquivos](https://restic.readthedocs.io/en/stable/040_backup.html).
- [Restic: verificação de integridade (`--read-data`)](https://restic.readthedocs.io/en/stable/045_working_with_repos.html).
- [Restic: restore em destino isolado](https://restic.readthedocs.io/en/stable/050_restore.html).

## Atualização operacional — WP-034 (2026-10-09)

O inventário WP-033 posterior confirmou Restic **instalado localmente**
(0.16.4) e um HDD SATA de destino separado do SSD do Ubuntu, montado
como **NTFS3**. A inspeção read-only adicional confirmou que o destino
proposto para novo repositório ainda **não existe** e que o índice privado
tem a estrutura básica e os modos esperados.

O [WP-034 — gates de backup e recuperação reais](../../specs/wp-034-restic-ntfs-recovery-gates.md)
define o teste sintético **na mídia NTFS3**, a custódia de senha com
cópia fora do host e a prova de restauração do índice real em destino
isolado. Essas operações **ainda não foram executadas**: nenhuma escrita
no HDD, geração de chave ou acesso ao conteúdo privado foi autorizada
por esta atualização documental. Se o teste NTFS3 falhar, considerar
outra mídia/filesystem sem formatar ou reparticionar o disco existente.

A separação de discos reduz o risco de falha isolada do SSD, mas **não**
substitui backup off-site/desconectado. O gate de recuperação do
PostgreSQL/ERPNext permanece independente.