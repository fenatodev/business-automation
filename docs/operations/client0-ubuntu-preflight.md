# WP-031 — primeiro inventário do Ubuntu para decidir backup real

**Estado:** GitHub prepara e testa o inventário; **nenhuma coleta local
executada ainda**. Esse preflight não ativa backup, não instala Restic,
não modifica serviços e não acessa o MXQ4K.

## Estado real do projeto

A suíte Github Actions validou em WPs anteriores o core privado,
o site estático e um ensaio de recuperação Restic **com três arquivos
fictícios**. O próximo problema é verificar condições reais do Ubuntu
**sem inferir** a partir da preparação sintética:

- Existência e permissões do índice privado: ausente/seguro/bloqueado;
  **não ler os arquivos de caso ou contatos**.
- Presença do executável Restic, Git, uv e OpenCode; **não instalar**.
- Existência de `/mnt/backup`, se há **montagem efetiva** ali e
  se seu filesystem difere do diretório pessoal; não listar mídia,
  não acessar conteúdo, não testar escrita.
- **Independência física nunca é afirmada:** mount e filesystem
  diferentes podem usar o mesmo disco, VM, bridge ou volume remoto.

O diagnóstico é apenas metadata-only com Python stdlib:

```bash
python3 -B scripts/ubuntu_readonly_preflight.py --check
```

A execução retorna um JSON com `kind=client0_ubuntu_readonly_preflight`,
`status=review_required|blocked`, estados de metadados de cada
componente, `tools_available` e `backup_storage`. Nunca contém
conteúdo de contratos, nomes de clientes, caminhos dinâmicos de casos,
fontes de montagem, CNPJ, credenciais, hashes de arquivos privados ou
senhas.

**status=review_required NÃO significa produção pronta.** Se tudo
estiver `safe`, ainda faltam mídia fisicamente independente,
custódia de senha, backup criptografado real, restore isolado real,
retention e procedimento de recuperação do PostgreSQL.

**status=blocked** impede iniciar backup real até revisão humana do
motivo (symlink, permissão/owner inadequados). Não corrigir
automaticamente nem rodar `chmod -R`.

## Uso com OpenCode após CI verde

O executor deve seguir literalmente
[`specs/wp-031-ubuntu-operational-preflight.md`](../../specs/wp-031-ubuntu-operational-preflight.md)
e usar **clone GitHub em diretório temporário**, nunca a árvore de trabalho
local do projeto. Executar **somente** o script com `--check`;
não fazer `uv run` e não invocar comandos de backup.

A escolha de **OpenCode** substitui o executor mencionado em
documentações antigas do projeto para este handoff; não alterar
configuração de agentes nem runtime como consequência disso.

O relatório pode informar flags de hardware e filesystem, mas
**não identifica modelo do MXQ4K ou compatibilidade Armbian**.
As verificações do TV Box continuam reservadas para etapa posterior,
após fechar o backup e aprovar a publicação.

## Ordem seguinte, somente após resultado local

1. Se estrutura privada não existir ou estiver insegura, analisar
   o motivo e decidir ação mínima com autorização — sem alterar
   arquivos reais por surpresa.
2. Se o Restic faltar, preparar eventual instalação aprovada
   (nenhum `sudo` neste WP).
3. Se `/mnt/backup` não for uma mídia independente validada, confirmar
   dispositivo e capacidade em passo distinto; **não presumir**.
4. Preparar **um** ensaio real de backup/restore protegido com senha
   custodiada localmente e destino explicitamente selecionado,
   sem colocar dados/segredos no Git.
5. Depois reavaliar fiscal/preços/contratos, ativação Armbian no MXQ4K
   e publicação do site com aprovação, antes de contato comercial.

**O inventário não encerra F2 nem autoriza prospecção, deploy,
pagamento, emissão fiscal ou operação de dados de clientes.**
