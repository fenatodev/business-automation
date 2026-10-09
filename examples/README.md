# Demonstração técnica — pedido fictício → CRM simulado

**WP-020 / F2 — demonstração 100% sintética, offline, sem cliente real.**

Esta demonstração corresponde à oferta interna
[`client0-integration-flow-v1`](../docs/operations/client0-offer-v1.md):
**um evento de pedido validado gera ou confirma uma referência em um CRM**.

Ela demonstra somente a **lógica do fluxo e sua disciplina de falhas**.
Não integra Tray, Olist, marketplaces, ERPNext, CRM comercial, redes sociais
ou qualquer serviço externo. Não prova economia, receita, prazo de implantação,
segurança multi-tenant, entrega comercial ou aceite do cliente.

## Executar em um checkout de testes

Requisitos: Python 3.12+; **não** requer `.env`, banco, rede, Docker,
token nem um modelo de IA.

```bash
python3 -m examples.order_to_crm
```

Saída: JSON determinístico com `kind: "synthetic_offline_demonstration"`,
resultados de cada evento e os registros **inventados** em memória.

## Cenários verificáveis

| Evento fictício | Resultado | Comportamento |
| --- | --- | --- |
| Novo pedido `ORD-101` | `created` | Uma gravação no CRM simulado |
| Mesmo pedido/cliente | `duplicate` | Zero gravações adicionais |
| Mesmo pedido/outro cliente | `conflict` | Preserva registro original |
| Identificador malformado | `rejected` | Validação sem gravar ou ecoar entrada |
| `ORD-202`: timeout **depois** de gravar | `unknown` | Não assume falha nem repete; bloqueia replay |
| Read-back de `ORD-202` coincide | `reconciled` | Só então libera e confirma como duplicado |
| `ORD-404`: timeout **antes** da gravação | `unknown` | Não repete cegamente |
| Read-back de `ORD-404` vazio | `unresolved` | Continua bloqueado para decisão humana |
| Pedido independente `ORD-303` | `created` | Fluxo não bloqueia outras chaves |

## Contrato e fronteira

Entrada exata, sem campos adicionais:

```json
{"order_ref": "ORD-101", "customer_ref": "CUST-001"}
```

Os dois campos são **identificadores fictícios** sem valores financeiros,
informações pessoais ou conteúdo de pedidos. O fake da saída usa
`order_ref` como chave de comparação e mantém apenas o último vínculo
criado para cada referência. `remote_writes` conta **somente** gravações
nesse objeto em memória durante **uma execução**.

**Não há garantia de replay durável entre processos**: fechar o comando
zera os registros. O `FakeCRM` é um double de teste, não um contrato de
fornecedor. No mundo real, identidades autorizadas, logs sanitizados,
armazenamento persistente, idempotência do sistema remoto, retries seguros,
observabilidade, autorização para dados e reconciliação precisam ser
especificados e testados **contra o provider real** antes de qualquer
implantação; não são parte deste WP.

## Evidência reproduzível

```bash
uv run pytest -q tests/test_demo_order_to_crm.py
uv run pytest -q
```

A validação cobre sucesso, replay, conflito, entrada inválida,
timeout antes/depois da gravação, bloqueio de repetição, reconciliação
positiva e negativa, eventos independentes e execução pelo CLI.

**Material de portfólio:** pode ser apresentado como **demonstração
técnica sintética** com código e testes públicos. Não apresentar como
case de cliente, integração ERP funcional, automação comercial operante
ou resultado financeiro alcançado.

**Próximo gate do roadmap:** site institucional **separado e estático**,
somente após validar esta demo e revisar o conteúdo público. Não vincular
o site à UI privada `/operator` nem ao PostgreSQL operacional.
