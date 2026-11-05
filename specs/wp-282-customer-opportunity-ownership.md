# WP-282 — preservar Customer ao criar oportunidade pela UI

O formulário de oportunidade aberto no detalhe de Customer agora envia
`customer_id`, preservando o vínculo explícito usado pela criação de conversa
da WP-279. A alteração é somente de payload da UI; a API já valida o contato
e o tenant. Nenhum envio externo ou migration nova.
