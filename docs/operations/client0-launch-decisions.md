# Client 0 — decisões pendentes para iniciar operação real

**Estado:** quadro de revisão humana, **não aprovado** e sem autorizar
contato, publicação, faturamento ou coleta de dados de clientes.
**Objetivo:** não continuar criando módulos sem uma decisão real.

## Porta de entrada: decisões P0 do responsável

| ID | Decisão indispensável | O que registrar em privado | Estado |
| --- | --- | --- | --- |
| D01 — atuação | Pessoa física/MEI/ME/EPP/outra condição, CNAE/atividade e possibilidade de prestar serviços; regime, município e emissão fiscal conforme orientação competente | Referência à análise ou assessor; canal autorizado de NFS-e/documento aplicável | **PENDENTE** |
| D02 — posicionamento | Confirmar nome público FenatoDev, identidade comercial e canal de contato realmente controlado | Fonte de identidade e canais aprovados; sem publicar documento pessoal no Git | **PENDENTE** |
| D03 — oferta e preço | Manter um fluxo por contrato; política de estimativa em horas, margem/contingência, terceirizados, tributos, entrada, marcos, validade, reembolso e alterações | Tabela/preço **privados**, sem número arbitrário e sem promessa de ROI | **PENDENTE** |
| D04 — contratos | Texto sobre escopo/limites, IP/licenças, prazo, suporte, proteção de dados, aceite e resolução de conflitos; conferir necessidade de revisão jurídica | Versão autorizada do documento e aprovador | **PENDENTE** |
| D05 — plataforma | Para cada canal (ex.: 99Freelas), conferir regras de propostas, comunicação, taxas, custódia e pagamentos, **sem contornar termos** | Plataforma/canal permitido, referência das condições vigentes | **PENDENTE** |
| D06 — back-office | Optar entre **fallback oficial/documental controlado** e ERPNext **já funcional**; definir emissor fiscal e fonte de conciliação bancária legítimos | Responsável G2/G3/G8/G9, fonte autoritativa e procedimento de falhas | **PENDENTE** |
| D07 — proteção do índice | **Restic escolhido (WP-030)** e ensaio criptografado apenas no runner GitHub; falta destino independente, custódia de chave e **restore isolado real** | [Runbook de ativação posterior](client0-restic-recovery.md), evidência sanitizada do host real e confirmação de mídia | **PENDENTE** |
| D08 — comunicação/site | Confirmar hospedagem MXQ4K **somente após** boot/segurança; HTTPS, headers, disponibilidade, identidade e copy revisados; autorizar versão exata do site | Destino, SHA, operador e ato de publicação. Cloudflare estático fica como fallback | **PENDENTE** |
| D09 — prospecção | Aprovação explícita para retomar seleção de leads e submissão de propostas por canal, limites de gastos e critérios de parada | Autorização humana de canal/escopo; propostas seguem gate G4a individual | **NÃO AUTORIZADA** |

**D01 é um bloqueio real independente de software.** Nenhum site,
modelo de IA, ERP ou nota em Markdown pode substituir condições
fiscais/legais do prestador. Não presumir tipo de empresa.

**D08 é ordem de operação escolhida pelo responsável:** concluir
preparação, depois ativar o SD Armbian no MXQ4K, publicar site somente
com aprovação e só depois buscar clientes.

## Etapas que NÃO precisam de mais software agora

- O cliente inicial pode ser atendido manualmente com os modelos de
  [proposta](templates/client0-proposal.template.md),
  [aceite](templates/client0-acceptance.template.md) e
  [conferência financeira](templates/client0-financial-check.template.md),
  desde que P0 esteja aprovado e as fontes oficiais estejam disponíveis.
- ERPNext é uma evolução possível, não pré-requisito automático se o
  fallback manual for válido e verificável.
- O core BA **não precisa** ter módulo de invoices, cadastro fiscal,
  emissão NFS-e, gateway Pix, outro painel ou automação de mensagens
  para um primeiro contrato assistido.
- Marketing pode usar rascunhos internos WP-022, sem publicação
  automática ou "cases" inventados.
- WP-028 validou ZIP sintético plaintext; [WP-030](client0-restic-recovery.md) valida Restic criptografado com dados fictícios. **Backup real e recuperação local continuam pendentes**; a chave/destino precisam de decisão operacional.

## Ordem curta para concluir a preparação

**Passo A — decisões D01–D07:** confirmar legalidade do serviço,
preço/condições, fallback comercial, canal de pagamento e backup
protegido. Uma vez resolvidos, não abrir novas features por hipótese.

**Passo B — D08:** inventariar o MXQ4K com SD Armbian **sem regravar
firmware**; confirmar Linux/atualizações/rede, servidor estático sem
privilégios, HTTPS e headers de segurança; optar por Cloudflare Pages
se o aparelho for inadequado. Publicação exige autorização exata.

**Passo C — D09:** somente o responsável autoriza início de
prospecção e **cada envio real**. Registrar oportunidades no
core existente, seguir `G0–G10` com prova da fonte externa.

**Critério para encerrar F2, que não se confunde com preparação:**
um ciclo **real** com oportunidade, proposta aprovada/enviada,
aceite comercial, entrega, recebimento verificado e revisão de
resultado. Sem cliente/recebimento, F2 segue formalmente aberta.

## Política de parada

Se algum dado fiscal, jurídico, financeiro, backup, conta ou
publicação exigir acesso, gasto, assinatura, credencial, dado
pessoal ou ação irreversível, **STOP** e obter autorização humana.
Não enviar ofertas externas nem ligar o DC por consequência
deste quadro. Não continuar criando WPs sintéticos para adiar
as decisões operacionais.
