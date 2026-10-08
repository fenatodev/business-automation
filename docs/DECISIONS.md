# Decision Log

## 2026-10-08 — WP-008: lifecycle de dados do Client 0

Status: Accepted para F1 / piloto privado.

Decision: aplicar minimização e lifecycle manual controlado antes do primeiro uso real do core. O core mantém apenas os dados necessários ao fluxo operacional sob sua autoridade; ERPNext/back-office permanece autoritativo para financeiro/fiscal; segredos não são dados de negócio; backup não cria retenção indefinida; exportação, correção e exclusão são procedimentos humanos no piloto e qualquer operação destrutiva sem mecanismo seguro exige tarefa própria.

Rationale: a fundação técnica de F1 já demonstra migrations/recovery, isolamento, backup/restore, bind privado, revogação e logs mínimos. O lifecycle fecha o risco restante de transformar o piloto em retenção descontrolada ou duplicar fontes de verdade antes de existir demanda para automação de governança.

Limits: esta é política operacional do piloto privado, não substitui avaliação jurídica/contábil, não define prazo fiscal universal, não autoriza coleta em massa, scraping, exposição pública ou categorias sensíveis.

Reference: [Client 0 — ciclo de vida de dados](operations/data-lifecycle.md).


## 2026-10-08 — ADR 0003: acesso privado e isolamento por Company

Status: Accepted para F1 / piloto privado.

Decision: usar Bearer API keys opacas configuradas fora do Git, identificadas na aplicação somente por SHA-256, com papéis mínimos `admin` e `operator`. `operator` é vinculado server-side a exatamente uma Company; `company_id` de payload/path nunca é autorização. Admin administra Companies e não ganha acesso implícito a dados tenant.

Rationale: fecha a API anônima e permite provar isolamento cross-tenant sem antecipar OAuth/OIDC/JWT, usuários persistidos ou IAM de SaaS antes de existir necessidade real.

Reference: [ADR 0003](architecture/adr/0003-access-and-tenancy.md).


## 2026-10-08 — ADR 0002: recuperação da cadeia Alembic

Status: Accepted.

O [ADR 0002](architecture/adr/0002-migration-recovery.md) define que a cadeia atual deve ser validada e reparada somente em PostgreSQL descartável. A estratégia candidata insere um bootstrap de `leads` antes da baseline histórica, preservando revisions posteriores e validando separadamente banco vazio e fixture legacy. A branch histórica de migration review serve apenas como referência; não é autorizada para merge em bloco.

## 2026-10-08 — ADR 0001: data ownership do Client 0

Status: Accepted.

O [ADR 0001](architecture/adr/0001-data-ownership.md) define o ownership do primeiro ciclo Client 0: CRM/qualificação/conversas e estado técnico no core; documentos comerciais formais, preço final e financeiro no ERPNext; aprovações sensíveis permanecem humanas. O primeiro handoff recomendado é criar/assegurar a contraparte de back-office sem duplicar o pipeline no ERP.

## 2026-10-07 — WP-001: direção arquitetural vigente

Status: Accepted.

A [Architecture Baseline v1](architecture/baseline-v1.md) passa a ser a referência arquitetural oficial do repositório. Esta decisão formaliza sua adoção, embora o documento original ainda registre o status de proposta da elaboração. Recomendações de implementação e decisões comerciais abertas continuam sujeitas aos seus gates; adoção não significa funcionalidade implementada nem autorização de deploy ou migrations.

Direção aceita:

- Client 0 é a operação da própria empresa: oportunidades, vendas, propostas, entrega, cobrança, suporte e geração de cases.
- ERPNext é o **back-office padrão inicial**, substituindo a formulação de mero candidato. Implantação, aderência e integração ainda precisam ser validadas; não reimplementar funções maduras de ERP sem justificativa.
- Cobrança de serviços é necessária agora, via processo operacional e back-office. Billing de SaaS, assinaturas self-service e cobrança por uso ficam para depois.
- Monólito modular, core horizontal, IA desacoplada de provider e implementação incremental em pacotes autossuficientes.
- n8n ou Activepieces podem executar automações auxiliares; não são a fonte central das regras de domínio.
- Configuração em vez de forks por cliente; instalações segregadas do mesmo código são permitidas. Company continua raiz lógica do tenant, distinta do cliente comercial do Client 0.

Preços, SLA, primeira oferta/fonte, providers de canais e demais decisões comerciais não são definidos por este registro.

### Substituições e histórico

| Direção anterior | Situação a partir do WP-001 | Referência histórica |
| --- | --- | --- |
| Reconciliação dependente de laboratório local, inventário e promoção de artefatos antigos | Substituída; lab e bridges antigos não são componentes existentes nem dependências do projeto | `docs/ARCHITECTURE.md` e README em `17b1626`, preservados em `main@84ea22e` |
| Dolibarr como avaliação/benchmark permanente | Retirada da direção padrão; ERPNext é o back-office inicial | Mesmos documentos e commits |
| ERPNext como candidato principal | Substituída pela adoção como padrão inicial, sem alegar instalação existente | Mesmos documentos e baseline original |
| Adiamento genérico de billing | Parcialmente substituído: cobrança de serviços agora, SaaS billing depois | Registro “Billing later” de 2026-09-01 abaixo |
| Evitar sistemas separados por cliente | Esclarecida: evitar forks, permitir isolamento de implantação com o mesmo código | Registro “Avoid separate systems per client” abaixo |
| Roadmap com agente configurável antes de segurança e cobrança apenas em LATER | Substituído pelos gates de fundação, operação assistida e automação gradual | `docs/ROADMAP.md` em `main@84ea22e` |

Os textos originais das decisões abaixo e o histórico Git são preservados. Premissas incompatíveis em documentos ainda não reconciliados, como `CLIENT0_FLOW.md`, ficam superadas por esta decisão; não devem orientar novas dependências.

Consulte [Arquitetura vigente](ARCHITECTURE.md) e [Roadmap](ROADMAP.md). Esta reconciliação altera apenas documentação.

## 2026-09-01 — Horizontal reusable core

Date: 2026-09-01  
Status: Accepted  
Decision: Use a horizontal, reusable core for multiple companies.  
Rationale: The platform must support businesses in different segments without hardcoded niche rules.

## 2026-09-01 — Company is the logical tenant root

Date: 2026-09-01  
Status: Accepted  
Decision: Use Company as the logical root of a tenant.  
Rationale: The same system must support multiple companies with future data and behavior isolation.

## 2026-09-01 — Avoid separate systems per client

Date: 2026-09-01  
Status: Clarified by WP-001 (2026-10-07); original wording preserved below.

Decision: Prefer configuration over client forks or independent applications.  
Rationale: Customer adaptations should validate and evolve the reusable shared core.

Current interpretation: prefer configuration over client forks; separate deployments of the same code are allowed to provide operational and data isolation. See the WP-001 adoption above.

## 2026-09-01 — Validate with Client 0 and real businesses

Date: 2026-09-01  
Status: Accepted  
Decision: Validate the product with Client 0 and real businesses.  
Rationale: The short-term strategy is to generate value through real automation services and learn from actual use.

## 2026-09-01 — First external validation client

Date: 2026-09-01  
Status: Accepted  
Decision: Use a buffet/barbecue-party business as the first known external validation case.  
Rationale: It is the first external client case with discussed automation, service, lead, scheduling, CRM, marketing, post-sale, and reactivation needs.

## 2026-09-01 — Second potential validation case

Date: 2026-09-01  
Status: Accepted  
Decision: Treat a drone maintenance company as a second potential validation case.  
Rationale: It can validate whether the shared core serves a substantially different segment without drone-specific core logic.

## 2026-09-01 — Security before public exposure

Date: 2026-09-01  
Status: Accepted  
Decision: Require security and tenant isolation before public API exposure.  
Rationale: Authentication, authorization, RBAC, and actual tenant isolation are mandatory before exposure.

## 2026-09-01 — Per-Company agent configuration

Date: 2026-09-01  
Status: Accepted  
Decision: Evolve toward specific agent configuration by Company.  
Rationale: The agent should respond according to the Company associated with a Conversation rather than relying permanently on one global prompt.

## 2026-09-01 — RAG later

Date: 2026-09-01  
Status: Accepted  
Decision: Defer RAG and per-company knowledge bases.  
Rationale: They require an adequate foundation of data, tenant, company configuration, and security.

## 2026-09-01 — Billing later

Date: 2026-09-01  
Status: Partially superseded by WP-001 (2026-10-07); original decision preserved below.

Decision: Defer billing and subscriptions.  
Rationale: Billing is not a current priority and belongs to a possible later self-service SaaS evolution.

Current direction: service invoicing, receivables and collection belong to the Client-0 operation now, using the back-office and human procedures where needed. Only SaaS billing, self-service subscriptions and usage billing remain deferred.

## 2026-09-01 — n8n as an auxiliary future tool

Date: 2026-09-01  
Status: Extended by WP-001 (2026-10-07); original decision preserved below.

Decision: Use n8n only as a potential future automation/integration aid, not as central domain.  
Rationale: It may accelerate integrations while the API must retain its own entities and business rules.

Current direction: n8n or Activepieces may serve as an optional auxiliary engine when a concrete flow justifies it. Neither becomes the domain authority.

## 2026-09-01 — Exclude IoT/home automation

Date: 2026-09-01  
Status: Accepted  
Decision: Exclude IoT/home automation from the current scope.  
Rationale: The repository core remains business software, AI, CRM, and automation.

## 2026-09-01 — Do not make video/marketing the software core

Date: 2026-09-01  
Status: Accepted  
Decision: Do not turn video editing, design, or marketing services into the software core.  
Rationale: They may be complementary commercial services but are not structural core requirements.
