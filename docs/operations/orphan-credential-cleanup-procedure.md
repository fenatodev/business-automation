# Procedimento: Remoção da credencial órfã `test-header` no n8n

**Status**: Preparado, não executado. Requer aprovação específica.
**Data**: 2026-10-15
**WP**: WP-052

## Contexto

A credencial `test-header` (ID: `TQRol30waRpD6BkA`, tipo: `httpHeaderAuth`)
foi criada durante a WP-048 e não é referenciada por nenhum workflow ativo.
Persiste no n8n por falta de permissão `credential:delete` na API key atual.

## Risco

**Baixo**. A credencial não é usada por nenhum workflow. Não contém dados
sensíveis além do valor de header de autenticação de teste.

## Procedimento oficial (n8n UI)

### Pré-requisitos

1. Acesso à interface web do n8n com conta autenticada.
2. Permissão `credential:delete` na conta ou role do usuário.

### Passos

1. Acessar a UI do n8n: `http://<n8n-host>:5678/credentials`
2. Localizar a credencial `test-header` (ID: `TQRol30waRpD6BkA`)
3. Verificar que nenhum workflow a referencia:
   - Coluna "Used by" deve estar vazia
   - Ou verificar via API: `GET /api/v1/credentials/TQRol30waRpD6BkA`
4. Clicar nos três pontos (⋮) → "Delete"
5. Confirmar a exclusão

### Verificação pós-exclusão

```bash
# Verificar que a credencial foi removida
curl -s -H "X-N8N-API-KEY: $N8N_KEY" \
  "http://<n8n-host>:5678/api/v1/credentials/TQRol30waRpD6BkA" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Status:', d.get('message', 'NOT_FOUND'))"
```

Esperado: HTTP 404 ou mensagem indicando credencial não encontrada.

## Procedimento alternativo (API pública n8n)

Se a UI não estiver disponível, usar a API pública do n8n:

```bash
# Excluir credencial via API
curl -s -X DELETE -H "X-N8N-API-KEY: $N8N_KEY" \
  "http://<n8n-host>:5678/api/v1/credentials/TQRol30waRpD6BkA"
```

**Nota**: A API key atual `business-automation-integration` não possui
o escopo `credential:delete`. Para usar este método, é necessário:

1. Ampliar temporariamente o escopo da API key via UI n8n:
   - Settings → API Keys → Editar `business-automation-integration`
   - Adicionar escopo `credential:delete`
2. Executar o comando DELETE acima
3. Remover o escopo `credential:delete` imediatamente após

## Proibições

- **NUNCA** modificar o banco SQLite interno do n8n para excluir a credencial.
- **NUNCA** descriptografar ou extrair o valor secreto da credencial.
- **NUNCA** acessar chaves de criptografia internas do n8n.
- **NUNCA** usar `sqlite3` ou ferramentas similares no banco do n8n.

## Rollback

Se a exclusão causar impacto inesperado (improvável, pois a credencial
não é referenciada):

1. Recriar a credencial via UI ou API com o mesmo nome e tipo
2. O valor do header pode ser redefinido, pois era um valor de teste

## Aprovação necessária

Este procedimento requer aprovação explícita do usuário antes da execução.
A aprovação deve especificar:

1. Método de exclusão: UI ou API
2. Se ampliação de escopo da API key é autorizada
3. Janela de tempo para execução

## Referências

- WP-048: Credencial `test-header` criada durante testes de integração
- WP-050: E2E sintético — credencial identificada como órfã
- WP-051: Verificação pós-E2E — remoção bloqueada por 403
- AGENTS.md: Seção "Integração n8n e governança" — política de credenciais
