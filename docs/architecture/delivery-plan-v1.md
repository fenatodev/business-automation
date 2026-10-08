# Architecture Baseline v1 — prioridades e roadmap

Data: 2026-10-07. Proposta, não compromisso de prazo nem autorização de implementação.
Referência: [baseline](baseline-v1.md). N = necessário agora para o ciclo inicial; P = contrato preparado, implementação posterior; A = adiado. “Agora” não significa implementar tudo antes de vender: procedimentos humanos e ERP podem suprir a operação.

## 1. Lista priorizada de capacidades

| Ordem | Capacidade | Horizonte | Menor entrega útil | O que evita construir |
| --- | --- | --- | --- | --- |
| 1 | Escolha da oferta e fluxo Client 0 | N | Uma oferta com entregáveis, aceite, responsável e processo de cobrança | Catálogo universal e decisão comercial inventada |
| 2 | Reprodutibilidade e integridade | N | Suíte atual preservada; plano e validação de migrations em PostgreSQL descartável | Deploy sobre schema desconhecido |
| 3 | Acesso e isolamento | N antes de dados operacionais na API | Identidade, contexto Company, matriz de ações, testes negativos e rede privada | Publicar CRUD sem autorização |
| 4 | Operação recuperável | N antes do piloto | Runbook, backup/restore, logs mínimos e responsável | “Produção” dependente da máquina de desenvolvimento |
| 5 | Catálogo e rotina comercial | N | Poucas ofertas versionadas e checklist de diagnóstico | CPQ, marketplace e preços gerados pela IA |
| 6 | Captação e qualificação | N manual/P conectores | Origem, triagem humana, deduplicação, próximo passo | Scraper generalista e scoring opaco |
| 7 | CRM orientado a trabalho | N rotina/P entidades | Oportunidades com responsável, próxima ação e motivo de perda | CRM completo antes do primeiro uso |
| 8 | Propostas e aprovações | N no processo/ERP | Documento versionado, revisão interna e evidência de aceite | Editor e assinatura eletrônica próprios |
| 9 | Financeiro e cobrança | N no ERP/processo | Recebíveis, vencimentos, confirmação e conciliação | Billing SaaS e ledger próprio |
| 10 | Execução e pós-venda | N no ERP/processo | Projeto, aceite, runbook, suporte e revisão de resultado | Outro gestor de tarefas ou helpdesk |
| 11 | Ownership e handoff ERP | N contrato/P código | Uma contraparte sincronizada com status, deduplicação e correção humana | Sincronização bidirecional geral |
| 12 | IA intercambiável | P; preservar atual N | Um port, adapter Ollama e fake; teste de falha | Framework de agentes e vários providers sem uso |
| 13 | Interface interna | P após escolher tarefas | Lista de próximas ações, timeline e pendências | Dashboard decorativo e frontend SaaS |
| 14 | Jobs duráveis e reconciliação | P antes de efeitos externos automáticos | Uma classe de job, um worker e fila de intervenção | Broker/cluster genérico |
| 15 | Configuração por empresa | P | Apenas configuração exigida pelo fluxo, versionada e validada | Linguagem de programação em JSON |
| 16 | Canal e automação repetível | P | Um conector e uma receita aprovados, pausáveis | Motor visual próprio; n8n e Activepieces simultâneos |
| 17 | Case e indicadores | N manual/P relatórios | Evidência de antes/depois e autorização de divulgação | Analytics sem resultado comercial |
| 18 | Onboarding externo repetível | P depois do Client 0 | Mesmo código, configuração segregada, teste de isolamento e restore | Fork por cliente |
| 19 | RAG, portal, self-service e planos | A | Somente após gatilho comercial e operacional mensurado | SaaS prematuro |

Prioridade é dependência/risco, não ordem serial absoluta. Oferta, rotina manual, documentação e diagnóstico podem avançar enquanto dados/segurança são preparados. Uso real da API e efeitos externos dependem dos respectivos gates.

## 2. Roadmap por gates

### F0 — baseline e recorte operacional

Entrega desta tarefa: análise local, baseline, prioridades, proposta de pacotes e reconciliação de documentação. Não inclui aprovação final de negócio.

Próximo trabalho: responsável escolhe uma oferta, fonte de oportunidade, roteiro de venda/entrega/cobrança, UI mínima e primeiro handoff. Registrar premissas, owner de cada dado e critérios de sucesso. Confrontar branches históricas sem importá-las.

Gate de saída: fluxo de uma página com responsáveis e exceções, matriz de ownership aprovada para esse recorte e nenhuma dependência de lab/bridge inexistente. Preço/SLA podem permanecer abertos enquanto a tarefa seguinte não depender deles. Nenhum conector externo é implementado com campos/gatilhos ainda indefinidos.

### F1 — fundação segura e reproduzível

Escopo: migrations/integridade em banco descartável; decisão de identidade; autorização/tenant nas rotas existentes; contratos de resposta/limites prioritários; observabilidade mínima, ambiente privado, runbooks e restore ensaiado. Não executar migration real sem tarefa explícita.

Gate de saída: testes normais e PostgreSQL separado passam; criação de banco vazio e upgrade de fixture sintética representativa demonstrados; tentativas cross-tenant negadas; acesso revogado funciona; backup restaurado em ambiente isolado; logs não expõem conteúdo/segredos; operador sabe parar envios e recuperar acesso.

Valor: permite pilotar dados reais em ambiente operacional controlado. Vendas e registro manual no ERP podem ocorrer fora da API durante preparação. Não há necessidade de todos os módulos futuros para sair dessa fase.

### F2 — primeiro ciclo Client 0 assistido

Escopo: captura/triagem manual, CRM mínimo, catálogo pequeno, proposta/aceite, projeto e cobrança no ERP/processo autoritativo, atendimento e revisão de resultado. Escolher apenas campos/consultas que o operador usa. IA é assistente opcional e pode permanecer desligada.

Gate de saída: um ciclo real rastreável de oportunidade a recebimento/resultado, sem dados reais no Git; venda perdida e proposta revisada também têm procedimento; oferta/aceite/recebível possuem fonte verificável; continuidade manual funciona. Métricas iniciais: tempo gasto, pontos de erro, próxima ação perdida, prazo de entrega e recebimento.

Não exigir integração completa para validar o negócio. O piloto ERP é trabalho separado, em instalação nova conhecida; documentos gerados manualmente podem ser vinculados por referência até o adapter estar pronto.

### F3 — automatizar o gargalo comprovado

Escopo candidato: um handoff ERP idempotente, status/reconciliação, worker mínimo se entrega automática for necessária, um adapter de canal ou uma receita de follow-up. Desacoplar IA e configurar por empresa apenas se ela participar desse fluxo.

Gate de saída: testes de indisponibilidade, timeout após efeito remoto, duplicação, evento fora de ordem, credencial revogada e restart; status desconhecido exige reconciliação; operador pausa/reprocessa com auditoria; efeito externo só ocorre uma vez dentro das garantias reais do provider ou fica pendente para resolução segura.

Valor: queda medida no esforço/erro em relação à F2. Se não houver benefício, manter processo simples e não ampliar a infraestrutura.

### F4 — primeiros clientes e serviço gerenciado repetível

Escopo: repetir oferta validada em outro cliente com o mesmo código. Preferir instalação/credenciais/backups segregados quando reduzir risco. Criar onboarding/offboarding, catálogo de configurações, suporte e custo operacional por implantação. Reconfirmar os casos externos antigos; não presumir contrato ativo.

Gate de saída: implantação repetida sem fork; dados/segredos isolados; permissões negativas testadas; exportação/encerramento e restore documentados; suporte e margem operacional sustentáveis; variações específicas ficam em configuração/adapters.

Portal de cliente e hosting compartilhado não são pré-condições. Se escolhidos, exigem revisão própria de segurança e carga antes do acesso externo.

### F5 — produto, apenas com evidência

Gatilhos: demanda repetida pela mesma capacidade, baixa necessidade de customização, onboarding previsível, custo de suporte conhecido e disposição real de pagar. Evidência de dois contextos distintos ajuda a testar reutilização, mas não é sozinha validação de mercado.

Opções: pacote de implantação, templates suportados, módulo licenciado ou serviço gerenciado antes de SaaS self-service. Decidir modelo comercial separadamente. Só então considerar planos, assinatura/usage billing, portal, provisioning automático e maior isolamento em instalação compartilhada.

Microserviços exigiriam gargalo mensurado ou autonomia operacional real de equipes/componentes. Kubernetes/multi-região não são fase automática desta evolução.

## 3. Documentos auxiliares recomendados

Criar documentos quando sua decisão/fluxo entrar na fase, não uma biblioteca de specs vazias. Todos devem declarar status, owner, data, versão/commit de referência e decisão que substituem.

| Documento sugerido | Quando | Conteúdo mínimo e finalidade |
| --- | --- | --- |
| `docs/CLIENT0_FLOW.md` revisado | F0 | Uma oferta/fonte, passos, responsáveis, falhas, manual fallback, campos e aceite do primeiro handoff |
| `docs/architecture/adr/0001-data-ownership.md` | F0 | Matriz por campo, Company versus entidade ERP, direção de sincronização e resolução de conflitos |
| `docs/architecture/adr/0002-migration-recovery.md` | F1 | Estado histórico, estratégia de banco vazio/existente e validação descartável; sem aplicar em produção |
| `docs/architecture/adr/0003-access-and-tenancy.md` | F1 | Mecanismo de identidade, papéis/ações, seleção de tenant, revogação e testes de ameaça |
| `docs/operations/client0-runbook.md` | F1 | Startup privado, saúde, parar jobs, incidentes, backup/restore, rollback, owner e evidências; segredos fora |
| `docs/contracts/erp-party-v1.md` | Antes do adapter F3 | Um comando, payload sintético, campos obrigatórios, mapping externo, erros e reconciliação |
| `docs/contracts/ai-generation-v1.md` | Quando desacoplar IA | Entrada/saída, limites, privacidade, falhas e avaliação; sem acoplamento ao agente de programação |
| `docs/operations/data-lifecycle.md` | Antes de dados reais | Classificação, acesso, retenção aprovada, exportação/exclusão, backups e relação com ERP |
| Catálogo operacional privado + template público sintético | F0/F2 | Oferta, preço aprovado, escopo, aceite, suporte e versão; dados privados não entram no repo |
| `docs/operations/client-onboarding.md` | F4 | Checklist de configuração, credenciais, acesso, restore, treinamento, suporte e encerramento |

Não criar ADR para toda função. `docs/DECISIONS.md` deve ser índice das decisões vigentes e substituídas; a baseline é visão transversal. Specs executáveis copiam apenas contratos pertinentes desses documentos, evitando obrigar Pi/Qwen a reconstruir contexto.

## 4. Medição e responsabilidades

No Client 0, uma pessoa pode exercer comercial, operação, técnico e financeiro. Mesmo assim, cada etapa identifica qual papel decide. Aprovação de preço não se confunde com execução técnica e confirmação financeira não vem do modelo de IA.

Revisar prioridades ao final de cada ciclo entregue: receita/recebimento, esforço de entrega/suporte, incidência de falhas, tempo parado e capacidade reaproveitada. Não estabelecer metas numéricas sem baseline real. Uma capacidade nova precisa reduzir risco obrigatório ou resolver gargalo demonstrado; “pode ser útil depois” não é critério suficiente.
