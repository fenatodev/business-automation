# business-automation

Plataforma reutilizável de automação de negócios, CRM e IA.

O projeto tem dois objetivos complementares:

1. estruturar e automatizar a operação da própria empresa como **Client 0**;
2. transformar as capacidades validadas em serviços, integrações e produtos de automação reutilizáveis para outros clientes.

## Papel do repositório

Este é o **repositório canônico do produto**. O core deve permanecer horizontal e configurável por empresa, evitando forks por cliente ou regras específicas de nicho.

O código atual contém uma API FastAPI com entidades e fluxos básicos para:

- Company;
- Lead;
- Customer;
- Conversation;
- Message;
- integração de agente local.

A implementação existente é uma base de produto, não um contrato definitivo de arquitetura.

## Relação com ERP e automação

O produto não pretende reimplementar um ERP completo.

Para o dogfooding inicial:

- **ERPNext** é o principal sistema de back-office/ERP a integrar e validar;
- **Dolibarr** permanece como alternativa de laboratório/benchmark;
- **n8n** pode ser usado como motor auxiliar de integração e automação, sem virar o domínio central;
- este repositório concentra o core reutilizável de CRM, IA, automações e adapters.

O laboratório local de ERP e scripts é tratado como ambiente experimental. Componentes comprovadamente úteis podem ser promovidos para este repositório de forma explícita e revisada.

## Segurança e dados

Este repositório é público. Portanto:

- não armazenar dados reais de clientes;
- não versionar `.env`, credenciais, tokens ou chaves;
- não tratar `company_id` enviado pelo cliente como autorização;
- autenticação, RBAC e isolamento real de tenant são obrigatórios antes de exposição pública;
- configurações operacionais privadas devem ficar fora do core público.

## Estado atual

A base existente é aproveitável, mas ainda possui dívida técnica conhecida:

- cadeia de migrations precisa ser validada desde banco vazio;
- autenticação/RBAC ainda não estão implementados;
- isolamento multi-tenant ainda não é uma fronteira de segurança;
- a integração antiga com Ollama deve ser revisada antes de ser tratada como runtime definitivo;
- o README anterior estava vazio e a organização do produto ainda não distinguia claramente core, adapters e laboratório.

## Direção imediata

A prioridade é validar a operação real da própria empresa sem transformar o core em um ERP monolítico:

1. consolidar e testar a base atual;
2. mapear o fluxo operacional da empresa;
3. definir a fronteira entre core próprio e ERPNext;
4. integrar o primeiro fluxo real ponta a ponta;
5. medir o que é reutilizável;
6. só então promover novas automações para produto.

Consulte também:

- [Produto](docs/PRODUCT.md)
- [Roadmap](docs/ROADMAP.md)
- [Decisões](docs/DECISIONS.md)
- [Arquitetura e reconciliação](docs/ARCHITECTURE.md)

## Desenvolvimento

Regras operacionais e validações do repositório estão em [AGENTS.md](AGENTS.md).
