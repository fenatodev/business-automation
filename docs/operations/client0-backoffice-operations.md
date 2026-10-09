# WP-019 / F2-O02 — Operação comercial, entrega e back-office Client 0

**Estado:** procedimento e modelo prontos para validação; não é integração ERPNext nem prova de venda.
**Versão:** 1.0 — 2026-10-08.
**Escopo:** um único serviço por registro privado, do brief técnico ao recebimento, com exceções, evidências e fallback manual.
**Autoridades:** [ADR 0001](../architecture/adr/0001-data-ownership.md), [oferta v1](client0-offer-v1.md), [ensaio G1–G10](client0-commercial-tabletop.md), [F2](../ROADMAP.md).

## 1. Escolha mínima de armazenamento — sem um segundo CRM

Usar **um registro privado por trabalho** na máquina controlada pelo operador, com referências aos documentos formais e suas fontes, **sem copiar o banco do core** ou manter outro pipeline editável.

- Raiz local **proposta para validação no Ubuntu:** `~/.local/share/business-automation/client0/cases/`.
- Uma subpasta por serviço, identificada por `case_ref` opaco, por exemplo `c0-2026-001`; não usar nome, e-mail, CPF, título de anúncio ou outros dados pessoais na pasta.
- Arquivo principal: `case.md`, **copiado** de [modelo de caso](templates/client0-case.template.md), editado **somente fora do repositório**. Arquivos externos, quando permitidos e necessários, ficam em `evidence/` com acesso mínimo.
- Pasta `cases` e subpastas **0700**; arquivos privados **0600**; `umask 077`. Verificar symlinks e caminho esperado antes de criar; não apontar para backup, volumes compartilhados ou diretórios públicos.
- **Este diretório não está criado nem validado por este WP.** No primeiro uso, Continue poderá preparar apenas a estrutura vazia; **não** copiar dados reais, anexos, contratos ou credenciais sem aprovação.
- Um diretório em `~/.local/share` **não é backup**. Confirmar política de cópia protegida, restore em destino isolado e critérios de retenção antes de guardar contratos ou provas comerciais sensíveis.
- O PostgreSQL existente continua sendo a fonte de `Opportunity`, triagem e `ProposalBrief`; usar `company_id`/`opportunity_id` apenas como referência, **nunca para autorizar** acesso.
- O ERPNext, quando **operacional e validado**, será autoridade para `Customer` de back-office, `Quotation` formal, documentos financeiros, recebíveis e pagamentos. Até lá, usar fallback manual privado **somente com documentos formalmente emitidos e conferidos**; o arquivo `case.md` não é nota fiscal, ERP, pagamento ou aprovação.

**Decisão de contenção:** não criar `ExternalReference`, tabela de pagamentos, `Quotation` paralela, serviço de e-mail, site público nem portal para resolver este passo documental.

## 2. Evidência obrigatória e ordem do processo

Uma ação só passa de `pendente` para `verificado` quando possui **referência, versão/identificador, responsável e evidência consultável**. O estado `desconhecido` não significa aprovado; falta de resposta, consulta vazia e prazo vencido não autorizam inferir aceite ou pagamento. Preservar histórico de decisões/correções, não sobrescrever o evento antigo para encobrir erro.

| Gate | Entrada exigida | Autoridade / resultado | Referência mínima no `case.md` |
| --- | --- | --- | --- |
| G0 — vínculo | Identidade operator autorizada + registro existente no core | Core confirma Company/Opportunity; humano abre registro privado | `case_ref`, `company_id`, `opportunity_id`, oferta/versão, responsável |
| G1 — revisão técnica | Brief `draft`/`ready_for_review`, dependências e aceite técnico definidos | **Humano** aprova ou bloqueia escopo; `ready_for_review` não aprova | `brief_ref`, versão, decisão, responsável, data, evidência |
| G2 — contraparte | Necessidade de documento confirmada; dados fiscais/permissões legítimos | ERP/back-office assegura contraparte validada | Fonte/instância, `external_party_id`, validação, sem vincular somente por nome/email |
| G3 — proposta formal | Escopo G1, preço/impostos/condições aprováveis | ERP/back-office emite versão específica | `proposal_external_id`, versão, hash opcional do artefato, local privado |
| G4a — autorização de envio | Versão G3 exata, preço/escopo revisados | **Humano** autoriza enviar **aquela versão** | Quem decidiu, quando, versão e referência da autorização |
| G4b — envio | G4a efetivamente verificado | **Humano** envia pelo canal permitido e confere saída | Quando/canal/versão/evidência de envio; envio ≠ aceite |
| G5 — aceite comercial | Proposta G4b enviada; resposta do cliente correspondente | **Humano** valida identidade, versão e condições aceitas | Referência de aceite, quem aceitou, data/versão, divergências |
| G6 — execução | G5 confirmado, condições contratuais de início atendidas | Técnico executa escopo aprovado com acessos legítimos | Plano, sistema de projeto/ID externo se houver, entregas, testes, incidentes |
| G7 — aceite técnico | Entrega conferível pelos critérios acordados | Cliente/responsável valida ou aponta retrabalho | Evidência de teste e aceite, versão, pendências |
| G8 — cobrança | **Gatilho contratual** (entrada, marco, recorrência ou entrega) ocorrido | ERP/financeiro emite recebível conforme contrato; pode vir **antes** de G7 | ID do documento, vencimento, período e gatilho; não registrar valor duplicado por conveniência |
| G9 — recebimento | Documento existente e registro de baixa/conciliação na fonte financeira | **Financeiro** confirma estado como de uma data, sem inferir de status técnico | Fonte, documento, `as_of`, `unknown|pending|partial|settled|overdue|reversed` |
| G10 — suporte/resultado | Acordo de suporte e medição verificável | Humano acompanha pós-venda; publicação exige autorização à parte | Chamado, resultado medido versus estimado, consentimento específico se houver |

**Nota:** G8 é uma trilha contratual independente da ordem temporal G6/G7; não bloquear cobrança de entrada só porque a entrega ainda não começou. G9 exige conciliação autoritativa, não comprovante unilateral, mensagem de cliente ou `HTTP 200`.

## 3. Três decisões separadas que nunca podem ser fundidas

1. **Aprovação interna:** escopo, versão, preço/condições e permissão de envio pertencem ao operador humano autorizado. Separar aprovador e executor como papéis mesmo quando forem a mesma pessoa.
2. **Envio:** ato externo com data, canal e prova de qual versão foi enviada. Aprovação **não** prova envio.
3. **Aceite comercial:** manifestação atribuível ao cliente **referindo a mesma versão**; silêncio, status da plataforma, cadastro `Customer` ou `Lead.won` não provam aceite.

Se `Quotation`/documento mudar de conteúdo ou versão **depois da autorização de envio**, essa autorização **não se transfere**. Exigir nova revisão e autorização. Um SHA-256 do artefato ajuda a identificar a versão, **mas não é assinatura, consentimento, autorização ou prova de autoria**. Guardar a prova humana separadamente.

## 4. Política de exceção — resolução antes de retomar

| Cenário | Estado e encaminhamento |
| --- | --- |
| Escopo inviável / orçamento ausente | `blocked`/qualificar; registrar próximo responsável e data, **não** inventar preço |
| Reprovação interna ou alteração de preço/escopo | `rejected` para aquela versão; criar nova versão com revisão, sem sobrescrever anterior |
| Documento G3 criado sem resposta (timeout) | `unknown`; consultar back-office por referência estável e reconciliar, **não** repetir criação |
| Referência remota conflitante | `blocked`; checar tenant, conexão, ID estável e fonte autoritativa; não resolver só por nome/email |
| Cliente pediu ajustes depois do envio | Nova proposta com nova versão; aceite antigo não aprova mudança |
| Cliente não responde / recusa | Registrar `pending` / `rejected` e próxima ação; não classificar ganho por cadastro |
| Entrega falha / aceite técnico recusado | Registrar incidente, evidência, correção e nova revisão do aceite |
| Pagamento parcial / atraso / estorno | Manter `partial`, `overdue` ou `reversed` **na fonte financeira**, com `as_of`; não tratar como `settled` |
| ERP indisponível | Processo humano com documento oficial e registro privado; não alegar documento ERP gerado |
| Evidência inexistente ou incerta | `unknown` ou `blocked`, responsável e próximo prazo; não marcar gate `verificado` |

**Contato, emissão, aprovação de preço, publicação, migração, compras e mudanças financeiras continuam fora de qualquer execução automática deste WP.** A IA pode ajudar a redigir um rascunho, sem conceder permissão.

## 5. Checklist de execução — o que o operador de fato faz

Para cada novo serviço **após retomada aprovada da prospecção**:

1. Confirmar oportunidade existente no painel `/operator` e oferta `client0-integration-flow-v1`. Abrir `case.md` em pasta privada, preenchendo somente referências necessárias. Não criar `Customer` automaticamente.
2. Registrar G1, quem revisou a versão e qual dúvida bloqueia avançar.
3. Usar ERPNext **somente após** smoke de instalação, login, Company/permissões, entidade/DocTypes e recuperação — ou formalizar um fallback manual com documento controlado e verificação por humano. Não improvisar financeiro em planilha paralela.
4. Para G3–G5, guardar documento imutável/versionado (ou referência estável), autorização humana, comprovante de envio e aceite correspondentes. Checar mudanças de versão entre os passos.
5. Planejar e entregar G6/G7 com evidências de testes, acesso autorizado, runbook e aceite técnico.
6. No gatilho financeiro contratado, confirmar G8/G9 na fonte autoritativa e registrar **referência e data da verificação**; sem fonte, permanecer `unknown`.
7. Registrar suporte, medição e eventual permissão de case em G10; sem consentimento de divulgação, **não publicar**.
8. Em cada atualização: campo de responsável, próxima ação/data e log de decisão com referência à evidência. Para encerramento, revisar pendências, retenção e backup.

## 6. Aceite do WP-019 e dependência local mínima

**WP-019 / O02 entrega documentação e modelo**, não um sistema de aprovação eletrônica. Aceite documental: G0–G10 auditáveis no checklist, recusa de estados sem evidência, opção manual realista, versão de proposta, pagamento parcial/estornado e consentimento tratados. O ERP permanece não validado.

**Única dependência do Ubuntu para esta etapa:** validar uma pasta **vazia** de referência privada (0700, com `umask 077`) e copiar o template localmente (0600), sem dados reais; confirmar que a pasta não é symlink e está fora do Git. Isso é um **preflight**, não armazenamento operacional recuperável até backup/restore ser aprovado. Testes Python/compileall são executados pelo Continue em checkout de testes ou branch limpa, sem tocar serviços ativos.

**Atualização após WP-029:** o [kit comercial manual](client0-manual-commercial-pack.md)
contém modelo de proposta, aceite comercial/técnico e checklist
fiscal/financeiro, todos inicialmente marcados **RASCUNHO / NÃO ENVIAR**.
O [quadro de decisões de lançamento](client0-launch-decisions.md)
registra formalização tributária, preço/condições, emissor, canal e backup
ainda **pendentes**. Nenhum documento desses comprova ERP funcional,
autorização de envio, recebimento ou emissão fiscal.

**Não** iniciar ERPNext/Docker, executar Alembic, ler o banco real,
reiniciar Uvicorn ou ativar prospecção por consequência da
documentação. A F2 permanece aberta até um ciclo comercial real com
recebimento e revisão de resultado.
