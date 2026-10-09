# Client 0 — WP-024: ensaio completo e sintético da F2

**Classificação:** simulação offline de contrato operacional, **não** transação
com cliente, cobrança, aceite, entrega ou conciliação de dinheiro real.
**Status:** simulador validado no GitHub Actions do PR #56 (suíte com 209 testes);
nenhuma transação, execução local, login, configuração do Client 0 ou
publicação exigida.

## 1. O que estamos de fato validando

Este WP cobre a **última etapa do plano de preparação pré-contato**, não
a saída da F2. A fase arquitetural F2 só encerra após um ciclo comercial
**real**, rastreável de oportunidade até recebimento e revisão de resultado.

Os WPs anteriores têm limites distintos:

| Entrega anterior | O que realmente demonstra | O que não demonstra |
| --- | --- | --- |
| [WP-013](client0-synthetic-pilot.md) | API real do core exercitada com três oportunidades **inventadas** em banco descartável; `ProposalBrief.ready_for_review` | Proposta comercial aprovada ou enviada |
| [WP-014](client0-commercial-tabletop.md) | Mapeamento humano de G1–G10 e exceções | Operação ERP ou recebimento confirmado |
| [WP-019](client0-backoffice-operations.md) | Modelo privado de G0–G10, versão, aceite e reconciliação | ERPNext funcional, documento fiscal emitido ou backup do índice |
| [WP-020](../../examples/README.md) | Fluxo Python de pedidos com CRM **em memória**, replay e timeout | Integração com cliente/plataforma ou ganho medido |
| [WP-021](../../site/README.md) | Vitrine institucional estática codificada e testada | Site publicado, domínio escolhido ou marca revisada |
| [WP-022](client0-marketing-drafts.md) | Gerador Qwen local de **rascunhos** vinculados a fontes públicas | Post publicado, canal de redes automatizado ou ROI |
| [WP-023](client0-proof-social.md) | Checklist de medição/consentimento e autorização **sempre negada** | Case de cliente autorizado, baseline e resultado reais |
| **WP-024** | Sequência puramente simulada de G0–G10, incluindo falhas e cobrança parcial | Integração fim a fim real entre API, ERP, cliente, banco e financeiro |

**Conectar o cenário do WP-013 ao back-office aqui é apenas uma correlação
conceitual com referências `SYN-*`.** O WP-024 não executa endpoints,
não lê o PostgreSQL e **não faz** chamadas ao ERPNext. O Python que
verifica o contrato não emite proposta, não muda estado de um serviço,
não envia mensagem, não gera fatura, não publica site/post e não altera
arquivos do operador.

## 2. Cenário artificial versionado

[Fixture de eventos](../../operations/fixtures/wp024-synthetic-cycle.json):
um cenário de **loja e integração inventadas**, sem nome de empresa,
dados de comprador, preço, imposto, CPF, credenciais ou serviços externos.
Oportunidade, contraparte, documentos, versões e evidências são apenas
códigos `SYN-*`.

| Gate | Referência fictícia / função | Regra validada |
| --- | --- | --- |
| G0 | Vínculo `SYN-OPP-V1` | Existe oportunidade **no cenário**, não no BA real |
| G1 | Revisão técnica `SYN-BRIEF-V1` | Pessoa técnica revisa escopo, não aprova envio |
| G2 | Contraparte `SYN-PARTY-V1` | Fonte `backoffice` é declarada **na simulação** |
| G3 | Proposta `SYN-QUOTE-V1` | Versão do documento formal é vinculada |
| G4a | Autorização de envio **simulada** | Diferente da existência da proposta |
| G4b | Envio **simulado** | Deve depender de G4a e mesma versão |
| G5 | Aceite comercial **simulado** | Versão exata do que seria enviado |
| G6 | Execução `SYN-DELIVERY-V1` | Só depois de aceite hipotético |
| G7 | Aceite técnico **simulado** | Mesma versão da entrega |
| G8 | Recebível `SYN-INVOICE-V1` | Respeita gatilho contratual, não sempre G7 |
| G9 | `partial` seguido de `settled` **fictícios** | Dois eventos, dois IDs; parcial sozinho bloqueia conclusão |
| G10 | Suporte/resultado **simulados** | Não autoriza case, marca ou divulgação |

A cobrança com gatilho `upfront` pode preceder execução/aceite técnico;
`milestone` precisa ter G6; `after_delivery` requer G7. Mesmo com um
ciclo simulado bem formado, `f2_exit_met=false`,
`commercial_success=false`, `proposals_sent=false`,
`contact_authorized=false`, `publication_authorized=false` e
`external_action_taken=false` são invariantes **obrigatórios**.

### Rodar o ensaio offline

```bash
uv run python -m operations.rehearsal --run
```

O resultado esperado em JSON contém:

- `simulation_result=simulated_sequence_complete`;
- os **12 gates distintos** G0–G10 (G4a e G4b separados);
- `finance_projection=simulated_settled`, referente **somente à
  fixture** que inclui a atualização `partial→settled`;
- `blocking_codes=[]` **para o contrato sintético**, não para o negócio;
- `known_live_gaps` com impedimentos que continuam abertos para a
  operação real;
- todos os flags de sucesso externo e autorização como **false**.

Saída não contém preço, nome de cliente, prova financeira ou dados do
operador. Não copiar `simulated_settled` para o ERP ou para o caso real.

## 3. Exercícios negativos e consequências

Os [testes](../../tests/test_synthetic_commercial_rehearsal.py)
comprovam que a **sequência fictícia é rejeitada** ao ocorrer:
falta de G4a/aceite; envio repetido; ator errado; versão de proposta,
entrega ou fatura divergente; evidência `SYN-*` reutilizada; timeout
`unknown` do documento/financeiro; `partial`, `reversed` ou
`overdue` sem conciliação; cobrança antes do gatilho; campos capazes
de acionar uma ação externa.

Esses comportamentos são **regras de um simulador**, não proteções
implementadas em todo back-office externo. Não presumir que ERPNext,
canal de freelancer ou bancos adotem esses contratos automaticamente.

## 4. Bloqueios para operação real, após o ensaio

| Gate real ainda aberto | Evidência exigida antes de declarar pronto | Estado |
| --- | --- | --- |
| Identidade, oferta e condições comerciais | Aprovação da identidade usada com clientes, serviço, exclusões, preço/tributos e procedimento de proposta | **Não validado** |
| Back-office financeiro autoritativo | Instância ERPNext testada **ou fallback documental privado efetivo**; emissão/consulta e permissões reais | **Não validado** |
| Aprovações e documentos privados | Versionamento, responsável, aceite e controle de referências operantes, não apenas template | **Não demonstrado** |
| Backup/restore de casos privados | Procedimento protegido e **restore isolado ensaiado** para dados de serviço autorizados | **Não demonstrado** |
| Site e primeiro contato | Revisão do conteúdo/branding, domínio/HTTPS/hosting e canal de contato aprovados | **Site codificado, não publicado** |
| Trabalho de cliente e aceite técnico | Projeto efetivo, escopo, acessos e aceite correspondente | **Nenhum ciclo real comprovado** |
| Financeiro/recebimento | Documento real, consulta e conciliação da fonte financeira, com data | **Nenhum recebimento real comprovado** |
| Resultado e prova social | Baseline antes/depois, direitos e consentimento específico da versão/canal | **Nenhum case autorizado** |

**Não transformar todos esses itens em desenvolvimento de software.**
Preço, marca, autorização e contrato são decisões humanas. Back-office
pode usar ferramenta madura ou procedimento controlado até haver
volume/erro que justifique automatizar. Não criar outro CRM, cobrança
própria, infraestrutura pública ou agentes extras por antecipação.

## 5. Decisão após o WP-024

A conclusão do WP-024, **se CI verde**, significa somente:
**o plano completo foi exercitado com dados artificiais e seus bloqueios
ficaram explícitos**. A restrição voluntária de "preparar antes de
prospectar" pode ser revisada pelo responsável depois de avaliar as
pendências, mas o simulador **não autoriza** reabrir leads, disparar
contatos, aprovar propostas ou marcar F2 concluída.

Próximo trabalho deve ser escolhido conforme o **primeiro bloqueio real
de prontidão**, preferindo decisões operacionais e validação do
back-office/hosting ao invés de codificar um produto prematuramente.
Não passar à F3 sem gargalo efetivamente observado e mensurado.

**Nenhum uso do Continue/Qwen ou Desktop Commander é necessário** para
rodar esta fixture no GitHub Actions; se o CI não estiver disponível,
parar, obter a causa e solicitar um handoff **curto e fechado** em
separado, sem operar o ambiente do Client 0.
