# Roadmap

Direção vigente em 2026-10-07, conforme a [Architecture Baseline v1](architecture/baseline-v1.md), referência oficial adotada no WP-001. O [plano detalhado](architecture/delivery-plan-v1.md) descreve prioridades e gates; este documento resume a sequência. Não é compromisso de prazo nem autorização para implementar ou executar migrations.

## Necessário agora

- Definir uma oferta e um fluxo Client 0: oportunidade → qualificação → proposta e aprovação → projeto e entrega → cobrança → pós-venda e suporte.
- Tratar Client 0 como a operação da própria empresa, com responsáveis, evidências de aceite e próxima ação.
- Adotar ERPNext como back-office padrão inicial; validar sua aderência e definir ownership antes da integração. Aproveitar funções maduras em vez de reconstruí-las no core.
- Incluir cobrança de serviços, recebíveis e conciliação no processo operacional, inicialmente com participação humana e back-office. Não construir billing próprio para começar a vender.
- Consolidar testes, integridade e reprodutibilidade de migrations em tarefa própria, com PostgreSQL descartável e revisão obrigatória.
- Preparar identidade, autorização, isolamento, acesso privado, observabilidade mínima e backup/restore antes de dados operacionais na API. Exposição pública depende de segurança comprovada.
- Validar o ciclo comercial e de entrega manualmente enquanto a fundação técnica é preparada.

“Agora” inclui decisões e procedimentos humanos; não exige implementar todas essas capacidades no repositório de uma vez.

### Status atual da F1

Em 2026-10-08, a F1 está **concluída para o piloto privado Client 0**, com evidência nos WPs 004–008:

- migrations/recovery em PostgreSQL descartável;
- autenticação e isolamento por Company;
- backup/restore ensaiado;
- startup loopback-only, revogação por restart e logs mínimos sem segredos;
- lifecycle operacional de dados definido.

Essa conclusão não equivale a produção pública. Permanecem proibidos por padrão: exposição pública, ingestão em massa, portal externo e ampliação de dados sensíveis sem gate próprio.

O próximo avanço é F2: executar um ciclo Client 0 real e assistido, preservando fallback manual e as fontes de verdade definidas.

## Prontidão de apresentação antes de novos contatos (restrição Client 0)

Por escolha do responsável em 2026-10-08, **pausar novas propostas e prospecção**
enquanto é preparada uma estrutura verificável. Esta ordem **não substitui
os gates F0–F5** e não transforma marketing em pré-requisito arquitetural
universal para outros clientes.

Na **F2**, executar recortes curtos, com um WP e validação por vez:

1. **O01 — oferta/diagnóstico versionados:** um fluxo de integração/automação
   por vez, com critérios de aceite, exclusões, custos e suporte a confirmar.
   Template em [oferta Client 0 v1](operations/client0-offer-v1.md).
2. **O02 — operação de ponta a ponta e back-office:** adotar
   [checklist de evidências G0–G10](operations/client0-backoffice-operations.md)
   e [índice privado por caso](operations/templates/client0-case.template.md),
   aproveitando o WP-014. O **modelo documental** está preparado;
   armazenamento local agora conta com o
   [WP-027 — bootstrap privado vazio](operations/client0-private-workspace.md)
   para verificação sintética, e o [WP-028 — ensaio de recuperação
   isolada do índice](operations/client0-private-recovery.md) usa
   **somente dados fictícios**. O [WP-029 — kit comercial
   manual e decisões de lançamento](operations/client0-manual-commercial-pack.md)
   prepara propostas, aceites e verificação fiscal/financeira com
   autoridades humanas e fontes reais **quando habilitadas**.
   [WP-030 — Restic e recuperação criptografada em CI](operations/client0-restic-recovery.md)
   escolhe ferramenta madura. [WP-031 — preflight read-only no Ubuntu](operations/client0-ubuntu-preflight.md)
   detectou inicialmente bloqueio na pasta privada e ausência de Restic;
   [WP-032 — investigar causa/topologia sem escritas](../specs/wp-032-ubuntu-blocker-cause.md)
   definiu os gates de remediação. A conferência posterior
   [WP-033 — estado operacional](operations/wp-033-current-state-report.md)
   verificou Ubuntu 24.04.5/Noble, Restic 0.16.4 instalado, permissões privadas
   e um **HDD SATA distinto** para backup (NTFS3). **Nenhum backup real,
   custódia de chave ou restauração real foi executado; F2 continua aberta.**
   [Decisões abertas](operations/client0-launch-decisions.md):
   formalização comercial e fiscal, valores, emissor oficial,
   mídia/chave e restore real, marca/site e autorização de contato.
   **ERPNext permanece opcional até ser validado.** Nenhum template é
   prova de documento emitido, serviço contratado ou pagamento.
3. **Demonstração real de capacidade técnica:** um fluxo **sintético**
   executável, reproduzível e documentado, sem dados privados e sem
   apresentar demo como resultado de cliente contratado.
4. **Site-vitrine institucional mínimo:** WP-021 codificou a
   vitrine estática, separada do core e da UI interna. O
   [WP-025 — pacote e gates de publicação](operations/site-publication-readiness.md)
   prepara quatro assets para Cloudflare e o
   [WP-026 disponibiliza três arquivos portáteis](operations/mxq4k-hosting-deferred.md)
   para servidor estático futuro. **TV Box MXQ4K adiado**: o usuário
   já tem Armbian preparado em SD, mas boot, inventário e segurança não
   foram verificados; sem conta, domínio, deploy, contato ou exposição do banco/API privada.
5. **Assistente de marketing inicial:** [WP-022 — rascunhos com Qwen local](operations/client0-marketing-drafts.md), baseados em fonte pública curada;
   revisão factual e autorização humana continuam obrigatórias. **Publicar
   é gate distinto**, não automático. Outros canais e imagens ficam para
   avaliação posterior, sem antecipar a automação da F3.
6. **O08 — preparo de cases/prova social:** [WP-023 — evidências,
   medição e consentimento](operations/client0-proof-social.md), com
   modelo de case privado e checklist **somente de leitura**. Publicar
   exige autorização humana separada por uso, canal e versão. **Não
   inventar depoimentos, métricas, clientes ou resultados.**
7. **Ensaio de prontidão:** [WP-024 — contrato sintético G0–G10](operations/client0-precontact-rehearsal.md)
   com referências fictícias, versão de proposta e conciliação simulada.
   **Teste verde não confirma proposta enviada, pagamento recebido,
   validação do ERP nem prontidão comercial real.**

A [matriz de prontidão pré-contato](operations/precontact-readiness.md)
explicita evidências, bloqueios e estado **pendente** de cada gate.

A **saída real da F2 continua exigindo oportunidade até recebimento e
revisão do resultado**, com fontes verificáveis. Concluir site, demo ou
simulação prepara a abordagem, mas **não comprova venda/entrega**
e não autoriza avançar automaticamente à F3.

## Preparar agora, implementar conforme o fluxo exigir

- Um contrato de handoff ERP com campos, ownership, idempotência, falhas e reconciliação explícitos.
- Evolução mínima de CRM, captura e qualificação orientada ao trabalho do operador.
- Interface interna para próximas ações e pendências reais.
- IA desacoplada de provider e configuração por Company, depois da fundação de acesso e dados.
- Jobs duráveis apenas quando efeitos externos automáticos precisarem sobreviver a reinícios.
- Um canal e uma receita de automação por vez; n8n ou Activepieces somente como motor auxiliar quando justificado.
- Onboarding e operação dos primeiros clientes com o mesmo core, configuração e credenciais segregadas, sem forks.

## Adiado

- Billing de SaaS, assinaturas self-service, planos e cobrança por uso.
- Provisionamento e portal self-service, RAG e bases de conhecimento por empresa.
- Analytics avançado, campanhas e múltiplos canais sem demanda validada.
- Microserviços, Kubernetes e infraestrutura distribuída sem necessidade comprovada.

## Fases e critérios de avanço

| Fase | Resultado esperado | Gate de saída |
| --- | --- | --- |
| F0 — recorte | Oferta, fluxo Client 0 e ownership definidos | Responsáveis, exceções e critérios de aceite claros |
| F1 — fundação | **Concluída para piloto privado Client 0**: dados reproduzíveis, acesso seguro, recuperação e lifecycle | Testes, isolamento, restore, revogação e política de lifecycle demonstrados; sem autorização de exposição pública |
| F2 — operação assistida | Ciclo de oportunidade a recebimento e revisão de resultado | Fontes de verdade e evidências rastreáveis, com continuidade manual |
| F3 — automação útil | Automatizar um gargalo comprovado | Falhas, duplicação, timeout e reconciliação testados; benefício medido |
| F4 — primeiros clientes | Entrega repetível com o mesmo core | Sem fork, com isolamento, suporte e custo operacional conhecidos |
| F5 — produto | Empacotamento guiado por demanda real | Repetibilidade e sustentabilidade demonstradas; SaaS é opcional |

Executar [work packages pequenos e autossuficientes](architecture/work-packages-v1.md), um por sessão. A arquitetura completa orienta o destino; cada implementação deve resolver um recorte verificável.

## Histórico

Este roadmap substitui o NOW/NEXT/LATER anterior, preservado no histórico Git de `main@84ea22e`. A prioridade de segurança foi antecipada em relação à configuração de agente; o antigo adiamento genérico de billing foi substituído por cobrança operacional agora e billing de SaaS depois. As substituições estão registradas em [DECISIONS.md](DECISIONS.md).
