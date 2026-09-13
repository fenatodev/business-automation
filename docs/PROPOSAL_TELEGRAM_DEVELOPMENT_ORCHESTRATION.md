# Proposta — Orquestrador privado de desenvolvimento pelo Telegram

**Status:** proposta para revisão de segurança e arquitetura
**Data:** 2026-09-01
**Escopo:** interface privada para iniciar, acompanhar e aprovar tarefas de desenvolvimento. Não é integração de atendimento a clientes.

## Objetivo

Usar um bot Telegram privado como interface de comando e acompanhamento de tarefas no repositório. O bot encaminha pedidos a um controlador local ou em infraestrutura controlada, que executa sessões de agentes em workspaces isolados e devolve progresso, resultado de validações, diff resumido e pedidos de aprovação.

Telegram é apenas a interface de interação; não recebe acesso de shell irrestrito, segredos de infraestrutura ou permissão implícita para modificar repositórios.

## Fluxo mínimo

1. Um chat/usuário previamente autorizado envia uma tarefa.
2. O webhook valida a origem e registra um pedido imutável com um ID de tarefa.
3. O controlador cria ou seleciona um workspace permitido e inicia uma sessão de agente com política de ferramentas restrita.
4. O controlador publica status, plano, perguntas e resumo de alterações no chat privado.
5. Antes de operações sensíveis, o controlador exige uma aprovação explícita vinculada ao ID da tarefa e à ação proposta.
6. Ao final, devolve o resultado de testes, diff, commit/push quando autorizado e links/IDs de auditoria.

## Capacidades da primeira versão

- criar tarefa em um repositório allowlisted;
- consultar status, logs sanitizados, diff resumido e validações;
- responder a perguntas do agente e aprovar/rejeitar uma etapa pendente;
- cancelar tarefa ainda não iniciada ou em estado seguro;
- manter uma única tarefa ativa por workspace inicialmente.

A primeira versão não deve permitir comandos shell arbitrários via mensagem, alteração de configuração de produção, acesso a outros repositórios, merge, force-push, rotação de segredos ou execução concorrente no mesmo workspace.

## Arquitetura proposta

### Bot gateway

Recebe updates do Telegram, valida o `secret_token` do webhook e aplica allowlist de chat e usuário. Ele aceita um vocabulário pequeno de comandos estruturados, por exemplo:

- `/task <repositório> <descrição>`
- `/status <id>`
- `/approve <id> <ação> <nonce>`
- `/reject <id> <ação> <nonce>`
- `/cancel <id>`

O gateway não executa Git, shell ou agentes diretamente.

### Controlador

Serviço interno que mantém máquina de estados da tarefa, seleciona repositório/workspace a partir de configuração allowlisted e inicia o agente. A política do controlador define ferramentas permitidas, timeouts, limites de custo, regras de checkpoint e operações que exigem aprovação humana.

A confirmação deve conter um nonce de uso único, expiração curta, ID da tarefa, branch e descrição exata da ação. Texto livre como “sim” não deve autorizar push, commit ou ações destrutivas.

### Executor isolado

Executa cada tarefa com identidade de menor privilégio e diretório de trabalho dedicado. Deve limitar CPU/memória/tempo, bloquear acesso desnecessário à rede e não compartilhar credenciais entre tarefas. O executor oferece ao agente apenas as ferramentas aprovadas para aquele repositório.

### Registro de auditoria

Persistir eventos de tarefa e aprovação com: ator Telegram autorizado, timestamp, tarefa, workspace, transição de estado, hash de comando/política, resultado e referências de commit. Não armazenar tokens, conteúdo integral de segredos ou logs sensíveis.

## Controles de segurança obrigatórios

- Bot token, webhook secret, credenciais Git e credenciais de executor em secret manager/variáveis seguras, nunca no Git ou nas mensagens.
- HTTPS e validação de `X-Telegram-Bot-Api-Secret-Token` no webhook.
- Allowlist de `chat_id` e `user_id`; negar chats de grupo inicialmente.
- Autorização por ação: iniciar, aprovar commit, aprovar push e cancelar não são equivalentes.
- Workspaces e repositórios allowlisted; branch protegida e sem push direto para `main` por padrão.
- Sem shell arbitrário, interpolação de mensagem em shell, upload automático de arquivos ou exfiltração de `.env`/chaves.
- Rate limit, tamanho máximo de mensagem, deduplicação por `update_id` e proteção contra replay.
- Redação de segredos antes de enviar logs/diffs ao Telegram.
- Kill switch para gateway, controlador e executor.

## Máquina de estados

`queued → planning → awaiting_input → running → awaiting_approval → validating → completed`

Estados terminais: `failed`, `cancelled`, `rejected`, `timed_out`.

Uma transição para `awaiting_approval` bloqueia a ação pendente até uma aprovação válida. Falha de envio ao Telegram não pode ser interpretada como aprovação ou falha da tarefa; o controlador mantém o estado como fonte de verdade.

## Política inicial de aprovações

| Ação | Política inicial |
| --- | --- |
| Ler código e propor plano | permitida |
| Editar workspace isolado | permitida dentro da tarefa |
| Executar testes/linters permitidos | permitida |
| Criar commit | aprovação explícita |
| Push para branch remota | aprovação explícita separada |
| Merge, release, force-push, alteração de produção ou secrets | proibida nesta versão |

As regras do repositório, como `AGENTS.md`, continuam sendo aplicadas pelo agente e pelo controlador; Telegram não as substitui.

## Entregas incrementais

1. Definir ameaça, papéis autorizados, ambiente de execução e política de retenção.
2. Criar controlador local sem Telegram: tarefa, estados, executor isolado e auditoria.
3. Adicionar gateway Telegram apenas para `/task`, `/status` e notificações, em chat privado allowlisted.
4. Adicionar aprovações com nonce e expiração para commit/push.
5. Fazer piloto em um repositório não crítico, com monitoramento e kill switch.
6. Só depois avaliar múltiplos repositórios, múltiplas tarefas e interface humana mais rica.

## Decisões pendentes

- Onde o controlador e executor rodarão: máquina local, servidor privado ou runner dedicado?
- Quais identidades Telegram podem iniciar e aprovar quais ações?
- Qual agente/harness será suportado e como suas sessões serão recuperadas?
- Como serão armazenados estado, auditoria e logs sanitizados?
- Qual mecanismo recebe webhooks sem expor a máquina de desenvolvimento diretamente?
- Quais repositórios e branches entram na allowlist inicial?
- Qual retenção de mensagens, logs e artefatos atende à operação e à LGPD?

## Revisão inicial

A proposta preserva o Telegram como interface, mantendo execução e autorização no controlador. Ela não deve ser implementada dentro da API pública de automação de negócios sem delimitar o domínio: trata-se de uma ferramenta interna de engenharia. Antes de qualquer código, a arquitetura, autenticação, segredos, isolamento do executor e modelo de aprovações precisam de revisão Codex.
