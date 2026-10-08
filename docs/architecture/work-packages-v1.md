# Architecture Baseline v1 — work packages para Pi/Qwen

Data: 2026-10-07. Proposta de execução posterior, **nenhum pacote autoriza implementação nesta tarefa**.
Alvo de execução: Pi usando Qwen 3.5 9B, uma sessão por pacote. Esse modelo não altera o runtime Ollama da API.

## 1. Unidade de trabalho e independência

Um pacote entrega um comportamento, contrato, teste de risco ou decisão pequena. Meta prática: 2–5 arquivos relevantes e poucos cenários de aceite; isso é limite de planejamento, não regra que force fragmentação ruim. Se leitura/edição ultrapassar uma sessão compreensível, dividir antes de executar. Migrations e segurança sempre passam pelo gate de review do AGENTS.

Independência significa **autossuficiência de contexto e verificação**, não ausência de dependências técnicas. Não é possível proteger uma rota antes de existir um contrato de autenticação. A dependência deve ser satisfeita por código/contrato estável no checkout e copiada para a ficha, sem exigir que o agente leia a spec da sessão anterior.

Este arquivo é catálogo de planejamento. As linhas de trabalho futuro não são specs prontas para execução. Antes de uma sessão, o responsável por preparar o pacote deve:

1. Conferir commit e estado do workspace; ler o código pertinente e AGENTS vigente.
2. Resolver decisões abertas indispensáveis. Se faltarem, o pacote deve ser de decisão, não de implementação especulativa.
3. Produzir **uma ficha completa**, copiando fatos/contratos necessários da baseline e do código atual, com exemplos sintéticos. A ficha deve caber em cerca de 1–3 páginas, como orçamento orientativo de contexto.
4. Incluir caminhos/símbolos exatos, comportamento atual e proposto, invariantes, exemplos de erro, testes e exclusões. Nunca escrever apenas “conforme WP anterior”.
5. Fazer preflight verificável: arquivos, símbolos, fixtures e contratos exigidos existem? Caso contrário, não começar alterações para compensar a dependência ausente.
6. Entregar ao Pi apenas a ficha, AGENTS e a pequena lista de arquivos de entrada. Baseline e outros ADRs são material de preparação, não leitura obrigatória acumulativa por sessão.

Não deixar pacote quebrado aguardando o seguinte. Ports/fakes podem ser entregues sem ativar integração. Feature parcialmente segura permanece inacessível/desabilitada até completar o gate; não chamar um endpoint isolado de “sistema seguro”. Um esquema aprovado e sua migration/teste de integridade podem precisar do mesmo pacote para manter consistência.

## 2. Contrato comum de execução

Copiar estes requisitos essenciais para **cada ficha emitida**, mesmo que pareçam repetidos:

- Escopo autorizado estrito; sem mudanças oportunistas e sem implementação de infraestrutura futura.
- Suíte normal somente SQLite em memória com StaticPool e `PRAGMA foreign_keys=ON`; nunca PostgreSQL real.
- Rodar `uv run pytest`, `.venv/bin/python -m compileall app tests` e `git diff --check` após alterações. Acrescentar teste específico de aceitação quando necessário; usar resultado real, sem contagem fixa.
- Não executar migrations sem autorização explícita da tarefa e revisão necessária. Testes PostgreSQL só em instância descartável positivamente identificada, isolada de `.env` e volumes reais.
- Nenhum segredo, `.env`, dados reais, `.ai/`, dump ou artefato temporário entra no Git.
- Pi sinaliza **“Codex review required”** antes de mudanças de auth/RBAC/tenant, schema/migrations, segurança, deploy, dependências importantes, grande refatoração ou correção que mude comportamento revelado por teste. Review é um gate, não outro agente editando simultaneamente.
- Handoff de review, se solicitado, em `.ai/codex-review.md`, fora do Git; ficha deve conter conclusão pertinente do review, não depender da memória da conversa.
- Inspecionar diff e registrar testes/limitações ao terminar. Política de commit/push deve constar da ficha e respeitar instrução da sessão. Nesta entrega: somente arquivos locais, sem commit, push, merge ou publicação.

## 3. Catálogo de pacotes pequenos

Legenda de review: **D** = documental; **R** = exige Codex review antes da mudança arriscada. Dependências abaixo são condições do repositório/decisões a verificar, não documentos de sessões anteriores a carregar. Todos incluem o contrato comum acima quando forem emitidos como ficha.

### F0: decisões e documentação

| ID | Entrega de uma sessão / arquivos candidatos | Pré-condição concreta | Aceite observável / fora do escopo |
| --- | --- | --- | --- |
| D01 | Revisar apenas `docs/CLIENT0_FLOW.md`: uma oferta, fonte, responsáveis e exceções | Respostas comerciais fornecidas pelo responsável; copiar na ficha | Fluxo permite registrar venda/perda, entrega e cobrança manual; sem código ou preços inventados |
| D02 | ADR de ownership do primeiro handoff | Gatilho e registro ERP escolhidos; campos/instância candidatos informados | Matriz campo→dono, direção e conflito; Company≠Customer≠Company ERP; sem adapter |
| D03 | Atualizar README e ARCHITECTURE como entrada da baseline | Baseline aceita e status declarado | Nenhuma dependência de lab/bridges; implementado separado de planejado; sem reescrever PRODUCT |
| D04 | Atualizar ROADMAP e decisão de billing | Distinção cobrança operacional/SaaS aceita | Gates de segurança/restore e cobrança nos lugares corretos; decisões substituídas preservadas |
| D05 | Revisar PRODUCT e contagem fixa em AGENTS | Situação dos casos externos reconfirmada ou marcada histórica | Nenhuma alegação de cliente contratado sem evidência; testes tratados dinamicamente; workflow preservado |
| D06 | Inventário focado de um commit histórico candidato | Commit disponível localmente; objetivo de reutilização explícito | Lista de arquivos, contratos aproveitáveis, incompatibilidades e testes faltantes; sem cherry-pick/merge |

### F1: dados, segurança e recuperação

| ID | Entrega de uma sessão / arquivos candidatos | Pré-condição concreta | Aceite observável / fora do escopo |
| --- | --- | --- | --- |
| F01 | Caracterizar conversão existente em `tests/test_api.py` | Endpoint atual `/leads/{id}/convert`; fixture SQLite preservada | Conversão preserva company/lead, marca won e rejeita repetição; não mudar regra comercial |
| F02 | Testar HTTP de `app/services/agent.py` em arquivo de testes próprio | Função/AgentServiceError atuais | Fake HTTP cobre timeout, erro HTTP, JSON inválido, conteúdo não string e sucesso; sem provider real/refatoração |
| F03 D/R | ADR de recuperação da cadeia Alembic | Migrations atuais e `29330b0` disponíveis para leitura | Estratégias vazio/existente, reversão e fixtures; review antes de escolher implementação; não executar migrations |
| F04 R | Harness isolado de PostgreSQL descartável | Decisão de ferramenta autorizada; Docker/alternativa disponível; review concluído | Conexão explícita ao recurso criado, recusa DB real, cleanup apenas do recurso próprio; sem migration real |
| F05 R | Correção mínima da criação de schema inicial | Estratégia F03 aprovada copiada; harness descartável funciona | Banco vazio chega ao head e fixture legada preserva dados; tarefa autoriza migrations apenas no descartável; sem auth |
| F06 R | Constraint XOR de Conversation e testes | Cadeia reproduzível; política para dados inválidos aprovada | Ambos/nenhum owner rejeitados no banco; um owner aceito; fixture inválida falha claramente, sem limpar dados |
| F07 R | Integridade cross-company de uma relação | ADR escolhe estratégia de FK/constraint e fixture de upgrade | Tentativa de ligar Conversation a lead de outra company rejeitada; pacote limitado à relação escolhida, não todas de uma vez |
| F08 D/R | ADR de identidade, sessões e capacidades | Modo de acesso Client 0 definido; histórico auth lido como referência | Matriz rota/ação/papel e revogação; mecanismo selecionado; sem login implementado |
| F09 R | Persistência mínima da identidade escolhida | ADR exato copiado; schema/migration revisados | Identidade/membership válidas e vínculos inválidos testados; sem adicionar rotas públicas |
| F10 R | Resolver identidade e revogação no mecanismo escolhido | Contrato da identidade e storage já presentes | Credencial válida/expirada/revogada/inativa tratadas; sem habilitar todo CRUD ou construir UI |
| F11 R | Resolver contexto Company autorizado | Identidade verificada; membership existente | Seletor adulterado não concede acesso; company ausente/negar acesso conforme contrato; sem migrar routers em massa |
| F12 R | Proteger **um router por ficha** | Contexto e matriz de ações disponíveis; contratos da rota copiados | Testes sem auth, tenant errado, papel negado e sucesso; emissão separada para companies/leads/customers/conversations |
| F13 R | Restringir mensagens de sistema | Router conversations protegido; política de papéis decidida | Ator comum não injeta role system; geração legítima e persistência em falha mantidas; sem redesenhar prompts |
| F14 R | Auditoria de **uma ação** privilegiada | Contexto autorizado e storage/auditoria mínimos aprovados | Ex.: mudança de membership gera ator/tenant/ação; rollback não deixa evento de sucesso; sem plataforma de auditoria |
| F15 | Contrato explícito de resposta e limites de **um endpoint** | Compatibilidade/campos permitidos decididos | Campo sensível extra do ORM não aparece; limites/paginação e erros testados; sem revisão de todos os schemas |
| F16 R | Runbook/ensaio de backup e restore isolado | Ambiente operacional candidato e metas RPO/RTO aprovados | Evidência de recuperação de dados sintéticos e reconciliação, envios desligados; sem tocar banco real |
| F17 R | Empacotamento reproduzível da API | Forma de deploy escolhida, dependências e entry point inspecionados | Imagem/artefato inicia API com config sintética; usuário/segredos adequados; sem publicar/deploy |
| F18 R | Configuração de execução privada e smoke test | Artefato executável, bind/rede/recursos aprovados | Banco não exposto à rede pública; readiness e reinício testados no ambiente isolado; sem release real |
| F19 | Logs mínimos e correlation ID | Contrato de sanitização aprovado, um fluxo escolhido | IDs propagados e erro útil sem conteúdo/credenciais; sem instalar stack de observabilidade |

F07, F12, F14 e F15 são **famílias**, não um ticket que acumula todas as variantes. Cada ficha leva sufixo e escopo fechado, por exemplo `F12-leads`. Se F09/F10 exceder uma sessão devido ao mecanismo escolhido, preparar fichas menores de storage, sessão ou bootstrap com gates explícitos; não entregar auth incompleta como liberada para uso.

### F2: operação assistida com o mínimo de software

| ID | Entrega de uma sessão / arquivos candidatos | Pré-condição concreta | Aceite observável / fora do escopo |
| --- | --- | --- | --- |
| O01 D | Template sintético de uma oferta/diagnóstico | Oferta escolhida, campos/aceite fornecidos | Entradas, exclusões, aceite, suporte e custos a preencher; sem catálogo de preços real no Git |
| O02 D | Checklist proposta→aceite→projeto→cobrança | Ownership e processo escolhidos | Versão aceita, responsáveis, exceções e referência de recebível rastreáveis; sem desenvolver ERP |
| O03 R | Persistir próximo passo de uma oportunidade/lead | Decisão de semântica e campos, auth/tenant e schema prontos para extensão | Data/responsável e validação tenant; migration revisada; sem criar Opportunity completo junto |
| O04 | Uma regra pura de qualificação explicável | Critérios/pesos/versão copiados e aprovados | Casos sintéticos conhecido/desconhecido e motivo; sem IA nem escrita de status automática |
| O05 R | Captura manual com uma chave de origem | Fonte/campos/dedupe decididos; schema revisado | Replay idêntico não duplica; outro tenant independente; conflito explícito; sem scraper |
| O06 | Uma consulta de trabalho do operador | Próxima ação disponível e permissão definida | Lista paginada de pendências ordenada, apenas tenant autorizado; sem dashboard geral |
| O07 | Uma tela/formulário interno para essa tarefa | Tecnologia/UI e contrato da API decididos; autenticação testada | Criar/consultar uma ação com erro e estado vazio; sem novo sistema de identidade |
| O08 D | Roteiro de pós-venda/case | Dados e condições do serviço disponíveis fora do Git | Medida antes/depois e autorização separada para divulgar; somente template sintético público |

Modelo de Opportunity, se necessário, exige um pacote de decisão e subsequentes recortes de persistência/consulta/transição. Não enfiar CRM inteiro em O03. ERP permanece interface de proposta, projeto, financeiro e ticket enquanto não houver motivo para integração.

### F3: adapters e automação confiável

| ID | Entrega de uma sessão / arquivos candidatos | Pré-condição concreta | Aceite observável / fora do escopo |
| --- | --- | --- | --- |
| I01 | Port/fake de um comando ERP | Contrato de ownership, payload e erros resolvido | Mesmo input/resultado em testes sintéticos; zero rede e dependência de ERP; sem alterar conversão |
| I02 R | Adapter HTTP do comando com servidor falso | Port disponível; API/campos/permissões da versão ERP verificados | Timeout, validação, auth e resultado unknown mapeados; sem chamada à instância real |
| I03 R | Persistir referência externa com isolamento | Tupla Company/conexão/tipos/IDs aprovada | Unicidade local/remota no escopo correto; conflito entre instâncias não colide; sem sincronização geral |
| I04 R | Persistir intenção/job para **um comando** | Efeito e chave idempotente decididos; schema revisado | Transação grava estado+job ou nenhum; replay/payload conflitante testados; sem broker/worker ainda |
| I05 R | Claim/lease do job no PostgreSQL | Tabela de job estável, harness descartável | Dois workers não reivindicam mesma lease; expiração testada; sem chamada externa |
| I06 | Executar **um tipo de job** usando fake/adapter | Claim, estados e adapter presentes; política de retry copiada | Sucesso, retry limitado, unknown e intervenção humana; transação não atravessa HTTP; sem novos tipos |
| I07 R | Comando de reconciliação/reprocessamento de um handoff | Referências/jobs e autorização presentes | Timeout após criação não duplica; estado unknown sem prova fica pendente; ação auditada |
| I08 | Projeção de **um status ERP** | Fonte e contrato de atualização conhecidos | Repetição/fora de ordem não regressam sem consulta; last_synced_at visível; sem escrita financeira |
| I09 | Port de geração IA + adapter atual | Contrato de `generate_agent_reply` e testes de falha presentes | Fake prova substituição; Ollama preserva retorno/503/persistência; sem segundo provider |
| I10 R | Idempotência de agent-reply | Semântica de replay/retry decidida e schema revisado | Mesma entrada não duplica customer; falha preserva mensagem; retry de geração é explícito; sem mudar envio de canal |
| I11 | Limite de contexto de IA | Orçamento e política de truncamento definidos | Histórico limitado de forma determinística, preserva políticas confiáveis; sem RAG |
| I12 R | Um campo/grupo de configuração Company | Schema/validação/permissão e versão aprovados | Tenant não altera outro, inválido rejeitado, versão auditável; sem configuração arbitrária de código |
| I13 R | Receber evento de **um canal** | Canal selecionado, binding/autenticidade/dedupe documentados | Falso/repetido/tenant adulterado rejeitados; fake provider; sem envio junto |
| I14 R | Enviar **um tipo de mensagem** aprovado | Canal de saída e política de aprovação prontos | Opt-out/pausa/duplicação/falha testados, delivery status distinto de geração; sem campanha em massa |
| I15 R | Uma receita executável de automação | Gatilho/efeito/aprovação/pausa escolhidos | Run versionado rastreável; motor não decide política; sem instalar vários motores |

Adapters com efeitos externos exigem review de segurança e autorização específica de teste integrado. Nenhum teste normal pode usar ERP, Ollama ou canal real. Integração sandbox com credenciais privadas é pacote próprio com destinos e efeitos permitidos explícitos.

### F4/F5: repetibilidade, com gatilho de uso

| ID | Entrega de uma sessão | Pré-condição concreta | Aceite / exclusões |
| --- | --- | --- | --- |
| P01 D | Checklist de onboarding/offboarding | Oferta e instalação validadas no Client 0 | Configuração, acesso, backup, treinamento e revogação; sem portal |
| P02 R | Teste negativo de isolamento de um recurso adicional | Segundo tenant sintético e recurso definido | Leitura/escrita/exportação/jobs conforme escopo negados entre tenants; sem alegação global de segurança |
| P03 D | Relatório de reutilização e custo operacional | Evidências privadas de dois usos, resumo anonimizado autorizado | Variações e custo explicitados; decisão sobre padronização; sem publicar dados de clientes |
| P04 D | Decisão de empacotamento comercial | Demanda/margem/suporte demonstrados | Escolha justificada entre serviço/pacote/produto; SaaS permanece opcional |

Não emitir pacote para Kubernetes, microserviços, RAG ou billing SaaS apenas para completar um roadmap. Esses itens exigem novo problema e gate.

## 4. Modelo de ficha autossuficiente

Copiar e preencher integralmente; campos vazios impedem começar implementação.

```markdown
# WP-<id>: <um resultado>
Status: pronto / bloqueado por decisão / aguardando review
Base: <branch, commit, data>; responsável: <papel>
Objetivo observável: <o que o operador ou teste poderá verificar>

## Autorização e limites
<Documentação/testes/código permitidos. Política de Git desta sessão.
Destinos externos proibidos/permitidos. Precisa review? Resultado do gate.>

## Contexto suficiente
<Estado atual comprovado, regra de negócio, owner do dado, semântica Company.
Copiar o contrato pertinente; não apenas linkar spec anterior.>

## Pré-condições verificáveis
<Símbolos/arquivos e testes que devem existir. Decisões já respondidas.
Se faltar algo, relatar bloqueio sem implementar dependência improvisada.>

## Ler / pode alterar / não alterar
<Lista curta de caminhos e símbolos atuais; arquivos novos permitidos.>

## Contrato desejado
<Entrada sintética, saída, erros, tenant, idempotência, transação,
limites e comportamento em falha pertinentes a esta tarefa.>

## Aceite
1. <Given/When/Then verificável>
2. <Falha relevante>
3. <Invariante de compatibilidade e isolamento>

## Fora do escopo
<Features vizinhas explicitamente excluídas.>

## Validação segura
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
<Teste adicional necessário e destino isolado exato; nunca banco real.>

## Encerramento
<Diff, testes, riscos, arquivos alterados, estado dos gates e pendências.
Não depender de memória da sessão; não incluir segredos/dados reais.>
```

## 5. Exemplo preenchido de pacote pequeno

**WP F02: caracterizar falhas HTTP do serviço de agente, sem refatorar.**

Base de planejamento: `main@84ea22e`; conferir novamente antes de executar. Status: proposta pronta para adaptação ao checkout, não execução autorizada por esta entrega.

Objetivo: verificar que falhas HTTP/JSON esperadas viram `AgentServiceError` sem capturar bugs genericamente.

Contexto suficiente: `app/services/agent.py` expõe `generate_agent_reply(message: str, history: list[dict]) -> str`. Usa `httpx.post`, URL/modelo de `app.database.settings`, `stream=False` e timeout de 120 s. Faz `raise_for_status`, lê `message.content`, exige string. Captura `httpx.HTTPError` e, na leitura do JSON, `ValueError`, `KeyError`, `TypeError`. `app/routers/conversations.py` persiste customer antes dessa chamada e converte AgentServiceError em 503 genérico. Os testes API atuais monkeypatcham a função de geração; não cobrem HTTP.

Pré-condições: esses símbolos e comportamentos ainda existem; `tests/conftest.py` define DATABASE_URL SQLite em memória antes de importar app e usa StaticPool/FK; nenhuma conexão de provider necessária. Se o código divergir, atualizar ficha antes de editar.

Ler: `AGENTS.md`, `app/services/agent.py`, `tests/conftest.py` e testes de falha de IA em `tests/test_api.py`. Alterar apenas novo `tests/test_agent_service.py`. Não alterar aplicação, dependências, `.env`, migrations ou infra. Usar monkeypatch de `httpx.post` no módulo alvo ou transporte falso compatível com o código real, sem adicionar biblioteca.

Aceite:

1. Resposta sintética válida devolve texto; fake confere modelo configurado, papéis do histórico, mensagem final incluída uma vez, `stream=False` e timeout atual.
2. Timeout e resposta HTTP de erro levantam `AgentServiceError`.
3. JSON inválido, estrutura sem message/content e conteúdo não string levantam `AgentServiceError`.
4. Erro de programação inesperado no fake não é convertido genericamente em indisponibilidade; não alterar serviço para satisfazer teste se isso revelar mudança de comportamento.
5. Nenhuma requisição real ocorre; testes API existentes continuam passando com persistência/503 preservados.

Validar: `uv run pytest`, `.venv/bin/python -m compileall app tests`, `git diff --check`. Banco isolado apenas. Se teste revelar comportamento existente inesperado, explicar e emitir outro pacote com review antes de corrigi-lo. Encerrar com diff e resultado atual. A ficha de execução deve explicitar política Git; não herdar autorização de push desta proposta.

Este exemplo ilustra a escala desejada: a sessão recebe contrato completo de um arquivo e seus limites; não precisa ler o projeto arquitetural inteiro nem a spec de outro pacote.

## 6. Revisão e encerramento de sessão

Cada pacote conclui com pequeno registro: resultado, commit-base, arquivos alterados, comandos/resultados, aceite demonstrado, limitações e dependências que agora existem. O próximo pacote é preparado contra o **código resultante**, não a narrativa anterior.

Quando um gate de segurança/schema/deploy impedir execução, Pi deve pedir o review exigido com escopo concreto e evidência, sem alargar o pacote ou operar produção para “descobrir”. Revisão Codex não autoriza automaticamente migrations reais, publicação ou ações externas; essas dependem da instrução da tarefa.

Pacotes de documentação e caracterização podem ser executados isoladamente. Pacotes de implementação devem entrar um por sessão e, se necessário, várias sessões independentes por família. A arquitetura pode ser ampla; o contexto de execução deve continuar pequeno e verificável.
