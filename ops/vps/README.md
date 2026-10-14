# VPS portável — F2 (laboratório privado, sem deploy)

> **Status:** template para revisão. NÃO cria uma conta, compra VM, configura DNS,
> abre portas públicas, migra dados reais nem envia mensagens. Nenhum cliente pode
> editar workflows do n8n Community, inclusive via uma UI/IA intermediária.

## Escolha de hospedagem (preços oficiais consultados em 14/10/2026)

| Provedor | Cenário | Limites importantes | Decisão |
| --- | --- | --- | --- |
| Oracle Always Free A1 (ARM64) | **2 OCPUs / 12 GB RAM** equivalentes, até 200 GB de volumes elegíveis, sujeito às horas mensais e limites da conta | Cartão para cadastro, região *home* escolhida permanentemente, A1 pode estar **sem capacidade**, instância ociosa pode ser recolhida. **ATENÇÃO:** artigos antigos citam 4 OCPUs / 24 GB, mas a documentação oficial foi reduzida em junho/2026 | Primeira tentativa, apenas se houver disponibilidade real |
| Hetzner CX23 (x86_64) | 2 vCPU / 4 GB RAM | **€5,49/mês + €0,50 IPv4 = €5,99/mês**, antes de IVA e outros extras | VPS econômica de início, atenção ao uso de memória |
| Hetzner CX33 (x86_64) | 4 vCPU / 8 GB RAM | **€8,49/mês + €0,50 IPv4 = €8,99/mês**, antes de IVA e outros extras | Fallback mais confortável para PostgreSQL + n8n + runners + API |
| Contabo Cloud VPS 4 (x86_64) | 4 vCPU / 8 GB RAM / 100 GB SSD | A partir de **US$5,28/mês** anunciado em contrato de 24 meses; periodicidade, taxa de localidade, renovação e desempenho real devem ser conferidos no checkout | Alternativa, sem assumir custo final ou performance |
| Google Always Free e2-micro | 1 GB RAM / 30 GB disco standard / 1 GB egress para destinos cobertos | Recursos modestos demais para este stack completo | Apenas microserviço auxiliar, não escolher |

Fontes e regras que mudam com frequência:
- Oracle (revisado em junho/2026): https://docs.oracle.com/pt-br/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- Oracle cadastro: https://docs.oracle.com/pt-br/iaas/Content/FreeTier/freetier.htm
- Hetzner (preços desde junho/2026): https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
- Hetzner IPv4: https://docs.hetzner.com/general/infrastructure-and-availability/ipv4-pricing/
- Contabo: https://contabo.com/en/pricing/
- Google: https://docs.cloud.google.com/free/docs/free-cloud-features

**Recomendação:** tentar Oracle A1 ARM64 gratuita uma vez **sem upgrade pago automático**. Caso a instância não esteja disponível, não perder semanas: escolher Hetzner CX33 apenas após autorização de custo. Para site público estático, preferir Cloudflare Pages Free sob gate de publicação separado. As imagens deste template devem ser verificadas para `linux/arm64` no registro antes de provisionar Oracle.

## Arquitetura — separar domínio e orquestração

```text
origem consentida → gateway/webhook autenticado (FUTURO, DESLIGADO)
                         ↓
                 FastAPI: tenant + políticas (FUTURO)
                         ↕
                 PostgreSQL do domínio (FUTURO)
                         ↓
                 outbox idempotente (FUTURO)
                         ↓
                 n8n: orquestração ←→ PostgreSQL n8n
                         ↓
                  runner de código isolado
                         ↓
                 adaptadores oficiais (FUTURO)
```

**Implementado neste template:** n8n 2.40.7, runners e seu PostgreSQL privado. Sem portas de Postgres, sem ingresso público, editor n8n ligado **somente ao loopback da VPS**. O runner fica em uma rede Docker separada da rede PostgreSQL, com raiz de sistema de arquivos somente leitura, `/tmp` temporário, capabilities removidas e limite de processos. Isso reduz o alcance de código executado, mas **não substitui políticas de egress, AppArmor/seccomp e testes reais de isolamento**. A API FastAPI e seus dados terão banco e credenciais separados quando integrados. Não usar credenciais de administração do PostgreSQL n8n no domínio.

**O core F2 em desenvolvimento** segue em branch separada; não oferecer atendimento real ou persistência entre clientes até revisão e migrações autorizadas. IA cloud paga só após teto de custo, orçamento, fallback e autorização explícitos; Qwen 9B permanece no PC como ferramenta de testes e não estará disponível 24 horas se o PC desligar.

## Pré-configuração e verificação SEM deployment

A partir da pasta `ops/vps`:

```bash
python3 preflight.py init
python3 preflight.py check
docker compose --env-file .env -f compose.yaml config --quiet
```

- `init` cria `.env` **exclusivamente se não existir** (modo `0600`), com senhas geradas aleatoriamente; jamais commitá-lo ou mostrá-lo em logs.
- `check` recusa env ilegível, permissões inseguras e senhas placeholder/fracas, sem imprimir os segredos.
- `config --quiet` valida a sintaxe do Compose e a interpolação, **sem criar serviços**.
- Não usar `docker compose config` sem `--quiet` em logs/CI porque expõe o conteúdo interpolado das variáveis.
- Não executar `docker compose up` no Ubuntu atual: o n8n existente utiliza outro Compose, banco SQLite, runners e credenciais preservadas. **Nunca transplantar apenas o SQLite** para Postgres; migração exige plano de exportação de workflows/credenciais, chave de criptografia, ensaio de restauração e autorização.

## Checklist obrigatório antes de provisão real

1. **Conta e limites:** usuário escolhe plano/região e aprova limite mensal. Não usar Pay As You Go ou inserir cartão por automação. Confirmar elegibilidade Always Free **na conta real** e marcar limites de gastos/alertas.
2. **Host:** Ubuntu LTS, SSH com chave, root login por senha proibido, firewall deny-by-default, atualização de segurança, relógio/NTP; arquitetura `aarch64` (Oracle) ou `x86_64`.
3. **Privacidade:** instância n8n privada, SSH tunnel (`ssh -L 5678:127.0.0.1:5678 usuario@VPS`), segredos em `.env` modo 600, volumes separados, sem portas PostgreSQL públicas.
4. **TLS público:** ingressos assinados e HTTPS separados para webhooks oficiais; não publicar editor n8n/fastapi por esta WP. `N8N_SECURE_COOKIE=false` é **somente para protótipo de acesso por túnel SSH**; ativar `true` com HTTPS antes da exposição de qualquer UI pública.
5. **Repetibilidade:** validar `docker compose config --quiet`, versões de imagens (preferencialmente SHA digest após prova), teste de restart, retomada da fila, idempotência, isolamento por Company, retenção, política e kill switch. Verificar que o runner continua funcional com raiz read-only e não alcança o PostgreSQL; validar também a compatibilidade ARM64 das três imagens antes de escolher Oracle A1. Não declarar essa validação concluída sem execução real.
6. **Backup:** cópia criptografada **fora da VPS** de banco/volume n8n/chave; restaurar em host isolado antes de primeiro cliente. Sem backup reproduzível não há serviço pago.
7. **Custos:** medir RAM, CPU, SSD/IOPS, saída de dados, mensagens oficiais e provedor LLM; alertar, pausar e escalar quando exceder limites.
8. **Licença:** n8n Community permite agência criar/operar workflows para clientes **sem clientes editarem ou controlarem a lógica**, nem via agentes/CRUD expostos. n8n embutido como editor / SaaS customizável precisa de licença comercial: https://support.n8n.io/article/can-i-use-your-license-for-my-use-case

## Próximos gates

- **Gate 0:** selecionar Oracle A1 x86/ARM ou Hetzner/Contabo e confirmar preço final, arquitetura e disponibilidade.
- **Gate 1:** validar stack em VPS privada sem domínio, dados reais ou canais externos.
- **Gate 2:** integrar FastAPI, banco do domínio, worker/outbox e canal **simulado**; evidências de reinício e testes.
- **Gate 3:** DNS/TLS, tokens de webhook, compliance, limites de mensagens, monitoração e autorização comercial.
- **Gate 4:** onboarding de um cliente real, com política consentida, fiscalização dos primeiros ciclos, escalonamento em exceções.

Documento orienta arquitetura **replicável para cada ambiente/cliente**, sem declarar capacidade multi-tenant real apenas por instalar containers. Não confundir "mesma VPS" com isolamento operacional comprovado.
