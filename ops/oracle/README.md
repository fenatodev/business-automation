# Oracle A1 — capacity retry sem ativação implícita

**Estado: preparação, sem ativar nem criar VPS.** O workflow
`.github/workflows/oci-a1-capacity.yml` só tenta criar uma instância quando a
variável GitHub Actions `OCI_A1_ENABLED=true` for configurada explicitamente,
após revisão e autorização de implantação. Sem isso, o agendamento não executa
nenhum provisionamento.

## Motivação

Oracle Cloud retorna `Out of capacity for shape VM.Standard.A1.Flex` em
`sa-saopaulo-1`, AD-1. Uma tentativa automatizada por hora é mais prática
que tentativas manuais, mas **não garante capacidade nem prazo**.

Este mecanismo usa apenas o CLI oficial OCI; a configuração é fixa:
- shape `VM.Standard.A1.Flex` (ARM64);
- 2 OCPUs, 12 GB RAM, 50 GB boot;
- região `sa-saopaulo-1`, IP público, nome `business-automation-01`;
- sem volumes adicionais, sem deployment, sem acesso público a n8n/API/DB.

Os limites Always Free em 2026 são 1.500 OCPU-h/mês, 9.000 GB-h/mês,
com até 200 GB em volumes em bloco. **Essas franquias são compartilhadas**.
Apenas selecionar shape elegível não garante ausência de custos se já houver
outros recursos ou se a conta passar a PAYG.

## Segurança e modos de falha

- `ops/oracle/a1_once.py` faz **uma** tentativa por execução. Dry-run por
  padrão; `--apply` é necessário para criar.
- Antes de criar, consulta instâncias no compartimento selecionado. Se houver
  A1 ou instância com o mesmo nome ainda não terminada, interrompe.
- Somente `Out of capacity` autoriza conclusão normal sem recurso criado;
  falhas de autenticação e resposta ambígua não disparam novo lançamento
  no mesmo processo.
- **Não é auditoria de custos da tenancy inteira**. Verifique manualmente
  instâncias/volumes em outros compartimentos, orçamento, cotas e elegibilidade
  da imagem AArch64 Ubuntu 24.04 antes de ativar.
- A credencial para API OCI é uma **API signing key diferente da chave
  privada SSH** da VM. Nenhuma delas deve ser versionada ou enviada pelo chat.
- Use usuário OCI de automação com privilégios mínimos e chaves exclusivas.
  Não conceda autorização de API da conta administradora ao workflow.
- A security list pública pode permitir SSH amplo; restrinja à origem
  administrativa antes de ativar provisionamento automático.
- GitHub Actions de repositório público requerem revisão de segurança
  e do workflow na branch principal antes de receberem secrets.

## Configuração futura — não realizada

1. Confirmar no OCI que a conta terminou de ser ativada e que não há outras
   A1/volumes consumindo o limite gratuito.
2. Criar usuário OCI de automação com menor privilégio e gerar API signing key.
3. Consultar OCIDs reais do compartment, AD, VCN/subnet pública e imagem
   Ubuntu 24.04 ARM64. A rede já existente chama-se
   `business-automation-vcn`.
4. Sob **GitHub → Settings → Secrets and variables → Actions**, cadastrar
   somente secrets privados:
   `OCI_A1_TENANCY_OCID`, `OCI_A1_USER_OCID`,
   `OCI_A1_API_FINGERPRINT`, `OCI_A1_API_PRIVATE_KEY`,
   `OCI_A1_COMPARTMENT_OCID`, `OCI_A1_AVAILABILITY_DOMAIN`,
   `OCI_A1_SUBNET_OCID`, `OCI_A1_IMAGE_OCID`,
   `OCI_A1_SSH_PUBLIC_KEY` (somente conteúdo da chave pública .pub).
5. Solicitar segunda revisão para a configuração de produção e aprovar
   explicitamente merge/ativação.
6. Definir **Actions variable** `OCI_A1_ENABLED=true`. A tarefa tentará
   uma vez por hora. Após `CREATED`, confirmar `RUNNING` no Console,
   desabilitar a variável e iniciar hardening manual.

## Testes offline

```bash
uv run pytest tests/test_oci_a1_once.py
python -m compileall -q ops/oracle tests/test_oci_a1_once.py
```

Não houve consulta à conta real nem tentativa de criação de VM.

Documentação: [Always Free](https://docs.oracle.com/pt-br/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm),
[CLI launch](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/compute/instance/launch.html),
[API signing key](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm).
