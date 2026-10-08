# WP-003 — Harness PostgreSQL descartável para caracterizar Alembic

Status: pronto para execução local  
Base de preparação: `main@1fc65d78` (confirmar `origin/main` antes de editar)  
Executor: Pi/Qwen local  
Motivo para execução local: requer Docker/PostgreSQL real descartável e execução de comandos/testes.

## Objetivo observável

Criar um harness seguro e reproduzível que demonstre a falha atual de `alembic upgrade head` em um PostgreSQL 17 vazio, sem tocar no banco real, sem alterar migrations e sem depender de `.env`.

Este pacote é somente de **caracterização + isolamento**. A correção da cadeia será outro WP após review.

## Contexto suficiente

A cadeia atual em `main` começa assim:

- `7c83bbc2b9f7`: baseline raiz vazia;
- `1a2fcfdc65b1`: tenta adicionar `created_at` e `updated_at` em `leads`;
- nenhuma migration anterior em `main` cria `leads`.

O ADR vigente é `docs/architecture/adr/0002-migration-recovery.md`.

Existe uma branch histórica com um bootstrap candidato, mas **não usar/cherry-pickar/importar nada dela neste WP**.

## Preflight Git seguro

1. `git fetch origin`.
2. Ler `AGENTS.md` de `origin/main`.
3. Ler esta spec de `origin/main`.
4. Não executar `git clean`, `reset --hard` ou apagar arquivos não rastreados.
5. Se houver mudança rastreada do usuário que impeça criar uma branch limpa, parar e relatar.
6. Criar a branch `wp/003-alembic-postgres-harness` a partir de `origin/main`.

Um diretório local `specs/` não rastreado não deve ser apagado. Se houver conflito de path que impeça checkout, parar sem sobrescrever.

## Pode alterar

Somente:

- novo `scripts/verify-alembic-postgres.sh`.

Nenhum outro arquivo deve ser modificado.

## Não alterar

- `migrations/**`;
- `app/**`;
- `tests/**`;
- `alembic.ini`;
- `.env` ou `.env.example`;
- Docker Compose;
- dependências;
- documentação;
- qualquer serviço/banco existente.

## Contrato do harness

O script deve:

1. usar Bash e falhar explicitamente; **não usar `set -e`**;
2. confirmar que `docker` está disponível antes de criar recurso;
3. criar um único container temporário com nome exclusivo prefixado por `business-automation-alembic-wp003-`;
4. usar imagem `postgres:17`;
5. usar banco/usuário/senha sintéticos exclusivos da validação;
6. não montar volumes;
7. publicar PostgreSQL somente em `127.0.0.1` com porta host aleatória;
8. aguardar `pg_isready` com limite finito;
9. construir `DATABASE_URL` exclusivamente a partir do container temporário;
10. nunca ler/sourcear `.env`;
11. executar `uv run alembic upgrade head` com `DATABASE_URL` inline;
12. **esperar que o upgrade falhe no estado atual**;
13. considerar sucesso do harness somente se a falha for compatível com a ausência da tabela `leads`/UndefinedTable;
14. considerar erro se o upgrade:
    - completar inesperadamente;
    - falhar por conexão, credencial, Docker, dependência ou outro motivo não relacionado a `leads`;
15. capturar saída suficiente para diagnóstico sem imprimir senha;
16. usar `trap` para remover somente o container criado pelo próprio script em EXIT/INT/TERM;
17. não remover containers, imagens, volumes ou redes preexistentes;
18. retornar exit code 0 somente quando a falha esperada tiver sido caracterizada corretamente.

## Segurança adicional

- Não usar `docker compose`.
- Não usar nomes de banco/containers existentes no projeto.
- Não executar `alembic stamp`.
- Não executar downgrade.
- Não executar qualquer migration contra URL externa ou recebida de `.env`.
- Não usar `Base.metadata.create_all`.
- Não deixar container rodando após a validação.
- Não adicionar segredos ao Git.

## Aceite

### A1 — sintaxe

```bash
bash -n scripts/verify-alembic-postgres.sh
```

deve passar.

### A2 — caracterização

```bash
bash scripts/verify-alembic-postgres.sh
```

deve retornar 0 **porque detectou a falha esperada da cadeia atual**, e não porque o upgrade passou.

A saída final deve ser curta e inequívoca, por exemplo:

```text
EXPECTED_ALEMBIC_FAILURE_CONFIRMED
```

Pode incluir resumo sanitizado do erro antes dessa linha.

### A3 — cleanup

Após o script:

```bash
docker ps -a --format '{{.Names}}' | grep '^business-automation-alembic-wp003-'
```

não deve retornar containers remanescentes.

### A4 — invariantes do repositório

Executar:

```bash
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
```

A suíte existente deve continuar passando.

### A5 — escopo

`git diff --name-only origin/main...HEAD` deve listar somente:

```text
scripts/verify-alembic-postgres.sh
```

## Se algo divergir

- Se `alembic upgrade head` passar em banco vazio, não modificar migrations: registrar que a premissa mudou e parar.
- Se a falha não for relacionada a `leads`, não adaptar o script para mascará-la: registrar evidência e parar.
- Se Docker não estiver disponível/operacional, parar sem instalar ou reconfigurar Docker.
- Se houver risco de tocar recurso preexistente, parar.

## Encerramento GitHub-first

Quando todos os critérios passarem:

1. revisar diff e status;
2. adicionar somente `scripts/verify-alembic-postgres.sh`;
3. commit sugerido: `test: add isolated Alembic PostgreSQL harness`;
4. push somente da branch `wp/003-alembic-postgres-harness`;
5. não abrir/rodar WP seguinte;
6. não fazer merge;
7. encerrar.

ChatGPT fará a revisão pelo GitHub. Não é necessário copiar saída da CLI para o usuário.
