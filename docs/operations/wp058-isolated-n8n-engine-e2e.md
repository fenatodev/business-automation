# WP-058 — teste isolado do motor n8n (sem Computer Use)

**Status:** procedimento de validação, não evidência de PASS. Executar somente com dados sintéticos. A branch mantém o workflow comercial de 5 nós inativo.

## Problema demonstrado

Na instância n8n 2.40.7 já em execução, `n8n execute-batch --ids=...` falhou com `Task Broker's port 5679 is already in use`. Portanto, **não** executar a CLI contra a mesma instância, matar o n8n existente, desabilitar a autenticação ou publicar o webhook para forçar sucesso.

Uma cópia descartável chamada `WP058 EPHEMERAL ENGINE PROBE - INACTIVE`, ID `d03b4f8a-3d73-4118-9649-3fb7352100e7`, foi criada nessa investigação. **Removê-la pelo mecanismo oficial autorizado** (API com escopo adequado ou UI legítima) depois de verificar exatamente o ID. Nunca editar o banco interno diretamente.

## Harness proposto (isolamento obrigatório)

1. Criar um projeto Compose temporário, identificador e rede Docker **separados** da instância n8n principal. Usar armazenamento temporário próprio, `N8N_ENCRYPTION_KEY` e credenciais de teste próprias; **não montar** `/mnt/infra/apps/n8n/data`, nem reutilizar o banco ou a encryption key da instância principal.
2. Reutilizar a imagem n8n 2.40.7 já baixada. Para eliminar a colisão de porta, executar o mecanismo de teste na instância descartável sem disputar o broker do n8n principal; se a versão exigir um broker próprio, garantir isolamento de namespace/rede/portas. Não publicar portas no host nem abrir entrada externa.
3. Para validar o caminho de entrada, importar uma **cópia descartável** do JSON de 5 nós; usar autenticação Header Auth temporária, sem recuperar segredos da instância existente. Criar também uma credencial Bearer operator temporária correspondente **somente** ao ambiente descartável do FastAPI/PostgreSQL.
4. A solução de teste precisa realmente entregar ao primeiro nó um evento equivalente a `{ "body": { "channel": "test", "message": "solicitacao ficticia", "event_id": "wp058-e2e-<id-unico>" } }`. Não declarar 5/5 PASS se apenas executar um manual trigger, fizer `curl` direto ao FastAPI ou verificar contratos de JSON.
5. Verificar na evidência de execução do n8n a passagem e saída de **todos os 5 nós**, o POST autenticado ao FastAPI descartável, HTTP esperado, persistência no PostgreSQL de teste, `GET /review-queue/` e idempotência com repetição do mesmo `event_id`. O teste repetido deve manter 1 linha.
6. Evitar `pip install` toda vez: preferir Dockerfile/lockfile já existentes, build/cache local e `ops/private-api/compose.private.yml` apenas se for seguro e autorizado no ambiente isolado. Não iniciar serviços pagos.
7. Desligar e remover **somente** os recursos identificados como descartáveis deste teste. Não tocar os 3 workflows comerciais/históricos, credenciais reais, PostgreSQL principal, `main` ou fluxos públicos.

## Condições de aceitação

- E2E `PASS` apenas com IDs e status da execução n8n e evidência dos 5 nós + linha de PostgreSQL de teste.
- `BLOCKED` se não existir mecanismo oficial de injetar evento no gatilho sob isolamento ou se a autorização para acesso estiver indisponível. Não procurar contornos.
- Relatar: ferramenta/método oficial, 5/5, status HTTP, row_count antes/depois da repetição, integração painel e recursos temporários removidos. Não imprimir tokens ou payloads sensíveis.

**Escopo autorizado:** testes sintéticos locais; nenhum workflow comercial publicado ou ativado, sem mensagens externas ou dados de clientes.