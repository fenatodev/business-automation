# ACEITE COMERCIAL E TÉCNICO — RASCUNHO / NÃO ENVIAR

**Modelo privado a copiar somente quando o serviço estiver autorizado.**
Não é assinatura eletrônica, aceite do cliente, contrato ou comprovante de envio.
Guardar o preenchimento apenas fora do repositório público.

| Identificador | Valor / evidência |
| --- | --- |
| Serviço (ID opaco) | `[case_ref]` |
| Oferta | `client0-integration-flow-v1` |
| Proposta formal (origem) | `[ERPNext validado ou documento de fallback autorizado]` |
| ID e versão da proposta | `[ID e versão conferidos]` |
| SHA-256 dos bytes imutáveis da proposta | `[digest calculado do documento final]` |
| Quem verificou as identidades e poderes | `[responsável, data e evidência]` |

## G4a — autorização humana de envio

- Estado inicial: **PENDENTE**.
- Autorizar `[versão e hash exatos]` após revisão de escopo,
  preço, tributos, suporte, validade e tratamento de dados.
- Aprovador: `[identidade e papel]`.
- Data/hora/fuso e evidência independente: `[a preencher]`.

**Hash não é assinatura ou autorização.** Mudou qualquer byte, valor,
escopo, destino ou versão? Reabrir revisão e registrar nova autorização.

## G4b — envio comprovado (diferente de autorização)

- Estado inicial: **NÃO ENVIADO**.
- Canal e destinatário autorizado: `[a verificar]`.
- Documento/versão/hash efetivamente enviados: `[a verificar]`.
- Data e comprovação externa: `[a verificar]`.

Não preencher por ausência de erro, `HTTP 200` ou confirmação do modelo.

## G5 — aceite comercial do contratante

- Estado inicial: **ACEITE NÃO CONFIRMADO**.
- Manifestação do contratante: `[referência consultável]`.
- Identidade/poderes verificados: `[responsável e evidência]`.
- Versão e condições efetivamente aceitas: `[ID/hash e escopo]`.
- Exceções ou contraproposta: `[se houver, nova versão e nova aprovação]`.

Silêncio, cadastro no CRM ou proposta enviada **não** são aceite.
O registro de aceite somente poderá ser considerado após a pessoa
responsável consultar a fonte e conferi-la.

## G6/G7 — entrega e aceite técnico independentes

- Plano de implementação autorizado: `[versão e escopo]`.
- Testes e evidências: `[resultado observado, falhas e limitações]`.
- Versão entregue: `[referência e hash, quando pertinente]`.
- Representante habilitado para homologar: `[verificar]`.
- Manifestação de aceite/retrabalho: `[referência da confirmação]`.
- Pendências e correções: `[lista com responsável e prazo]`.

**G7 não confirma recebimento financeiro.** G8 pode ocorrer antes
do aceite técnico **se o contrato fixar cobrança antecipada ou por marco**.
A situação financeira segue a verificação independente em
[`client0-financial-check.template.md`](client0-financial-check.template.md).

## Retenção e integridade

Manter cópias imutáveis ou referências à fonte autoritativa, histórico
de alterações e permissões apropriadas, respeitando política de
retenção e backup protegido. Não compartilhar documentos reais,
nomes, comprovantes ou dados de contato em Git, chat ou repositório público.

**ESTADO DESTE MODELO: RASCUNHO / NÃO ENVIAR.**
