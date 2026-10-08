# Architecture Baseline v1 — revisão documental e de decisões

Data: 2026-10-07. Referência: `main@84ea22e` e refs locais inspecionadas.
Esta entrega acrescenta documentos em `docs/architecture/`; não altera nem remove os documentos anteriores. As ações abaixo são propostas explícitas para evitar substituir decisões silenciosamente.

## 1. Documentos atuais: ação objetiva

| Arquivo/seção | Ação recomendada | Motivo e substituição | Prioridade |
| --- | --- | --- | --- |
| `README.md` — Relação com ERP e automação | Atualizar | Retirar lab existente e Dolibarr como trilha permanente; citar ERPNext candidato, n8n/Activepieces opcionais e baseline | P0 documental |
| `README.md` — Estado atual | Atualizar | Remover nota histórica “README anterior estava vazio”; separar implementação real de destino; indicar 11 testes somente como resultado datado | P1 |
| `docs/ARCHITECTURE.md` — Status | Marcar como substituído após aceite da baseline | Documento é reconciliação histórica, não arquitetura operacional completa; linkar baseline como visão vigente | P0 documental |
| `docs/ARCHITECTURE.md` — Local business-automation lab e prioridades 1–2 | Remover da orientação vigente | Lab/bridges não existem como premissa; não mandar agente procurar, operar ou promover esses artefatos | P0 documental |
| `docs/ARCHITECTURE.md` — Dolibarr | Remover como requisito atual | Benchmark não justificado pelo fluxo; ERPNext é candidato principal; avaliação alternativa só por impedimento concreto | P1 |
| `docs/ARCHITECTURE.md` — Productization path | Atualizar | Segurança/restore precisam preceder dados operacionais na API, não aparecer só depois de dogfooding; distinguir piloto sintético de operação | P0 |
| `docs/CLIENT0_FLOW.md` — Goal/Local ERP lab | Remover premissa e substituir | Manter fronteira core/ERP e dados privados sem depender de ambiente antigo | P0 documental |
| `docs/CLIENT0_FLOW.md` — First candidate flow | Expandir visão e manter corte pequeno | Incluir oferta, aprovação, entrega, cobrança e pós-venda como ciclo; primeira implementação continua um único handoff | P1 |
| `docs/CLIENT0_FLOW.md` — comandos candidatos | Atualizar antes do adapter | Não criar Opportunity no ERP por default; definir `ensure_business_party` ou equivalente aprovado, ownership por campo e tratamento de resultado desconhecido | P0 antes de integrar |
| `docs/CLIENT0_FLOW.md` — Acceptance criteria | Clarificar | “Antes de implementar” pede adapter/fake já existentes; distinguir pré-condições documentais de critérios da implementação | P1 |
| `docs/PRODUCT.md` — Vision/AI | Atualizar ênfase | Operação/receita com Client 0 primeiro; IA opcional ao fluxo; multi-tenant é direção, não SaaS já decidido | P1 |
| `docs/PRODUCT.md` — casos externos | Reconfirmar/reclassificar | Segmentos são hipóteses históricas; não afirmar cliente contratado nem prioridade atual sem confirmação | P1 |
| `docs/PRODUCT.md` — Open commercial decisions | Preservar e complementar | Continuam abertos preços, SLA, canais, cloud e modelo comercial; adicionar primeira oferta/fonte, ownership aprovado e recovery targets | P1 |
| `docs/ROADMAP.md` — NOW/NEXT | Substituir por gates | Segurança não deve ficar atrás de agente configurável; falta operação de propostas/entrega/cobrança; incorporar plano incremental | P0 |
| `docs/ROADMAP.md` — Billing/subscriptions | Dividir | Cobrança de serviços é necessária; assinaturas SaaS continuam adiadas | P0 |
| `docs/DECISIONS.md` | Atualizar status/indexar ADRs | Não apagar decisões antigas; registrar superseded com data/motivo e ligação à decisão nova | P0 documental |
| `AGENTS.md` — “Atualmente existem 9 testes” | Remover frase fixa | Há 11 testes definidos no checkout; já existe instrução correta de usar resultado atual | P1 |
| `AGENTS.md` — arquitetura e workflow | Preservar; depois incluir leitura orientada da baseline | Não mudar regras de segurança/checkpoint/revisão por inferência; tarefa atual proíbe push e não fez commit | P1 |
| `migrations/README` | Expandir em tarefa de fundação | Texto genérico não explica baseline vazia, instalação legada nem validação descartável | P1 |
| `.env.example` | Preservar agora | Valores de exemplo e modelo atual não são configuração de produção nem modelo obrigatório do Pi; evoluir somente com feature/config correspondente | P2 |
| `pyproject.toml` e `src/business_automation/__init__.py` | Registrar dívida, não alterar nesta tarefa | Descrição placeholder e entry point de saudação não representam inicialização da API | P2 |

Não remover arquivos inteiros automaticamente. Recomenda-se transformar `docs/ARCHITECTURE.md` em página curta de entrada com nota histórica quando a baseline for aceita. Os outros documentos mantêm papéis distintos: produto, plano, decisões e fluxo concreto. Remover premissas ultrapassadas da orientação corrente; preservar o histórico Git.

## 2. Decisões existentes: manter, alterar ou retirar

Todas as decisões listadas abaixo constam em `docs/DECISIONS.md` com data 2026-09-01. A classificação é proposta; o arquivo original permanece intacto nesta entrega.

| Decisão existente | Disposição | Precisão necessária |
| --- | --- | --- |
| Horizontal reusable core | Manter | Reutilização guiada por processos reais, não abstração universal antecipada |
| Company is the logical tenant root | Manter | Company do core é workspace; Customer comercial e Company contábil ERP são conceitos distintos |
| Avoid separate systems per client | Alterar redação | Proibir forks de produto; permitir instalações isoladas do mesmo artefato como estratégia inicial |
| Validate with Client 0 and real businesses | Manter | Client 0 valida receita, entrega e operação com dados protegidos |
| First external validation client | Reclassificar | Hipótese/caso histórico a reconfirmar; não dependência arquitetural nem contrato presumido |
| Second potential validation case | Manter como hipótese | Não inserir lógica de segmento no core nem assumir prioridade |
| Security before public exposure | Manter e ampliar gate operacional | Dados reais na API exigem acesso controlado; exposição/compartilhamento exigem isolamento comprovado |
| Per-Company agent configuration | Manter, ajustar sequência | Após fundação de acesso/dados, apenas parâmetros necessários; provider não é identidade do domínio |
| RAG later | Manter | Reabrir só com caso de conhecimento mensurado e isolamento |
| Billing later | Substituir parcialmente | Cobrança operacional agora via ERP/processo; billing SaaS/subscriptions depois |
| n8n as an auxiliary future tool | Manter e ampliar alternativa | n8n ou Activepieces quando necessário; regras centrais permanecem em dono explícito |
| Exclude IoT/home automation | Manter | Fora deste repositório |
| Do not make video/marketing the software core | Manter | Serviço complementar não vira módulo obrigatório |

Decisões adicionais propostas pela baseline: monólito modular; ownership por campo; ERP para back-office maduro; efeitos externos idempotentes/reconciliáveis; IA sem autoridade comercial; jobs duráveis apenas diante de necessidade; revisão/restore como gate operacional. Registrar ADRs pequenos ao aceitar cada uma, sem carimbar decisões comerciais abertas como aceitas.

## 3. História útil sem importação implícita

| Referência local | O que oferece | Tratamento recomendado |
| --- | --- | --- |
| `29330b0` / branch migration-baseline-review | Bootstrap de leads e alteração da raiz histórica | Analisar compatibilidade com instalações legadas; não copiar nem executar sem tarefa e revisão |
| `17a1fe7` | Check de exatamente um owner | Reavaliar junto de integridade cross-company; não confundir XOR com isolamento |
| `c4ca998` | Configuração de agente por Company | Referência para contratos/testes; não priorizar antes de acesso |
| `7d6f3e9`, `1407669`, `5900474` | Sessões, memberships, autorização e auditoria | Reutilização possível por recorte após revisão de segurança; não atestada por inspeção histórica |
| `origin/chore/pre-transition-checkpoint-2026-09-13` | Checkpoint anterior à transição local | Evidência histórica, não base de runtime ou recuperação operacional atual |
| `origin/docs/portfolio-positioning` (`8346742`, `1e1f091`) | Apresentação de portfólio e descrição do pacote | Incorporar apenas o que é verdadeiro e útil; operação/receita prevalecem sobre apresentação de case |

Nenhuma dessas referências prova instalação ativa, suíte passando hoje ou review concluído. Não executar scripts antigos que criam containers/migrations durante uma revisão documental.

## 4. Ordem da reconciliação

1. Aceitar/ajustar baseline e primeiro fluxo com decisões comerciais necessárias.
2. Revisar README/ARCHITECTURE/ROADMAP para apontarem à direção nova, removendo lab e ambiguidade de billing.
3. Atualizar DECISIONS com status de substituição, sem apagar justificativas históricas.
4. Revisar PRODUCT e CLIENT0_FLOW com oferta/fonte/ownership concretos; remover contagem fixa em AGENTS.
5. Criar ADRs/contracts/runbooks somente quando seus pacotes entrarem em execução.

Essa sequência é uma proposta de trabalho futuro. Nenhum desses documentos anteriores foi alterado para fabricar consenso com a baseline.
