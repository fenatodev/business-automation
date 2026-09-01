# Decision Log

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
Status: Accepted  
Decision: Prefer configuration over client forks or independent applications.  
Rationale: Customer adaptations should validate and evolve the reusable shared core.

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
Status: Accepted  
Decision: Defer billing and subscriptions.  
Rationale: Billing is not a current priority and belongs to a possible later self-service SaaS evolution.

## 2026-09-01 — n8n as an auxiliary future tool

Date: 2026-09-01  
Status: Accepted  
Decision: Use n8n only as a potential future automation/integration aid, not as central domain.  
Rationale: It may accelerate integrations while the API must retain its own entities and business rules.

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
