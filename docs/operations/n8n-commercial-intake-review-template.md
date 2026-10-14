# Client0 — n8n commercial intake review template

Status: **template inativo; não é produção**.

Arquivo importável:

`ops/n8n/workflows/client0-commercial-intake-review.json`

## Fluxo preparado

```text
Webhook autenticado
  -> normalização estrita
  -> deduplicação persistente por event_id
  -> throttle operacional simples (10/min)
  -> POST para FastAPI privada
  -> verificação can_send=false / simulation_only=true
  -> Data Table de revisão humana
```

O workflow está versionado com `active=false`. Não há node de WhatsApp,
email, Telegram, redes sociais ou outro canal de saída.

## Controles

- Webhook usa `headerAuth`; o JSON contém somente referência de
  credential local, nunca o segredo.
- A chamada da API usa `httpBearerAuth`; a credencial real deve existir
  somente no n8n local.
- `Remove Duplicates` v2 guarda `event_id` entre execuções, escopo
  workflow e histórico limitado a 10.000 entradas.
- O Code node de rate guard é um **throttle operacional**, não um controle
  de segurança/DoS: usa static data do workflow, não oferece garantia
  transacional sob concorrência.
- Antes de gravar na fila, o workflow aborta se a API retornar
  `can_send != false` ou `simulation_only != true`.
- A fila é uma Data Table local chamada
  `client0_commercial_review_queue`.
- O template nunca aprova ou envia o `draft_reply`.

## Dependências locais ainda não efetivadas

A importação pode ser validada sem ativação. Execução real continua
**bloqueada** até todos os itens abaixo serem resolvidos localmente:

1. **Reachability API:** o template aponta provisoriamente para
   `http://host.docker.internal:8000/internal/commercial-intake/evaluate`.
   No Ubuntu/Linux, o container n8n pode não resolver/alcançar
   `host.docker.internal`. Não adicionar host-gateway, publicar FastAPI
   nem mudar rede antes de validar a situação real.
2. **Credential de entrada:** criar/bind de uma credencial n8n Header Auth
   chamada `business-automation-internal-ingress`.
3. **Credential da API:** criar/bind de uma credencial n8n Bearer Auth
   chamada `business-automation-operator`, usando identidade operator
   privada apropriada. Segredo não entra no Git.
4. **Data Table:** criar
   `client0_commercial_review_queue` com as colunas exatas presentes no
   template antes de executar o fluxo.
5. **Ativação:** exige um gate separado. Importar não autoriza ativar.

## Validação GitHub

`tests/test_n8n_commercial_intake_workflow.py` valida:

- workflow inativo;
- tipos de node permitidos;
- ausência de segredos literais;
- autenticação requerida;
- dedupe persistente;
- URL da API fixa;
- redirect HTTP desabilitado;
- schema da fila;
- ausência de canais externos;
- invariantes de não envio.

## Próxima validação local mínima

A próxima ação no Ubuntu deve ser somente:

- clonar a revisão exata;
- copiar **este workflow** para `/tmp` do container;
- executar `n8n import:workflow` sem `--activeState=fromJson`;
- confirmar que a importação termina com sucesso e fica desativada;
- não criar credentials, Data Table, rede ou ativação nessa validação;
- remover apenas o arquivo temporário copiado para o container.

Se a importação falhar por incompatibilidade de schema/node, registrar
somente a mensagem sanitizada e parar. A correção volta para GitHub.
