# ADR 0003 — Acesso privado e isolamento por Company

Data: 2026-10-08  
Status: Accepted para F1 / piloto privado  
Escopo: autenticação mínima da API e isolamento de tenant antes de dados operacionais.

## Contexto

A API atual expõe CRUDs e mutações sem autenticação. `Company` já é a raiz lógica do tenant, mas várias rotas globais e buscas por ID podem atravessar Companies. O campo `company_id` enviado pelo cliente não é uma fronteira de autorização.

O primeiro uso é Client 0 em ambiente privado. Ainda não há necessidade demonstrada de OAuth/OIDC, portal self-service, sessão de usuário final ou RBAC amplo.

## Decisão

Adotar uma fronteira de acesso mínima e reversível para F1:

1. `GET /` permanece health endpoint sem autenticação.
2. Todas as rotas de domínio exigem `Authorization: Bearer <token>`.
3. Tokens são opacos, de alta entropia e provisionados fora do Git.
4. A configuração da aplicação contém somente SHA-256 dos tokens e os claims autorizativos mínimos.
5. Dois papéis iniciais:
   - `admin`: pode criar/listar Companies; não recebe acesso implícito a dados tenant;
   - `operator`: obrigatoriamente vinculado a exatamente uma `company_id`.
6. O tenant efetivo de uma requisição `operator` vem da identidade autenticada, nunca do payload ou path.
7. Quando uma rota ainda recebe `company_id`, ele é apenas um valor de consistência:
   - se coincidir com a identidade, a operação pode continuar;
   - se divergir, negar sem usar esse valor para elevar ou trocar tenant.
8. Listagens globais de Lead/Customer/Conversation devem ser filtradas pela Company autenticada.
9. Buscas por ID devem incluir a Company no predicado e responder como não encontrado quando o recurso pertence a outro tenant, evitando vazamento de existência.
10. Message e agent-reply herdam a Company da Conversation e precisam passar pela mesma fronteira.
11. Chaves inválidas ou ausentes recebem erro genérico e não expõem configuração, hash, Company existente ou detalhes internos.
12. Revogação no F1 ocorre removendo o hash da configuração secreta e reiniciando/recarregando o processo. Revogação dinâmica fica adiada até existir necessidade operacional.
13. A configuração secreta não entra no repositório nem em logs.

## Formato de configuração

A implementação deverá usar uma configuração estruturada equivalente a uma lista de identidades:

```json
[
  {"token_sha256": "<64 hex>", "role": "admin"},
  {"token_sha256": "<64 hex>", "role": "operator", "company_id": 1}
]
```

O nome exato da variável/configuração pode ser escolhido no WP, desde que:

- nenhum token cru seja persistido no Git;
- o parser rejeite papel desconhecido;
- `operator` sem `company_id` seja inválido;
- `admin` não ganhe tenant implícito;
- configuração inválida falhe de forma explícita no startup/uso, sem imprimir segredos.

## Matriz mínima

| Ação | admin | operator |
| --- | --- | --- |
| `GET /` | público | público |
| criar/listar Company | permitido | negado |
| criar/listar/ler/alterar Lead | negado por padrão | somente própria Company |
| criar/listar/ler Customer | negado por padrão | somente própria Company |
| converter Lead | negado por padrão | somente própria Company |
| criar/listar/ler Conversation | negado por padrão | somente própria Company |
| criar/listar Message | negado por padrão | somente Conversation da própria Company |
| agent-reply | negado por padrão | somente Conversation da própria Company |

Admin que precisar operar dados deve usar uma identidade `operator` explícita. Isso evita um bypass universal acidental.

## Semântica de erro

- ausência/credencial inválida: `401`;
- identidade autenticada sem permissão para a classe de operação: `403`;
- recurso de outro tenant consultado por ID/path: `404`;
- `company_id` de consistência divergente da identidade operator: `403`.

Não diferenciar em mensagens externas token inexistente, hash não cadastrado ou configuração interna.

## Testes obrigatórios

A implementação deve provar pelo menos:

- root continua acessível sem token;
- rota de domínio sem token retorna 401;
- token inválido retorna 401;
- operator A lista somente dados A;
- operator A não lê/altera/converte recurso B por ID;
- operator A não cria recurso em B usando `company_id` do payload;
- operator A não acessa path `/companies/B/...`;
- mensagens e agent-reply não atravessam tenant via `conversation_id`;
- operator não cria/lista Companies;
- admin cria/lista Companies, mas não obtém dados tenant por consequência;
- nenhum erro contém token/hash/configuração secreta.

## Não objetivos

Este ADR não introduz:

- usuários humanos persistidos;
- senha/login;
- OAuth/OIDC;
- JWT;
- refresh token;
- permissões granulares;
- portal;
- SSO;
- API keys persistidas em banco;
- auto-provisionamento;
- exposição pública.

Esses mecanismos só entram quando o piloto exigir identidade multiusuário ou hosting compartilhado mais amplo.

## Consequências

### Positivas

- fecha a exposição anônima atual;
- cria isolamento verificável sem nova tabela ou migration;
- mantém o tenant derivado de autoridade do servidor;
- permite Client 0 privado com baixo custo operacional;
- é substituível por provider de identidade futuro.

### Limitações

- rotação/revogação exige atualização de segredo e reload/restart;
- não há identidade individual de usuário humano;
- não é solução final para SaaS público;
- distribuição segura de chaves continua responsabilidade operacional.

## Gate

Nenhum dado operacional real deve entrar na API até que o WP de implementação deste ADR passe testes negativos de cross-tenant e revisão de segurança.
