# WP-005 — Acesso privado e isolamento por Company

Status: concluído  
Base: `origin/main` após conclusão do WP-004  
Referência obrigatória: `docs/architecture/adr/0003-access-and-tenancy.md`

## Objetivo observável

Fechar a API anônima atual e provar isolamento de Company no conjunto de rotas existente, sem introduzir IAM completo, migration nova ou dependência de autenticação externa.

Ao concluir:

1. `GET /` continua público;
2. todas as rotas de domínio exigem Bearer token;
3. `admin` administra somente Companies;
4. `operator` opera somente a Company vinculada à identidade;
5. payload/path `company_id` nunca eleva ou troca tenant;
6. buscas por ID e mensagens/agent-reply não atravessam tenant;
7. testes negativos demonstram isolamento;
8. nenhuma chave/token real entra no Git.

## Regra de risco

Este WP envolve authentication, authorization e tenant isolation.

Antes de merge:

- revisão de segurança obrigatória;
- executar testes normais completos;
- revisar explicitamente cada rota existente;
- não expandir para OAuth/JWT/RBAC completo.

## Implementação mínima

### Identidades

Configuração secreta estruturada contendo somente:

- `token_sha256`;
- `role`: `admin` ou `operator`;
- `company_id` obrigatório apenas para `operator`.

Requisitos:

- calcular SHA-256 do Bearer token recebido;
- comparar digests sem registrar token;
- rejeitar configuração inválida;
- não imprimir segredo/digest em resposta;
- nenhuma dependência externa de auth necessária.

### Contexto

Criar abstrações pequenas equivalentes a:

- identidade autenticada;
- dependência `require_admin`;
- dependência `require_operator` / tenant context.

Não duplicar parsing de Authorization em routers.

### Regras de rota

#### Público

- somente `GET /`.

#### Company

- `POST /companies`: admin;
- `GET /companies`: admin.

#### Lead

- create/list/get/update: operator;
- consultas sempre limitadas à `company_id` autenticada;
- create com `company_id` divergente: 403;
- `/companies/{company_id}/leads` exige path igual ao tenant.

#### Customer

- list/get/create/convert: operator;
- resource lookup inclui tenant;
- conversão só para Lead da própria Company;
- create com `company_id` divergente: 403;
- path company mismatch: 404 ou 403 conforme ADR; manter semântica consistente e testada.

#### Conversation / Message / agent-reply

- operator somente;
- Conversation deve pertencer ao tenant;
- Lead/Customer associados devem pertencer ao mesmo tenant;
- get/list/create Message e agent-reply validam tenant via Conversation;
- nenhuma busca só por `conversation_id` pode atravessar Company.

### Admin

Admin não recebe tenant implícito e não deve acessar dados de Lead/Customer/Conversation/Message. Para operar dados, usar uma identidade operator explícita.

## Arquivos esperados

Escopo provável, podendo reduzir mas não expandir sem parar:

- `app/database.py`;
- `app/dependencies.py`;
- novo módulo pequeno de auth/context em `app/`;
- routers existentes;
- `tests/test_api.py`;
- `tests/conftest.py` se necessário para configuração/overrides;
- documentação/config exemplo somente se necessária e sem segredo real.

Não alterar migrations.

## Testes obrigatórios

Além de preservar comportamentos existentes dentro do tenant:

1. root sem token = 200;
2. domínio sem token = 401;
3. token inválido = 401;
4. operator não pode criar/listar Company = 403;
5. admin pode criar/listar Company;
6. admin não acessa dados tenant = 403;
7. operator A lista apenas A;
8. operator A não lê Lead/Customer/Conversation de B por ID = 404;
9. operator A não altera Lead B;
10. operator A não converte Lead B;
11. operator A não cria Lead/Customer/Conversation em B usando payload divergente;
12. operator A não usa paths de Company B;
13. operator A não cria/lê mensagens em Conversation B;
14. operator A não chama agent-reply em Conversation B;
15. erro 401/403/404 não contém token, hash ou configuração secreta.

Preferir fixtures sintéticas e dependency/settings overrides. Nenhum segredo real.

## Validação

Obrigatória:

```bash
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
```

Também inspecionar diff para confirmar:

- nenhuma migration;
- nenhuma dependência nova desnecessária;
- nenhum token/hash de produção;
- todas as rotas de domínio cobertas pela fronteira;
- `company_id` do cliente não é fonte de autorização.

## Stop conditions

Parar e relatar se:

- implementação exigir migration;
- for necessário escolher OAuth/OIDC/JWT/provider externo;
- houver rota cuja ownership por Company não possa ser determinada do modelo atual;
- os testes exigirem dados/credenciais reais;
- surgir necessidade de exposição pública;
- o escopo virar RBAC geral ou gestão de usuários.

## Commit sugerido

`feat: enforce private access and tenant isolation`

Push apenas da branch do WP. Não mergear sem revisão de segurança.


## Resultado

Concluído em 2026-10-08.

- branch: `wp/005-access-tenancy`;
- commits: `163f00f`, `6d15719`;
- PR: #21;
- merge commit: `ec8694f9c33e4b6273901fdbc8f8e910ab8de56f`;
- `GET /` permanece público;
- todas as rotas de domínio exigem autenticação;
- admin administra Companies e não ganha tenant implícito;
- operator é vinculado server-side a uma Company;
- listagens e buscas por ID são tenant-scoped;
- Message e agent-reply validam Company via Conversation;
- cross-tenant por ID retorna 404; mismatch explícito de Company retorna 403;
- configuração inválida de acesso retorna 503 genérico sem expor detalhes;
- nenhuma migration ou dependência de auth foi adicionada;
- 16 testes passaram;
- compileall e diff check passaram;
- revisão independente pré-implementação não encontrou blockers;
- findings pós-implementação foram triados: limitações de chave estática/rate limiting/replay permanecem restritas ao piloto privado e não autorizam exposição pública.
