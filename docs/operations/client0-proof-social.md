# Client 0 — O08: evidências, medição e autorização de case (WP-023)

**Estado:** procedimento e checklist de prontidão documental; **nenhum case real
comprovado, publicado ou autorizado**. Aplicável à F2, após a entrega.
Este documento **não é termo jurídico pronto**, política fiscal ou comprovação
de consentimento.

## 1. Quando um trabalho pode se tornar prova social

Há três registros diferentes, que não devem ser confundidos:

1. **Execução técnica:** entrega, testes e aceite do cliente — G6/G7 do
   [processo de serviço](client0-backoffice-operations.md).
2. **Resultado medido:** métrica **observada antes e depois**, sob método,
   população, períodos, fonte de dados e limites comparáveis.
3. **Permissão de divulgação:** autorização legítima **para a versão exata**
   do material, canais e usos solicitados (ex.: métricas, marca, nome,
   logotipo, depoimento, imagem). Contrato de prestação de serviço,
   aprovação interna ou consentimento para executar **não** autorizam
   automaticamente publicar.

**Regra absoluta:** nenhuma dessas etapas isoladas permite apresentar o
trabalho como case, usar marca de cliente ou publicar números.
Apenas o responsável humano pode autorizar **ação externa específica**,
depois de conferir todos os elementos e direitos.

## 2. Metodologia mínima de medição

Escolher **uma métrica por case inicial** (por exemplo minutos por tarefa
ou contagem de erros por período). Registrar antes de começar a implantação:

| Campo | Evidência mínima | Evitar |
| --- | --- | --- |
| Identidade do indicador | Nome, unidade, finalidade e cálculo definidos antes da entrega | Trocar unidade/conceito para melhorar número |
| Baseline (antes) | Valor **observado**, período, fonte, versão do método | Estimativa, hipótese ou memória como medição |
| Pós-implantação (depois) | Valor **observado**, período, fonte independente e método comparável | Selecionar somente o melhor dia |
| Comparabilidade | Quem avaliou sazonalidade, volume, amostra, fluxo, automações de terceiros e mudanças de processo | Atribuir toda diferença automaticamente à automação |
| Custos/limites | Custo operacional e exceções, quando relevantes à afirmação | Declarar economia líquida/ROI sem esses dados |
| Controle editorial | Formulação exata da alegação, evidências e revisão de interpretação | Converter correlação em causalidade |

O checker bloqueia períodos no futuro, pares incompletos, estimativas,
ausência de revisão de comparabilidade e fontes duplicadas. **Ele não**
interpreta estatística, causalidade, inflação, impostos, representatividade
da amostra ou licitude da coleta. Ausência de erro automático não prova que a
métrica ou a economia alegada seja verdadeira.

Se a medição não existe, a alternativa honesta é mostrar **demo técnica
sintética** identificada como tal, não um resultado comercial.

## 3. Pasta e modelo privados — um case por entrega

A operação mantém o índice em
`~/.local/share/business-automation/client0/cases/<case_ref>/case.md`.
O registro de prova social é **um arquivo auxiliar** na mesma pasta:

`~/.local/share/business-automation/client0/cases/<case_ref>/proof-social.json`

O [modelo JSON sem dados reais](templates/client0-proof-social.template.json)
fica no Git, mas o arquivo **preenchido nunca vai para GitHub, chat,
prompts externos ou site público**.

- `case_ref`: identificador opaco como `c0-2026-001`, vinculado ao
  mesmo `case.md`; não usar nome, e-mail ou telefone no caminho.
- `classification`: inicialmente `unverified`; só marcar
  `real_verified` após confirmação **humana** da entrega e da fonte do
  resultado. Uma string no JSON não é autenticação.
- `evidence`: referências privadas a aceite comercial e técnico,
  propriedade/direitos, revisão de privacidade e revisão editorial
  **independentes**. Identificadores de referência não são documentos.
- `metric.before/after`: observações, período ISO `AAAA-MM-DD`,
  unidade, método e fonte. Não gravar documentos brutos no JSON.
- `asset`: versão e SHA-256 do **arquivo final sanitizado**,
  `requested_uses` e canal pretendido (`linkedin` ou `site`).
  Hash identifica bytes, **não autentica autorização ou titularidade**.
- `consents`: **uma concessão separada por uso, canal e SHA-256**, com
  referências verificáveis a ato de consentimento/permissão, pessoa com
  autoridade revisada, data, eventual vencimento e revogação.
  `revoked_at` preenchido **bloqueia** aquela concessão.
- `withdrawal_requested`: por padrão `null` (desconhecido/bloqueado).
  `false` deve refletir conferência atual, e **não** ser presumido.

**Não salvar** captura de tela, foto, depoimento, token, nome, e-mail,
CPF, print de cliente ou dado fiscal neste repositório público.
Se houver autorização para guardar evidência real, aplicar minimização,
segregação de acesso, retenção/eliminação e backup protegido; a pasta local
com `0700` **não equivale a backup**.

Antes de criar a pasta de um novo serviço, confirmar dados mínimos de
entrega, autoridade, local de evidência e política de recuperação. Se
não houver backup/restore para material sensível, **não coletar esse
material ainda**.

## 4. Auditoria somente de leitura

O [checklist Python](../../proof_social/checklist.py) **não usa IA**.
Não possui `POST`, integração, banco, rede, geração de case, publicação,
alteração de consentimento nem escrita em pasta de cliente.

### Teste sintético seguro (sem acessar clientes)

```bash
uv run python -m proof_social.checklist --template-check
```

Resultado **esperado**: JSON com `"status": "blocked"`,
`"publication_authorized": false` e códigos de pendências;
o comando retorna exit code 0 porque **verificou corretamente um
modelo deliberadamente incompleto**.

### Verificação opcional de um case privado, somente no futuro

```bash
uv run python -m proof_social.checklist --check-private \
  "$HOME/.local/share/business-automation/client0/cases/c0-2026-001/proof-social.json"
```

Substituir o ID pelo case realmente existente, **após** permissão para
guardar/inspecionar seus metadados. O checker exige:

- raiz `cases/` e subpasta por case `0700`, pertencentes ao usuário;
- arquivo **regular** `0600`, do mesmo usuário, até 64 KiB;
- formato de caminho e `case_ref` coerentes; proíbe symlinks;
- JSON sem chaves duplicadas; sem impressão dos valores privados.

**Estados retornados:**

| Resultado | Significado |
| --- | --- |
| `blocked` + `blocking_codes` | Falta metadado, fonte, medição, revisão, direitos ou autorização de uso; não publicar |
| `human_review_required` | Campos preenchidos de maneira consistente; uma pessoa ainda deve verificar as fontes, permissões e alegações |
| `publication_authorized=false` | **Sempre**; mesmo quando `blocking_codes=[]` |
| `external_action_taken=false` | **Sempre**; o programa não publica, envia ou altera sistemas |

A validação estrutural não identifica consentimento fraudulento, lacunas
de direitos autorais, conteúdo alterado externamente, métricas falsas ou
uso secundário não autorizado. **Somente a confirmação humana das
evidências reais e uma autorização explícita posterior** podem abrir o
gate de um canal/versão específicos. Nenhum `status` do checklist dá
permissão ao assistente para publicar.

## 5. Revogação, atualização e rastreabilidade

- Guardar a versão exata do asset, autor e canal aprovado; alterar texto,
  imagem, números, marca ou canal => **nova avaliação e autorização**.
- Uma autorização para exibir métricas não concede direito de usar
  logotipo, nome, foto ou depoimento, nem permissão para outro canal.
- Se houver revogação, contestação, expiração ou pedido de exclusão:
  **bloquear republicação imediatamente**, registrar o evento, acionar
  o operador para revisar publicações existentes e cumprir solicitações
  legítimas segundo a [política de dados](data-lifecycle.md).
- Não confiar na ausência de novo evento em backup antigo: restaurar
  não cancela revogações posteriores.
- Registrar responsáveis por expiração, retenção e revisão periódica,
  sem assumir prazo legal uniforme.
- O catálogo de **rascunhos de marketing** não deve aceitar conteúdo de
  cases privados como fonte pública por este WP. Após autorização
  editorial específica, um pacote posterior poderá curar **uma
  versão sanitizada pública**, sem gerar novos poderes.

## 6. Critérios de conclusão do WP-023

Entregue: método, modelo privado, checklist read-only, testes sintéticos e
instruções de auditoria. **Não entregue**: evidência real, software jurídico
de consentimento, medição real, backup/restore do diretório, publicação,
integração com redes, painel de cases, analytics ou automação de aprovação.

**Próximo gate da sequência pré-contato:** ensaio operacional **100%
sintético** do caminho oportunidade → brief → aprovação simulada →
entrega demo → aceite/recebimento fictícios claramente rotulados. Nenhuma
transição simulada pode escrever no Client 0 real ou fechar a F2.
