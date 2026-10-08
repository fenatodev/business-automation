# Piloto sintético Client 0 — 3 oportunidades (WP-013)

**Estado:** cenários executáveis em testes; aprovação do piloto real pendente.
**Escopo:** somente a etapa `Opportunity → triagem → ProposalBrief → ready_for_review`.
**Fonte simulada:** 99Freelas; anúncios **inventados**, não extraídos da plataforma.
**Ambiente dos testes:** SQLite em memória, via `tests/conftest.py`. **Nunca** usar o PostgreSQL persistente do Client 0 para esses cenários.

## Objetivo

Validar o contrato operacional já implementado sem depender de captar clientes,
acessar plataformas, usar Open Interpreter, ERPNext ou enviar propostas.
A simulação valida o software, **não** demonstra demanda, preço viável ou aceite real.

## Cenários e decisões humanas simuladas

| Caso | Oportunidade fictícia | Decisão de triagem | Resultado esperado |
| --- | --- | --- | --- |
| A | Sincronizar pedidos de uma loja com CRM por API, com acesso ainda a confirmar | `prepare_proposal` | Criar brief em `draft`, revisar e marcar `ready_for_review`; não aprovar/enviar |
| B | Integrar planilhas a sistema não identificado, sem volume nem API informados | `follow` | Registrar necessidade de esclarecimento; bloquear criação de brief |
| C | Obter dados pessoais de terceiros sem autorização demonstrada | `ignore` | Registrar risco e recusar preparação de brief |

Os links usam o domínio reservado `example.invalid` e não apontam para vagas reais.
A escolha de triagem é **entrada humana fixada no cenário**, não decisão automática
da API ou da IA.

## Operação que o teste percorre

1. Criar Company sintética como admin; autenticação de oportunidade requer operator.
2. Capturar oportunidade com `source=99freelas`, URL, descrição, requisitos e horário.
3. Verificar estado inicial `pending`, listagem isolada e duplicação rejeitada (`409`).
4. Registrar decisão e justificativa humana por `PATCH /opportunities/{id}/triage`.
5. Em `follow` ou `ignore`, confirmar que a API bloqueia criação do brief (`409`).
6. Em `prepare_proposal`, criar brief com diagnóstico, escopo, entregáveis,
   aceite, pressupostos e riscos; confirmar `draft`.
7. Atualizar para `ready_for_review`, consultar o brief, verificar que `approved`
   é estado inválido (`422`).
8. **Parar para revisão humana.** O software atual não possui aprovação nem envio;
   não criar preço, proposta formal, Lead ou handoff ERP neste WP.

## Execução e evidências

```bash
uv run pytest tests/test_client0_simulation.py -q
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
```

Usar checkout isolado com dependências de desenvolvimento disponíveis. O conftest
fixa o banco como SQLite em memória antes de importar a aplicação. **Não** executar
Alembic, Compose, POST/GET na API privada, scripts de cleanup, ou usar `.env` do Client 0.
Registrar o resultado **real** de cada comando, sem inferir sucesso apenas pelo código.

**Aceite técnico:** três variações concluídas e testes existentes sem regressão.
**Aceite operacional:** responsável humano revisou o brief sintético e identificou
informações ainda desconhecidas; `ready_for_review` não representa aprovação.

## Observações para o próximo ciclo

- O endpoint exige manipular JSON; a falta de formulário aumenta a fricção de operação.
- A triagem guarda somente o estado/nota mais recentes, não o histórico de decisões.
- `follow` não possui prazo, responsável ou lembrete operacional específico.
- `ready_for_review` não registra quem revisou, decisão ou versão aprovada.
- As informações essenciais para estimar preço e implantação dependem de validação
  com interessado real. Não gerar valores fictícios como se fossem proposta comercial.
- A simulação cobre **somente o início** da F2; entrega, cobrança e pós-venda
  continuam fora deste teste e não estão validados por ele.

## Critério para priorizar software novo

Não abrir nova feature apenas por ser uma lacuna da simulação. Antes, comparar:
tempo manual por oportunidade, campos faltantes, repetição, erros, volume e
custo de manter uma automação versus executar manualmente.

**Próximo gate:** após validação técnica, revisar o caso A e escolher uma única
melhoria comprovadamente útil. O primeiro anúncio real, quando oportuno,
exige nova decisão humana e dados privados fora do Git.
