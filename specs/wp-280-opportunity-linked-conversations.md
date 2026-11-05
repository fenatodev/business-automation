# WP-280 — conversas realmente relacionadas à oportunidade

O painel da oportunidade não deve exibir todas as conversas da empresa como se
fossem relacionadas. A nova rota `/opportunities/{id}/linked-conversations`
retorna somente conversas do Lead ou Customer explicitamente associado à
oportunidade, com isolamento tenant-scoped, ordenação decrescente e limite 50.

O endpoint legado `/opportunities/{id}/conversations` permanece compatível para
não quebrar consumidores existentes. A UI usa a rota vinculada e invalida
respostas atrasadas quando o operador troca de oportunidade.

Não há migration, envio externo ou alteração de autenticação nesta WP.
