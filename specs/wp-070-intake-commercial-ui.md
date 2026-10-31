# WP-070 — Interface de intake comercial no operador

Base: `origin/main` (após merge WP-065 a WP-069).
Branch: `wp/070-intake-commercial-ui`.

## Motivação

`POST /internal/commercial-intake/create` (WP-069) avalia uma mensagem comercial
e persiste como Opportunity, mas não possui interface na UI do operador.
O operador só pode testar o endpoint via curl/Postman, sem integração
com o fluxo visual de triage e lista de oportunidades.

## Entrega

### HTML — Nova seção de intake

- Seção "Intake comercial" em `index.html` entre a fila de revisão e
  a captura manual, índice "06 / INTEGRAÇÃO IA".
- Formulário com: canal (select), mensagem (textarea), ID do evento (input).
- Botão "Avaliar e registrar" que chama `/internal/commercial-intake/create`.
- Área de resultado que exibe a decisão (intent, next_step, flags).
- Mensagem de sucesso com link para a opportunity criada.

### JavaScript — intakeApi()

- Nova função `intakeApi()` com allowlist estrita para
  `/internal/commercial-intake/create`.
- Segue padrão `reviewApi()`: validação de rota, epoch check, 401 disconnect.
- Handler de submit do formulário que:
  1. Envia para `/internal/commercial-intake/create`.
  2. Exibe decisão na área de resultado.
  3. Recarrega lista de oportunidades.
  4. Auto-seleciona a opportunity criada para triage.
- Tratamento de erros: 409 (duplicado), 503 (agente indisponível).

### CSS

- Reutilizar estilos existentes (panel, form, readout, review-card).
- Adicionar `.intake-decision` para exibir resultado da avaliação.

## Design

- Sem mudanças no backend — apenas UI.
- Allowlist estrita seguindo padrão existente.
- Se o agente retornar 503, exibir mensagem genérica sem expor detalhes.
- Event_id duplicado (409) exibe aviso claro.
- Após criação bem-sucedida, recarregar lista e selecionar a opportunity.

## Aceite

- Testes runtime JavaScript validam:
  - Conexão com endpoint de intake.
  - Exibição de decisão.
  - Recarregamento da lista.
  - Tratamento de 409 e 503.
  - Rejeição de rotas inválidas.
- `uv run pytest`, compileall, git diff --check: PASS.

## Próximo passo

Após integração, avaliar se o intake precisa de histórico de decisões
ou se o fluxo atual (decisão inline + triage note) é suficiente.
