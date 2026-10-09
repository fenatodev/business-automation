# WP-024 — F2, ensaio sintético completo de ponta a ponta

**Base:** `main@77bce6a023c7a6de3569e9a14d545f4a312ce6a0`
**Branch:** `wp/024-synthetic-commercial-cycle`
**Execução:** ChatGPT/GitHub + CI. **Continue/Qwen 3.5 9B não necessário** se CI verde.
**Objetivo único:** testar as regras operacionais de G0–G10 com um cenário
totalmente inventado, identificando bloqueios reais **sem interagir com
nenhuma fonte real** e sem fechar a F2.

## Limite exato

Implementar apenas:

- `operations/__init__.py`, `operations/rehearsal.py` e
  `operations/fixtures/wp024-synthetic-cycle.json`: avaliador puro,
  cenário de teste versionado e CLI somente leitura.
- `tests/test_synthetic_commercial_rehearsal.py`: cenários negativos e
  positivos, todos artificiais.
- `docs/operations/client0-precontact-rehearsal.md`: relatório de
  preparação e lacunas reais pendentes.
- Este arquivo; links/status em `docs/ROADMAP.md` e
  `docs/operations/precontact-readiness.md`.
- CI: adicionar `operations` ao compileall e um único teste do CLI com
  asserts de `f2_exit_met=false`, `external_action_taken=false`,
  `publication_authorized=false` e `commercial_success=false`.

**Proibido:** acessar cliente/99Freelas, `.env`, credencial, DB/SQL,
ERPNext, serviços locais, APIs, LinkedIn, GitHub Pages, site real,
financeiro, e-mail, publicação, migrations, Docker e `app/`.
Nenhuma mensagem ou ação externa; o GitHub Actions recebe só dados
sintéticos já commitados.

## Cenário e autoridades

- G0: vínculo de oportunidade **SYN-OPP-001**, hipotética.
- G1: revisão técnica humana **simulada**, não é aprovação real.
- G2/G3: contraparte e proposta **simuladas**; nunca documentos ERP emitidos.
- G4a/G4b: aprovação e envio **simulados e separados**; nenhuma proposta sai.
- G5: aceite de versão **fictício**; não há cliente real.
- G6/G7: execução e aceite técnicos **simulados**; a demo WP-020
  constitui apenas referência técnica demonstrável, não entrega a cliente.
- G8: cobrança hipotética conforme gatilho (`upfront`, `milestone`
  ou `after_delivery`) definido antes; pode preceder G7.
- G9: financeiro `partial` não é `settled`; conciliação
  fictícia positiva exige referência financeira e atualização explícita.
- G10: suporte e medição referenciados **sinteticamente**; sem prova
  social, autorização de divulgação ou resultado medido real.

**Cada evento:** `gate`, `actor`, `evidence_ref`, `version`,
`outcome`. Todas as referências começam com `SYN-`, sem nomes, números
fiscais, mensagens, URLs, dados privados ou valores financeiros.
Atores e dependências pertencem a gates distintos. Versões de proposta
(G3,G4a,G4b,G5) devem coincidir exatamente; versões de entrega (G6,G7),
cobrança (G8,G9) idem. Repetição de gate é rejeitada, exceto G9
`partial→settled` com referência distinta, que **não** valida financeiro
real. Estados `unknown` bloqueiam sem repetição cega.

## Aceite

1. CLI `uv run python -m operations.rehearsal --run` produz relatório
   JSON sintético com G0–G10 cobrindo 12 gates distintos, incluindo G4a
   e G4b e pagamento `partial→settled` **fictício**.
2. A saída tem `simulation_result=simulated_sequence_complete` somente
   quando o contrato sintético passa; **sempre**
   `commercial_success=false`, `f2_exit_met=false`,
   `publication_authorized=false`, `external_action_taken=false`,
   `proposals_sent=false` e `contact_authorized=false`.
3. Testes negativos verificam gate fora de ordem, falta de evidência,
   ator incorreto, documento de outra versão, cobrança antes do
   gatilho, pagamento parcial/estornado, timeout `unknown` e
   ausência de consentimento como **bloqueios**, não sucessos.
4. Rastrear divergências do ciclo hipotético em relatório público,
   sem fingir que ERP, back-office e contrato real foram validados.
5. GitHub Actions green no SHA do PR; contagem **real** de testes do CI.
6. Nenhuma alteração no core, dados reais, serviço, Docker, site,
   modelo local ou máquina do usuário.

## Anti-loop e resultado

Um erro do CI => ler log; efetuar **no máximo uma correção motivada**
por causa distinta e revalidar. Nunca repetir mesmo comando/falha ou
pedir ao Qwen para adivinhar caminhos. Se CI não rodar, **parar sem
merge**, relatar bloqueio específico.

**Depois:** relatório da F2 é sobre capacidade de ensaiar o processo,
**não** autorização para voltar à prospecção nem fim da F2. Antes do
primeiro contato seguem pendentes revisão editorial e publicação do
site, decisão de contato, rotina documentada de back-office real,
condições comerciais, backup do índice e políticas aplicáveis.
