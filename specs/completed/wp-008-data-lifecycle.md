# WP-008 — Data lifecycle do Client 0

Status: concluído  
Base: `origin/main` atual no início da execução  
Executor: GitHub/ChatGPT  
Motivo: decisão operacional/documental; não exige runtime local.

## Objetivo

Fechar o gate mínimo de ciclo de vida de dados antes do primeiro uso real do Client 0, sem criar funcionalidade que ainda não existe.

O resultado deve responder claramente:

- quais dados podem entrar no core;
- quais dados não devem entrar;
- quem é autoridade por classe de dado;
- quando um registro deixa de ser necessário;
- como exportação/correção/exclusão são tratadas no piloto;
- como backups afetam exclusão;
- como incidentes e evidências preservam apenas o necessário;
- quais lacunas impedem expansão além do piloto privado.

## Pode alterar somente

- novo `docs/operations/data-lifecycle.md`;
- `docs/operations/client0-runbook.md`;
- `docs/DECISIONS.md`;
- `docs/ROADMAP.md`.

Nenhum código, migration, teste, dependência ou schema.

## Princípios obrigatórios

1. Minimização: coletar apenas o necessário para o fluxo Client 0.
2. Autoridade: respeitar ADR 0001; core e ERPNext não viram duas fontes editáveis do mesmo fato.
3. Segredos nunca são dados de negócio e não entram em registros, logs ou evidências.
4. Dados reais nunca entram no repositório Git.
5. Dados financeiros/fiscais formais permanecem no ERPNext/back-office autoritativo.
6. Conteúdo de plataforma externa não autoriza coleta em massa, scraping ou contato automático.
7. Não afirmar base legal, prazo fiscal ou obrigação jurídica específica sem decisão jurídica/contábil própria.
8. Não inventar delete endpoint, anonymizer, scheduler ou job que não existe.
9. No piloto, exportação/correção/exclusão podem ser procedimentos humanos controlados.
10. Backup não deve ser tratado como mecanismo de retenção indefinida.

## Classificação mínima

O documento deve distinguir pelo menos:

### Público / referência externa

Exemplos:

- URL pública da oportunidade;
- título público;
- requisitos publicamente exibidos pela fonte.

### Operacional interno

Exemplos:

- score/triagem;
- próxima ação;
- diagnóstico;
- notas técnicas;
- estado de execução.

### Dados pessoais de contato

Exemplos:

- nome;
- telefone;
- email;
- cargo;
- mensagens vinculadas a pessoa identificável.

Coletar apenas quando necessário ao fluxo.

### Financeiro/fiscal

ERPNext/back-office é autoridade.

O core pode manter somente referência/status mínimo quando necessário.

### Segredos/credenciais

Tokens, passwords, API keys, cookies de sessão e DATABASE_URL completa:

- nunca persistir como dado de negócio;
- nunca colocar no Git;
- nunca copiar para evidência operacional.

### Dados sensíveis ou excessivos

O primeiro piloto não deve coletar deliberadamente categorias sensíveis, documentos pessoais, biometria, saúde, dados bancários brutos ou conteúdo sem relação com a entrega, salvo decisão posterior explícita e necessária.

## Entrada e minimização

Para a primeira fonte 99Freelas:

- descoberta/avaliação permanece manual;
- registrar somente os campos necessários definidos em `CLIENT0_FLOW.md`;
- não copiar perfil inteiro, histórico irrelevante ou dados que não serão usados;
- não automatizar coleta ou envio de proposta neste WP.

Para contato direto:

- registrar somente o canal e dado necessário para continuidade comercial;
- evitar duplicação do mesmo contato em múltiplos sistemas sem ownership definido.

## Estados de lifecycle

Definir estados operacionais, não necessariamente campos de banco:

- coletado;
- em uso;
- encerrado;
- retenção necessária;
- elegível para remoção/anonymização;
- preservado por obrigação/conflito/incidente;
- removido do core.

A mudança de estado pode ser manual no piloto.

## Retenção

Não definir prazo fiscal/legal universal.

Para o core, usar gatilhos operacionais:

- oportunidade rejeitada/perdida sem razão de retenção: revisar e remover/minimizar quando não houver próxima ação;
- lead sem atividade futura: não reter indefinidamente;
- cliente/projeto encerrado: manter somente enquanto houver necessidade operacional, suporte, garantia, disputa, case autorizado ou referência contratual;
- case/depoimento/nome/marca: somente com autorização humana explícita;
- financeiro/fiscal: segue política do ERPNext/back-office e requisitos aplicáveis fora deste documento.

O documento deve exigir uma revisão periódica manual enquanto não existir job de lifecycle.

Não inventar automação.

## Exportação/correção/exclusão no piloto

Definir procedimento humano:

1. verificar identidade/escopo do pedido;
2. localizar dados no core e referências no ERP;
3. exportar somente dados pertinentes;
4. corrigir na fonte autoritativa;
5. excluir/anonymizar no core somente quando permitido e tecnicamente seguro;
6. não apagar silenciosamente documento financeiro/fiscal autoritativo;
7. registrar resultado mínimo sem copiar dados removidos.

Se a exclusão exigir SQL destrutivo ou operação sem ferramenta segura, parar e abrir procedimento/tarefa específica. Não improvisar no banco real.

## Backups

Definir:

- backups são protegidos como o dado original;
- não são usados para reintroduzir dado removido na operação corrente;
- exclusão lógica/operacional pode permanecer em backup até expiração/rotação normal;
- restore de backup antigo exige reaplicar exclusões/restrições conhecidas antes de voltar à operação;
- nenhuma retenção eterna "porque está no backup".

## Incidentes

Preservar somente evidência necessária:

- horário;
- identificadores técnicos;
- status;
- referência do evento;
- conteúdo pessoal somente se indispensável à investigação.

Segredos continuam proibidos.

## Gate para dados reais

O documento deve declarar que dados reais no core só são permitidos no piloto privado quando:

- WP-004 migrations/recovery está concluído;
- WP-005 auth/tenant isolation está concluído;
- WP-006 backup/restore está concluído;
- WP-007 private startup/revocation/logging está concluído;
- este lifecycle está aceito;
- acesso permanece privado;
- não há exposição pública;
- operador conhece backup, revogação, parada e procedimento manual de lifecycle.

Isso não autoriza SaaS público nem ingestão em massa.

## Atualizações auxiliares

### Runbook

Adicionar referência curta ao lifecycle:

- antes de inserir dado real;
- antes de exportar/excluir;
- após restore de backup antigo.

### DECISIONS

Registrar decisão de lifecycle F1, deixando explícito que:

- é política do piloto privado;
- não substitui orientação jurídica/contábil;
- não autoriza coleta em massa;
- ERP permanece autoridade financeira/fiscal.

### ROADMAP

Marcar F1 como concluída para **piloto privado Client 0**, condicionada ao cumprimento operacional dos documentos e sem autorização de exposição pública.

Não alterar os gates F2-F5.

## Acceptance

- novo lifecycle cobre classificação, minimização, retenção, exportação/correção/exclusão, backup e incidente;
- não há prazo jurídico inventado;
- ownership bate com ADR 0001;
- runbook referencia o lifecycle;
- DECISIONS registra a decisão;
- ROADMAP registra F1 concluída para piloto privado;
- diff limitado aos quatro arquivos autorizados;
- `git diff --check` conceitualmente limpo pela revisão remota.

## Git

Branch de implementação:

`wp/008-data-lifecycle`

Commit sugerido:

`docs: define Client 0 data lifecycle`

Merge somente após revisão remota.


## Resultado

Concluído em 2026-10-08.

- branch: `wp/008-data-lifecycle`;
- PR: #32;
- merge commit: `e8458b4f117393fbb2eabe346dfce844d493aa7f`;
- criado `docs/operations/data-lifecycle.md`;
- classificação, minimização, ownership, retenção por gatilho operacional, correção, exportação, exclusão/anonymização, backups e incidentes documentados;
- nenhum prazo jurídico/fiscal universal foi inventado;
- ERPNext/back-office permanece autoritativo para financeiro/fiscal;
- runbook passou a referenciar lifecycle antes de dados reais e após restore antigo;
- DECISIONS registra a política do piloto privado;
- ROADMAP marca F1 concluída somente para piloto privado Client 0;
- nenhuma alteração de código, migration, dependência ou schema.
