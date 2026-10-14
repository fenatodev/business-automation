# Oracle A1 — chegada da VM e primeira inicialização (sem deploy)

**Operação:** `fenatodev/business-automation`, workflow
`.github/workflows/oci-a1-capacity.yml`, ambiente protegido
`oci-a1-provisioning`. A tentativa horária usa
`OCI_A1_ENABLED=true`; acionamento manual é sempre somente leitura.

Este roteiro só deve ser executado **após confirmação de `CREATED`**
em GitHub Actions e de `RUNNING` no Console Oracle. Não confundir sucesso
do pedido de criação com sistema operacional pronto ou acesso seguro.

## 1. Confirmações que não alteram recursos

1. Em Compute → Instances, no compartimento `business-automation`,
   localizar `business-automation-01`, conferir estado `RUNNING`,
   shape `VM.Standard.A1.Flex` (2 OCPU, 12 GB), origem Ubuntu
   **24.04 ARM64**, disco boot **50 GB**, AD São Paulo e o vínculo à sub-rede
   prevista. Não imprimir no repositório OCIDs/endereço IP da instância.
2. Em Billing/Cost Management, conferir que a conta está sob as
   condições Always Free, que nenhum serviço adicional foi criado e
   que alertas/cotas de consumo estão de acordo com o plano. Os limites
   do software **não são garantia contratual de ausência de cobrança**.
3. Após confirmar instância ativa, colocar a variável GitHub
   `OCI_A1_ENABLED` em `false` (ou remover) para evitar jobs futuros:
   `gh variable set OCI_A1_ENABLED -R fenatodev/business-automation --body false`.
   Não alterar segredos nem desabilitar o workflow para inspeções futuras.
4. Verificar ingress real da subnet: Security List, Network Security
   Groups associados e regras para TCP/22, TCP/80, TCP/443, bancos ou
   qualquer porta administrativa. **Nunca** expor FastAPI, Postgres,
   ERPNext, n8n ou portas de desenvolvimento à internet sem revisão.

## 2. Primeiro acesso privado por SSH (quando aprovado)

A chave SSH **privada** não é a chave de API Oracle e não deve ser
copiada para GitHub. Ela deve permanecer **somente no computador
autorizado**. No Ubuntu local, o par SSH baixado para o primeiro boot está
em `~/Downloads/keys/ssh-key-2026-10-14.key` (privada) e
`ssh-key-2026-10-14.key.pub` (pública).

Antes de conectar, confira o IP público pelo Console OCI e confirme
a fingerprint SSH do host por canal confiável; não aceite cegamente
fingerprints desconhecidas. Use `ubuntu` como usuário de login da
imagem Ubuntu. Após conferir permissões do arquivo SSH, conexão típica:

```bash
chmod 600 "$HOME/Downloads/keys/ssh-key-2026-10-14.key"
ssh -i "$HOME/Downloads/keys/ssh-key-2026-10-14.key" \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=ask \
  ubuntu@ENDERECO_IP_CONFIRMADO_NO_CONSOLE
```

`ENDERECO_IP_CONFIRMADO_NO_CONSOLE` é placeholder; não executar
literalmente. Se não houver rota de SSH, não abra portas genéricas por
conta própria: verificar ingress/security list, VNIC, IP público,
cloud firewall e estado da VM. Nunca desativar a checagem de host key.

## 3. Endurecimento, em sequência verificável

1. Checar distribuição/arquitetura, relógio e espaço
   (`uname -m`, `cat /etc/os-release`, `df -h`), sem mudanças.
2. Restringir SSH (chave apenas, sem senha/root), aplicar patches
   estáveis e configurar firewall permitindo SSH **somente da origem
   administrativa**. Guardar rollback antes de mudar regras que podem
   derrubar acesso. Não executar `ufw enable` sem regra de SSH funcional.
3. Opção recomendada para acesso continuado: Tailscale, tailnet já
   existente no computador administrador, instalado e autenticado na
   VM **somente após revisão da chave/dispositivo e ACLs**. Provar acesso
   via tailnet antes de remover TCP/22 público, se removê-lo.
4. Separar usuário de deploy não-root, diretórios de app e segredos
   fora do checkout; habilitar atualizações e logs mínimos necessários;
   validar reboot e recuperação de SSH antes de instalar aplicações.
5. Confirmar monitoramento, orçamento e backup/restore conforme o
   armazenamento Always Free restante; backups/snapshots podem contar
   na franquia ou gerar custo. **Não criar volumes extras sem auditoria**.

## 4. Serviços — permanecem independentes

- O **n8n self-hosted já existente** pode continuar como motor de
  automação; não migrá-lo de imediato para a A1.
- A API FastAPI do negócio continua privada, sem permissão para
  `0.0.0.0` público ou abertura de porta no OCI.
- O site institucional estático não precisa de VPS; Cloudflare Pages
  ou outro serviço estático reduz risco e manutenção. Publicação e
  domínio exigem autorização separada.
- O TV Box MXQ4K/Armbian é alvo alternativo, sujeito a inventário e
  teste de estabilidade próprio. Não alterar seu firmware neste fluxo.

**Gate de saída:** VM RUNNING, acesso SSH validado, rede restrita,
custo revisado, ambiente privado estável e rollback operacional.
Só depois disso preparar deploy de serviços, com escopo e aprovação
específicos.

Nenhum comando deste documento é executado automaticamente.
