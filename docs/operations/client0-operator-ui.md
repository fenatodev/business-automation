# WP-017 — Interface interna mínima do operador Client 0

**Status:** implementada no código para revisão; não é release nem interface pública.  
**Dependência:** WP-009/010, WP-013 (piloto sintético), ADR 0003 (operator vinculado à Company).  
**Escopo fechado:** captura manual de Opportunity, listagem, triagem e ProposalBrief.
Não cria aplicação SPA separada, framework frontend, nova API, migrations ou autenticação.

## Acesso

Com a API privada já iniciada em **loopback**, abrir:

`http://127.0.0.1:8788/operator`

As rotas `GET /operator`, `GET /operator/app.js` e
`GET /operator/styles.css` servem **somente conteúdo estático**. Verificam
cliente/Host local; são ocultas do OpenAPI. **Não é proteção de produção**:
bind da API em `127.0.0.1`, firewall, host seguro e identidade continuam
obrigatórios. Não expor API/UI via rede, proxy público ou túnel sem gate próprio.

A tela é visível sem credenciais, mas não contém dados operacionais. O usuário
deve fornecer um token **operator** privado pela própria página. A API continua
exigindo Bearer em **cada** operação. Tokens `admin` não operam o tenant.

O token é mantido somente em variável JS na memória da aba: **não** é
armazenado em cookies, `localStorage`, `sessionStorage`, URL ou logs
da página. Ao desconectar/recarregar/fechar a aba, perde-se a sessão.
O navegador e extensões ainda são parte do ambiente de confiança; não usar
em dispositivo compartilhado ou não confiável. Não inserir token em chats,
capturas de tela, URLs, documentação ou commits. Não há implementação de
login OAuth, senha ou revogação dinâmica neste WP.

Cabeçalhos defensivos em todos os ativos: `Cache-Control: no-store`,
CSP sem scripts/estilos inline ou fontes remotas, `frame-ancestors 'none'`,
`X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`,
`X-Content-Type-Options: nosniff` e CORP same-origin.
O JS usa fetch same-origin com `credentials: omit`, Bearer apenas
no header e não renderiza HTML recebido da API: conteúdos são inseridos
via `textContent` ou propriedades `value`. Links externos informados
por oportunidades aparecem **somente como texto**, sem navegação automática.

## Operação manual

1. Inserir token de operador e conectar. A UI consulta
   `GET /opportunities`; sem token válido, nenhum dado é exibido.
2. Registrar oportunidade **somente de fonte `99freelas`**: título,
   URL HTTPS, descrição, requisitos, orçamento e prazo opcionais.
   O horário é `new Date().toISOString()` do relógio do navegador.
   **Conferir relógio do host.**
3. Selecionar oportunidade na lista do **tenant vinculado ao token**.
   A UI não permite escolher ou enviar `company_id`.
4. Registrar decisão humana `pending`, `follow`, `ignore` ou
   `prepare_proposal`, com nota. Não há classificação por IA.
5. Somente quando estiver em `prepare_proposal`, criar um
   `ProposalBrief` em `draft`. Depois editar e marcar
   `ready_for_review` conforme revisão interna.
6. **Parar** antes de proposta formal, preço, aprovação, envio e handoff ERP.
   `ready_for_review` não significa aprovado.

O formulário de brief usa somente `offer_reference`, `diagnosis`,
`scope`, `deliverables`, `acceptance_criteria`, `assumptions`,
`risks` e, no update, `status`. Não permite `price` nem
`approved`.

## Falhas / limitações

- `401`: descarta token da memória, exige nova conexão.
- `403`: papel sem permissão; usar identidade `operator`.
- `404`: recurso/brief não existe ou não pertence ao tenant.
- `409`: oportunidade duplicada ou estado de brief inválido.
- `422`: entrada rejeitada pela API; revisar campos.
- A API atual ainda não possui histórico de triagem, prazo de follow-up
  ou aprovação eletrônica. A UI **não** fabrica esses recursos.
- Não é modo offline. Se a API cair depois de uma escrita e antes
  da resposta, **verificar a lista antes de repetir**; POST de oportunidade
  rejeita duplicidade por URL e brief permite somente um por oportunidade.
- Não adotar URL `http://` de plataformas externas para captura: a UI
  exige `https://`. Dados de negócio continuam protegidos no back-end.
- Não usar CSS/JS de CDN ou abrir links de anúncios automaticamente.

## Validação e ativação

Executar somente em checkout **de teste**, nunca usando o banco persistente:

```bash
uv run pytest tests/test_operator_ui.py -q
uv run pytest -q
.venv/bin/python -m compileall app tests
git diff --check
node --check app/operator_ui/app.js
```

Testes de rota cobrem CSP, no-store, assets, restrições de cliente/Host,
ausência de token incorporado, campos e manutenção da autenticação nas APIs.
O cliente UI usa os **mesmos endpoints** já testados em `tests/test_api.py`
e `tests/test_client0_simulation.py`.

Para ativar no **runtime real** do Client 0 será necessário atualizar o
checkout e **reiniciar intencionalmente** somente a API privada, conforme
`docs/operations/client0-runbook.md`. Merge Git **não** altera
processo Uvicorn em execução. Não reiniciar banco nem trocar credenciais
por consequência deste WP. Operação real e publicação dependem de gate
e decisão humana separados.

## Critério de saída

A UI reduz manipulação manual de JSON e oferece uma rotina mínima
sem introduzir infraestrutura. O trabalho do operador e sua fricção
precisam ser medidos antes de criar dashboards, adapters ERP ou
automações de captação. Nenhuma simulação substitui o gate real da F2.

## CSV de tarefas internas

Na seção Tarefas internas, selecionar a ordenação por Data, ID, Status ou
Tentativas e clicar em Exportar CSV. O arquivo segue a mesma ordem decrescente
da lista (ID decrescente no desempate), preservando status, busca e datas.
Exporta todos os resultados filtrados, incluindo os que estão em outras páginas.
Consumidores diretos de `/internal-tasks/export.csv` que omitem `sort` continuam
recebendo ID crescente. O arquivo mantém os campos existentes, sem payloads.

## CSV de leads

Na seção Leads, escolher ID, Data, Status ou Nome e clicar em Exportar CSV.
O arquivo segue a ordem da lista: data decrescente; ID, status e nome
crescentes; ID crescente no desempate. Status, fonte, busca e datas são
preservados, incluindo resultados de outras páginas. O endpoint
`/leads/export.csv` mantém ID crescente quando `sort` é omitido e retorna
422 para uma ordenação desconhecida.

## CSV da fila de revisão

Na fila de revisão, escolher Data, ID ou Status e exportar CSV. O arquivo
segue data decrescente ou ID/status crescentes, com ID crescente no desempate.
Status, busca e datas permanecem aplicados a todos os resultados, sem limite
de página. Sem `sort`, `/review-queue/export.csv` mantém ID crescente; uma
ordenação desconhecida retorna 422. A exportação não registra decisões.

## CSV de conversas

Em Conversas, escolher Última mensagem, Data de criação ou ID e exportar CSV.
O arquivo preserva a ordenação e os filtros de canal, status, busca, contato e
período, incluindo resultados de outras páginas e suas mensagens. Datas são
decrescentes; ID é crescente, inclusive no desempate. O endpoint mantém ID
crescente sem `sort` e retorna 422 para ordenação desconhecida.

## CSV de oportunidades

Exportar CSV transmite a ordem ID, Data, Status ou Prioridade selecionada.
Exporta todos os resultados dos filtros existentes, sem limite de página.
Data e ID de desempate são decrescentes; status é crescente com ID crescente;
prioridade usa score decrescente e ID crescente no empate. Sem `sort`, a API
mantém ID crescente; valor desconhecido retorna 422. A lista por prioridade
continua usando seu endpoint próprio, sem alterar seu contrato de filtros.

## CSV de briefs

Em Proposal Briefs, escolher Data, ID, Status ou Título e exportar CSV.
O arquivo segue a ordem da lista, preservando status, oportunidade, busca e
período em todos os resultados, inclusive os de outras páginas. Data e ID de
desempate são decrescentes; status/título e seu desempate por ID são crescentes.
Sem `sort`, `/proposal-briefs/export.csv` mantém ID crescente; valor desconhecido
retorna 422. Os campos detalhados permanecem no arquivo.

## Falha ao atualizar conversas

Se a consulta da lista ou da contagem falhar, a seção Conversas informa que
não foi possível atualizar e oferece **Tentar novamente**. Resultados e
seleção anteriores permanecem visíveis e podem estar desatualizados. A nova
tentativa mantém filtros, ordenação e página, repetindo somente consultas de
leitura. O indicador de carregamento é anunciado à tecnologia assistiva;
uma resposta vazia bem-sucedida continua mostrando o estado vazio normal.

## Falha ao atualizar clientes

Se a lista ou a contagem de Clientes falhar, a tela preserva os resultados,
a contagem e as seleções anteriores e informa que podem estar desatualizados.
**Tentar novamente** repete apenas consultas de leitura com os filtros,
a ordenação e a página atuais. O carregamento é anunciado à tecnologia
assistiva. Uma consulta vazia bem-sucedida mostra o estado vazio normal;
a notificação de atualização concluída só aparece após sucesso.

## Falha ao atualizar leads

Se a lista ou contagem de Leads falhar, resultados, contagem, badge e seleção
anteriores permanecem na tela e podem estar desatualizados. **Tentar novamente**
repete consultas de leitura com filtros, ordenação e página atuais. A seção
anuncia carregamento e falha; só anuncia atualização concluída após sucesso.
Uma resposta vazia bem-sucedida mostra o estado vazio normal.

## Falha ao atualizar tarefas internas

Se a lista ou contagem de tarefas falhar, resultados, paginação e seleção
anteriores permanecem visíveis, com aviso de possível desatualização.
**Tentar novamente** repete somente consultas de leitura usando filtros,
ordenação e página atuais; não reprocessa tarefas. A seção anuncia o
carregamento. Após sucesso, a seleção é limpa e resultados vazios mostram
o estado vazio normal.

## Falha ao atualizar fila de revisão

Falhas na lista, resumo, atrasos ou contagem preservam o snapshot e a seleção
anteriores, com aviso de possível desatualização. **Tentar novamente** repete
somente consultas de leitura com filtros, ordem e página atuais; não registra
decisões nem envia mensagens. O carregamento é anunciado à tecnologia assistiva.
Após sucesso, a seleção é limpa e a fila vazia mostra seu estado normal.

## Falha ao atualizar briefs

Se a lista ou contagem de briefs falhar, os resultados, paginação e seleção
anteriores permanecem visíveis com aviso de possível desatualização.
**Tentar novamente** repete consultas de leitura com filtros, ordem e página
atuais. O carregamento é anunciado; após sucesso, a seleção é limpa e uma
lista vazia mostra o estado normal. Nenhuma nova tentativa altera briefs.

## Ordem das oportunidades na tela

Os cards preservam a ordem retornada pela API: ID crescente, Data decrescente,
Status alfabético ou Prioridade por score decrescente. Selecionar um card
mantém essa sequência. Os filtros e páginas continuam sob o contrato dos
endpoints existentes; Prioridade usa sua consulta própria.
