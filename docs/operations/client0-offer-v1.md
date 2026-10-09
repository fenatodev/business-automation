# Client 0 — oferta operacional v1: implantação de um fluxo

**Status:** template de trabalho F2 / O01; **não é proposta aprovada nem serviço contratado**.  
**Data:** 2026-10-08.  
**Responsáveis funcionais:** comercial (qualificação/condições), técnico (viabilidade/entrega), financeiro (cobrança); a mesma pessoa pode exercer mais de um papel, mas cada decisão deve ser distinguida.  
**Versão da oferta:** `client0-integration-flow-v1`.  
**Fonte de decisão:** `docs/CLIENT0_FLOW.md` (primeiro foco: 99Freelas e implantação de fluxo), `docs/architecture/adr/0001-data-ownership.md`, `docs/architecture/delivery-plan-v1.md`.

## 1. Definição e cliente-alvo

**Oferta inicial escolhida para validação:** diagnóstico direcionado e **implantação de um fluxo de automação ou integração**, envolvendo sistemas/APIs, CRM ou assistência de IA **apenas quando o problema justificar**.

A unidade vendável é **um fluxo concreto**, não uma plataforma completa. Exemplos de formato: mover pedidos recebidos para um sistema interno com confirmação e tratamento de duplicação; substituir lançamento repetitivo de informações entre ferramentas; validar e encaminhar uma entrada autorizada. **Os exemplos são hipóteses técnicas, não projetos realizados nem promessas de resultado.**

Um diagnóstico pode ser uma **etapa prévia** à implantação, não uma obrigação de implantar um fluxo sem acesso, dados ou processo confirmado. Sem evidência técnica mínima, não emitir promessa de prazo, economia ou ROI.

**Enquadramento:** a oferta é uma hipótese comercial F2, sujeita a validação com caso real. Não publicar o texto como uma oferta com preço/prazo fechados, nem declarar clientes atendidos com base neste template.

## 2. Entrada mínima do diagnóstico (perguntas de descoberta)

Preencher em registro privado, sem dados reais no Git:

| Campo | O que confirmar | Estado aceitável |
| --- | --- | --- |
| `opportunity_ref` | ID da Opportunity no core, tenant e fonte; referência à URL externa | Referência validada, sem transferir tenant a partir do payload |
| `problem_statement` | Qual ação manual/erro custa tempo ou dinheiro, e quem sofre o efeito? | Uma frase do responsável, não suposição de IA |
| `workflow_before` | Gatilho, passos atuais, dono, ferramenta de origem/destino, frequência | Mapeamento manual mínimo; desconhecidos explícitos |
| `desired_outcome` | O que deve acontecer ao concluir o fluxo? | Resultado observável, com limites |
| `systems_access` | APIs, planos, permissões, sandbox, tokens necessários | Acesso legítimo e escopo das permissões confirmados; segredos fora da documentação |
| `data_risk` | Se há dados pessoais/sensíveis, transferência, retenção, controles e consentimentos necessários | Revisão de segurança e minimização antes da ingestão |
| `volume_errors` | Volume, falhas, reprocessamento e cenário de indisponibilidade | Desconhecidos registrados; sem inventar métricas |
| `dependencies` | Quem fornece acesso, ambiente, contas, homologação e validação? | Responsáveis e bloqueios identificados |
| `budget_timeline` | Faixa de investimento, data real de necessidade e urgência | Cliente confirmou ou marcado `não informado` |
| `acceptance_owner` | Quem demonstra o resultado e quem pode aceitá-lo? | Responsável e evidências definidos |
| `maintenance` | Quem recebe alertas, opera exceções, paga SaaS/APIs, solicita mudanças? | Fronteiras e responsáveis combinados |

Se o pedido incluir **gestão contínua de redes sociais, produção de vídeos, tráfego pago, design recorrente ou manutenção genérica de e-commerce**, separar essas atividades da oferta técnica. Podem virar serviços distintos, **não** escopo implícito deste pacote.

## 3. Template de escopo para cada proposta

Todos os marcadores abaixo são **campos a preencher por pessoa autorizada** antes de oferta formal. Não copiar marcadores literais para documento enviado.

| Campo | Template |
| --- | --- |
| Referência | `[id privado da oportunidade]`; `[versão do brief]`; oferta `client0-integration-flow-v1` |
| Fluxo-alvo | `[evento de início] → [transformação/regras] → [destino] → [resultado verificável]` |
| Objetivo de negócio | `[problema informado pelo cliente e efeito esperado]` |
| Origem/destino | `[sistemas, versões, APIs e responsáveis confirmados]` |
| Entradas e regras | `[campos mínimos, validação, mapeamento, casos inválidos]` |
| Tratamento de falhas | `[duplicação, timeout, estado remoto desconhecido, reprocessamento humano]` |
| Critérios de aceite | `[testes observáveis, dados sintéticos, falhas, segurança, evidência de execução]` |
| Entregáveis | `[integração/configuração]`, `[testes]`, `[instruções de operação]`, `[handoff de acessos sem expor segredos]` |
| Dependências do cliente | `[contas/API/permissões/homologação/pessoa de aceite]` |
| Exclusões | `[novos fluxos/canais]`, `[funcionalidades não acordadas]`, `[marketing/design contínuo]`, `[licenças e tarifas de terceiros]` |
| Mudança de escopo | `[critério, revisão comercial, aceite da versão revisada]` |
| Condições comerciais | `[preço, impostos, moeda, marcos, prazo, validade e cobrança no back-office autoritativo]` |
| Suporte | `[janela, canal, horas/limites, responsável e preço quando aprovado]` |
| Aprovações | `[responsável/horário para escopo]`, `[responsável/horário para preço]`, `[autorização de envio]` |

**O sistema core mantém somente o brief técnico**; o documento formal e condições comerciais aprovadas pertencem ao ERPNext/back-office (ou ao fallback manual privado com controle de versão), conforme ADR 0001. `ready_for_review` **não** equivale a aprovação nem a envio.

### Critérios técnicos mínimos de aceite (selecionar e ajustar)

1. **Caminho positivo**: dado de teste com pré-condições válidas percorre um fluxo e gera exatamente o resultado **observável especificado**, não apenas HTTP 200.
2. **Entrada inválida**: dado ausente/fora do formato previsto produz falha controlada, sem efeitos colaterais inesperados.
3. **Replay/duplicação**: definir chave/semântica e evidenciar comportamento seguro na mesma requisição; **não afirmar exactly-once distribuído** sem prova do destino.
4. **Falha de integração**: desconexão, credencial revogada ou timeout possuem resultado diagnosticável; timeout após possível efeito remoto fica `unknown`, **não** dispara repetição cega.
5. **Segurança**: menor privilégio, proteção de credenciais, acesso autorizado, logs sem dados pessoais desnecessários e nenhuma exposição pública não autorizada.
6. **Operação**: documentação curta de instalação, configuração, execução, parada, recuperação e proprietário das dependências.
7. **Aceite do cliente**: evidência dos cenários acordados, versão exata, exceções e pessoa que validou, **separado da aprovação interna**.

Esses são **critérios candidatos**, não promessa de que todo sistema externo suporta idempotência. Se uma condição não for tecnicamente possível, registrar exceção e reaprovar escopo antes de fechar proposta.

## 4. Sequência de entrega e controles

| Gate | Ação e evidência | Bloqueio |
| --- | --- | --- |
| Q1 — Qualificação | Confirmar problema, acesso, orçamento e prioridade | Escopo não verificável → acompanhar, não precificar no escuro |
| Q2 — Diagnóstico | Versão inicial do fluxo, riscos, dependências e plano de teste | Sem APIs/permissões → não prometer integração |
| Q3 — Revisão técnica | Brief versionado em `draft` / `ready_for_review` | Revisão interna não é aprovação |
| Q4 — Comercial | Documento formal do back-office, preço, condições e autorização humana da versão | Sem preço aprovado → não enviar |
| Q5 — Aceite comercial | Confirmar versão aceita, identidade, evidência e condições de cobrança | Sem aceite → não começar execução contratual |
| Q6 — Entrega | Implementar somente escopo aprovado; testes, evidências e runbook | Falha ou novo escopo → reabrir revisão |
| Q7 — Aceite técnico | Critérios conferidos pelo cliente; registrar pendências | Não declarar entregue por execução local isolada |
| Q8 — Cobrança | Emitir/conciliar segundo marcos combinados no financeiro | Não marcar pago por status do código |
| Q9 — Pós-venda | Registrar suporte, medir resultado e tratar incidentes | Sem medição/autorização → não publicar case |

**Fallback permitido:** registro privado manual, referência ao documento financeiro real e revisão humana. Não exigir ERPNext integrado para executar um ensaio humano, mas **não declarar instalação/integração ERP funcional** sem teste de sua instância.

## 5. Estimativa, custos e suporte — campos em aberto

**Proibido presumir** valor, prazo, ROI, SLA, volume ou consumo de provider. O operador deverá registrar e aprovar separadamente:

- custo estimado em horas de diagnóstico, implementação, teste, implantação e documentação;
- infraestrutura/licenças/consumo de APIs de terceiros e quem as contrata/paga;
- risco de manutenção, credenciais, limites de API, mudanças do fornecedor;
- faixa de preço, impostos, condições de pagamento e reserva para contingência;
- prazo viável condicionado ao recebimento de acessos/insumos do cliente;
- política de suporte, mudanças e critério para término.

`[a definir após diagnóstico]` é resposta aceitável **internamente**. Para envio ao cliente, substituí-la por termo comercial aprovado ou explicitar formalmente a pendência sem criar obrigação indevida.

## 6. Demonstração para portfólio (não é case de cliente)

É permitido preparar **um fluxo demonstrativo reprodutível**, com entradas e resultados **100% sintéticos**, código/testes executáveis, captura de evidência e descrição clara de limitações. Rotular explicitamente como **demonstração técnica**, sem atribuir ao cliente real, sem inventar economias/depoimentos e sem exibir tokens, URLs privadas ou dados coletados.

Antes de usar uma entrega verdadeira como case: estabelecer baseline de resultado, medir depois, confirmar a fonte da métrica e obter **consentimento explícito e específico** para citar nome, marca, imagens, dados, números ou testemunho. Ausência de permissão significa publicar no máximo relato anonimizado **se** também não identificar pessoa/empresa e houver direito de divulgação do conteúdo.

## 7. Gate de conclusão deste template

Template está pronto para **preenchimento e revisão**, mas não prova prontidão comercial até haver:
- um serviço escolhido e fronteiras conhecidas;
- pergunta de diagnóstico e critérios de aceite compreensíveis;
- responsáveis por aprovação, cobrança, implantação e suporte;
- preço, prazo, impostos e condições tratados pelo sistema/processo comercial apropriado;
- evidências reais e consentimentos **nunca fabricados**.

A F2 **não** pode ser encerrada com este arquivo: requer ciclo real rastreável até recebimento e avaliação de resultado, conforme roadmap.
