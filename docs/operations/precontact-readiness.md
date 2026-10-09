# Client 0 — prontidão antes de prospecção ativa

**Status:** ordem de preparação adotada pelo operador, **não** checklist concluído nem replanejamento das fases.  
**Data:** 2026-10-08.  
**Referências:** `docs/ROADMAP.md` (F0–F5), `docs/architecture/delivery-plan-v1.md`, `docs/operations/client0-offer-v1.md`.  
**Premissa do responsável:** finalizar uma estrutura demonstrável antes de contatar clientes, enviar novas propostas ou retomar prospecção. A oportunidade já armazenada permanece como dado privado; **não** exportar seus detalhes, identidade ou conteúdo para o Git, site ou marketing.

## A. Situação técnica verificada, sem extrapolação

| Item | Estado / evidência | Interpretação correta |
| --- | --- | --- |
| Banco do core | **Existe**: PostgreSQL privado com persistência e bind local | Não criar um segundo banco por causa do site. Banco presente não prova que o processo completo de venda funciona |
| F1 — fundação | Concluída **para piloto privado**: auth/tenant, schema/migrations em descartável, backup/restore ensaiado, lifecycle | Não autoriza API pública |
| Oportunidade/triagem | API e interface de operador locais, com fluxo de captura e `ProposalBrief` | `ready_for_review` não aprova proposta; `follow` não agenda ação |
| Oferta F2 | `client0-integration-flow-v1`: template de **um** fluxo implantável e diagnóstico | Sem preços, prazos e condições inventados; ainda depende de aprovação humana |
| ERPNext | Sandbox preparado, configuração testada; runtime/DocTypes/operabilidade **não demonstrados** | Não declarar integração, emissão de Quotation ou pagamento |
| Assistente de marketing | **WP-022:** geração local Qwen de rascunhos fundamentados em [fonte pública curada](client0-marketing-drafts.md); **um primeiro texto foi gerado e salvo para revisão** | Serviço de conversas do core é separado; não existe publicação, coleta de rede social ou aprovação automática |
| Site institucional | **WP-021/025/026:** site estático testado e pacotes Cloudflare (4 arquivos) e [portátil (3 arquivos)](mxq4k-hosting-deferred.md) preparados; **não publicado** | Usuário já dispõe de Armbian em SD para MXQ4K, mas **boot e segurança não comprovados**; CI não configura hosting nem autoriza publicação |
| Cases e avaliações | **WP-023:** modelo privado e checklist de evidências de case em [prova social](client0-proof-social.md); **não há case real nem depoimento autorizado** | Checker somente de leitura, teste/consentimento real pendentes; demos não são resultados comerciais |

## B. Sequência de preparo — não pular gates

Estes passos são uma **restrição de prontidão pré-contato do responsável**, distinta do gate formal de saída da F2. Nenhuma fase da arquitetura é renomeada ou dada como concluída por este checklist.

| Ordem | Gate e fase | Entrega verificável | Estado no início deste plano | Regra de parada |
| --- | --- | --- | --- | --- |
| 0 | F0/F1 — fundamento | Oferta-foco, ownership, API/banco/recovery e acesso privado | **F1 concluída no piloto privado**; regras F0 documentadas | Não ampliar exposição nem inserir dados reais no Git |
| 1 | F2/O01 — oferta e diagnóstico | Ficha versionada de implantação de **um fluxo**, checklist de perguntas, escopo, limites, aceite, suporte e custos a confirmar | **Template criado**; precificação comercial segue aberta | Não precificar nem prometer automações/canais não verificados |
| 2 | F2/O02 — continuidade comercial/back-office | G0–G10, índice WP-027, ZIP fictício WP-028, kit manual WP-029, Restic WP-030 e [inventário local read-only WP-031](client0-ubuntu-preflight.md) | CI valida código/testes isolados; **execução do preflight no Ubuntu, mídia/chave e backup/restore real pendentes**. Fiscal, preços e emissão ainda requerem decisão humana | Verificar metadata-only não é autorização para instalar, coletar casos, restaurar ou iniciar prospecção |
| 3 | F2 — demonstração de entrega | **Uma demo técnica executável e reproduzível** da oferta: cenário sintético, testes, README de execução, captura sanitizada opcional e limitações | **WP-020 validado:** [demo offline pedido → CRM fictício](../../examples/README.md) e testes; material visual/site ainda pendente | Demo não vira “case de cliente”, nem prova integração com provider real ou usa dados da oportunidade real |
| 4 | F2 — vitrine institucional | Site estático [WP-021](../../site/README.md) com portfólio e [pacote candidato WP-025](site-publication-readiness.md) de quatro assets + headers | **Pacote tecnicamente preparado para CI**, sem conta/hosting/URL, identidade aprovada ou publicação; site continua offline | Não publicar sem autorização humana da versão/destino; banco e API privados permanecem isolados |
| 5 | F2 — assistência de marketing | Gerador de **rascunhos LinkedIn** com fonte pública curada, prompts versionados, modelo local opcional, fila privada e revisão humana obrigatória | **WP-022 validado:** testes + uma geração real com Qwen 3.5 9B; JSON privado `pending_review` e não publicado. Calendário/imagens/outros canais ainda pendentes | Zero publicação ou contato automático; fonte/IDs não substituem revisão factual; sem alegações inventadas |
| 6 | F2/O08 — preparo de prova social | [WP-023](client0-proof-social.md): modelo privado antes/depois, referências de evidência, revisão de direitos e consentimentos por uso/canal/versão, auditoria read-only | **WP-023 validado pelo GitHub Actions e integrado**; sem case real, resultados medidos, aprovações ou material publicado | Mesmo `human_review_required` **não autoriza publicação**; consentimento, versão e revisão humana são gates separados |
| 7 | F2 — ensaio operacional de prontidão | [WP-024](client0-precontact-rehearsal.md): validador **somente de regras sintéticas**, com G0–G10, aprovação/envio separados, evidências fictícias, cobrança parcial e reconciliação simulada | **WP-024 validado pelo GitHub Actions (209 testes na suíte)**; não valida instância ERPNext, contrato, envio, pagamento ou cliente real | `simulation_result=simulated_sequence_complete` **não** significa `f2_exit_met`, venda, publicação ou autorização de contato |

**Após os gates de prontidão:** o responsável pode decidir retomar prospecção/contatos reais. Isso **não significa F2 encerrada**: o gate arquitetural da F2 continua sendo o **ciclo comercial real** com aceites e recebimento verificável; só depois se mede o gargalo que merece automação na F3. Um site e um gerador de posts não substituem venda, entrega ou conciliação.

## C. Como será a vitrine — critérios antes de decidir stack/hosting

O site codificado no WP-021 **não precisa ter login, CRM próprio, formulário público ou banco**. Uma primeira versão estática reduz custo, risco e manutenção. Stack, domínio, marca, DNS, hospedagem, identidade pública e política de contato serão escolhidos em pacote próprio, com comparação técnica e validação, **não assumidos** aqui.

Conteúdo mínimo de um MVP verificável:

1. **Quem oferece** — identidade profissional consistente com perfis públicos e serviços reais.
2. **Que problema resolve** — `client0-integration-flow-v1`, com escopo e exclusões claros.
3. **Como trabalha** — diagnóstico, proposta revisada, entrega testada, evidência, suporte conforme contrato.
4. **Demonstração** — projeto sintético funcional, repositório e resultados reproduzíveis, com aviso explícito “demonstração, não cliente”.
5. **Contato** — opção aprovada que não publique segredos ou dados pessoais além do necessário.
6. **Privacidade** — informação coerente com dados realmente coletados; se não houver formulário ou tracking, não inventar backend ou política de coleta.
7. **Prova social** — seção opcional **não exibida ou marcada “em preparação”** até haver consentimento e resultado verificável; não fabricar avaliações, logos ou números.

Nunca compartilhar a página `http://127.0.0.1:8788/operator` como link de apresentação: ela é **UI interna privada**, não site da empresa. Hospedagem estática pública deve usar repositório/artefato separado ou build isolado que não carregue `.env`, tokens ou dados do core.

## D. Assistente de posts: menor experimento permitido

Primeiro pacote elegível **depois de existirem fontes públicas honestas**:

- entrada: links aprovados de repositório/demo, mudanças técnicas públicas e oferta vigente;
- saída: **rascunho** de post/caption e sugestões de imagem, com fonte associada e sinalização de afirmações não comprovadas;
- revisão: humano confirma precisão, marca, terceiros, política do canal, links e autorização de publicação;
- publicação: **fora do escopo inicial**; ação posterior e separada, sob aprovação explícita;
- armazenamento: drafts privados; nenhum segredo, contato de cliente, conversa privada ou conteúdo de contrato em prompt público ou ferramenta externa sem autorização.

Não começar com equipe de agentes, scraping, auto-post ou workflow multicanal. Avaliar primeiro se o rascunho economiza trabalho e se a revisão continua segura.

## E. Evidência de caso e consentimento

Para cada entrega real futura, guardar **fora do repositório público**:

- fonte e método da linha de base (antes): volume, tempo, falha ou custo;
- período e condições da medição posterior;
- números observados versus estimativas claramente separados;
- limites/ocorrências de erro e custo de operação;
- documento/versão do escopo e autorização de quem tem legitimidade sobre os dados;
- autorização **granular** para publicar nome/marca, fotos, números, depoimento e canal de divulgação, com possibilidade de revogação tratada;
- versão sanitizada para publicar **apenas depois** de uma revisão humana.

**Repositório com testes, demo e documentação demonstra capacidade técnica, mas não é prova de resultado comercial ou aprovação de cliente.**

## F. Escopo e definição de encerramento deste plano

Este documento organiza a fila, **não ativa a fila**: a cada WP, verificar dependências, implementar **um recorte** e validar; não iniciar o próximo automaticamente na mesma sessão.

Sem novos serviços, dependências, base de dados, alterações na API, migrations, ERP, deploy, mensagens, submissões ou publicações por consequência deste plano.

**O01 concluído como template, O02 preparado para validação privada.**
O procedimento G0–G10 e suas exceções estão em
[operação/back-office](client0-backoffice-operations.md) e o formulário de
[índice por serviço](templates/client0-case.template.md). A documentação
não demonstra ERPNext instalado, proposta formal emitida, dinheiro recebido,
backup/restore do índice nem caso entregue.

**Andamento da preparação pré-contato:** WP-020 tem demonstração técnica
sintética, WP-021 tem site codificado **não publicado**, WP-022 tem um
rascunho de marketing `pending_review` **não publicado**, e WP-023
tem controles de [medição/consentimento](client0-proof-social.md)
validados por CI, mas **nenhum case real autorizado**.

**WP-024:** o [ensaio sintético G0–G10](client0-precontact-rehearsal.md)
foi aprovado por CI, mas não comprova proposta enviada, recebimento,
ERP validado, backup do índice, site publicado ou serviço prestado.
**WP-025/026:** a [pré-publicação do site](site-publication-readiness.md)
agora entrega opções Cloudflare e portátil, **sem deploy**. O
[MXQ4K foi reservado para avaliação futura](mxq4k-hosting-deferred.md).
Nenhuma instalação, firmware, rede, domínio ou API privada será alterada
antes da autorização do responsável.

**WP-027:** [preflight e bootstrap do índice privado](client0-private-workspace.md)
testados com dados sintéticos no CI; não confirmam o HOME real.
**WP-028:** [ensaio de recuperação do índice](client0-private-recovery.md)
com ZIP temporário **não criptografado** e verificação SHA-256, usando
somente três arquivos **inventados**. Isso não comprova backup real,
custódia de chaves ou recuperação de documentos comerciais reais.

**MXQ4K:** o responsável informou que Armbian já está em um SD preparado.
A decisão vigente é continuar a operação Client 0 primeiro; boot,
inventário e ativação pública do site ficam para momento apropriado.

**WP-029:** [kit de proposta, aceite e conciliação manual](client0-manual-commercial-pack.md)
preparado em rascunho; nenhum documento emitido/enviado. A
[lista finita de decisões de lançamento](client0-launch-decisions.md)
evita transformar decisões fiscais/financeiras humanas em novos módulos.

**WP-030:** [Restic escolhido para o índice](client0-restic-recovery.md);
CI testa senha sintética, repositório criptografado e recuperação de
arquivos fictícios, **sem acesso à pasta real ou mídias do usuário**.

**Próximos bloqueios reais:** confirmar condições comerciais e
habilitação fiscal adequadas; escolher mídia e custódia de chave e
executar **backup e restore local isolado com autorização**. O MXQ4K com Armbian
em SD será avaliado depois, conforme decisão do responsável. Não
criar CRM/ERP paralelo nem considerar template uma operação financeira.

**Contato e site público continuam sem aprovação.** A F2 exige **ciclo
real até recebimento e revisão de resultado** para encerramento formal.
