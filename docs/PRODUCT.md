# Product

## Vision

Business Automation API is evolving into a horizontal, reusable AI Business Automation Platform: multi-tenant, configurable per company, and supporting service, CRM, automation, AI, and API integrations. It must provide a shared core for companies in different segments rather than a separate system per customer or hardcoded niche rules. A future SaaS model is possible.

## Commercial strategy

In the short term, the platform will also support delivery of real automation services to clients. It does not need a complete self-service SaaS experience before creating commercial value. Real usage should validate the shared core; customer adaptations should preferably be configuration over that core, not forks or independent applications.

The project also demonstrates development, AI, automation, and security capabilities.

## Validation cases

### Client 0 / dogfooding

Fenato DevSec's own operation is the first demonstration and validation environment for AI service, lead capture and qualification, CRM, automations, channel integrations, and a demonstrable case for portfolio and clients.

### First external client

A buffet/barbecue-party business is the first known external validation case. Discussed needs include publication automation, assistance responding to comments, initial service, lead capture and qualification, scheduling, opportunity organization, marketing, post-sale, reactivation, remarketing, and CRM.

Video editing may be offered as an additional service, but is not a structural core requirement at this stage.

### Second potential case

A drone maintenance company is a potential second case, intended to validate the shared core across a substantially different segment. The core must not gain drone-specific logic.

## Desired capabilities

The product direction includes lead capture and qualification, service, customers, conversation history, CRM, commercial pipeline/status, post-sale, remarketing, reactivation, applicable birthday reminders/actions, scheduling, automations, integrations, analytics, API, and AI agents. These do not all belong in the first MVP.

## Multi-tenancy

`Company` is the logical root of a tenant. The same system must support multiple companies with future data and behavior isolation.

Future per-company configuration may include branding, business description, agent instructions, offered services, hours, service rules, commercial pipeline, automations, knowledge base, and channel settings. The agent should respond according to the Company associated with a Conversation; one global prompt is not the final solution.

## Security

Authentication, authorization, RBAC, and actual tenant isolation are required before public API exposure. A client-provided `company_id` must not be treated as authorization; the tenant must come from authenticated context.

Security and DevSecOps are a technical differentiator, without premature complexity. Never place real credentials, real `.env` files, customer data, or private commercial information in a public repository. Real deployments may need private infrastructure/configuration while the core remains public.

## AI

AI agents are a central product capability. Current integration uses local Ollama, configured through `OLLAMA_URL` and `OLLAMA_MODEL`, with `qwen3:8b` as the current default. This runtime model is distinct from the programming agent used to develop the project.

Per-Company agent configuration is an important upcoming capability. RAG and per-company knowledge bases are future capabilities, after adequate data, tenant, company-configuration, and security foundations exist.

## Automation and integrations

n8n may later be used as an automation/integration layer where it accelerates delivery, but must not become a central application-domain dependency. The API must retain its own entities and business rules. Specific providers for service channels, marketing, scheduling, and other external tools remain undefined.

## Principles

1. Reuse before client-specific customization.
2. Configuration by Company before client forks.
3. Solve real problems before increasing feature count.
4. Do not add complex infrastructure without proven need.
5. Security before public exposure.
6. Never put real client data in the public repository.
7. Validate with real clients early.
8. Keep product domain separate from external tools.
9. Avoid coupling to one AI model, channel, or niche.
10. Do not turn every additional commercial service into a SaaS feature.

## Non-goals now

IoT/home automation (including Home Assistant, ESP32, MQTT, Zigbee, curtains, lighting, and outlets) is outside this platform's current scope. Video editing, design, and marketing can be complementary commercial services, but the repository core remains business software, AI, CRM, and automation.

## Open commercial decisions

The following are unresolved and must not be assumed: pricing, plans, monthly fees, usage billing, billing provider, freemium, trial period, commercial contract, SLA, cloud provider, WhatsApp provider, social-network providers, definitive scheduling tool, final onboarding format, exact first commercial MVP boundary, final production architecture, and final strategy between managed service and self-service SaaS.
