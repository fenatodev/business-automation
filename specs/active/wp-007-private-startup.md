# WP-007 — Startup privado, revogação e observabilidade mínima

Status: pronto para validação local  
Base: `origin/main` atual no início da execução  
Executor local preferido: Continue Agent  
Motivo local: precisa iniciar PostgreSQL e API reais em recursos descartáveis, verificar sockets e inspecionar logs locais.

Esta spec é autossuficiente. Não carregar WPs anteriores.

## Objetivo observável

Demonstrar, em ambiente totalmente descartável, que o core atual pode operar como piloto privado com:

1. PostgreSQL 17 local-only e schema no Alembic head;
2. API Uvicorn escutando somente em `127.0.0.1`;
3. health público funcional;
4. rotas de domínio protegidas;
5. uma credencial operator válida funcionando;
6. a mesma credencial deixando de funcionar após remoção da identidade e restart da API;
7. access/startup logs mínimos presentes;
8. nenhum token, hash, senha ou DATABASE_URL completa exposto nos logs capturados;
9. cleanup completo.

Não é deploy de produção.

## Pode alterar somente

- novo `scripts/verify-private-startup.sh`;
- `docs/operations/client0-runbook.md`.

Nenhum outro arquivo.

## Não objetivos

Não adicionar:

- systemd;
- Docker Compose novo;
- reverse proxy;
- TLS público;
- firewall automatizado;
- cloud;
- logging framework;
- middleware de observabilidade;
- Prometheus;
- OpenTelemetry;
- Sentry;
- migration;
- tabela;
- dependência Python;
- exposição pública.

O Uvicorn existente é suficiente como fonte de logs mínimos neste gate.

## Recursos descartáveis

Usar exatamente:

- um container `postgres:17`;
- um processo Uvicorn por vez;
- arquivos temporários em `/tmp`.

Container prefix:

`business-automation-startup-wp007-`

Sem volume persistente.

PostgreSQL deve ser publicado somente em:

`127.0.0.1::5432`

A API deve usar:

`--host 127.0.0.1`

com porta efêmera/local escolhida para a execução.

Não iniciar segundo container auxiliar.

## Segredos sintéticos

Gerar na execução:

- usuário PostgreSQL exclusivo;
- password PostgreSQL de alta entropia;
- admin Bearer token sintético;
- operator Bearer token sintético;
- hashes SHA-256 correspondentes.

Nenhum valor cru ou hash deve ser impresso.

Nunca usar valores de `.env`.

Não imprimir:

- Bearer token;
- token hash;
- password;
- JSON completo de identidades;
- DATABASE_URL completa.

## Banco descartável

Após readiness do único PostgreSQL:

1. descobrir a porta host aleatória;
2. criar um banco sintético;
3. executar `DATABASE_URL=<efêmera> uv run alembic upgrade head`;
4. confirmar `alembic current` no único head;
5. inserir uma Company sintética com `id = 1` somente se necessário para validar operação operator.

Não tocar em banco existente.

## Primeira inicialização da API

Configurar em ambiente apenas do processo:

- `DATABASE_URL` descartável;
- `BA_ACCESS_IDENTITIES_JSON` com:
  - um admin sem Company;
  - um operator com `company_id = 1`.

Iniciar:

```bash
uv run uvicorn app.main:app \
  --host 127.0.0.1 \
  --port "$APP_PORT" \
  --log-level info \
  --no-use-colors
```

Redirecionar stdout+stderr para um arquivo temporário de log fora do repo.

Não passar token/password/URL como argumentos CLI.

## Validações — execução 1

Esperar o health responder.

Confirmar:

### Socket

Com `ss -ltn` ou equivalente:

- existe listener `127.0.0.1:$APP_PORT`;
- não existe `0.0.0.0:$APP_PORT`;
- não existe `[::]:$APP_PORT`.

### HTTP

Confirmar:

- `GET /` sem auth → 200;
- `GET /leads` sem auth → 401;
- `GET /leads` com operator válido → 200;
- `GET /companies` com operator → 403;
- `GET /companies` com admin → 200.

Não imprimir headers Authorization.

## Revogação

Parar somente o processo Uvicorn da execução 1.

Manter o mesmo banco/container.

Reiniciar a API na mesma interface/porta ou em nova porta local-only com uma configuração que mantém o admin, mas **remove totalmente o operator**.

Com o mesmo operator token usado anteriormente:

- `GET /leads` deve retornar 401.

Com o admin ainda configurado:

- `GET /companies` deve retornar 200.

Isso é a prova F1 de revogação por atualização de segredo + restart, conforme ADR 0003.

## Logs mínimos

Nos logs capturados das duas inicializações, confirmar presença de evidência operacional equivalente a:

- startup do servidor;
- request de `GET /`;
- pelo menos um status 200;
- pelo menos um status 401;
- pelo menos um status 403 na execução 1.

Não exigir formato estruturado neste WP.

Confirmar por busca literal que os logs **não contêm**:

- admin token;
- operator token;
- SHA-256 desses tokens;
- password PostgreSQL;
- DATABASE_URL completa;
- `BA_ACCESS_IDENTITIES_JSON` completo.

Não imprimir os valores proibidos durante essa verificação.

## Markers obrigatórios

Emitir exatamente:

```text
PRIVATE_BIND_VERIFIED
PRIVATE_AUTH_VERIFIED
ACCESS_REVOCATION_VERIFIED
MINIMAL_LOGGING_VERIFIED
PRIVATE_STARTUP_VERIFIED
```

Markers somente depois da respectiva validação.

## Cleanup

Trap obrigatório.

Ao terminar, com sucesso ou falha:

- parar somente o(s) processo(s) Uvicorn iniciado(s) pela execução;
- remover somente o container PostgreSQL da execução;
- remover logs temporários da execução;
- não matar Uvicorn/processos de outros projetos;
- não usar prune;
- não usar cleanup amplo.

Após sucesso, não deve restar:

- container com o nome desta execução;
- processo Uvicorn desta execução;
- arquivo temporário WP-007 desta execução.

## Runbook

Atualizar `docs/operations/client0-runbook.md` sem reescrever conteúdo correto existente.

Adicionar seções curtas:

### Health e logs mínimos

- health `GET /`;
- access/startup log do Uvicorn;
- logs não devem conter conteúdo de body, Authorization, tokens, hashes, passwords ou URL completa do banco;
- evidência mínima para incidente: horário, método/path, status e evento de startup/shutdown disponível.

Não afirmar que existe logging estruturado.

### Revogação de acesso

Para F1:

1. remover o hash da identidade revogada da configuração secreta;
2. reiniciar/recarregar o processo;
3. confirmar que o token antigo retorna 401;
4. confirmar que uma identidade autorizada remanescente continua funcionando;
5. não registrar o token/hash na evidência.

Revogação dinâmica continua fora de escopo.

### Parada segura

- identificar o processo correto;
- parar a API antes de mudanças operacionais sensíveis;
- não matar processos por padrão amplo;
- verificar que o listener privado desapareceu.

## Validação obrigatória

Executar:

```bash
bash -n scripts/verify-private-startup.sh
bash scripts/verify-private-startup.sh
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
```

Acceptance:

- harness sai 0;
- cinco markers aparecem;
- 16 testes existentes continuam passando ou a contagem atual da suíte passa integralmente;
- compileall passa;
- diff check passa;
- nenhum container/processo/arquivo temporário WP-007 da execução permanece;
- diff contra `origin/main` contém somente os dois arquivos autorizados.

## Stop conditions

Parar e relatar se:

- o schema não sobe até o Alembic head em PostgreSQL descartável;
- Uvicorn não consegue iniciar em `127.0.0.1`;
- qualquer secret aparece nos logs;
- revogação por restart não produz 401;
- for necessário alterar aplicação, auth, migration ou dependência;
- já existir container remanescente com prefixo WP-007 antes da execução;
- houver necessidade de `0.0.0.0`.

## Git

Branch:

`wp/007-private-startup`

Commit sugerido para eventual correção local:

`ops: verify private startup and access revocation`

Push somente da branch.

Não mergear localmente.

Parar após validação/push.
