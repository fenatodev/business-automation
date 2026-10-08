# WP-012 — Bootstrap do runtime privado real do Client 0

Status: autorizado para execução local  
Fase: F2 — operação assistida  
Tipo: operação persistente local, privada, sem dados reais de cliente.

## Objetivo

Criar o primeiro runtime persistente real do Client 0 na workstation, sem exposição pública e sem inserir dados reais de oportunidades/clientes.

Ao final devem existir:

- PostgreSQL 17 persistente via Compose;
- bind PostgreSQL somente em 127.0.0.1;
- .env real local, fora do Git;
- credenciais fortes;
- DATABASE_URL real local;
- BA_ACCESS_IDENTITIES_JSON com admin + operator Client 0;
- schema no Alembic head atual;
- Company operacional "Client 0";
- API privada em 127.0.0.1;
- health/auth/tenant validados;
- segredo bruto armazenado somente fora do repo com permissão 0600.

## Regras de segurança

- Não apagar nem reutilizar volume/container existente sem identificar ownership.
- Se já houver .env real, container/volume do projeto ou banco com dados desconhecidos: PARAR e reportar.
- Não usar docker compose down -v.
- Não usar prune.
- Não imprimir token, hash, password, DATABASE_URL completa ou BA_ACCESS_IDENTITIES_JSON.
- Não enviar segredo ao GitHub/chat.
- Não inserir dado real de cliente/oportunidade.
- Não expor API/PostgreSQL em 0.0.0.0 ou ::.
- Não criar systemd neste WP.
- Não alterar código do repositório.

## Local paths

Repositório canônico:

`/home/fenatodev/dev/worktrees/business-automation-dev`

Segredos brutos fora do repo:

`~/.config/business-automation/client0-secrets.env`

Permissão obrigatória: 0600.

.env operacional:

`<repo>/.env`

O .env é ignorado pelo Git e deve ter permissão 0600.

## Identidade inicial

Criar exatamente uma Company:

- name: `Client 0`
- slug: `client0`

Criar duas identidades de acesso:

- admin;
- operator vinculado ao company_id real de Client 0.

Gerar tokens aleatórios de alta entropia.

No .env ficam apenas hashes SHA-256 em BA_ACCESS_IDENTITIES_JSON.
Tokens brutos ficam somente em `~/.config/business-automation/client0-secrets.env`.

## Banco

- usar docker-compose.yml canônico;
- usar POSTGRES_PORT livre, preferencialmente 55432 se disponível;
- volume persistente normal do projeto;
- executar `uv run alembic upgrade head`;
- confirmar `uv run alembic current` no head;
- criar Company via API ou SQL controlado somente após migrations.

## API

Iniciar Uvicorn apenas em:

`127.0.0.1`

Usar porta livre local, preferencialmente 8788.

Não criar serviço persistente de boot ainda.

Validar:

- GET / sem auth => 200;
- GET /opportunities sem auth => 401;
- GET /companies com operator => 403;
- GET /companies com admin => 200;
- GET /opportunities com operator => 200;
- listener API somente em 127.0.0.1;
- listener PostgreSQL somente em 127.0.0.1.

## Company

Se o banco estiver vazio, criar Client 0 uma única vez.

Se já existir slug `client0`, validar que name é `Client 0` e reutilizar.
Qualquer outro estado inesperado => PARAR.

## Persistência

Após validação:

- PostgreSQL permanece rodando;
- volume permanece;
- .env permanece local;
- secret file permanece local;
- Uvicorn pode permanecer rodando somente nesta sessão; não prometer persistência após reboot.

## Acceptance

- git working tree continua limpo;
- .env não aparece em git status;
- secrets file fora do repo;
- permissions 0600 em ambos;
- PostgreSQL healthy;
- Alembic current = head;
- Client 0 existe exatamente uma vez;
- health/auth/tenant checks passam;
- bind privado confirmado;
- nenhum segredo foi impresso;
- nenhum dado real foi inserido.

## Stop conditions

Parar se:

- houver .env preexistente;
- houver volume/container Compose existente com dados não identificados;
- porta escolhida estiver ocupada por serviço não pertencente ao WP;
- migration falhar;
- auth falhar;
- bind não for loopback-only;
- qualquer passo exigir operação destrutiva.

## Resultado esperado

Entregar apenas evidência sanitizada:

- container/health;
- portas;
- Alembic head;
- Company id/slug;
- códigos HTTP;
- paths dos arquivos secretos;
- nunca valores secretos.
