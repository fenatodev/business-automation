# F2 — Sandbox n8n de atendimento comercial autônomo

## Objetivo e estado
Workflow **exclusivamente sintético**, para validar as duas frentes sem infraestrutura adicional:
- Recuperação de orçamentos/propostas pendentes.
- Qualificação inicial de leads inbound consentidos.

**NÃO É PRODUÇÃO.** Nenhum webhook, disparo de mensagem, CRM real, serviço pago ou contato externo está integrado. Não usar resultados sintéticos como prova comercial. O workflow é importado **desativado**; o Schedule Trigger serve apenas como ponto de integração futuro. Nenhuma tarefa é agendada por padrão.

## Arquitetura observada no Ubuntu (14/10/2026)
- n8n Community **2.40.7**, self-hosted via `/mnt/infra/apps/n8n/compose.yaml`.
- Banco n8n: SQLite privado em `/mnt/infra/apps/n8n/data`, sem workflows existentes antes do piloto.
- n8n está **sem portas publicadas no host**; não alterar binding por este WP.
- business-automation usa FastAPI/PostgreSQL (loopback); Qwen 3.5 9B disponível **somente enquanto PC ligado**.
- MXQ4K tem SD Armbian preparado, porém **CPU, RAM, boot, IP, armazenamento e SSH ainda não verificados**. Não há confirmação de que possa operar n8n 24x7.
- Site estático portátil já preparado: **preferir hospedagem estática gerenciada gratuita para site público**; considerar MXQ somente após benchmark, backup e rede segura. Nenhum deploy autorizado por este documento.

## Workflow do sandbox
Arquivo: `automation/n8n/f2-commercial-sandbox.json`.

`Manual Sandbox Trigger` e `Daily Simulation Trigger` compartilham um conjunto fechado de 9 registros fictícios, de duas categorias (`quote` e `inbound_lead`). A política determinística aplica, nesta ordem: formato válido, Company permitida, deduplicação **dentro da execução**, opt-out, opt-in, antiguidade mínima da proposta, template aprovado fora da janela. O resultado prepara dois **rascunhos internos** e um relatório de decisão. **Não há nó de envio.**

Resultado esperado da simulação: 9 registros avaliados, 2 rascunhos, 0 mensagens enviadas, 1 tenant fora do escopo bloqueado, 1 opt-out, 2 sem opt-in, 1 duplicata, 1 template não aprovado e 1 follow-up prematuro.

### Limitações explícitas
- Deduplicação por `Set` JS vale **somente dentro da execução**: não fornece idempotência entre reinícios. Para produção é obrigatório evento persistente em Postgres (chave única por Company/contato/ação/janela).
- A política atual opera sobre **fixtures**, não consultas ao PostgreSQL real. Não contém IA generativa nem agente conversacional; estes entram após testes do contrato e política de canais.
- O trigger diário permanece **inativo** até uma nova autorização; não ativar cron sem definir retenção, recursos e objetivo.
- O isolamento real multiempresa deve ser imposto **também no domínio/API**, não somente por string `company_id` dentro do n8n.
- Mensagens externas somente após opt-in/base legal, template e janela oficial quando aplicável, limites de custos, identidade válida, autorização por campanha/canal e opt-out. Sem WhatsApp Web não oficial.

## Validação permitida
1. Verificar JSON com `python -m json.tool automation/n8n/f2-commercial-sandbox.json >/dev/null`.
2. Verificar que `active = false`, apenas 5 nós e **nenhum nó externo** (`httpRequest`, `emailSend`, `webhook`, etc.).
3. Executar somente teste sintético manual em n8n local sem porta pública.
4. Antes de importar, verificar configurações e fazer backup seguro/consistente do banco n8n. Não interromper outros workflows.
5. Ao finalizar, n8n deve continuar restrito e a branch `main` intacta.

## Caminho para operação real com intervenção por exceção
1. Autorização por **política versionada** (domínio, empresa, consentimento, janelas, templates, limites e kill switch).
2. Entrada via adaptadores oficiais, **Company derivada da autenticação**, nunca do payload externo.
3. Idempotência transacional em PostgreSQL, outbox de efeitos externos e reconciliação de status de entrega.
4. n8n agenda/reexecuta workflows; FastAPI valida regras e autoriza transições; modelo gera apenas conteúdo estruturado.
5. Falhas e reclamações passam para exceção humana; ações ordinárias prosseguem automaticamente.
6. Monitoramento, backup verificado, host 24x7 confiável e integração com LLM fora do PC (se necessário) antes do piloto real.

## Licenciamento
Conforme FAQ oficial da n8n (set/2026), a edição Community permite que uma agência opere workflows **em instância própria** para clientes que recebem resultados, **sem acesso à construção/edição** de fluxos. Não permite oferecer n8n como serviço para clientes criarem/editarem workflows. Verificar versão vigente e enquadramento do produto antes de comercializar.

Referências: https://docs.n8n.io/n8n-community-license/community-license/license-faq , https://docs.armbian.com/user-guide/faq/ , https://docs.armbian.com/getting-started/sd-cards/

**Governança:** este protótipo não autoriza contato com empresas, tratamento de dados pessoais, publicação de site, abertura de portas ou backup real. Ver issue #81.
