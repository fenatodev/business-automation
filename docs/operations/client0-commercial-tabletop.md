# WP-014 — Ensaio de mesa do ciclo comercial Client 0

**Status:** simulação documental, **não** operação ou validação comercial real.  
**Data:** 2026-10-08.  
**Base:** WP-013, `docs/operations/client0-synthetic-pilot.md`.  
**Escopo:** prosseguir da revisão de `ProposalBrief` até entrega, recebimento e pós-venda,
**sem criar entidades, endpoints, preços, documentos ERP ou efeitos externos**.

## 1. O que já existe e o que não existe

O core atualmente consegue registrar `Opportunity`, triagem e `ProposalBrief`
com status `draft` / `ready_for_review`. `ready_for_review` **não** é
aprovação nem emissão de proposta. Os passos seguintes ainda pertencem ao
**processo humano e ao back-office**; este ensaio não os apresenta como API pronta.

Autoridades: [ADR 0001](../architecture/adr/0001-data-ownership.md) e
[fluxo comercial](../CLIENT0_FLOW.md).

- **Core BA:** origem, qualificação, diagnóstico, próximo passo e oferta técnica.
- **ERPNext/back-office:** contraparte, proposta formal e preço, condições,
  projeto convencional, documento financeiro e recebimento.
- **Humano:** escopo, preço, envio, aceite, exceções e divulgação.
- **IA:** sugestões e rascunhos sem poderes de aprovação ou autorização.
- **Limite atual:** instalação, configuração e aderência do ERPNext **não foram
  validadas por este WP**; o fallback é controle manual privado, não um ERP fictício.

`Company` representa o **tenant** do BA; não representa a contraparte
comercial/fiscal que será cadastrada no back-office.

## 2. Cenário A: continuidade **hipotética** da oportunidade do WP-013

Anúncio, empresa, contraparte e documentos abaixo são **inteiramente fictícios**.
Referências `SYN-*` servem **somente** para correlação neste ensaio; não
são IDs de banco nem comprovação de atividade financeira.

- Oportunidade fictícia: integração unidirecional de pedidos de loja com CRM.
- Decisão prévia simulada: `prepare_proposal`.
- Brief sintético: integração de API, deduplicação, trilha de falhas, testes e
  homologação; `ready_for_review` no WP-013.
- Aspectos desconhecidos: acesso à API, volume, regras de negócio, dados fiscais,
  identidade do cliente, orçamento, preço, impostos, condições e SLA.
- **Proibido inferir:** cliente contratado, preço viável, proposta aprovada,
  aceite do cliente, entrega, faturamento, pagamento ou resultado comprovado.

### Roteiro de ensaio (cada `simulado` é uma condição, não um fato)

| Gate / etapa | Pré-condição verificável em operação real | Autoridade e saída | Evidência que o operador teria de guardar |
| --- | --- | --- | --- |
| G1. Revisão técnica | Brief versionado, dúvidas de API e escopo resolvidas | Humano decide corrigir, reprovar ou liberar elaboração formal | Decisão, ator, horário, versão do brief, pendências |
| G2. Contraparte no back-office | Necessidade formal confirmada e identidade fiscal validada | Back-office cria/assegura contraparte; BA guarda apenas referência | ID estável externo; sem dedupe por nome ou email |
| G3. Proposta formal | Escopo G1 liberado e preço, tributos, prazo e condições definidos por responsáveis | ERPNext/back-office produz versão formal | ID+versão, referência do brief, condições aprovadas |
| G4. Aprovação e envio | Versão exata de G3, escopo e preço aprovados por humano | Comercial autorizado envia **somente** versão aprovada | Quem/quando aprovou; referência imutável; registro de envio |
| G5. Aceite do cliente | Envio comprovado; aceite correspondente à versão vigente | Humano interpreta o aceite; só então inicia entrega | Evidência de aceite, data, versão e exceções |
| G6. Execução | Aceite G5, plano de trabalho e acessos legítimos | Responsável executa; back-office acompanha projeto | Critérios de aceite, testes, changelog, incidentes |
| G7. Aceite técnico | Entregáveis e critérios conferidos pelo cliente | Humano registra aceite, rejeição ou retrabalho | Quem validou, quando, quais entregáveis e pendências |
| G8. Cobrança | Condição contratual de cobrança atingida (entrada/marco/pós-entrega) | Financeiro/back-office emite recebível conforme acordo | ID e versão do documento, vencimento, gatilho e status |
| G9. Recebimento | Referência e baixa/conciliacão no sistema financeiro autoritativo | Financeiro confirma pago, parcial, vencido ou desconhecido | ID do recebível, conciliação e data; não inferir de mensagem |
| G10. Pós-venda e case | Suporte conforme acordo; resultados medidos e autorização explícita | Suporte atende; humano aprova eventual divulgação | Chamados, medição antes/depois, autorização de divulgação |

**Execução de mesa:** considerar **condicionalmente** que G1–G10 poderiam
progredir **se** as pré-condições e evidências fossem obtidas. No WP-014,
nenhuma foi obtida de cliente real e **nenhum estado comercial foi
persistido**. Não preencher o campo de aprovação ou pagamento como `realizado`
em controles operacionais com base neste exercício.

A cobrança **não depende necessariamente do aceite técnico**: o seu gatilho
é o acordo aprovado (entrada, marco, recorrência ou após entrega). Suporte
também não depende necessariamente de pagamento integral.

## 3. Exceções exercitadas em mesa

| Caso de ensaio | Condição | Resposta segura / gate de saída |
| --- | --- | --- |
| E1. Proposta rejeitada | Escopo, preço ou condições rejeitados internamente | **Não enviar**; voltar a G1/G3, versionar nova proposta; aprovação anterior não se transfere |
| E2. Cliente solicita mudança | Aceite referente a outra versão ou escopo novo | **Não assumir aceite da versão nova**; reavaliar impacto e obter nova aprovação |
| E3. Entrega não aceita | Critérios G7 falham ou há defeito | Registrar não conformidades, corrigir e repetir aceite; não declarar projeto concluído |
| E4. Pagamento parcial | Recebível emitido e baixa parcial no financeiro | Registrar **parcial** no back-office, saldo pendente e próxima ação; não marcar como quitado |
| E5. Timeout no handoff futuro | Criação de contraparte/documento pode ter ocorrido, mas retorno falhou | Marcar situação **desconhecida**, consultar destino e reconciliar; **não repetir criação cegamente** |
| E6. Dados conflitantes | Dado fiscal ERP diverge do core | ERP vence no fiscal; divergência de contato é escalada, sem sobrescrever silenciosamente |
| E7. Falta de consentimento | Pedido para divulgar case com marca ou dados privados | **Não publicar** até haver autorização explícita para conteúdo/versão específicos |
| E8. Cliente desaparece | Proposta não respondida | Acompanhar manualmente; não declarar ganho, perda ou aceite por inferência |

Nenhuma dessas transições é implementada no BA por este documento. Elas
definem comportamentos esperados para operação humana e futuros adapters
**somente se** houver motivo para automatizá-las.

## 4. Registro mínimo para um ciclo **real** (privado, fora do Git)

Manter **um único índice privado** por trabalho, protegido por permissões
adequadas; registrar referências e evidências sem replicar dados fiscais,
documentos ou credenciais do back-office no BA. Modelo:

| Campo do índice | Como preencher / autoridade |
| --- | --- |
| `case_ref` | Identificador local estável, sem dados pessoais |
| `company_id` e `opportunity_id` | Tenant/Opportunity do BA, nunca usados como autorização |
| `brief_ref/version` | Referência/versionamento técnico do BA ou do arquivo privado |
| `proposal_external_ref/version` | ID e versão do documento **autoritativo** de back-office |
| `scope_price_send_approval_ref` | Quem aprovou cada gate, quando e para qual versão; nenhum token |
| `client_acceptance_ref` | Evidência e versão aceita, ou estado pendente/rejeitado |
| `delivery_acceptance_ref` | Critérios e evidência de aceite técnico ou pendências |
| `receivable_external_ref` | ID do recebível no financeiro; sem replicar valores por conveniência |
| `payment_status_as_of` | Pendente/parcial/conciliado/desconhecido **conforme o financeiro**, com data da consulta |
| `support_result_ref` | Chamado, medição e autorização de case (se houver) |
| `owner_next_action_due` | Responsável, ação e prazo; sem prazo → pendência explícita |
| `exception_ref` | Divergência, timeout, rejeição e sua resolução auditável |

As chaves são **campos de um checklist privado**, não novos campos
persistidos, colunas SQL ou promessa de endpoint implementado.

## 5. Avaliação do WP-014

**Comprovado por inspeção do código e WP-013:**
- O BA permite captura/triagem/brief, com três caminhos sintéticos testados.
- Nenhuma API atual deve ser tratada como emissora/aprovadora de proposta.
- O início da F2 pode ser ensaiado sem 99Freelas, ERP e dados reais.

**Comprovado apenas como decisão documental neste WP:**
- Dono de cada etapa, condição de avanço, artefato esperado e parada em erro.
- Alternativa manual sem introduzir segundo CRM/financeiro.
- Tratamento de revisão de proposta, pagamento parcial e resultado incerto.

**Não comprovado / bloqueia declarar F2 concluída:**
- Adesão real de um cliente, oferta e preço, envio, entrega e recebimento.
- Instalação/uso de ERPNext ou outro back-office efetivo.
- Experiência e tempo gasto do operador em uma execução real.
- Segurança, idempotência e reconciliação de qualquer adapter externo.

### Próximo gate, sem construir infraestrutura por hipótese

1. Confirmar **onde será mantido o índice privado** e como serão guardadas
   referências a propostas, aprovações e recebíveis quando houver casos reais.
2. Identificar **uma tarefa manual específica** cujo esforço ou erro justifique
   uma melhoria; sem medição, não desenvolver painel, adapter ou workflow completo.
3. Antes de propostas reais, validar o mecanismo efetivo de back-office
   (ERPNext quando implantado ou procedimento manual controlado) e autoridade
   humana para escopo, preço e envio.
4. A F2 somente se encerra com **ciclo real rastreável** até recebimento/resultado
   e evidências privadas; **simulação não substitui esse gate**.

**Nenhuma busca de leads, envio de proposta, integração, migration, publicação,
manipulação de banco ou ação financeira foi autorizada ou executada aqui.**
