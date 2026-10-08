# WP-016 — Contrato mínimo de contraparte com simulador

**Status:** contrato e fake de teste; **não** integração ERPNext.
**Base:** ADR 0001, WP-014 (ensaio de mesa), WP-015 (sandbox ERPNext preparado, site não validado).
**Escopo único:** `customer local autorizado para back-office → ensure_business_party → referência externa`.

## Motivação e escolha

O próximo passo não precisa de ERPNext instalado, Docker, uma fila ou um
framework de agentes. Implementar só um **port tipado + fake em memória**
para exercitar um único handoff, com erros explícitos e chave de identidade.

Frappe oferece CRUD REST em `/api/resource/{doctype}` e listagem por filtros,
mas a existência dessas operações **não prova idempotência de POST** ou a
configuração efetiva dos campos obrigatórios do ERPNext instalado.
Documentação oficial consultada:
- https://docs.frappe.io/framework/user/en/guides/integration/rest_api
- https://docs.frappe.io/framework/user/en/guides/integration/rest_api/listing_documents

**Nenhum endpoint HTTP, adapter, DocType específico ou credencial é implementado
neste WP.** Esses detalhes exigirão contrato da versão ERPNext realmente validada.

## Superfície criada

| Local | Responsabilidade |
| --- | --- |
| `app/services/business_party_port.py` | Protocol `BusinessPartyPort.ensure_business_party(request)`, request, key, referência e exceções tipadas |
| `app/services/fake_business_party.py` | Fake com registro temporário em memória, falhas injetáveis e consulta/reconciliação **apenas simuladas** |
| `tests/test_business_party_port.py` | Caracteriza replay, conflito, isolamento, erros, estado remoto desconhecido e validações |

O port define um só comando:

```python
reference = port.ensure_business_party(
    BusinessPartyRequest(
        key=BusinessPartyKey(
            company_id=1,                # Tenant RESOLVIDO pela camada autorizada
            connection_ref="erpnext-a",   # Conexão RESOLVIDA pela camada autorizada
            customer_id=10,              # Customer local validado pela camada autorizada
        ),
        display_name="Empresa Ficticia",
    )
)
# reference.remote_id: identificador remoto estável (no fake, apenas sintético)
```

**Este código é ilustração de teste, não procedimento autorizado para dados reais.**
O port/fake não verifica roles, aprovação ou Customer no banco e **não concede
permissão**. A chamada de produção exigiria identidade autenticada, verificação
do Customer do mesmo tenant, conexão autorizada e decisão humana de encaminhar
ao back-office. A conversão `Lead → Customer` **não** executa esse comando.

## Identidade, idempotência e isolamento

- Chave lógica: `(Company.id, connection_ref, Customer.id)`. `Company` é o
  tenant do BA; não a empresa fiscal do ERP.
- `connection_ref` identifica uma instância/conexão de ERP no contexto do
  tenant; não é endereço, token ou autorização.
- `Customer.id` vem do BA. Não deduplicar por `display_name`, telefone ou email.
- Mesmo input em sequência no fake: **mesma referência remota**, sem segundo
  registro. Input alterado para a mesma chave: `BusinessPartyConflict`.
- Mesmos nomes/IDs em tenants ou conexões diferentes não colidem no fake.
- A garantia demonstrada é **local, sequencial e em memória**: não equivale a
  exatamente-uma-vez entre processos, concorrentes ou após restart. O futuro
  adapter precisará de vínculo persistente, busca remota por chave confiável,
  restrição de unicidade/consistência e reconciliação.

## Erros sem retries perigosos

| Evento | Tipo | Ação permitida no futuro |
| --- | --- | --- |
| Payload diferente para mesmo vínculo | `BusinessPartyConflict` | Parar; revisão humana e versionamento |
| Validação ou permissão negada | `BusinessPartyRejected` (razão explícita) | Parar; corrigir premissa ou permissão; **sem retry automático** |
| Indisponível **antes de qualquer escrita** | `BusinessPartyUnavailable` | Política de retry futura, limitada e comprovadamente segura |
| Timeout com escrita possivelmente efetivada | `BusinessPartyOutcomeUnknown` | **Não repetir**; consultar referência autoritativa e reconciliar antes |
| Consulta remota retorna vazio após timeout | Ainda `unknown` | **Vazio não prova ausência** sob concorrência/consistência eventual |

O fake simula timeout antes e depois da criação. Após timeout, bloqueia novo
`ensure_business_party`. Sua `inspect_synthetic_remote` mostra apenas o
estado da memória do fake. Sua `confirm_observed_reference` desbloqueia
**somente quando** o ID observado coincide com um registro realmente simulado;
não desbloqueia estados `unknown` sem prova positiva. São helpers exclusivos
do fake, **não** autorização para reconciliação em ERP real.

## Exatamente o que WP-016 não faz

- Não conecta, instala, configura ou acessa ERPNext.
- Não chama API do BA, não cria Company/Customer nem mexe no PostgreSQL.
- Não altera schema, Alembic, autenticação, permissões ou endpoints.
- Não produz Quotation, preço, Invoice, pagamento ou envio.
- Não cria worker, job persistente, event bus, retries ou UI.
- Não registra dados reais ou segredos no Git.
- Não estabelece que a F2 está concluída ou que o sandbox está funcional.

## Validação reproduzível

No checkout descartável com ambiente de teste (`tests/conftest.py` usa
SQLite em memória e credenciais exclusivamente fictícias):

```bash
uv run pytest tests/test_business_party_port.py -q
uv run pytest -q
.venv/bin/python -m compileall app tests
git diff --check
```

Registrar saída e contagens **reais**. Esses testes não acessam rede,
ERPNext, Docker ou PostgreSQL persistente. Sem instância real validada,
o gate de integração ERPNext permanece fechado.

## Próxima decisão (não é WP adicional automático)

Verificar a aderência do ERPNext na versão instalada **somente quando o host
comportar o teste sem afetar a operação**. Confirmar então:
`Customer`/campos/IDs, autenticação/roles, mecanismo remoto seguro de busca,
comportamento em 409/403/422, timeout após POST e reconciliação. Sem isso,
não avançar para adapter HTTP, migrações ou automação de envio.

**Alternativa simples:** para um primeiro negócio real, manter o handoff
manual documentado no WP-014 até que repetição e ganho sejam medidos.
