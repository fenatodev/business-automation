# CONFERÊNCIA FISCAL E FINANCEIRA — RASCUNHO / NÃO ENVIAR

**Índice privado somente de referências; não é NFS-e, fatura,
livro contábil, recibo, cobrança ou prova de pagamento.**
**Fonte financeira autoritativa:** banco/provedor legítimo verificado
pelo responsável; nenhum estado é declarado por este formulário.
Estado inicial da conciliação: `unknown`.

## 1. Autoridade fiscal e documental — bloquear sem validação

| Item | Referência / decisão humana |
| --- | --- |
| Serviço | `[case_ref; oferta client0-integration-flow-v1]` |
| Natureza da atuação/prestador | `[Pessoa Física / MEI / ME / EPP / outro, APÓS verificar]` |
| Município e atividade/serviço tributável | `[validado com orientação profissional/habilitação]` |
| Regime aplicável e obrigações | `[revisão atual, não presumir CNPJ ou enquadramento]` |
| Canal de NFS-e ou documento legalmente cabível | `[portal nacional autorizado ou emissor competente]` |
| Autoridade do documento comercial | `[ERPNext REAL validado ou fallback documental controlado]` |
| Quem pode emitir/consultar e evidência | `[identidade, permissão, data]` |
| Backup/restore privado habilitado | `[evidência ou PENDENTE]` |

A emissão fiscal é uma **ação real separada**: seguir obrigações do
prestador e regras vigentes. Markdown e ERPNext sem integração fiscal
verificada não emitem automaticamente NFS-e válida.

## 2. G8 — evento de cobrança conforme proposta aceita

| Campo | Estado inicial |
| --- | --- |
| Versão exata e aceite comercial G5 | `[PENDENTE; verificar fonte real]` |
| Gatilho contratual | `[entrada / marco / pós-entrega / outro aprovado]` |
| Ocorrência do gatilho, verificada | `[PENDENTE]` |
| Documento fiscal real, emitido quando exigível | `[ID e fonte, PENDENTE]` |
| Recebível / documento financeiro real | `[ID, versão, fonte e situação]` |
| Data de vencimento | `[conforme documento real]` |
| Responsável e data da consulta | `[a preencher]` |

**Cobrança antecipada** pode preceder G7 se contratada. Não criar
recebível fictício, duplicado ou nota fiscal por inferência da IA.

## 3. G9 — conciliação de recebimento com fonte autoritativa

| Campo | Estado inicial |
| --- | --- |
| Identificador do recebível | `[referência autoritativa ou não existe]` |
| Fonte de recebimento | `[banco/provedor legítimo, nunca este índice]` |
| Data `as_of` e conferente | `[PENDENTE]` |
| Estado financeiro | `unknown` |
| Movimento/baixa e vínculo ao recebível | `[referência verificável]` |
| Situação atual/valor em aberto | `[consultar fonte; não inventar]` |
| Divergência, estorno ou contestação | `[pendente/registrar]` |
| Próxima ação / responsável / prazo | `[a verificar]` |

Estados admitidos: `unknown`, `pending`, `partial`, `settled`,
`overdue`, `reversed`. `partial` e `reversed` **não**
significam `settled`. Comprovante enviado pelo cliente, mensagem,
aceite técnico ou registro do core não comprovam conciliação.

**Nunca** marcar `settled` só porque o dinheiro parece ter sido
transferido: conferir fonte bancária legítima, ID do recebível, data,
responsável e reconciliação. Não guardar senhas, chave Pix,
dados bancários nem extratos completos neste formulário.

## 4. Incidente ou fonte indisponível

Documento externo criado com timeout => `unknown`, buscar pelo
identificador estável no provedor oficial; **não recriar cegamente**.
Status desconhecido, pagador incompatível ou duplicação impedem
conclusão até resolução humana. Registrar histórico sem apagar fatos.

**ESTADO DESTE MODELO: RASCUNHO / NÃO ENVIAR.**
