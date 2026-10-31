# WP-085 — Converter lead em customer via UI do operador

## Problema

O backend possui `POST /leads/{lead_id}/convert` que converte um lead em customer
e atualiza o status para "won". No entanto, o operador não tinha interface para
acessar essa funcionalidade — era necessário usar a API diretamente.

## Solução

Botão "Converter" em cada lead na seção "07 / LEADS" do operador. Ao clicar,
o lead é convertido em customer via `POST /leads/{lead_id}/convert`, o status
é atualizado para "won" e a lista é recarregada. O botão só aparece para leads
que ainda não foram convertidos (status != "won").

## Changes

### HTML (app/operator_ui/index.html)
- Botão "Converter" em cada item de lead (`#lead-convert-{id}`)
- Mensagem de confirmação antes da conversão

### JavaScript (app/operator_ui/app.js)
- `convertLead()` envia POST para `/leads/{id}/convert`
- Allowlist em `leadApi()` inclui `/leads/{id}/convert`
- `renderLeads()` esconde botão para leads já convertidos (status === "won")
- Confirmação via `confirm()` antes de converter

### CSS (app/operator_ui/styles.css)
- `.lead-convert-btn` estilo de botão secundário

### Testes (tests/test_wp085_lead_convert_ui.py)
- Testes de contrato UI: botão, allowlist, handler, confirmação

## Validação

- pytest, compileall, diff-check

## Notas

WP-085 depende de WP-084 (PR #168). Base do PR: `wp/084-reject-brief`.
