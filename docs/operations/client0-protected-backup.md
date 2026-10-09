# WP-030 — Backup criptografado e restauração com Restic (ensaio real, dados fictícios)

**Status:** implementação remota de prova de funcionamento. Este pacote
executa **o binário real Restic** com um repositório descartável no
GitHub Actions, mas **não cria backup de nenhum dado do operador**,
não instala software no Ubuntu local e **não valida recuperação de
dados reais**.

## Por que Restic

Restic é gratuito, open source, multiplataforma e utiliza criptografia
autenticada internamente; suporta repositórios locais e remotos, além
de verificação de integridade e restauração. É mais adequado aqui do
que criar uma cifra, exportar ZIP em claro, acrescentar um ERP ou
instalar um sistema complexo de backup.

**Alternativas avaliadas:** BorgBackup é maduro e competitivo;
Kopia também possui backup criptografado. Para um índice documental
pequeno, a escolha de Restic reduz dependências e preserva a
possibilidade futura de destino local, mídia externa ou SFTP sem
reimplementar criptografia. Não é uma promessa de desempenho superior
em todos os cenários.

Referências oficiais:
- [Restic — apresentação](https://restic.net/).
- [Restic — criação de repositório e senhas](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html).
- [Restic — snapshots, check e restore](https://restic.readthedocs.io/en/stable/).
- [Restic — opções seguras de senha](https://restic.readthedocs.io/en/stable/faq.html).

## Prova funcional automatizada (sem acesso a casos reais)

`client0_workspace/restic_drill.py` só aceita:

```bash
python -m client0_workspace.restic_drill --synthetic-drill
```

A ferramenta cria exclusivamente arquivos artificiais numa pasta
temporária privada, gera uma senha aleatória **apenas para o ensaio**,
cria um repositório Restic local, executa backup, `check --read-data`,
nega uma senha diferente, restaura o snapshot em destino **novo** e
verifica as três cópias byte a byte, com permissão 0600.
Em seguida, elimina automaticamente o repositório e a senha do ensaio
pela limpeza do diretório temporário.

O workflow [restic-recovery.yml](../../.github/workflows/restic-recovery.yml)
instala o pacote oficial Ubuntu **somente no runner efêmero do GitHub**
(não no computador do responsável); executa o Restic real e valida:

```text
status=pass
snapshot_count=1
restored_files=3
restic_repo_checked_read_data=true
wrong_password_tested=true
isolated_restore_verified=true
synthetic_encrypted_repository_verified=true
temporary_secret_only=true
real_workspace_accessed=false
real_backup_restore_verified=false
offsite_backup_verified=false
production_backup_authorized=false
external_action_taken=false
```

**Nunca** são anexados artifacts de backup, nem arquivos em claro,
dados pessoais, chaves ou paths do operador. A saída do subprocesso
é capturada e descartada; erros usam códigos constantes.

Os testes anteriores [WP-028](client0-private-recovery.md) continuam
válidos, mas o ZIP plaintext daquele WP **não** pode ser reaproveitado
para dados reais.

## Procedimento futuro para dados reais — BLOQUEADO, NÃO EXECUTAR AGORA

Antes de configurar qualquer backup no Ubuntu, resolver com aprovação
humana específica:

1. **Fonte:** definir unicamente o índice privado realmente existente
   `~/.local/share/business-automation/client0/cases` e o modelo
   `.../templates`; verificar permissões/ownership e symlinks
   **sem ler ou exportar casos no chat**. Confirmar se o local contém
   apenas informações cuja coleta e retenção foram autorizadas.
2. **Destino independente:** identificar uma unidade física/mídia
   confiável **diferente do SSD principal**, confirmar montagem,
   proprietário, espaço livre e acesso. A pasta `/mnt/backup`
   pode existir, mas **o nome do mount não prova disco independente**.
   Repositório no mesmo SSD não protege contra falha do SSD.
3. **Chave:** senha longa e única, criada pelo responsável e guardada
   em gerenciador confiável **com recuperação fora da máquina**.
   Nunca salvar em Git, chat, variáveis inline de shell, log ou
   pasta incluída no backup. Sem senha, repositório pode ficar
   irrecuperável. Não criar automatização com senha embutida.
4. **Primeira inicialização:** após confirmação do destino e
   autorização expressa, instalar Restic de forma legítima, criar
   repositório criptografado e guardar seu identificador com cuidado.
   Não usar `--insecure-no-password`.
5. **Backup real:** executar manualmente só da allowlist privada,
   com conta sem privilégios excessivos. Não usar `--exclude` amplo
   que silencie erros, não apagar snapshots, não programar rotinas
   automáticas antes de verificar o primeiro restore.
6. **Prova de restauração:** restaurar em **destino privado inexistente
   e separado**; conferir arquivos e permissões sem imprimir seu
   conteúdo. Registrar `as_of`, identificador do snapshot,
   hash/resumo sanitizado, retenção e responsáveis. Não sobrescrever
   `cases/` ativo.
7. **Cópia recuperável:** preservar acesso à mídia, à senha e ao
   procedimento em caso de falha do Ubuntu, além de testar perda
   de um disco. Se houver apenas uma mídia adicional, reconhecer
   que ainda não há redundância off-site.
8. **Limpeza e exposição:** qualquer diretório com documentos
   restaurados em claro requer descarte/retensão autorizados,
   e backup antigo **não restaura consentimento revogado**.

**Não executar comandos que criam/apagam/alteram repositórios reais
sem autorização explícita do operador.** A execução prática será o
menor handoff local possível, nunca uma reconstrução do sistema.

## Orientação para a execução manual futura

Depois de aprovados fonte, destino e chave, o fluxo Restic corresponde
a estes comandos conceituais (substituir caminhos somente após validação):

```bash
# Exemplo genérico; NÃO EXECUTAR SEM DESTINO REAL APROVADO.
restic -r <repositorio_em_midia_independente> init
restic -r <repositorio_em_midia_independente> backup <pasta_privada_autorizada>
restic -r <repositorio_em_midia_independente> snapshots
restic -r <repositorio_em_midia_independente> check --read-data
restic -r <repositorio_em_midia_independente> restore <snapshot_id> \
  --target <diretorio_privado_novo_e_vazio>
```

O exemplo usa senha interativa e não pressupõe ferramenta instalada,
conta, CNPJ, senha, mídia ou permissão de acesso. No WP de operação
real, os caminhos e parâmetros deverão ser resolvidos em momento
posterior e conferidos individualmente antes da escrita.

## Impacto na preparação comercial

A documentação [D07](client0-launch-decisions.md) passa a recomendar
Restic **condicionalmente**, mas continua **PENDENTE** até existir
repositório real, destino independente, chave recuperável e restauração
isolada efetivamente comprovada.

A escolha de atuar inicialmente como pessoa física ou com empresa
é uma **decisão fiscal separada** (D01). Não colocar dados de CNPJ,
pendências pessoais, valores ou capturas do portal fiscal neste Git
público. Site/MXQ4K e prospecção continuam **sem autorização**.

**Critério F2 permanece invariável:** um ciclo comercial real,
documentado, com entrega, recebimento e revisão de resultado.
