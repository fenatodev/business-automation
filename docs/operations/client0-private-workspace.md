# WP-027 — Client 0: preparo do índice privado (sem dados de clientes)

**Fase:** F2 / O02. Após o site WP-026, o gargalo é a continuidade
operacional **real**, não mais a geração de novas demonstrações.
**Este pacote cria apenas estrutura vazia e um modelo público**; não
declara backup, faturamento, proposta, implantação ERPNext ou F2 concluídos.

## Artefato funcional: `client0_workspace.workspace`

Comandos (somente quando houver necessidade no Ubuntu):

| Modo | Efeito | Gate |
| --- | --- | --- |
| `--synthetic-drill` | Cria e verifica um diretório **temporário sintético**; não lê `$HOME` real | CI GitHub automático |
| `--preflight` | Inspeciona **somente metadados** dos diretórios/arquivo previstos sob `~/.local/share/business-automation/client0/` | Read-only, pode retornar `missing` |
| `--bootstrap-empty` | Cria **somente** diretórios privados ausentes e copia o template **em branco**, sem sobrescrever nada | Execução local explícita, quando necessária |

### Layout seguro e separação de autoridade

```text
~/.local/share/business-automation/client0/
├── cases/               # 0700; neste WP NÃO são criados cases
└── templates/           # 0700
    └── case.md          # 0600; cópia em branco do modelo público
```

Não cria bancos, documentos, propostas, `Quotation`, clientes,
arquivos `proof-social.json`, recibos ou dados fiscais. Mesmo se
`cases/` já tiver conteúdo, os comandos **não o enumeram ou abrem**.

O arquivo `templates/case.md` é só um **formulário privado vazio**
vinculado ao [modelo público](templates/client0-case.template.md).
Um `case.md` preenchido futuramente deve existir somente numa pasta
de caso separada, mediante fluxo humano e política de retenção. O
template não constitui evidência de aceitação ou sistema financeiro.

O código usa descritores de diretório com `O_DIRECTORY|O_NOFOLLOW` e
checa owner e modos. Refusa symlinks, diretórios de negócio inseguros
ou arquivo preexistente com permissões erradas. **Não** corrige
permissões antigas silenciosamente, não apaga, não faz `chmod`
de diretórios existentes e não sobrescreve modelos existentes.
A pasta `cases/` deve permanecer em 0700; o template em 0600.
Uma futura evolução do modelo público **não** sobrescreve automaticamente
a cópia privada; a atualização requer revisão e migração explícitas.

Os caminhos usados são fixos e originam-se de `Path.home()`;
a ferramenta não aceita um parâmetro `--path` arbitrário. Testes
usam `tmp_path` e simulam `home` em local isolado.

## Validação no GitHub sem ligar DC

```bash
uv run pytest -q
.venv/bin/python -m compileall -q app tests examples marketing proof_social operations site_release client0_workspace
uv run python -m client0_workspace.workspace --synthetic-drill
```

A saída de sucesso `status=pass` confirma **apenas** que o bootstrap
de pastas e a integridade do template funcionam no teste sintético.
Os campos `backup_restore_verified=false`,
`external_action_taken=false` e
`backoffice_operational_verified=false` quando aplicáveis continuam
rejeitando qualquer interpretação de prontidão real.

### Handoff futuro mínimo para Continue — não rodar preventivamente

Somente depois de CI verde no `main`, usar no Ubuntu, se necessário:

```bash
# 1. Preflight sem escrever:
uv run python -m client0_workspace.workspace --preflight

# 2. Se o preflight retornar "missing" (exit 2), e somente após
# confirmar que a estrutura vazia ainda é desejada:
uv run python -m client0_workspace.workspace --bootstrap-empty

# 3. Repetir somente o preflight, sem mudar dados:
uv run python -m client0_workspace.workspace --preflight
```

O `uv run` deve ser executado em um checkout **limpo, de commit
conhecido**, nunca em diretório com alterações do usuário. Não repetir
bootstrap que falhou. Não compartilhar no chat a localização de dados
privados, listagem de cases, conteúdo da pasta, credenciais ou logs de
ambiente.

## Pendência fundamental: recuperação de documentos privados

**Este WP não faz backup ou restore.** Uma pasta `0700` não é backup.
Não coletar anexos contratuais sensíveis enquanto não existir estratégia
de cópia protegida, retenção, controle de acesso, chave/recuperação,
e **restore isolado demonstrado**. Também não confiar somente no
backup da base PostgreSQL: o índice `cases/` está **fora do banco**.
O [WP-028 — ensaio sintético de recuperação](client0-private-recovery.md)
define e testa cópia, integridade SHA-256 e restore **somente em ambiente
temporário com dados fictícios**. Não cria cópia operacional real nem
fornece criptografia; um backup protegido e o restore real ainda
exigem escolha de ferramenta madura, custódia de chaves e gate
operacional separado.

A escolha do back-office segue [procedimento G0–G10](client0-backoffice-operations.md):
ERPNext precisa de validação real, **ou** o operador deve formalizar
fallback manual com **documentos verdadeiros e autorizados**, nunca
usar o template como nota fiscal ou prova de recebimento.

## MXQ4K continua fora do escopo

O usuário informou que **já existe um cartão SD preparado com Armbian
para o MXQ4K**, mas ainda não foi demonstrado o boot, a arquitetura da
placa, o suporte do kernel, atualizações ou rede estável. A hospedagem
pública permanece adiada; o site [portátil WP-026](mxq4k-hosting-deferred.md)
não depende do hardware para ser desenvolvido.

Se futuramente escolhido, realizar primeiro inventário local **sem
flash, sudo, DNS, encaminhamento de portas ou exposição externa**;
a publicação exige gate humano específico.
