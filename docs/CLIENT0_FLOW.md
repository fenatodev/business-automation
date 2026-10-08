# Client 0 - Fluxo Operacional Comercial

## Status

Documento operacional completo para fluxo comercial da empresa Client 0.

## Objetivo

Definir o fluxo operacional comercial completo, da descoberta da oportunidade até pós-venda e geração de case.

Permite operação manual de ciclo completo sem depender de funcionalidades não implementadas.

## Fluxo Obrigatório

```
oportunidade -> triagem -> qualificacao -> diagnostico -> escolha da oferta
-> proposta -> aprovacao interna -> envio -> aceite do cliente
-> projeto/execucao -> aceite tecnico -> suporte/post-venda
-> medicao de resultado -> case/recompra

A cobranca corre em trilha financeira vinculada ao acordo comercial e pode ocorrer
como entrada, por marcos, de forma recorrente ou apos a entrega. Confirmacao de
recebimento sempre vem do sistema financeiro autoritativo.
```

---

## Fontes de Oportunidades

### 1. 99Freelas

- **tipo de entrada**: formulario de cadastro de projeto
- **referencia/URL externa**: https://www.99freelas.com.br
- **dados minimos**: titulo, descricao, orcamento, prazo, categoria
- **responsavel**: comercial (quem monitora fonte)
- **proxima acacao**: aplicar triagem e qualificacao
- **restricoes conhecidas**: integracao depende dos termos da plataforma e de mecanismo permitido; nenhuma automacao assumida
- **possibilidade futura de integracao**: API/feed/email/browser assistido somente quando permitido pelos termos da plataforma

### 2. Workana

- **tipo de entrada**: formulario de cadastro de projeto
- **referencia/URL externa**: https://www.workana.com
- **dados minimos**: titulo, descricao, orcamento, prazo, categoria
- **responsavel**: comercial (quem monitora fonte)
- **proxima acacao**: aplicar triagem e qualificacao
- **restricoes conhecidas**: integracao depende dos termos da plataforma e de mecanismo permitido; nenhuma automacao assumida
- **possibilidade futura de integracao**: API/feed/email/browser assistido somente quando permitido pelos termos da plataforma

### 3. Upwork

- **tipo de entrada**: formulario de cadastro de projeto
- **referencia/URL externa**: https://www.upwork.com
- **dados minimos**: titulo, descricao, orcamento, prazo, categoria
- **responsavel**: comercial (quem monitora fonte)
- **proxima acacao**: aplicar triagem e qualificacao
- **restricoes conhecidas**: integracao depende dos termos da plataforma e de mecanismo permitido; nenhuma automacao assumida
- **possibilidade futura de integracao**: API/feed/email/browser assistido somente quando permitido pelos termos da plataforma

### 4. Freelancer

- **tipo de entrada**: formulario de cadastro de projeto
- **referencia/URL externa**: https://www.freelancer.com
- **dados minimos**: titulo, descricao, orcamento, prazo, categoria
- **responsavel**: comercial (quem monitora fonte)
- **proxima acacao**: aplicar triagem e qualificacao
- **restricoes conhecidas**: integracao depende dos termos da plataforma e de mecanismo permitido; nenhuma automacao assumida
- **possibilidade futura de integracao**: API/feed/email/browser assistido somente quando permitido pelos termos da plataforma

### 5. LinkedIn

- **tipo de entrada**: mensagem direta, post de recrutamento, conexao com post
- **referencia/URL externa**: https://www.linkedin.com
- **dados minimos**: nome do contato, empresa, cargo, titulo do projeto, descricao, orcamento
- **responsavel**: comercial (quem monitora fonte)
- **proxima acacao**: aplicar triagem e qualificacao
- **restricoes conhecidas**: automacao depende das politicas e permissoes da plataforma; nenhuma coleta automatica assumida
- **possibilidade futura de integracao**: API ou browser assistido somente quando permitido pelos termos do LinkedIn

### 6. Formulario/Site Proprio

- **tipo de entrada**: formulario web (contato, orcamento, servico)
- **referencia/URL externa**: site proprio da empresa
- **dados minimos**: nome, empresa, email, telefone, servico desejado, descricao, orcamento
- **responsavel**: comercial (quem monitora canal proprio)
- **proxima acacao**: aplicar triagem e qualificacao
- **restricoes conhecidas**: exigir consentimento/aviso de privacidade adequado e minimizar dados coletados
- **possibilidade futura de integracao**: entrada direta no core por formulario/API quando a capacidade existir

### 7. Indicao

- **tipo de entrada**: indicacao de cliente existente
- **referencia/URL externa**: contato direto
- **dados minimos**: nome do indicado, empresa, servico desejado, descricao
- **responsavel**: comercial (quem recebe indicacao)
- **proxima acacao**: aplicar triagem e qualificacao
- **restricoes conhecidas**: pode nao ter orcamento definido inicialmente
- **possibilidade futura de integracao**: registro manual em sistema ou formulario dedicado

### 8. Prospeccao Manual

- **tipo de entrada**: prospeccao ativa (cold call, email, visita)
- **referencia/URL externa**: lista de contatos
- **dados minimos**: nome, empresa, cargo, servico desejado, descricao
- **responsavel**: comercial (quem prospecta)
- **proxima acacao**: aplicar triagem e qualificacao
- **restricoes conhecidas**: depende de disponibilidade do comercial
- **possibilidade futura de integracao**: enriquecimento ou assistencia somente com fonte licita, politica de contato e aprovacao humana

### 9. Outras Fontes Futuras por Adapter

- **tipo de entrada**: variavel conforme adapter
- **referencia/URL externa**: variavel
- **dados minimos**: variavel conforme fonte
- **responsavel**: variavel
- **proxima acacao**: aplicar triagem e qualificacao
- **restricoes conhecidas**: desconhecidas ate implementacao
- **possibilidade futura de integracao**: dependente de adapter especifico

---

## Modelo Operacional por Etapa

### 1. Oportunidade

- **entrada**: dados brutos da fonte (titulo, descricao, orcamento, prazo, categoria, contato)
- **responsavel**: comercial (quem monitora fonte)
- **decisao necessaria**: registrar como oportunidade no sistema
- **saida**: registro de oportunidade com origem e metadados
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: planilha ou registro em CRM basico
- **erro/excecao relevante**: dados incompletos ou fonte nao confiavel
- **evidencia necessaria**: captura da fonte (print, link, arquivo)

### 2. Triagem

- **entrada**: oportunidade registrada
- **responsavel**: comercial
- **decisao necessaria**: filtrar oportunidades nao relevantes ou fora do escopo
- **saida**: oportunidade aprovada para qualificacao ou arquivada
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: checklist manual de criterio de elegibilidade
- **erro/excecao relevante**: oportunidade rejeitada por criterio comercial
- **evidencia necessaria**: criterio de triagem aplicado e decisao registrada

### 3. Qualificacao

- **entrada**: oportunidade aprovada em triagem
- **responsavel**: comercial
- **decisao necessaria**: validar perfil do cliente, viabilidade do projeto e alinhamento
- **saida**: oportunidade qualificada ou desqualificada
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: BANT ou SPIN tradicional
- **erro/excecao relevante**: cliente desqualificado apos qualificacao
- **evidencia necessaria**: checklist de qualificacao preenchido

### 4. Diagnostico

- **entrada**: oportunidade qualificada
- **responsavel**: especialista tecnico ou comercial
- **decisao necessaria**: entender problema do cliente, escopo e requisitos
- **saida**: relatorio de diagnostico com analise de viabilidade
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: reuniao presencial ou videochamada com questionario
- **erro/excecao relevante**: diagnostico inviavel ou escopo nao fechado
- **evidencia necessaria**: documentacao do diagnostico (PDF, documento, gravacao)

### 5. Escolha da Oferta

- **entrada**: diagnostico concluido
- **responsavel**: especialista tecnico
- **decisao necessaria**: selecionar a familia de solucao apropriada
- **saida**: oferta proposta (familia de solucao + escopo preliminar)
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: matriz de decisao interna
- **erro/excecao relevante**: nenhuma oferta adequada encontrada
- **evidencia necessaria**: documentacao da escolha (justificativa tecnica)

### 6. Proposta

- **entrada**: oferta escolhida
- **responsavel**: comercial + especialista tecnico
- **decisao necessaria**: redigir proposta formal com escopo, preco, prazo, termos
- **saida**: proposta formal enviada para aprovacao interna
- **sistema autoritativo**: ERPNext (documentos comerciais)
- **fallback manual**: documento Word/PDF redigido manualmente
- **erro/excecao relevante**: proposta rejeitada na aprovacao interna
- **evidencia necessaria**: versao identificavel da proposta e registro de revisao interna

### 7. Aprovacao Interna

- **entrada**: proposta formal
- **responsavel**: gerente ou socio (segundo hierarquia)
- **decisao necessaria**: aprovar ou rejeitar proposta
- **saida**: proposta aprovada ou arquivada
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: aprovacao por email ou documento assinado
- **erro/excecao relevante**: proposta rejeitada
- **evidencia necessaria**: registro explicito de quem aprovou, quando e qual versao foi aprovada

### 8. Envio

- **entrada**: proposta aprovada internamente
- **responsavel**: comercial
- **decisao necessaria**: enviar proposta ao cliente
- **saida**: proposta entregue ao cliente
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: email com anexo ou entrega fisica
- **erro/excecao relevante**: proposta nao entregue (erro de envio)
- **evidencia necessaria**: confirmacao de entrega (email de envio, tracking)

### 9. Aceite do Cliente

- **entrada**: proposta entregue
- **responsavel**: cliente + comercial
- **decisao necessaria**: cliente aceita ou rejeita proposta
- **saida**: aceite formal ou rejeicao
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: email de aceite ou documento assinado
- **erro/excecao relevante**: cliente nao responde (follow-up necessario)
- **evidencia necessaria**: aceite assinado digitalmente ou por email

### 10. Projeto/Execucao

- **entrada**: aceite do cliente
- **responsavel**: equipe tecnica
- **decisao necessaria**: iniciar projeto e executar escopo
- **saida**: projeto concluido
- **sistema autoritativo**: ERPNext (projeto convencional)
- **fallback manual**: gestao de projeto manual
- **erro/excecao relevante**: desvio de escopo, atraso, qualidade abaixo do esperado
- **evidencia necessaria**: documentacao de execucao (changelog, relatorios)

### 11. Aceite Tecnico

- **entrada**: projeto concluido
- **responsavel**: cliente + equipe tecnica
- **decisao necessaria**: cliente valida entrega tecnica
- **saida**: aceite tecnico formal
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: checklist de aceite tecnico
- **erro/excecao relevante**: nao conformidades detectadas (devolucao para retrabalho)
- **evidencia necessaria**: documento de aceite tecnico assinado

### 12. Cobranca

- **entrada**: gatilho comercial acordado na proposta/contrato (entrada, marco, recorrencia ou pos-entrega)
- **responsavel**: financeiro
- **decisao necessaria**: emitir cobranca conforme a condicao comercial aprovada
- **saida**: documento de cobranca/recebivel registrado
- **sistema autoritativo**: ERPNext (financeiro)
- **fallback manual**: emissao e controle manual no back-office
- **erro/excecao relevante**: falha de emissao, divergencia de valor ou gatilho ainda nao cumprido
- **evidencia necessaria**: referencia do documento emitido, valor, vencimento e condicao que originou a cobranca

### 13. Confirmacao de Recebimento

- **entrada**: recebivel emitido e evento/registro financeiro da fonte autoritativa
- **responsavel**: financeiro
- **decisao necessaria**: confirmar recebimento somente com evidencia do sistema financeiro
- **saida**: recebimento confirmado, parcial, vencido ou pendente
- **sistema autoritativo**: ERPNext (financeiro)
- **fallback manual**: conciliacao manual no back-office
- **erro/excecao relevante**: pagamento atrasado, parcial, estornado ou nao identificado
- **evidencia necessaria**: registro de conciliacao/recebimento no sistema autoritativo

### 14. Suporte/Post-Venda

- **entrada**: entrega iniciada/concluida ou periodo de suporte contratado; nao depende obrigatoriamente de pagamento integral
- **responsavel**: suporte tecnico
- **decisao necessaria**: atender conforme escopo e condicoes de suporte contratadas
- **saida**: solicitacao resolvida, escalada ou registrada como fora de escopo
- **sistema autoritativo**: processo manual do Client 0; futuro core ou ferramenta unica de suporte quando adotada
- **fallback manual**: atendimento por email, telefone ou chat com registro da pendencia
- **erro/excecao relevante**: problema nao resolvido, solicitacao fora de escopo ou dependencia do cliente
- **evidencia necessaria**: registro da solicitacao, resposta, responsavel e desfecho

### 15. Medicao de Resultado

- **entrada**: periodo de post-venda concluido
- **responsavel**: comercial + cliente
- **decisao necessaria**: validar resultados alcançados pelo cliente
- **saida**: relatorio de resultados
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: reuniao de revisao com cliente
- **erro/excecao relevante**: resultados abaixo do esperado
- **evidencia necessaria**: documento de medicao de resultados (KPIs, metricas)

### 16. Case/Recompra

- **entrada**: resultados validados
- **responsavel**: comercial
- **decisao necessaria**: criar case de sucesso ou oferecer nova oportunidade
- **saida**: case publicado ou nova oportunidade aberta
- **sistema autoritativo**: processo manual do Client 0; futuro core apenas quando a capacidade correspondente existir
- **fallback manual**: documento case em PDF ou blog post
- **erro/excecao relevante**: cliente nao concorda com publicacao do case
- **evidencia necessaria**: case publicado ou nova oportunidade registrada

---

## Catálogo Comercial Inicial

### 1. Diagnostico de Automação

- **hipótese operacional**: fase inicial de descoberta de problemas e oportunidades
- **entregáveis**: diagnostico detalhado, analise de viabilidade
- **hipótese de valor**: identificacao precisa do problema e escopo
- **nao inventar**: precos, SLA ou prazo especificos

### 2. Implantacao de Fluxo

- **hipótese operacional**: fase de implementacao da solucao proposta
- **entregáveis**: fluxo automatizado implantado, documentacao tecnica
- **hipótese de valor**: automatizacao funcional que resolve problema
- **nao inventar**: precos, SLA ou prazo especificos

### 3. Assistencia Comercial/CRM

- **hipótese operacional**: fase de suporte ao uso da solucao
- **entregáveis**: treinamento, ajustes, otimizacoes
- **hipótese de valor**: operacao continua da automatizacao
- **nao inventar**: precos, SLA ou prazo especificos

### 4. Sustentacao de Automações

- **hipótese operacional**: fase de manutencao preventiva e corretiva
- **entregáveis**: monitoramento, correcoes, atualizacoes
- **hipótese de valor**: disponibilidade continua da solucao
- **nao inventar**: precos, SLA ou prazo especificos

---

## Ownership

### BA (Business Automation) / Core

Responsavel por:

- lead (registro, origem, estado)
- origem da oportunidade
- qualificacao
- oportunidade
- proxima acacao
- conversa e inteligencia operacional

### ERPNext

Responsavel por:

- proposta formal
- preco final
- documentos comerciais
- projeto convencional
- financeiro
- cobranca
- recebimento

### Humano

Responsavel por:

- aprovar escopo
- aprovar preco
- aprovar envio
- interpretar aceite
- acoes sensiveis (aprovacoes, assinaturas, liberacoes)

### IA

Responsavel por:

- sugerir classificacoes
- resumir conversas
- classificar oportunidades
- redigir documentos (esboscos)

**Nao autoriza nem confirma fatos financeiros.**

---

## Critério de Sucesso

O documento deve permitir que uma pessoa opere manualmente um ciclo completo:

```
oportunidade -> triagem -> qualificacao -> diagnostico -> escolha da oferta
-> proposta -> aprovacao interna -> envio -> aceite do cliente
-> projeto/execucao -> aceite tecnico -> suporte/post-venda
-> medicao de resultado -> case/recompra

A cobranca corre em trilha financeira vinculada ao acordo comercial e pode ocorrer
como entrada, por marcos, de forma recorrente ou apos a entrega. Confirmacao de
recebimento sempre vem do sistema financeiro autoritativo.
```

**Sem depender de funcionalidades ainda nao implementadas.**

---

## Decisões Documentadas

1. **Fluxo completo definido** - 16 etapas do ciclo comercial
2. **Fontes de oportunidade listadas** - 9 fontes candidatas com metadados
3. **Modelo operacional por etapa** - entrada, responsavel, decisao, saida, sistema, fallback, erro, evidencia
4. **Ownership claro** - BA/core, ERPNext, humano, IA com responsabilidades definidas
5. **Catálogo comercial inicial** - 4 familias de solucao como hipóteses operacionais
6. **Precos, SLA e prazos nao inventados** - deixados para definicao futura
7. **Operacao manual possivel** - fallback manual definido para cada etapa
8. **Fontes sem integracao implementada** - apenas registro manual de metadados

---

## Decisões Abertas

1. **Qual fonte implementar primeiro?** - entre as 9 fontes listadas
2. **Qual etapa automatizar primeiro?** - prioridade de automatizacao no fluxo
3. **Campos obrigatorios minimos para handoff** - quais dados minimos para ERPNext
4. **Falhas com retry automatico** - quais erros sao retriables
5. **Interface UI/API minima** - qual operacao manual e viavel sem UI
6. **Hierarquia de aprovacao interna** - quem aprova proposta (gerente? socio?)

---

## Validação Executada

```bash
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
```

Todos os comandos executados com sucesso. Nenhum codigo alterado - apenas documento de fluxo operacional criado.

---

## Histórico

- **Criado em**: 2026-10-08
- **Ultima atualizacao**: 2026-10-08
- **Versao**: 1.0 - Fluxo operacional completo
