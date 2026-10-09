# MODELO PRIVADO — case.md (Client 0)

> **Modelo público sem dados reais.** Copiar para **fora deste repositório**,
> em `~/.local/share/business-automation/client0/cases/<case_ref>/case.md`,
> somente depois de validar o destino e permissões. **Nunca** preencher ou
> commitar esta cópia no Git público.
>
> Este arquivo é **índice de evidências**, não proposta formal, nota fiscal,
> sistema contábil, aprovação eletrônica, assinatura ou fonte de pagamento.
> **Não marcar gates como concluídos sem evidência externa consultável.**

## 0. Registro mínimo

| Campo | Valor |
| --- | --- |
| `case_ref` | `[id opaco local; sem dados pessoais]` |
| `company_id` (tenant do BA) | `[verificado pela identidade operator]` |
| `opportunity_id` (BA) | `[id validado, sem copiar conteúdo do anúncio]` |
| `offer_ref/version` | `client0-integration-flow-v1` |
| `brief_ref/version` | `[referência/versionamento interno]` |
| `commercial_owner` | `[pessoa ou função]` |
| `technical_owner` | `[pessoa ou função]` |
| `financial_owner` | `[pessoa ou função]` |
| `current_next_action` | `[ação operacional específica]` |
| `next_action_owner` | `[responsável]` |
| `next_action_due` | `[ISO 8601 com fuso ou pendente]` |
| `backoffice_authority` | `[ERPNext validado / fallback formal privado / ainda não definido]` |
| `backoffice_connection_ref` | `[identificador da instalação, sem URL com credenciais]` |
| `private_evidence_root` | `[pasta privada local validada, sem caminho público]` |
| `backup_restore_evidence` | `[backup/restore isolado confirmado ou PENDENTE]` |
| `retention_review_due` | `[data de revisão conforme política ou pendente]` |

## 1. Gates comerciais e técnicos

Use somente estados `pending`, `blocked`, `unknown`,
`verified`, `rejected` ou `not_applicable`. Cada linha
`verified` exige **origem, ID/versão, evidência e responsável/data**.
`not_applicable` requer justificativa. `unknown` **não** libera
próxima etapa. G8 pode ocorrer antes de G6/G7 se houver gatilho contratual.

| Gate | Estado inicial | Documento / ID + versão | Evidência / origem autoritativa | Validador + momento | Bloqueio / próxima ação |
| --- | --- | --- | --- | --- | --- |
| G0 — vínculo BA | pending | — | — | — | — |
| G1 — escopo técnico revisado | pending | — | — | — | — |
| G2 — contraparte fiscal/back-office | pending | — | — | — | — |
| G3 — documento formal e condições | pending | — | — | — | — |
| G4a — aprovação humana para envio | pending | — | — | — | — |
| G4b — envio comprovado | pending | — | — | — | — |
| G5 — aceite comercial da versão | pending | — | — | — | — |
| G6 — execução/entregáveis | pending | — | — | — | — |
| G7 — aceite técnico | pending | — | — | — | — |
| G8 — recebível emitido pelo gatilho | pending | — | — | — | — |
| G9 — conciliação verificada | unknown | — | — | — | — |
| G10 — suporte e revisão de resultado | pending | — | — | — | — |

## 2. Versionamento e decisões independentes

Não editar uma proposta enviada no mesmo arquivo e chamá-la de mesma
versão. Criar nova versão; novas aprovações são necessárias quando
escopo, condições ou preço mudam.

| Artefato/versão | Fonte de verdade | Referência externa / caminho relativo privado | Hash SHA-256 opcional | Responsável + momento | Observações |
| --- | --- | --- | --- | --- | --- |
| `[brief v…]` | BA / registro privado | — | — | — | — |
| `[proposta v…]` | ERP/back-office | — | — | — | — |

Um hash ajuda a detectar mudanças em um arquivo; **não** prova assinatura,
autorização, identidade do aprovador nem aceite.

### Aprovações, envio e aceite

| Decisão distinta | Estado | Versão exata | Quem decidiu/executou | Quando (ISO 8601) | Evidência privada |
| --- | --- | --- | --- | --- | --- |
| Escopo revisado | pending | — | — | — | — |
| Preço/condições aprovados | pending | — | — | — | — |
| Envio autorizado | pending | — | — | — | — |
| Envio realizado | pending | — | — | — | — |
| Aceite comercial do cliente | pending | — | — | — | — |
| Aceite técnico da entrega | pending | — | — | — | — |

## 3. Financeiro — SOMENTE PROJEÇÃO DA FONTE AUTORITATIVA

**Não registrar valores, tributos, saldos ou dados fiscais neste índice
se estiverem no documento financeiro autoritativo.** Referenciar ID e
data da conferência. Nunca inferir `settled` a partir de tela do core,
comprovante unilateral, aceite técnico ou mensagem.

| Campo | Valor |
| --- | --- |
| `receivable_external_ref` | `[documento financeiro autoritativo / ainda não existe]` |
| `billing_trigger` | `[entrada / marco / recorrente / entrega / outro conforme contrato]` |
| `billing_due` | `[data em fonte financeira / pendente]` |
| `payment_status` | `unknown` |
| `payment_status_as_of` | `[sem consulta autoritativa]` |
| `payment_source` | `[instância e referência fiscal, sem credenciais]` |
| `financial_review_owner` | `[função/pessoa autorizada]` |
| `financial_next_action` | `[consultar fonte / conciliar / tratar divergência]` |

Estados financeiros são **`unknown`**, `pending`, `partial`,
`settled`, `overdue` ou `reversed`. Mudanças devem acompanhar
evidência e `as_of`; atualização fora de ordem exige nova consulta.
`partial` e `reversed` **não** significam `settled`.

## 4. Operação, suporte e prova social

| Campo | Valor |
| --- | --- |
| Critérios de teste definidos | `[versão/documento/pendente]` |
| Evidência de execução/entrega | `[referência privada, sem tokens]` |
| Exceções/retrabalho | `[IDs de incidente ou nenhum, se confirmado]` |
| Início e escopo do suporte | `[conforme acordo ou pendente]` |
| Indicador antes (fonte e período) | `[não medido]` |
| Indicador depois (fonte e período) | `[não medido]` |
| Resultados estimados separados dos medidos | `[sim/não/pendente]` |
| Permissão de divulgar nome/marca | **NÃO CONCEDIDA** |
| Permissão de divulgar métricas/resultados | **NÃO CONCEDIDA** |
| Permissão de divulgar depoimento/imagem | **NÃO CONCEDIDA** |
| Identidade, abrangência e versão autorizadas | `[nenhuma]` |
| Revisão humana para eventual publicação | `[pendente]` |
| Índice auxiliar de prova social (WP-023) | `[proof-social.json no mesmo diretório ou ainda não criado]` |

O [procedimento O08](../client0-proof-social.md) define medição,
permissões específicas, revisão e auditoria somente de leitura. A
existência do arquivo auxiliar ou um checklist preenchido **não**
concede direito de publicar nem modifica os estados acima.

**Sem autorização de divulgação específica, não publicar.** Não usar
marcas, capturas, dados comerciais ou conversas privadas como prova social.

## 5. Log de decisões — acrescentar, não apagar

Atualizações manuais devem criar **nova linha** com momento, autor,
referência de versão, transição e evidência. Este arquivo não fornece
auditoria imutável: proteger permissões, versões e backups; resolver
disputas pela fonte autoritativa e sua trilha de evidência.

| Data/hora + fuso | Papel e responsável | Gate/campo | De → para | Referência do artefato/versão | Evidência privada | Próxima ação |
| --- | --- | --- | --- | --- | --- | --- |
| `[a preencher]` | — | — | — | — | — | — |

## 6. Confirmação de integridade antes de encerrar

- [ ] `case_ref` corresponde à oportunidade validada, sem identidades vazadas.
- [ ] Versões, aprovações, envio e aceite são **evidências independentes**.
- [ ] Nenhum `unknown` foi tratado como `verified`/ `settled`.
- [ ] Pagamento foi conferido **no financeiro**, incluindo parciais/estornos.
- [ ] O índice tem responsável, próxima ação/data e exceções tratadas.
- [ ] Não há dados reais no Git ou em capturas/prompts públicos.
- [ ] Suporte, retenção, backup/restore e consentimentos foram revisados.
- [ ] Nenhum dado do Cliente 0 foi apresentado como case público sem permissão.
