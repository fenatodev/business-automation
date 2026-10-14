# F2 — núcleo autônomo com estado persistente (somente sandbox)

## Resultado alcançado em 14/10/2026
Este WP introduz um **núcleo interno testável** para a operação comercial autônoma:
- recepção de um sinal **fictício** de orçamento atrasado ou lead inbound;
- avaliação de política versionada (empresa confiável, canal, prazo de validade, consentimento verificado, opt-out, janela/template, idade da proposta e limite semanal);
- elaboração automática de um **rascunho**, usando template local ou **Qwen 3.5 9B local** opcional;
- registro transacional de decisões + fila em SQLAlchemy;
- deduplicação por `(company_id, event_id)`, detecção de replay contraditório e isolamento por Company;
- lease com prazo, recuperação após reinício, retry exponencial e estado terminal da **simulação**.

Arquivos: `app/services/autonomy_core.py`, `app/services/autonomy_local_qwen.py`, `tests/test_autonomy_core.py`, `tests/test_autonomy_local_qwen.py`.

**Esta não é uma plataforma 24x7 implantada.** A fila não tem despachante real, canal de saída, webhook, jobs ativos nem serviço de sistema. A única confirmação aceita pela API de exemplo chama-se `finish_simulation` e grava estado `simulated`, nunca `sent`. Nenhum cliente foi contatado.

## Relação com n8n
PR #82: workflow sintético de 5 nós importado **inativo** como `f2-commercial-demo` na instalação n8n 2.40.7 já existente, sem portas públicas, com execução CLI local bem-sucedida.

O núcleo deste WP **não é executado pelo n8n ainda**. Uma etapa seguinte deverá conectar o n8n como agendador/orquestrador ao backend privado autenticado, sem conceder ao n8n ou ao modelo permissão implícita para despachar mensagens. Os dados de identidade e opt-in devem vir de fontes verificadas, não de JSON de webhook sem autenticação.

## Persistência: o que está comprovado e o que falta
A persistência foi ensaiada com **SQLite descartável em diretórios temporários de teste**, usando os modelos SQLAlchemy orientados ao futuro PostgreSQL. Testes incluem sessão fechada/reaberta, replays, retries e expiração de lease. **Nenhuma tabela nova foi criada no PostgreSQL operacional.**

Antes da utilização real, executar uma WP própria de revisão/geração de **migration Alembic** para `autonomy_decisions` e `autonomy_jobs` e executar apenas em PostgreSQL descartável. Revisar índices, integridade referencial, bloqueios `FOR UPDATE SKIP LOCKED`, revalidação de consentimento e política no momento do envio, e unicidade de cadência por caso em concorrência multiworker. **Não executar migrations sem autorização específica.**

`CampaignPolicy` atualmente é objeto imutável fornecido pelo chamador. Antes de produção deverá existir **repositório autenticado e auditável de políticas aprovadas por um humano**, com versões, expiração e revogação; nunca ler permissões das mensagens/rascunhos gerados por IA.

**Cuidado:** estes modelos permanecem sem importação em `app/main.py`. Nenhuma API pública ou serviço em execução foi alterado. O worker da demo faz apenas lease/ack **simulado** e não cumpre ainda SLA, escala, continuidade 24h ou despacho real.

## Qwen local
`LocalQwenDraftComposer` aceita apenas `qwen3.5-9b` em `127.0.0.1:1251/v1/chat/completions`, `trust_env=False`, timeout limitado, sem chaves externas. O único dado enviado ao modelo é a classe `quote` ou `inbound_lead`. Não são enviados telefone, nome, conteúdo de mensagens, preços, identidade de clientes nem documentos. Há validação de tamanho, texto e termos perigosos. Se o modelo falhar, o evento fica como `escalate` **sem fila de envio**.

Prova local com sinal inteiramente fictício: resposta do Qwen 9B em **3,73 segundos**, sem qualquer envio de mensagem. A latência varia com GPU e carga; este é **um teste**, não um benchmark de SLA.

## Próximas WPs, em ordem técnica
1. **Revisão de contratos e migration PostgreSQL descartável**; preservar isolamento por Company em APIs, jobs e consultas. Simular concorrência real e deduplicação.
2. **Aprovação por política persistente:** opt-in com origem e timestamp verificável, opt-out e supressão durável, janelas por canal, templates oficiais, teto de custos, lista de serviços e escalonamento humano.
3. **n8n ↔ FastAPI via endpoint interno autenticado**, sem webhook público; fila durável com timeout, retry, dead-letter e heartbeat supervisionado. Revalidar todos os gates imediatamente antes de cada efeito externo.
4. **Adaptadores oficiais de comunicação** (somente após autorização de canal/campanha), inbox inbound consentido e status de entrega; sem Whatsapp Web não oficial.
5. **Host 24x7 e observabilidade:** MXQ RK322x ARMv7/970 MiB não atende stack n8n+PostgreSQL+LLM. PC Ubuntu só opera enquanto ligado; escolher host adequado antes de vender disponibilidade.
6. Demonstração ponta a ponta gravando métricas sintéticas e posterior validação comercial humana dos critérios de aceite e margens.

## Governança
Não executar contatos, pagamentos, descontos, publicação de site, migração real, abertura de portas, ingestão de dados pessoais, criação de contas em provedores ou contratação de APIs com este WP. Os dois fluxos comerciais continuam obrigatórios: **recuperação de propostas** e **qualificação de inbound**. Mensagens geradas por modelo são **conteúdo, não autorização**.

Issues #78 e #81; PR #82 precede a integração n8n.
