# Client 0 — WP-029: kit comercial manual controlado (G0–G10)

**Estado:** modelos e procedimento utilizáveis **após revisão humana**.
Nenhuma proposta foi enviada, nenhum documento fiscal foi emitido e
nenhum recebimento foi conciliado. Preços, formalização e meios de
cobrança continuam **não definidos**.

## Decisão de menor custo: fallback manual primeiro, ERPNext depois

A F2 deve provar um **serviço real de integração/automação de um fluxo**,
não a necessidade de manter outro ERP. O core BA já mantém oportunidades,
triagem e brief técnico. O registro `case.md` segue como **índice
privado de referências** e nunca se torna emissor fiscal/contábil.

Para o **primeiro serviço**, recomendar **fallback documental controlado**,
caso o responsável tenha formalização e emissor fiscal aplicáveis já
confirmados. ERPNext fica **opcional e desativado** até que haja validação
de instalação, permissões, `Quotation`, `Sales Invoice`,
`Payment Entry`, recuperação e custo operacional. Não criar CRM,
sistema de faturamento ou integração paralela para economizar essa etapa.

| Domínio/ato | Fonte de verdade | Quem valida |
| --- | --- | --- |
| Oportunidade e brief | PostgreSQL privado do BA | Operador autenticado |
| Identidade do contratante e documentos formais | Fonte legítima e documentação comercial privada; futuramente ERPNext se validado | Comercial/back-office |
| Proposta aprovada e versão enviada | Documento versionado no repositório **privado autorizado**, referência no `case.md` | Comercial **humano** |
| Aceite e mudança de escopo | Manifestação inequívoca do cliente, vinculada à versão | Comercial e cliente |
| NFS-e ou documento fiscal aplicável | **Emissor oficial/habilitado para o prestador**, não BA/Markdown | Prestador e assessor fiscal quando necessário |
| Recebível e baixa | Fonte financeira habilitada + consulta/conciliação legítima | Financeiro **humano** |
| Resultado e prova social | Medição real + direitos e consentimentos específicos | Técnico, comercial e titular dos dados |

### Ponto fiscal que bloqueia a operação real até decisão

Não há confirmação do tipo de prestador, regime tributário, município
competente, habilitação fiscal, natureza do serviço ou emissor usado.
**Não presumir que o responsável é MEI, possui CNPJ, é optante pelo
Simples ou já está habilitado para NFS-e.** Não enviar proposta contendo
tributos ou emitir documentos antes de esclarecer isso.

Informação oficial disponível em outubro de 2026:
- MEI prestador de serviços usa NFS-e no padrão nacional, com
  obrigações específicas conforme destinatário.
- A Resolução CGSN 191/2026 adiou a obrigatoriedade do Emissor
  Nacional da NFS-e para os demais optantes do Simples Nacional
  de 1º/09 para **1º/11/2026**; verificar a regra vigente **no dia
  da emissão** e o enquadramento correto.
- Outros regimes e situações exigem validação própria; não inferir
  que o mesmo procedimento ou dispensa fiscal se aplica.

Referências primárias:
- [Portal NFS-e nacional](https://www.gov.br/nfse/pt-br/pagina-inicial);
- [Prorrogação oficial — 11/08/2026](https://www.gov.br/nfse/pt-br/noticias/comite-gestor-do-simples-nacional-prorroga-a-obrigatoriedade-de-emissao-de-notas-fiscais-de-servico-pelo-emissor-nacional-da-nfs-e);
- [Gov.br: obrigações do MEI para emissão de nota](https://www.gov.br/empresas-e-negocios/pt-br/empreendedor/perguntas-frequentes/nota-fiscal-inscricao-estadual-e-ou-municipal/o-microempreendedor-individual-mei-e-obrigado-1).

**Para oportunidades via 99Freelas ou outra plataforma:** conferir
primeiro regras contratuais, taxas, custódia e pagamento **da plataforma**;
não propor cobrança ou comunicação por fora violando seus termos.
A transferência direta de contato/dinheiro pode ser proibida; sem
revisão, manter `blocked`.

## Documentos prontos para copiar e revisar em privado

Os modelos públicos **não contêm dados de clientes** e começam
com `RASCUNHO / NÃO ENVIAR`:

- [Proposta comercial de um fluxo](templates/client0-proposal.template.md):
  escopo observável, entregáveis, dependências, riscos, exclusões,
  cronograma, preço/tributos e suporte **em aberto**.
- [Aprovação, envio e dois aceites](templates/client0-acceptance.template.md):
  G4a, G4b e G5 **separados**, G6/G7 independentes.
- [Conferência fiscal, cobrança e conciliação](templates/client0-financial-check.template.md):
  emissor habilitado, gatilho G8, estados G9, `as_of` e fonte financeira.

Usar o [modelo de índice por serviço](templates/client0-case.template.md)
para guardar **referências privadas**, não duplicar documentos fiscais,
nomes, extratos, senhas ou credenciais no core. **Não preencher arquivos
públicos ou commitar suas cópias**. O WP-028 provou somente uma recuperação
sintética; backups reais protegidos continuam pendentes.

## Processo operacional por gate, sem automação externa

| Gate | Ação concreta quando autorizada | Evidência de saída | Bloqueio |
| --- | --- | --- | --- |
| G0/G1 | Abrir oportunidade autenticada, revisar brief e uma entrega viável | Referência/versão do brief + responsável | Escopo/acesso desconhecido |
| G2 | Confirmar contratante e condição de emissão, respeitar plataforma | Documento de contraparte ou referência autoritativa | Formalização fiscal não verificada |
| G3 | Preencher proposta privada, conferir custos, impostos, prazo e suporte; congelar versão | Documento e digest SHA-256 + revisão de preço | Campos abertos, preço não aprovado |
| G4a | Humano autoriza **exatamente** versão e digest | Referência independente de aprovação | Falta de autoridade/preço |
| G4b | Humano envia pelo canal legitimamente permitido | Evidência de envio real, data e versão | Aprovação não autoriza mensagem automática |
| G5 | Conferir aceite do cliente da mesma versão | Referência e identidade do aceite | Silêncio ou contraoferta exigem nova revisão |
| G6/G7 | Implementar escopo aprovado, testar e obter aceite técnico | Testes, entrega versionada e aceite/retrabalho | Resultado técnico não é recebimento |
| G8 | Após gatilho contratual, emitir documento no **sistema habilitado** | Referência oficial, vencimento, obrigação fiscal revisada | Nunca gerar "nota" em Markdown |
| G9 | Conferir recebível/baixa com fonte financeira real | `as_of`, referência, responsável e estado | `unknown/partial/reversed` não é pago |
| G10 | Operação, suporte, revisão de resultado | Evidências e escopo de suporte | Divulgação exige consentimento próprio |

G8 **pode preceder G7** para entrada ou marco quando previsto na
proposta aceita. Na venda de serviços, não presumir uma sequência fixa
`entrega → nota → pagamento` para todos os contratos.

**Se o ERPNext for escolhido depois:** confirmar operação antes de
transferir responsabilidade ao ERP. Fluxos oficiais previstos:
`Quotation` (proposta), `Sales Invoice` (contábil, **não
automaticamente NFS-e válida**) e `Payment Entry` (pagamento e
alocação). Fonte/integração fiscal real continua separada.

Documentação ERPNext:
- [Quotation](https://docs.frappe.io/erpnext/quotation);
- [Sales Invoice](https://docs.frappe.io/erpnext/sales-invoice);
- [Payment Entry](https://docs.frappe.io/erpnext/payment-entry).

## Exceções e STOP

- **Preço/prazo/tributo não aprovado:** não enviar; solicitar revisão.
- **Proposta modificada após G4a:** gerar nova versão + autorização.
- **Timeout de envio ou emissão externa:** `unknown`; pesquisar fonte
  pela referência estável, **não** repetir criação às cegas.
- **Recusa ou contraproposta do cliente:** não iniciar execução; versionar
  novamente e reavaliar.
- **Pagamento parcial, estornado ou recebido por canal desconhecido:**
  não marcar `settled`. Fonte financeira prevalece.
- **Backup de documentos privados sem recuperação protegida:** não
  coletar contratos/anexos sensíveis por este fluxo.
- **Sem permissão de case:** não divulgar identidade, marca, métricas,
  imagens ou depoimentos.

## Último gate antes de operar

O [quadro de decisões de lançamento](client0-launch-decisions.md)
lista apenas decisões reais que o responsável deve tomar: identidade,
formalização tributária, preço, suporte, uso de plataforma, back-office,
recuperação, site/contato e autorização de prospecção.

**O WP-029 não executa contato, envio, cobrança, assinatura, emissão de
nota, pagamento, deploy ou acesso ao banco.** O sucesso do CI comprova
somente completude dos modelos; não habilita nenhum canal comercial
nem fecha F2. O primeiro ciclo real ainda exige aceite, entrega,
recebimento e revisão de resultado verificáveis.
