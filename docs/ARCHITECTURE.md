# Arquitetura vigente

## Referência oficial

A [Architecture Baseline v1](architecture/baseline-v1.md) é a referência arquitetural oficial do `business-automation`, adotada em 2026-10-07 pelo WP-001. Este documento é o ponto de entrada para essa direção.

O cabeçalho de proposta da baseline registra seu estado na elaboração. A adoção está formalizada em [DECISIONS.md](DECISIONS.md); não significa que suas capacidades futuras estejam implementadas nem resolve decisões comerciais que continuam abertas. ERPNext passa de candidato a **back-office padrão inicial**, ainda sujeito à validação de implantação e dos contratos de integração.

## Direção vigente

- **Client 0 é a operação da própria empresa:** captar e qualificar oportunidades, vender, entregar projetos, cobrar, prestar suporte e medir resultados.
- **Monólito modular inicialmente:** preservar o core horizontal e evoluir em pacotes pequenos, sem microserviços ou infraestrutura especulativa.
- **Core:** CRM, qualificação, conversas, regras reutilizáveis, coordenação de automações, configuração por empresa e contratos de integração.
- **ERPNext:** back-office padrão inicial para funções maduras, como documentos comerciais, financeiro, cobrança e gestão convencional de projetos e suporte, conforme aderência validada. Evitar duplicação e definir um dono por dado.
- **Cobrança de serviços agora:** parte do ciclo operacional, podendo começar com processo humano no back-office. Billing de SaaS, assinaturas self-service e cobrança por uso ficam para depois.
- **Automações:** n8n ou Activepieces são motores auxiliares opcionais; regras de domínio ficam no core ou no sistema autoritativo explícito.
- **IA:** assistência com aprovação humana quando necessária, desacoplada de modelo/provider; indisponibilidade não deve impedir a operação manual.
- **Segurança e operação:** acesso controlado, integridade, backups e recuperação antes do uso operacional da API; autenticação, autorização e isolamento comprovados antes da exposição pública.

Company permanece a raiz lógica do tenant. Clientes que compram serviços da empresa são Customers do Client 0; uma venda não cria automaticamente outro tenant. Instalações segregadas do mesmo código são compatíveis com evitar forks por cliente.

A implementação atual permanece aproveitável. Esta adoção documental não instala ERP, cria integrações ou altera código, schema, migrations ou infraestrutura.

## Documentos de apoio

- [Baseline completa](architecture/baseline-v1.md): fronteiras, ownership, operação, riscos e dívida técnica.
- [Prioridades e roadmap detalhado](architecture/delivery-plan-v1.md): capacidades e gates de evolução.
- [Work packages](architecture/work-packages-v1.md): preparação de sessões autossuficientes para Pi/Qwen.
- [Roadmap vigente](ROADMAP.md): síntese de agora, preparação e adiamentos.
- [Decisões](DECISIONS.md): adoção e histórico de substituições.

## Histórico preservado

A reconciliação arquitetural de `17b1626`, presente em `main@84ea22e`, foi substituída por esta direção em 2026-10-07. Seu conteúdo original permanece no histórico Git.

Foram retiradas da direção vigente as premissas de laboratório local e bridges antigos existentes, a prioridade de inventariá-los e o benchmark permanente com Dolibarr. Nenhum desses componentes é pré-requisito para o trabalho atual. A separação entre core, ERP, automação e configuração privada foi mantida.

Referências anteriores em documentos ainda não reconciliados, inclusive `CLIENT0_FLOW.md`, não restabelecem essas premissas. Para direção arquitetural, prevalecem a baseline e as decisões de adoção registradas no WP-001.
