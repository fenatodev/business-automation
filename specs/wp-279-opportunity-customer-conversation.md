# WP-279 — conversa de oportunidade vinculada a Customer

WP-278 integrou vínculo explícito de oportunidade com Lead ou Customer, mas o
painel só renderizava o caminho de Lead. Esta WP completa a mesma UX sem nova
migration: consulta `/linked-customers`, mostra o contato e usa `customer_id`
na sugestão/criação da conversa.

O vínculo continua tenant-scoped, mutuamente exclusivo e sem envio externo.
Respostas antigas permanecem protegidas pelo controle de seleção da WP-278.
