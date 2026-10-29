# WP-061 — Codex temporário, Junie permanente

## Objetivo e limites

Aproveitar temporariamente a cota já incluída no plano do Codex para revisar e melhorar a arquitetura. **A operação do produto e a continuidade do desenvolvimento não podem depender do Codex, de uma sessão de chat, de memória privada de um agente ou de créditos de API.**

O repositório GitHub é a fonte de verdade. A instância privada de n8n, as credenciais e o banco de dados ficam fora do Git. Codex e Junie são executores intercambiáveis do mesmo contrato técnico.

## Antes de iniciar qualquer implementação

1. Ler `AGENTS.md`, specs e documentação de operação atuais; não assumir que relatórios históricos descrevem o ambiente ativo.
2. Registrar estado Git, testes executáveis, dependências, serviços envolvidos, riscos e critério objetivo de aceite.
3. Preferir corrigir falhas reais a introduzir novas camadas, frameworks de agentes, infraestrutura ou ferramentas redundantes.
4. Para tarefas com banco/n8n: usar dados sintéticos e serviços descartáveis; não executar migrações no ambiente principal sem autorização específica.
5. Não ativar workflow comercial, publicar endpoint, enviar mensagens reais, efetuar cobrança, consumir APIs pagas ou fazer merge sem autorização explícita.

## Uso do Codex (temporário)

- Uma tarefa delimitada por branch/PR; contexto persistente no GitHub, não em mensagens do Codex.
- Revisão arquitetural com achados reproduzíveis: arquivo, linha, impacto, cenário de falha, correção e teste.
- Testes no CI e, quando indispensável, harness privado no Ubuntu.
- Compressão e memória do Codex são otimizações opcionais **do executor**, não pré-requisitos da aplicação.
- Não modificar configurações locais do Codex, plugins, MCP, memória ou permissões até inspeção da instalação real e comparação com alternativas existentes.
- Ao terminar cada tarefa, atualizar o handoff com estado, decisões e comandos; não armazenar segredos.

## Retorno obrigatório ao Junie

Ao atingir a cota do Codex, o Junie deve conseguir, **sem acesso ao histórico de chats do Codex**:

1. Fazer checkout de uma branch informada.
2. Ler `AGENTS.md`, o spec da tarefa e o handoff registrado no PR.
3. Executar `uv run pytest -q`, compilação e validação do diff em ambiente descartável e documentado.
4. Retomar o próximo passo descrito, registrar evidências e abrir/atualizar o PR.
5. Identificar claramente qualquer dependência local (Docker, n8n, PostgreSQL), evitando repetir experimentos já documentados.

**Gate de portabilidade:** um agente diferente daquele que implementou a mudança deve reproduzir o teste sem contexto privado da sessão anterior. Se não conseguir, a tarefa não está pronta para merge.

## Modelo de handoff para cada PR

- **Objetivo:** comportamento a entregar; não apenas atividade técnica.
- **Estado:** concluído / pendente / bloqueado.
- **Branch, PR e último commit:** referências verificadas.
- **Decisões arquiteturais:** alternativas recusadas e justificativas.
- **Arquivos alterados:** resumo.
- **Testes:** comando, quantidade, resultado, e identificação de E2E real quando exigido.
- **Riscos:** segurança, tenancy, exposição pública, custo, migrações.
- **Ambiente local necessário:** apenas se indispensável; nenhuma senha/token.
- **Próxima ação inequívoca:** tarefa que o Junie pode começar diretamente.

## Auditoria de arquitetura antes de automatizar operação contínua

Prioridades em ordem:
1. Verificar fluxo real de intake, review queue, n8n e estados duráveis após reinício.
2. Revisar idempotência, corrida entre workers, retry com backoff, estado de falha e observabilidade sem PII.
3. Conferir isolamento por tenant, controle de acesso e bloqueio de envios externos não autorizados.
4. Definir como recuperar PostgreSQL/n8n com backup validado, sem substituir instâncias por engano.
5. Eliminar referências obsoletas e caminhos absolutos do ambiente Python nos contratos dos agentes.

Não criar uma nova arquitetura de orquestração antes de demonstrar lacuna concreta na existente.

## Estado da inspeção local em 29/10/2026

A tentativa de acesso ao Ubuntu via conector remoto retornou **dispositivo offline**. A versão do Codex CLI, opções de compressão, memória persistente e plugins **não foram verificadas nesta sessão**. Não afirmar que estão habilitados ou funcionais até inspecionar configurações e comportamento com ferramentas locais.
