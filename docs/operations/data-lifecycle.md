# Client 0 — ciclo de vida de dados

Data: 2026-10-08  
Status: Accepted para F1 / piloto privado  
Escopo: dados usados pelo primeiro ciclo Client 0 no core Business Automation e referências ao ERPNext/back-office.

## Objetivo

Definir o mínimo necessário para usar dados reais no piloto privado sem transformar o core em repositório indefinido, duplicar a autoridade do ERP ou criar automações de retenção/exclusão que ainda não existem.

Este documento é política operacional do piloto. Ele não substitui avaliação jurídica, contábil ou contratual aplicável ao negócio.

## Princípios

1. **Minimização:** coletar e manter apenas o dado necessário para a próxima ação, entrega, suporte, evidência operacional ou obrigação aplicável.
2. **Autoridade única por fato:** respeitar o ADR 0001. Core e ERPNext não devem ser duas fontes editáveis do mesmo dado.
3. **Privado por padrão:** o piloto continua restrito ao ambiente privado validado em F1.
4. **Sem segredos como dado de negócio:** tokens, passwords, cookies, API keys e DATABASE_URL completa não entram em entidades, evidências ou logs.
5. **Sem dados reais no Git:** exemplos, testes e documentação pública usam apenas dados sintéticos.
6. **Sem coleta em massa implícita:** informação acessível em plataforma externa não autoriza scraping, enriquecimento ou contato automático.
7. **Retenção não é indefinida:** um dado sem finalidade operacional, suporte, disputa, case autorizado ou outra necessidade reconhecida deve ser revisado para remoção/minimização.
8. **Exclusão não é improviso:** se a operação exigir SQL destrutivo, edição direta de banco ou ferramenta não validada, parar e abrir procedimento específico.
9. **Backup não vence a política de lifecycle:** restore de backup antigo não pode reintroduzir silenciosamente dados que já deveriam permanecer removidos/restritos.

## Classificação

### 1. Público / referência externa

Exemplos:

- URL pública de oportunidade;
- título e descrição publicamente exibidos;
- requisitos, orçamento ou prazo informados publicamente pela fonte;
- referência pública de empresa/projeto.

Uso:

- registrar somente quando necessário para triagem, proposta ou rastreabilidade;
- não copiar perfil completo, histórico irrelevante ou conteúdo sem relação com o trabalho.

Autoridade:

- a fonte externa continua sendo a referência original;
- o core mantém apenas a referência necessária ao fluxo.

### 2. Operacional interno

Exemplos:

- resultado de triagem;
- qualificação;
- próxima ação;
- diagnóstico técnico;
- notas de entrega;
- estado de execução;
- evidência técnica;
- motivo de perda.

Autoridade:

- core Business Automation, conforme ADR 0001.

Regra:

- manter enquanto houver utilidade operacional, necessidade de suporte, análise de resultado ou case autorizado;
- remover/minimizar quando o contexto deixar de ter utilidade.

### 3. Dados pessoais de contato

Exemplos:

- nome;
- telefone;
- email;
- cargo;
- mensagens vinculadas a pessoa identificável.

Regra:

- coletar somente o que for necessário para continuidade comercial, entrega ou suporte;
- evitar duplicar o mesmo contato em múltiplos sistemas quando não houver necessidade;
- não usar contato coletado para nova finalidade automática sem decisão própria.

### 4. Financeiro e fiscal

Exemplos:

- razão social validada;
- identificadores fiscais;
- proposta/quotation formal;
- preço final;
- impostos;
- recebível;
- vencimento;
- pagamento;
- estorno.

Autoridade:

- ERPNext/back-office, conforme ADR 0001.

Core:

- pode manter apenas referência externa, ID, estado ou projeção mínima necessária;
- não deve se tornar ledger financeiro paralelo.

Correção/exclusão:

- ocorre na fonte autoritativa apropriada;
- remover um registro local não apaga automaticamente documento financeiro/fiscal no ERP.

### 5. Segredos e credenciais

Inclui:

- Bearer token;
- hash de token;
- password;
- API key;
- cookie de sessão;
- segredo de provider;
- DATABASE_URL completa.

Regra:

- nunca persistir como dado de negócio;
- nunca registrar em Git;
- nunca incluir em evidência operacional;
- nunca copiar para ticket, case ou log de exemplo.

### 6. Dados sensíveis ou excessivos

O piloto não deve coletar deliberadamente:

- biometria;
- dados de saúde;
- documentos pessoais completos;
- dados bancários brutos;
- credenciais do cliente;
- conteúdo privado sem relação com a entrega;
- categorias sensíveis sem necessidade explícita.

Se uma oportunidade ou cliente exigir esse tipo de dado, o fluxo atual não é suficiente: abrir decisão específica antes da coleta.

## Entrada de dados no primeiro ciclo

### 99Freelas

A primeira fonte continua manual.

Pode entrar no fluxo somente o necessário para a decisão comercial definida em `CLIENT0_FLOW.md`, como:

- URL;
- título;
- descrição;
- orçamento quando informado;
- prazo;
- stack/requisitos;
- horário da captura;
- resultado da triagem;
- próxima ação.

Não copiar por padrão:

- perfil completo;
- histórico de trabalhos;
- avaliações sem utilidade para a decisão;
- mensagens de terceiros;
- dados de contato não necessários;
- anexos irrelevantes.

Automação de coleta, scraping ou envio de proposta não é autorizada por este documento.

### Contato direto

Registrar apenas:

- identificação suficiente para não confundir a pessoa/empresa;
- canal de continuidade;
- dado necessário para proposta, execução ou suporte.

Se o dado já é autoritativo no ERP/back-office, preferir referência ao registro em vez de manter uma segunda cópia editável.

## Estados operacionais de lifecycle

Os estados abaixo descrevem o tratamento do dado; não são novos campos obrigatórios no schema.

### Coletado

Dado acabou de entrar no fluxo e ainda precisa de triagem/validação.

### Em uso

Existe próxima ação, negociação, entrega, suporte ou investigação ativa.

### Encerrado

O fluxo correspondente terminou: perdido, recusado, entregue, cancelado ou concluído.

### Retenção necessária

Há motivo operacional reconhecido para manter o dado após encerramento, por exemplo:

- suporte/garantia;
- disputa;
- referência contratual;
- reconciliação;
- incidente;
- case autorizado;
- obrigação externa aplicável.

### Elegível para remoção/minimização

Não existe mais próxima ação nem motivo reconhecido de retenção.

### Preservado

A remoção fica suspensa porque há incidente, disputa, obrigação ou investigação ativa.

### Removido do core

O dado deixou de estar disponível na operação corrente do core. Referências autoritativas externas podem continuar existindo conforme a política própria do sistema responsável.

## Retenção operacional

Este documento não define prazo fiscal, contábil ou jurídico universal.

### Oportunidade rejeitada ou perdida

Quando não houver próxima ação, disputa, aprendizado necessário ou case autorizado:

- revisar o registro;
- remover conteúdo pessoal/descritivo desnecessário;
- evitar retenção indefinida apenas para formar histórico.

### Lead sem atividade futura

Se não houver ação comercial planejada ou motivo de retenção:

- marcar operacionalmente como encerrado;
- incluir na próxima revisão manual de lifecycle;
- remover/minimizar quando seguro.

### Cliente/projeto encerrado

Manter apenas enquanto existir finalidade como:

- suporte;
- garantia;
- disputa;
- referência contratual;
- continuidade operacional;
- medição de resultado;
- case autorizado.

Após isso, revisar para minimização.

### Case, nome, marca e depoimento

Somente entram em material de divulgação após autorização humana explícita.

A autorização para operar o projeto não implica autorização para publicar identidade, marca, depoimento ou resultados.

### Financeiro/fiscal

Segue a política e requisitos aplicáveis ao ERPNext/back-office.

O core não decide sozinho prazo de retenção fiscal nem apaga documento financeiro por consequência de exclusão local.

### Logs

Logs mínimos de startup/access são evidência operacional, não arquivo permanente de conteúdo do cliente.

- não registrar body/Authorization por padrão;
- não arquivar indefinidamente sem finalidade;
- preservar cópia específica apenas quando necessária para incidente ou auditoria operacional.

### Revisão manual

Enquanto não existir mecanismo automatizado de lifecycle, o operador deve fazer revisão manual periódica durante o piloto e também:

- ao encerrar oportunidade sem próxima ação;
- ao encerrar projeto/suporte;
- antes de usar dados em case;
- ao receber pedido de correção/exportação/exclusão;
- após restaurar backup antigo.

Nenhum job automático de retenção é assumido.

## Correção

1. identificar qual sistema é autoritativo para o dado;
2. corrigir na fonte autoritativa;
3. atualizar projeções/referências locais quando necessário;
4. não sobrescrever silenciosamente dado financeiro/fiscal do ERP com valor do core;
5. registrar apenas evidência mínima da correção.

## Exportação

No piloto, exportação é procedimento humano controlado.

1. verificar identidade, escopo e finalidade do pedido;
2. localizar os registros pertinentes no core;
3. localizar referências relacionadas no ERP/back-office quando necessário;
4. exportar somente o conjunto pertinente;
5. excluir segredos, dados de terceiros e informação interna não relacionada;
6. revisar o pacote antes da entrega.

Não existe endpoint de exportação geral autorizado por este WP.

## Exclusão ou anonimização

No piloto:

1. verificar escopo e autoridade do pedido;
2. identificar dados no core e referências em sistemas autoritativos;
3. confirmar se existe motivo ativo de preservação;
4. remover ou minimizar no core apenas por mecanismo tecnicamente seguro e revisado;
5. não apagar automaticamente documento financeiro/fiscal no ERP;
6. registrar resultado mínimo sem reproduzir o conteúdo removido.

Se o core não oferecer mecanismo seguro para uma exclusão necessária, **parar**. Qualquer SQL destrutivo, cascade manual, edição direta de banco real ou procedimento semelhante exige tarefa própria, backup verificado e revisão explícita.

## Backups e dados removidos

Backup recebe a mesma classificação de proteção do dado original.

Regras:

- backup não é fonte operacional de leitura diária;
- dado removido do ambiente corrente pode permanecer em backup até a rotação/expiração normal desse backup;
- não criar retenção eterna apenas porque o dado está em um dump;
- restore de backup antigo deve ser tratado como reintrodução potencial de estado antigo;
- antes de promover um restore para operação, reaplicar exclusões, restrições e correções conhecidas que ocorreram depois do backup;
- restore destrutivo sobre banco ativo continua proibido pelo runbook atual.

## Incidentes e evidência

Preservar somente o necessário para investigar e recuperar:

- horário;
- identificador técnico;
- método/path/status quando aplicável;
- ID de recurso;
- referência de operação;
- erro técnico sanitizado.

Conteúdo pessoal pode ser preservado somente quando indispensável para a investigação.

Segredos continuam proibidos mesmo durante incidente.

## Gate para dados reais

Dados reais podem entrar no core **somente no piloto privado Client 0** quando todas as condições abaixo continuam verdadeiras:

- WP-004: cadeia Alembic e recovery validados;
- WP-005: autenticação e isolamento por Company validados;
- WP-006: backup/restore ensaiado;
- WP-007: bind privado, revogação e logs mínimos validados;
- esta política de lifecycle está aceita;
- API permanece privada;
- não há exposição pública;
- operador sabe parar a API, revogar acesso, executar/validar backup e aplicar este lifecycle manualmente.

Isso autoriza apenas uso operacional controlado do Client 0. Não autoriza:

- SaaS público;
- portal externo;
- ingestão em massa;
- scraping;
- sincronização bidirecional geral;
- coleta de categoria sensível;
- automação de exclusão;
- retenção indefinida.

## Próximos gatilhos

Criar capacidade adicional apenas quando o piloto mostrar necessidade real, por exemplo:

- rotina de exportação repetível;
- anonimização;
- política de retenção com prazos formalmente aprovados;
- job de lifecycle;
- trilha de auditoria;
- fluxo de solicitação do titular;
- expansão para cliente externo ou ambiente compartilhado.

Até lá, procedimento humano controlado é a opção deliberada.
