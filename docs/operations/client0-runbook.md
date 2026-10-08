# Client 0 — runbook operacional mínimo

Status: piloto privado  
Escopo: operação básica do core Business Automation antes de exposição pública.

## Estado atual

- O sistema está autorizado somente para piloto privado.
- A API não está autorizada para exposição pública.
- O acesso de domínio usa Bearer token conforme o ADR 0003.
- PostgreSQL é a fonte operacional do core.
- ERP/financeiro continuam sendo as fontes autoritativas para propostas, cobrança, recebimento e demais dados já atribuídos ao back-office.
- Segredos e dados reais não pertencem ao repositório.

## Startup privado

Antes de iniciar a API:

1. confirmar que banco e segredos pertencem ao ambiente correto;
2. manter o bind em loopback ou em rede privada explicitamente autorizada;
3. não usar `0.0.0.0` sem um gate posterior de exposição;
4. confirmar que tokens, hashes e DATABASE_URL não aparecem em comandos, documentação pública ou logs de exemplo;
5. iniciar o serviço somente após validar o destino do PostgreSQL.

Validação mínima:

- `GET /` deve responder como health check;
- rotas de domínio sem credencial devem permanecer protegidas;
- verificar o endereço de escuta com ferramenta local apropriada, como `ss -ltnp`;
- confirmar também firewall/NAT/rede do ambiente: bind privado por si só não substitui revisão de exposição.

Este runbook não define systemd, reverse proxy, TLS público ou deploy.

## Backup

Para dados operacionais, usar backup lógico PostgreSQL e armazená-lo fora do repositório, em local protegido e com acesso restrito.

Para cada backup:

1. registrar data, ambiente e responsável;
2. verificar o exit code de `pg_dump`;
3. verificar que o arquivo existe e tem tamanho maior que zero;
4. proteger o arquivo conforme a sensibilidade dos dados;
5. nunca considerar a existência do arquivo como prova suficiente de recuperação.

Um backup só é operacionalmente confiável quando existe restore drill periódico e verificável.

O script `scripts/verify-postgres-backup-restore.sh` valida o mecanismo apenas com PostgreSQL descartável e dados sintéticos. Ele não realiza backup de dados reais.

## Restore

Restaurar primeiro em banco novo e isolado.

Procedimento mínimo:

1. selecionar explicitamente o backup correto;
2. criar um banco vazio separado do banco ativo;
3. restaurar com `pg_restore`;
4. verificar a revisão Alembic restaurada;
5. validar contagens, relacionamentos e registros esperados;
6. revisar o resultado antes de qualquer promoção operacional.

Não restaurar destrutivamente sobre o banco ativo. Esse tipo de recuperação exige procedimento próprio, janela operacional e aprovação humana.

## Incidente mínimo

Em caso de suspeita de corrupção, perda de dados ou comportamento operacional inseguro:

1. parar escrita e efeitos externos quando aplicável;
2. preservar logs e demais evidências disponíveis;
3. identificar o último backup conhecido e seu contexto;
4. restaurar esse backup em ambiente isolado;
5. validar schema, dados e relacionamentos;
6. revisar a causa e a integridade do ambiente;
7. somente promover o retorno após revisão humana.

Se a integridade não puder ser comprovada, manter o sistema fora de operação em vez de assumir que o restore está correto.

## Segredos

Nunca registrar em Git, exemplos públicos ou logs de diagnóstico:

- Bearer token;
- hash de token;
- senha de banco;
- DATABASE_URL completa;
- credenciais de ERP/provider;
- dados reais de clientes.

Ao compartilhar evidência operacional, preferir IDs sintéticos, nomes genéricos e mensagens sem conteúdo real.
