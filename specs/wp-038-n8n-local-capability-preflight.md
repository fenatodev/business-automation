# WP-038 — Preflight local mínimo do n8n para workflow comercial interno

**Status:** ficha de validação local para Junie.  
**Objetivo:** coletar somente evidência técnica indispensável do n8n instalado
no Ubuntu para que o workflow seja preparado e revisado posteriormente
**direto no GitHub**, sem adivinhar nodes/CLI/versões.

## Contexto

O núcleo comercial já está na `main`:

- WP-035: guard/decisão comercial pura;
- WP-036: gerador de candidato, static + Ollama loopback;
- WP-037: `POST /internal/commercial-intake/evaluate`, privado,
  autenticado, sem DB e sem efeitos externos.

Próximo passo desejado: workflow n8n **inativo por padrão**, com entrada
interna, deduplicação, limitação de frequência e fila/revisão antes de
qualquer canal externo.

Não implementar esse workflow neste WP. Primeiro provar quais recursos
existem na instalação local do n8n.

## Escopo local — somente leitura

No Ubuntu autorizado, inspecionar apenas:

1. nome/estado do container n8n e imagem em uso;
2. versão do CLI n8n;
3. health local do serviço dentro do próprio container;
4. existência, no pacote instalado, dos nodes/capacidades candidatos:
   - Webhook
   - Respond to Webhook
   - HTTP Request
   - Code
   - Wait
   - Remove Duplicates
   - Data Table / Data Store (o nome exato que existir)
   - Execute Workflow
5. ajuda do CLI para importação de workflow, sem importar nada;
6. se o container publica porta no host ou apenas na rede Docker;
7. nomes das redes Docker às quais o container n8n pertence.

## Proibições

- Não ler `.env`.
- Não executar `docker inspect` exibindo `Env`, labels sensíveis,
  mounts com secrets ou command line completa.
- Não exportar workflows existentes.
- Não listar ou exportar credentials.
- Não consultar banco interno do n8n.
- Não alterar container, restart, image, volume ou rede.
- Não importar workflow.
- Não ativar workflow.
- Não criar webhook.
- Não fazer chamadas a APIs externas.
- Não acessar dados reais.
- Não alterar Oracle, PostgreSQL, FastAPI ou Docker Compose.
- Não instalar pacote.
- Não usar `docker exec` para escrever arquivos dentro do container.
- Não executar comandos destrutivos.
- Não fazer merge.

## Branch e handoff

Criar branch:

`wp/038-n8n-local-capability-preflight`

A partir da `main` atualizada.

Produzir somente:

`docs/operations/n8n-local-capability-report.md`

O relatório deve conter apenas:

- timestamp UTC;
- n8n version;
- image;
- container state/health resumidos;
- published ports no formato seguro (sem IP privado se não for necessário);
- nomes de redes;
- tabela `capability | available | exact node/package path or CLI evidence`;
- resultado do health;
- sintaxe relevante de `n8n import:workflow --help` resumida,
  sem logs integrais;
- limitações encontradas.

Não incluir IDs Docker, hashes, IPs, tokens, credenciais, headers,
workflow names existentes, paths privados irrelevantes ou conteúdo de
qualquer workflow.

## Comandos permitidos

Use comandos equivalentes a estes, adaptando somente se a imagem não
contiver uma ferramenta específica:

```bash
docker ps --filter name=^/n8n$ --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}'
docker exec n8n n8n --version
docker inspect n8n --format '{{json .NetworkSettings.Networks}}'
docker exec n8n n8n import:workflow --help
docker exec n8n sh -lc 'find /usr/local/lib/node_modules/n8n -type f \( -iname "*Webhook*" -o -iname "*RespondToWebhook*" -o -iname "*HttpRequest*" -o -iname "*Code*" -o -iname "*Wait*" -o -iname "*RemoveDuplicates*" -o -iname "*DataTable*" -o -iname "*DataStore*" -o -iname "*ExecuteWorkflow*" \) 2>/dev/null | head -120'
```

Para health, preferir chamada **de dentro do container** para
`http://127.0.0.1:5678/healthz`, com Node.js/fetch caso curl não exista.
Registrar somente status HTTP + texto curto não sensível.

Ao usar `docker inspect ...Networks`, extrair **somente os nomes das redes**
para o relatório. Não registrar IP/MAC/Gateway.

## Validação

Antes de push:

```bash
git diff --check
git status --short
```

O diff deve conter somente o relatório.

Fazer commit e push da branch. Não abrir implementação adjacente.

## Saída esperada

Responder apenas:

- PASS ou FAIL;
- branch;
- commit SHA;
- n8n version;
- capabilities encontradas/ausentes em resumo;
- bloqueio, se houver.

**STOP após o preflight.**
