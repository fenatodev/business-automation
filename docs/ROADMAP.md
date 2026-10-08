# Roadmap

Direção vigente em 2026-10-07, conforme a [Architecture Baseline v1](architecture/baseline-v1.md), referência oficial adotada no WP-001. O [plano detalhado](architecture/delivery-plan-v1.md) descreve prioridades e gates; este documento resume a sequência. Não é compromisso de prazo nem autorização para implementar ou executar migrations.

## Necessário agora

- Definir uma oferta e um fluxo Client 0: oportunidade → qualificação → proposta e aprovação → projeto e entrega → cobrança → pós-venda e suporte.
- Tratar Client 0 como a operação da própria empresa, com responsáveis, evidências de aceite e próxima ação.
- Adotar ERPNext como back-office padrão inicial; validar sua aderência e definir ownership antes da integração. Aproveitar funções maduras em vez de reconstruí-las no core.
- Incluir cobrança de serviços, recebíveis e conciliação no processo operacional, inicialmente com participação humana e back-office. Não construir billing próprio para começar a vender.
- Consolidar testes, integridade e reprodutibilidade de migrations em tarefa própria, com PostgreSQL descartável e revisão obrigatória.
- Preparar identidade, autorização, isolamento, acesso privado, observabilidade mínima e backup/restore antes de dados operacionais na API. Exposição pública depende de segurança comprovada.
- Validar o ciclo comercial e de entrega manualmente enquanto a fundação técnica é preparada.

“Agora” inclui decisões e procedimentos humanos; não exige implementar todas essas capacidades no repositório de uma vez.

### Status atual da F1

Em 2026-10-08, a F1 está **concluída para o piloto privado Client 0**, com evidência nos WPs 004–008:

- migrations/recovery em PostgreSQL descartável;
- autenticação e isolamento por Company;
- backup/restore ensaiado;
- startup loopback-only, revogação por restart e logs mínimos sem segredos;
- lifecycle operacional de dados definido.

Essa conclusão não equivale a produção pública. Permanecem proibidos por padrão: exposição pública, ingestão em massa, portal externo e ampliação de dados sensíveis sem gate próprio.

O próximo avanço é F2: executar um ciclo Client 0 real e assistido, preservando fallback manual e as fontes de verdade definidas.

## Preparar agora, implementar conforme o fluxo exigir

- Um contrato de handoff ERP com campos, ownership, idempotência, falhas e reconciliação explícitos.
- Evolução mínima de CRM, captura e qualificação orientada ao trabalho do operador.
- Interface interna para próximas ações e pendências reais.
- IA desacoplada de provider e configuração por Company, depois da fundação de acesso e dados.
- Jobs duráveis apenas quando efeitos externos automáticos precisarem sobreviver a reinícios.
- Um canal e uma receita de automação por vez; n8n ou Activepieces somente como motor auxiliar quando justificado.
- Onboarding e operação dos primeiros clientes com o mesmo core, configuração e credenciais segregadas, sem forks.

## Adiado

- Billing de SaaS, assinaturas self-service, planos e cobrança por uso.
- Provisionamento e portal self-service, RAG e bases de conhecimento por empresa.
- Analytics avançado, campanhas e múltiplos canais sem demanda validada.
- Microserviços, Kubernetes e infraestrutura distribuída sem necessidade comprovada.

## Fases e critérios de avanço

| Fase | Resultado esperado | Gate de saída |
| --- | --- | --- |
| F0 — recorte | Oferta, fluxo Client 0 e ownership definidos | Responsáveis, exceções e critérios de aceite claros |
| F1 — fundação | **Concluída para piloto privado Client 0**: dados reproduzíveis, acesso seguro, recuperação e lifecycle | Testes, isolamento, restore, revogação e política de lifecycle demonstrados; sem autorização de exposição pública |
| F2 — operação assistida | Ciclo de oportunidade a recebimento e revisão de resultado | Fontes de verdade e evidências rastreáveis, com continuidade manual |
| F3 — automação útil | Automatizar um gargalo comprovado | Falhas, duplicação, timeout e reconciliação testados; benefício medido |
| F4 — primeiros clientes | Entrega repetível com o mesmo core | Sem fork, com isolamento, suporte e custo operacional conhecidos |
| F5 — produto | Empacotamento guiado por demanda real | Repetibilidade e sustentabilidade demonstradas; SaaS é opcional |

Executar [work packages pequenos e autossuficientes](architecture/work-packages-v1.md), um por sessão. A arquitetura completa orienta o destino; cada implementação deve resolver um recorte verificável.

## Histórico

Este roadmap substitui o NOW/NEXT/LATER anterior, preservado no histórico Git de `main@84ea22e`. A prioridade de segurança foi antecipada em relação à configuração de agente; o antigo adiamento genérico de billing foi substituído por cobrança operacional agora e billing de SaaS depois. As substituições estão registradas em [DECISIONS.md](DECISIONS.md).
