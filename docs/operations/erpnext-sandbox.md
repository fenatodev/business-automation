# WP-015 — Sandbox descartável ERPNext para F2

**Status:** sandbox reproduzível, não back-office de produção.
**Natureza:** teste técnico local com dados exclusivamente sintéticos.
**Dependência:** WP-014 e [ADR 0001](../architecture/adr/0001-data-ownership.md).
**Não altera:** `docker-compose.yml`, PostgreSQL do BA, migrations, API, tokens, tenant ou arquivos privados existentes.

## Decisão técnica

Usar o **`pwd.yml` oficial do Frappe Docker somente como sandbox descartável**
de avaliação. A própria equipe do Frappe não recomenda esse arquivo para produção,
migração posterior ou desenvolvimento permanente.

O arquivo oficial contém credenciais de demonstração `admin` e publica HTTP em
todas as interfaces por padrão. **Não executar o `pwd.yml` sem endurecimento.**
O script deste WP:
- baixa **exatamente** `frappe/frappe_docker@5aa31a4aedf5caaf5abd46d94aada11e40d1709c/pwd.yml`;
- verifica SHA-256 antes de modificar;
- substitui as credenciais padrão por duas senhas fortes aleatórias geradas localmente;
- publica **somente** HTTP em `127.0.0.1:18080`, sem porta SQL exposta;
- mantém todos os containers e volumes no projeto Docker **`baerpnextwp015`**;
- cria `~/.local/share/business-automation/erpnext-sandbox` com modo `0700`,
  incluindo `.env` privado `0600`, não versionado;
- valida o Compose resolvido sem exibir senhas;
- exige **6 GiB disponíveis de RAM** e **12 GiB livres** antes de iniciar;
- permite **parar sem excluir volumes**, nunca executa `down -v`.

**Atenção:** senhas em environment de containers Docker são visíveis para
usuários com acesso privilegiado ao daemon. Esse é um laboratório estritamente
local e descartável, **não** a configuração de segurança para clientes reais.
Tags de imagens Docker estão fixadas por versão, mas não por digest OCI;
validar integridade de imagens será tarefa separada se o uso evoluir.

Documentação oficial: `https://github.com/frappe/frappe_docker` e
`https://frappe.github.io/frappe_docker/`.

## Comandos operacionais

No checkout **atualizado** do BA:

```bash
python3 scripts/erpnext_sandbox.py prepare
python3 scripts/erpnext_sandbox.py validate
python3 scripts/erpnext_sandbox.py start
python3 scripts/erpnext_sandbox.py status
python3 scripts/erpnext_sandbox.py smoke
python3 scripts/erpnext_sandbox.py stop
```

- `prepare`: requer acesso HTTPS ao GitHub; não inicia container; não sobrescreve
  sandbox preexistente. Se já estiver preparado, usar `validate`.
- `validate`: verifica projeto, imagens, porta exclusiva, senhas e estrutura.
  **Nunca executar `docker compose config` sem redigir saída:** o JSON interpolado
  inclui segredos.
- `start`: permite download de imagens e criação de **volumes do projeto sandbox**
  somente; não altera sistemas externos. O container `create-site` pode levar
  alguns minutos para concluir. Não confundir `up -d` com site pronto.
- `status`: mostra os processos desse projeto, incluindo `create-site` encerrado
  normalmente (`Exited (0)`) após a criação.
- `smoke`: HTTP `200` em `http://127.0.0.1:18080/login`. Confirma rota, **não**
  confirma que Customer/Quotation/Invoice foram usados.
- `stop`: para apenas o projeto do sandbox; preserva volumes. **Não** usar
  `docker compose down -v` sem revisar exatamente os recursos do projeto.

**Credenciais:** ficam somente no arquivo `.env` privado do sandbox. Não as
colar em chat, documentação, logs ou Git. O login local é `Administrator`.
Não reutilizar essas senhas em outros serviços.

## Separação obrigatória

| Domínio | Dados | Banco/serviço |
| --- | --- | --- |
| BA Client 0 | Opportunity, triagem, ProposalBrief | PostgreSQL persistente já existente (`127.0.0.1:55432`) |
| ERPNext *sandbox* | Empresa, Customer, Quotation, projeto e dados financeiros **fictícios** | MariaDB isolado no Compose `baerpnextwp015` |
| Operação comercial real | Documentos, preço e cobrança reais | Back-office a escolher/validar em gate futuro |

**Não** conectar o BA ao ERP sandbox nem publicar `18080`. Se a avaliação
justificar operação real, utilizar o método de implantação adequado, com
credenciais/backup/segurança/revisão independentes. O sandbox é descartável.

## Roteiro de verificação funcional posterior (somente dados falsos)

1. Confirmar versão do ERPNext e que `create-site` terminou com código zero.
2. Fazer login local, completar configuração mínima com empresa fictícia.
3. Verificar existência/semântica efetivas de `Customer`, `Quotation`,
   `Project`, `Sales Invoice` e `Payment Entry` na versão instalada.
4. Criar **apenas registros sintéticos**, sem emissão fiscal, email, gateway
   de pagamento, envio ou clientes reais.
5. Testar versão de proposta, rejeição, aceite simulado, pagamento parcial
   e reconciliação **como ensaio**, sem enviar efeitos externos.
6. Registrar identificadores falsos, comportamento, bloqueios e tempo de
   execução em relatório no Git **sem copiar dados/segredos do sandbox**.

**Gate para integrar:** somente após validação funcional de um fluxo e contrato
de handoff com identidade externa estável, idempotência, timeout `unknown`,
reconciliação e aprovação humana. **Não** criar adapter nem duplicar pipeline.

## Evidência esperada no WP-015

- Testes de transformação que recusam drift, exposição de portas e imagens
  inesperadas, sem depender de Docker ou rede.
- Validação de Compose e, se iniciado, rota HTTP local e log de conclusão de
  `create-site` (sem senhas).
- Testes normais do BA sem regressão.
- Nenhuma mudança no PostgreSQL, Docker Compose ou ambiente `.env` do BA.

**Gate F2 permanece aberto**: software sintético não substitui venda,
execução e recebimento real.
