# WP-029 — kit comercial executável manualmente, sem novo ERP

**Fase:** F2/O02, depois de WP-028.
**Base:** `main@dfd84647b456f4975e040195f688d9c819382025`.
**Branch:** `wp/029-manual-commercial-pack`.
**Execução:** GitHub-first + Actions; sem Desktop Commander, Continue ou MXQ4K.

## Objetivo único

Preparar documentos utilizáveis pelo responsável **quando** o contato
com clientes for liberado: proposta versionada, comprovação de aceite,
verificação de cobrança/recebimento e um runbook de fallback manual.

**Não** criar sistema próprio de invoices, empresa/cliente, banco,
notificação, assinatura, emissão fiscal ou adapter ERP. O BA core
continua com `Opportunity`, triagem e `ProposalBrief`; nenhuma dessas
entidades emite proposta comercial formal ou fatura.

## Entregáveis delimitados

1. `docs/operations/templates/client0-proposal.template.md` — minuta
   comercial reutilizável para **um fluxo** e resultado verificável,
   incluindo exclusões, acesso, aceite, alterações, suporte, prazo,
   preço e tributação **sempre pendentes de avaliação humana**.
2. `docs/operations/templates/client0-acceptance.template.md` —
   evidências independentes de proposta enviada, aceite comercial,
   entrega e aceite técnico; nunca inferir aceite de silêncio.
3. `docs/operations/templates/client0-financial-check.template.md` —
   checagem privada da autoridade fiscal/financeira, recebível,
   fonte de conciliação, pagamento parcial/estorno e `as_of`.
4. `docs/operations/client0-manual-commercial-pack.md` — sequência
   G0–G10 com **fallback manual oficial/documental** enquanto ERPNext
   não estiver funcional; referências ERPNext e orientação NFS-e
   nacional, com revisão do regime tributário do operador.
5. `docs/operations/client0-launch-decisions.md` — gates humanos
   finais para iniciar operação real, sem inventar preço, CNPJ, domínio,
   banco, datas ou identidade de negócio.
6. `tests/test_commercial_launch_templates.py` — contrato de estrutura
   documental no CI, sem rede e sem dados de clientes.
7. Atualizar `docs/ROADMAP.md`,
   `docs/operations/precontact-readiness.md` e
   `docs/operations/client0-backoffice-operations.md`, somente links
   e estado real do recorte.

## Critérios de aceite

- Os três modelos ficam com marca explícita **RASCUNHO / NÃO ENVIAR**,
  decisões e dados específicos em campos vazios, sem simular autorização.
- Oferta inicial permanece `client0-integration-flow-v1`;
  uma automação/integração por contrato; suporte opcional e limites
  explícitos, com revisão humana de escopo, preço e riscos.
- `G4a` (autorização de versão) separado de `G4b` (envio) e
  `G5` (aceite do cliente); sem aceites automáticos.
- `G8` segue gatilho contratual definido e pode ocorrer antes do G7.
  `G9` não marca `settled` sem fonte financeira autoritativa
  consultada, data e responsável; parcial ou estorno não equivale a pago.
- **Nota fiscal** é emitida exclusivamente em portal/provedor habilitado,
  conforme enquadramento confirmado (nunca em Markdown nem pela IA).
  Não presumir que usuário tem CNPJ, MEI, Simples, ERPNext ativo ou
  autorização fiscal — registrar decisão pendente.
- Referências normativas atuais (outubro/2026) nos documentos com
  URL oficial e verificação obrigatória antes de operar.
- Nenhuma publicação, cliente, preço, emissão, envio, cobrança ou
  registro real criado; nenhum script toca Ubuntu, API, banco,
  repositórios privados, segredos, MXQ4K ou rede.
- `uv run pytest -q` com contagem real e CI verde no HEAD exato da PR.
  Se CI falhar, corrigir causa observada, sem pedir Qwen para refatorar.

## Fechamento

O WP-029 **não fecha F2** e não substitui decisão humana. Ele evita
desperdício de novo desenvolvimento de ERP e oferece um procedimento
manual controlado para o primeiro cliente, assim que os gates
fiscal/comercial, cópia protegida, identidade e publicação forem
autorizados. O trabalho seguinte deve ser apenas **gate real específico
que esteja bloqueando lançamento**, não criar mais demonstrações sintéticas.
