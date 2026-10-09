# WP-033 — ajuste mínimo de permissões, Restic oficial e conferência do destino

**Situação:** especificação operacional para o **Continue/Qwen3.5-9B**,
preparada no GitHub. **Nenhuma etapa local foi executada pelo GitHub.**
Uma autorização explícita do responsável cobre **apenas**: conferir e,
se seguro, corrigir o modo do **único diretório** identificado no WP-032;
instalar **somente Restic do repositório oficial do Ubuntu**; e confirmar
a topologia do volume montado de backup em modo read-only.

## Evidência de entrada — não reexecutar WP-031/032 por rotina

WP-032 foi executado uma vez em checkout validado, com stdout original:

- `kind=client0_ubuntu_blocker_diagnosis`, exit 0,
  `workspace_blocker.state=private_mode_mismatch`,
  `workspace_blocker.mode=0775`,
  `workspace_blocker.owned_by_current_user=true`.
- `backup_disk_topology.topology=different_block_disks`;
  **`physical_independence_verified=false`**.
- WP-031 já havia reportado `restic=false`.

**Premissas não autorizadas:** a topologia observada não confirma
fisicamente a independência; não assumir que ninguém usa a permissão
de grupo do diretório e não presumir que `client0/cases` existe.
Mesmo após este WP, **não haverá backup ou restore real**.

## Escopo local fechado

O Continue executa no Ubuntu **somente** estes três gates, nesta ordem:

### A. Verificações de segurança, integridade e armazenamento (somente leitura)

Trabalhar em **clone temporário novo** de
`https://github.com/fenatodev/business-automation.git`, branch `main`,
conferindo o **SHA completo enviado pelo ChatGPT** antes de executar.
Ler esta spec **daquele clone**, nunca de checkout antigo e nunca usar
o diretório de trabalho do usuário. `git clone` é a única escrita
permitida *antes* dos gates B e C.

Conferir por metadados, sem enumerar conteúdo privado:
- `$HOME/.local/share/business-automation` é **diretório real, não
  symlink**, propriedade do UID atual e modo `0775` ou já `0700`.
- Nenhum dos diretórios pais `$HOME`, `.local` e `.local/share`
  é symlink ou gravável por grupo/outros (fazer `lstat`).
- O diretório-alvo não é ponto de montagem e não tem ACL POSIX
  adicional: consultar `os.listxattr(..., follow_symlinks=False)`
  para `system.posix_acl_access` ou `system.posix_acl_default`.
  Falha na consulta de ACL => **STOP**.
- Confirmar **se serviços ou outras identidades dependem de acesso
  pelo grupo**. Inspecionar apenas metadados/configurações relevantes
  dos serviços próprios; **não abrir arquivos de cliente, secrets,
  `.env` nem registrar unit files integralmente**. Se a dependência
  não puder ser esclarecida, **STOP sem `chmod`**. Ausência de ACL
  **não** prova que não há serviço compartilhado.
- `/mnt/backup` é montagem real: `mountpoint -q /mnt/backup`,
  `findmnt --mountpoint /mnt/backup` e
  `lsblk -J -o NAME,TYPE,PKNAME,TRAN,SIZE,MOUNTPOINTS`. Conferir
  se o volume de HOME e o backup pertencem a árvores de dispositivos
  distintas; inspecionar se são realmente unidades físicas
  independentes e se a montagem não é rede/overlay/device mapper
  ambíguo. **Não imprimir nomes de dispositivos, serial, UUID,
  fonte de montagem ou logs integrais ao chat.** Sem confirmação
  física, reportar **`independencia_fisica=nao_comprovada`**,
  mesmo que `different_block_disks=true`.
- Falta de montagem / mesmo disco / erro inesperado => **STOP antes
  de alterar permissões e instalar**, informando bloqueio sanitizado.

**Não investigar indefinidamente.** Nenhuma busca genérica, varredura
recursiva ou comando para descobrir outros projetos.

### B. Corrigir exatamente UM diretório (permitido condicionalmente)

**Somente após A passar**, e somente se não houver uso compartilhado
identificado ou incerto, executar no terminal, com usuário atual e
sem `sudo`:

```bash
TARGET="$HOME/.local/share/business-automation"
test ! -L "$TARGET" &&
test -d "$TARGET" &&
test "$(stat -c %u -- "$TARGET")" = "$(id -u)" &&
case "$(stat -c %a -- "$TARGET")" in
  775) chmod 0700 -- "$TARGET" ;;
  700) : ;;
  *) echo "WP033_STOP_UNEXPECTED_MODE"; exit 2 ;;
esac
test "$(stat -c %a -- "$TARGET")" = "700"
```

**Pré-requisito:** a avaliação de tipo, dono, caminhos-pais,
mount e ACL do gate A foi concluída; o `chmod` acima **não revalida
ACLs nem protege contra alterações concorrentes**. Em caso de
mudanças concorrentes, STOP. Nunca executar `chmod -R`, `chown`,
`setfacl`, `sudo chmod`, ajustar outra pasta ou usar `umask` como
substituto. Não criar `client0`, casos ou templates.

Se o gate A detectar referência por serviço/grupo, **não executar
este bloco**, registrar `permissao=adiada_compartilhamento` e STOP.

### C. Instalar somente Restic oficial do Ubuntu e validar versão

**Somente após B confirmado (`0700`)**, conferir a origem do pacote
via `apt-cache policy restic` e a simulação
`apt-get -s install --no-install-recommends restic`.

- Se Restic já estiver instalado: usar `restic version` e
  `dpkg-query -W restic`. Não instalar novamente.
- Se ausente, aceitar **somente** pacote de repositório Ubuntu
  gerenciado pelo APT (mirror Ubuntu autorizado); recusar origem PPA,
  script `curl|bash`, binário avulso, versão sem candidato,
  downgrade, remoções, alterações inesperadas ou instalação de
  outras aplicações. Se os metadados APT estiverem desatualizados,
  **uma** execução de `sudo apt-get update` com os repositórios
  Ubuntu já existentes é permitida, sem adicionar repositórios;
  depois repetir `apt-cache policy` e a simulação **uma vez**.
- Se candidato e simulação forem adequados, comando de instalação
  autorizado:

```bash
sudo apt-get install --yes --no-install-recommends restic
restic version
dpkg-query -W -f='restic_version=${Version}\n' restic
```

A elevação por `sudo` é autorizada **exclusivamente para atualizar
índices APT oficiais, se necessário, e instalar o pacote Restic**.
Não pedir nem capturar senha sudo em chat ou arquivo. Se APT indicar
problema de assinatura, pacote não oficial, mudança inesperada,
prompt administrativo além da autenticação normal ou erro, **STOP**.
Não usar `apt upgrade`, `autoremove`, `dpkg --force`,
`add-apt-repository` nem baixar executáveis fora do APT.

A instalação do binário **não** autoriza `restic init`,
`restic backup`, `restic restore`, chave, timer, cron,
configuração de repositório ou qualquer escrita em `/mnt/backup`.

## Verificação final e STOP

Executar uma única vez o preflight **já versionado** no clone
temporário, sem o alterar:

```bash
python3 -B scripts/ubuntu_readonly_preflight.py --check
```

Estar no diretório raiz do clone verificado ao executar; se o
preflight indicar `missing` para `client0`, isso é esperado até
que o bootstrap vazio seja aprovado separadamente: **não criá-lo**.
O status `review_required` não certifica backup pronto. Se houver
`blocked` de uma etapa diferente, não tentar corrigir na mesma
sessão.

**Handoff literal (e somente estas informações):**

```text
WP033_LOCAL=PASS|PARTIAL|BLOCKED
main_sha=<sha completo>
filesystem=montado|nao_montado|indeterminado
discos_logicos=diferentes|mesmo|indeterminado
independencia_fisica=comprovada_pelo_operador|nao_comprovada
workspace_inicial=0775|0700|outro
workspace_final=0700|inalterado
restic=instalado:<versao>|ja_presente:<versao>|nao_instalado
wp031_final=review_required|blocked|nao_executado
real_backup=false
real_restore=false
dados_cliente_acessados=false
bloqueio=<codigo sanitizado ou nenhum>
```

Se `independencia_fisica=comprovada_pelo_operador`, descrever no
máximo `mídia separada fisicamente: sim` sem serial/dados pessoais.
**Não inferir fisicalidade de nomes `sda/sdb` ou de filesystem
diferente.**

**STOP ao concluir.** O Continue não deve iniciar WP-034 nem abrir
PR/push; GitHub entrega a spec, não é local de registro de dados
fiscais, credenciais ou backups. Não publicar, prospectar, faturar,
alterar Docker/PostgreSQL/ERPNext, acessar MXQ4K ou expor serviços.

## Critério de encerramento do WP

WP-033 valida só modo de uma pasta, disponibilidade Restic oficial e
evidência de armazenamento. Ainda ficam para outro gate:
custódia de chave, retenção, destino independente adequado e
**primeiro backup + restore real isolado** — aprovação humana distinta.
F2 segue aberta, e o site continua não publicado.
