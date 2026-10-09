# WP-028 — recuperação isolada do índice Client 0 (dados fictícios)

**Estado:** ensaio de backup/restore **somente sintético**; recuperação
protegida de dados reais **não está implementada nem autorizada**.

**Distinção obrigatória:** ZIP e SHA-256 servem para verificar integridade
de uma cópia de teste. **Não fornecem criptografia, autenticidade,
assinatura, proteção de acesso ou garantia de recuperação real.**
O pacote produzido neste WP é temporário, em claro e com dados fictícios
versionados; nunca deve ser levado para um sistema de backup real.

## Por que precisamos deste ensaio

O Client 0 tem dois estados de natureza diferente:

| Estado | Responsável/fonte | Recuperação |
| --- | --- | --- |
| API/CRM do BA e oportunidades privadas | PostgreSQL do core | Procedimento e teste descartável de [WP-006](../operations/client0-runbook.md); **não** recuperar banco real neste WP |
| Índice documental por serviço (`cases/`) e modelos (`templates/`) | Arquivos **privados**, fora do PostgreSQL | **WP-028** testa a restauração de uma estrutura artificial, sem ler `$HOME` real |
| Cotação, faturas e recebíveis | ERPNext validado ou fallback formal autorizado | Fonte externa própria; nenhum documento financeiro é gerado pelo ensaio |
| Evidências originais, anexos, identidade e contratos reais | Repositório privado autorizado conforme o caso | **Fora do WP-028**, requer política de acesso/retensão/recuperação por classe |

A existência de `cases/` não comprova backup. O ensaio valida que o
formato futuro consegue enumerar somente documentos permitidos,
detectar mudanças de bytes, recusar caminhos de fuga e reconstruir
a estrutura em **diretório novo, isolado e não privilegiado**.

## Comando CI (sem acesso ao operador)

```bash
uv run python -m client0_workspace.recovery --synthetic-drill
```

A ferramenta cria um diretório temporário do próprio runner, com:

```text
source/
  templates/case.md               # modelo público em branco
  cases/c0-2026-001/case.md        # nota inteiramente artificial
  cases/c0-2026-001/proof-social.json  # placeholder fictício
client0-synthetic-index.zip         # ZIP temporário NÃO criptografado
restored/                           # destino novo, sem substituição do source
```

Os diretórios exigem **0700**, arquivos **0600**. A criação recusa
arquivos desconhecidos, nomes fora do padrão, links simbólicos, tamanho
excessivo, caminhos `../`, membros compactados e conteúdo com SHA-256
divergente. A restauração **nunca usa `extractall()`** nem sobrescreve
destino existente. O ZIP e as cópias fictícias são eliminados pela
limpeza automática do diretório temporário.

A saída esperada contém:

```json
{
  "status": "pass",
  "source_classification": "synthetic_only",
  "snapshot_files": 3,
  "restored_files": 3,
  "integrity_sha256_verified": true,
  "restore_isolated": true,
  "archive_encrypted": false,
  "real_workspace_accessed": false,
  "real_backup_restore_verified": false,
  "production_backup_authorized": false,
  "external_action_taken": false
}
```

Não existe `--backup`, `--restore` ou opção `--source` no CLI.
**Não modificar o código para aceitar um diretório de clientes reais
ou usar o ZIP plaintext como um backup de produção.**

## Requisitos para backup real posterior (sem execução agora)

1. **Custódia e autorização:** definir quais diretórios privados serão
   protegidos, quem pode restaurar, classificação e retenção. Metadados
   `case.md` não devem conter o contrato ou credenciais completas.
2. **Criptografia autenticada:** escolher ferramenta madura, revisada
   (por exemplo `age` ou solução de backup como Restic), com chave de
   recuperação gerenciada **fora** do backup, Git e chat. Nunca
   implementar cifra caseira; SHA não substitui autenticação.
3. **Destino independente:** cópia protegida em mídia/ambiente diferente
   do SSD da operação, com política de retenção e restauração possível
   mesmo se o Ubuntu principal falhar; sem incluir anexos não
   autorizados e sem sincronizar dados reais no GitHub Actions.
4. **Teste obrigatório:** executar backup real sob autorização explícita
   e restaurar **em pasta isolada e vazia**, comparar conteúdo e
   metadados sem divulgar informação no terminal/chat, registrar
   evidência sanitizada e responsável. Nunca restaurar por cima do
   `cases/` ativo.
5. **Restauração e lifecycle:** confrontar eventos posteriores ao
   snapshot — exclusões, correções, revogações, consentimentos, pagamentos
   e retenção. Backup antigo **não reabre permissões**.
6. **Back-office separado:** recuperar referências privadas não valida
   ERPNext, documento fiscal, conciliação bancária, saldo de cliente,
   integração, envio ou aceite. Cada fonte tem seu próprio gate.
7. **Mídia de backup:** MXQ4K, mesmo com Armbian em SD preparado, **não**
   foi aprovado como destino de backup. Não compartilhar a unidade com
   hospedagem pública sem isolamento e análise adicionais.

**WP-030:** [Restic escolhido e ensaio criptografado validável no CI](client0-restic-recovery.md), com senha temporária e recuperação isolada de três arquivos inventados. **Isso ainda não cria repositório ou cópia real do usuário.** O próximo gate é escolher destino fisicamente independente, proteger a chave e realizar **backup real e restore local isolado com autorização específica**, antes de declarar `real_backup_restore_verified=true`. Até lá, não coletar contratos/anexos sensíveis por esse fluxo.

## Limitações declaradas

- A verificação de SHA-256 acusa corrupção acidental, mas uma pessoa
  mal-intencionada com acesso ao ZIP pode adulterar o arquivo e o
  manifest em conjunto.
- O WP-028 não prova integridade de backup criptografado; o WP-030 adiciona ensaio com o **Restic real**, mas não valida chave, mídia, restore ou capacidade de boot do MXQ4K na operação.
- ZIP temporário de teste é plaintext e **não** deve sair da pasta
  descartável; caso o processo falhe e a limpeza não ocorra, usar
  somente o ambiente CI descartável previsto.
- `restore_isolated=true` refere-se **só** ao ensaio com dados inventados.
  Os caminhos privados existentes nunca foram lidos ou alterados.

**Próxima etapa da F2:** fechar a continuidade operacional via
back-office efetivo e decisões comerciais humanas, não adiantar
prospecção/site público apenas porque o CI passou.
