# WP-278 — conversas da oportunidade com contato explícito

## Decisão

Uma oportunidade pode apontar para um `Lead` ou `Customer` do mesmo tenant,
mas nunca para ambos. O vínculo é persistido na oportunidade para que a UI
possa criar conversa sem adivinhar qual contato pertence ao caso.

O botão de nova conversa aparece somente quando há lead vinculado. A sugestão
de mensagem e a criação usam esse lead e a API existente; não há envio externo.
O endpoint de leads da oportunidade retorna apenas o lead vinculado, mantendo
o estado vazio para oportunidades sem contato.

## Segurança e compatibilidade

- IDs fornecidos pelo cliente são verificados contra a Company autenticada.
- O vínculo é opcional para não invalidar oportunidades históricas.
- A migration adiciona FKs, índices e check de exclusão mútua.
- O admin continua sem acesso implícito a dados tenant.
- O painel não usa o primeiro registro da empresa nem cria conversa sem contato.

## Validação

Testes cobrem criação com lead, sugestão/criação de conversa, isolamento
cross-tenant e rejeição de dois contatos. Executar a suíte completa,
compileall, diff-check e o harness PostgreSQL descartável antes do merge.
Migration real/produção permanece proibida.
