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

A [Architecture Baseline v1](docs/architecture/baseline-v1.md) é a referência arquitetural oficial, adotada pelo WP-001 em 2026-10-07. A adoção e as decisões substituídas estão registradas em [Decisões](docs/DECISIONS.md). Capacidades planejadas não devem ser confundidas com funcionalidades implementadas.

## Relação com ERP e automação

O produto não pretende reimplementar um ERP completo.

Para o dogfooding inicial:

- **ERPNext** é o back-office padrão inicial, com implantação e integração ainda a validar;
- **n8n ou Activepieces** podem ser usados como motor auxiliar de integração e automação, sem virar o domínio central;
- este repositório concentra o core reutilizável de CRM, IA, automações e adapters.

Propostas formais, financeiro, cobrança e gestão convencional de projetos e suporte devem aproveitar o ERP quando apropriado, com ownership explícito dos dados. Não há dependência de ambientes ou integrações antigos.

**Cobrança de serviços faz parte da operação atual do Client 0**, inicialmente por processo humano e back-office. Billing de SaaS, assinaturas self-service e cobrança por uso ficam para depois, mediante demanda comprovada. Isso não implica implementar um financeiro próprio.

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
- a integração atual com Ollama deve ser revisada antes de ser tratada como runtime definitivo;
- ERPNext e motores de automação ainda não estão integrados à API.

## Direção imediata

A prioridade é validar a operação real da própria empresa sem transformar o core em um ERP monolítico:

1. definir uma oferta e o fluxo de oportunidade → proposta → entrega → cobrança → pós-venda;
2. consolidar dados, testes, acesso seguro e recuperação antes do uso operacional da API;
3. estabelecer ownership entre core e ERPNext;
4. validar o ciclo Client 0 com participação humana;
5. automatizar o gargalo demonstrado e medir o que é reutilizável;
6. atender primeiros clientes com o mesmo core; considerar SaaS somente quando justificado.

A arquitetura inicial é um monólito modular, com IA desacoplada de provider e implementação em pacotes pequenos. Client 0 é a operação da própria empresa, incluindo venda, execução, cobrança e suporte.

Consulte também:

- [Produto](docs/PRODUCT.md)
- [Roadmap](docs/ROADMAP.md)
- [Decisões](docs/DECISIONS.md)
- [Arquitetura vigente](docs/ARCHITECTURE.md)
- [Architecture Baseline v1](docs/architecture/baseline-v1.md)

## Desenvolvimento

Regras operacionais e validações do repositório estão em [AGENTS.md](AGENTS.md).
