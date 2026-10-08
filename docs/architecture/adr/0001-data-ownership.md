# ADR 0001 — Data ownership do primeiro ciclo Client 0

Data: 2026-10-08  
Status: Accepted  
Escopo: primeiro ciclo comercial Client 0 e primeiro handoff com ERPNext.

## Contexto

O core do Business Automation e o ERPNext participam do mesmo ciclo operacional, mas não podem manter duas fontes de verdade editáveis para o mesmo fato. O primeiro ciclo precisa funcionar manualmente antes de integração completa e deve preservar separação entre CRM/inteligência operacional e back-office formal.

## Decisão

### Core / Business Automation

O core é autoritativo para:

- origem da oportunidade e referência externa;
- lead bruto e qualificação;
- oportunidade e estágio comercial operacional;
- próxima ação, responsável e motivo de perda;
- diagnóstico técnico e referência da oferta;
- conversas e mensagens;
- estado técnico das automações implantadas;
- evidência operacional de execução;
- referência para documentos/IDs externos;
- métricas de case e autorização de divulgação.

### ERPNext

ERPNext é autoritativo para:

- contraparte validada de back-office quando necessária;
- razão social e identificadores fiscais usados no faturamento;
- proposta/quotation formal;
- preço final aprovado, moeda, impostos e condições comerciais formais;
- pedido/documento comercial quando aplicável;
- projeto/tarefas/horas convencionais quando usados;
- fatura/recebível, vencimento, pagamento, recebimento parcial e estorno;
- registro administrativo/financeiro necessário à operação.

### Humano

A decisão humana é autoritativa para:

- aprovação de escopo;
- aprovação de preço/condições antes do envio;
- autorização de envio de proposta;
- interpretação de aceite quando a evidência não for mecanicamente verificável;
- exceções comerciais;
- reprocessamento sensível;
- publicação de case/nome/marca/depoimento.

### IA

IA pode sugerir, extrair, resumir, classificar e redigir. Não é fonte de verdade para:

- aprovação;
- preço final;
- identidade/tenant;
- aceite contratual;
- pagamento/recebimento;
- autorização de contato;
- publicação.

## Primeiro handoff ERP

O primeiro handoff recomendado é:

`customer local aprovado para back-office -> ensure_business_party -> referência externa ERPNext`

Regras:

- conversão técnica de Lead para Customer não dispara handoff automaticamente;
- não criar Opportunity no ERPNext por padrão;
- pipeline comercial permanece no core;
- o handoff ocorre somente quando houver necessidade de documento/back-office;
- vincular por ID externo estável, nunca apenas por nome/email;
- retry não pode criar duplicata;
- timeout sem prova do efeito remoto vira estado `unknown` e exige reconciliação;
- erro de validação/autorização não entra em retry infinito.

## Matriz resumida

| Dado/fato | Autoridade | Projeção permitida |
| --- | --- | --- |
| origem/URL da oportunidade | Core | nenhuma obrigatória no ERP |
| qualificação/score/próxima ação | Core | nenhuma obrigatória no ERP |
| contato comercial inicial | Core | campos acordados no handoff |
| dados fiscais/faturamento | ERPNext | leitura mínima no core |
| oferta técnica/versão | Core | referência na proposta |
| preço/impostos/condições formais | ERPNext | status/ID no core |
| proposta formal | ERPNext | referência/versão/status no core |
| projeto/tarefas convencionais | ERPNext | ID/marcos no core |
| automação implantada/runs | Core | link no projeto/chamado |
| conversas/mensagens | Core | resumo/referência somente se necessário |
| fatura/vencimento/recebimento | ERPNext | projeção com `last_synced_at` |
| case/autorização de divulgação | Core/processo humano | nenhuma automática |

## Resolução de conflito

- dado financeiro/fiscal conflitante: ERPNext vence;
- dado de pipeline/qualificação conflitante: core vence;
- contato alterado nos dois lados: não sobrescrever silenciosamente; sinalizar revisão;
- estado remoto desconhecido: reconciliar antes de repetir;
- exclusão/inativação no core não apaga documento financeiro no ERP.

## Consequências

Positivas:

- evita CRM/financeiro duplicados;
- permite operação manual antes do adapter;
- mantém ERP substituível por contrato;
- reduz risco de duplicação e divergência.

Custos:

- exige referências externas e reconciliação;
- algumas telas futuras exibirão projeções, não dados editáveis;
- integração precisa tratar idempotência e estado desconhecido.

## Fora do escopo

Este ADR não:

- instala ERPNext;
- escolhe campos/DocTypes definitivos da versão instalada;
- cria adapter;
- cria migrations;
- define preço, imposto ou política fiscal;
- autoriza sincronização bidirecional geral.
