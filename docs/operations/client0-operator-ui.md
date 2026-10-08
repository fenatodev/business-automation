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
