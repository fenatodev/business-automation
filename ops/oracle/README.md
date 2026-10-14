# Oracle A1 — capacity retry sem ativação implícita

**Estado: preparação, sem ativar nem criar VPS.** O workflow
`.github/workflows/oci-a1-capacity.yml` só tenta criar uma instância quando a
variável de **repositório** GitHub Actions `OCI_A1_ENABLED=true` for configurada explicitamente,
após revisão e autorização de implantação. Sem isso, o agendamento não executa
nenhum provisionamento.

## Motivação

Oracle Cloud retorna `Out of capacity for shape VM.Standard.A1.Flex` em
`sa-saopaulo-1`, AD-1. Uma tentativa automatizada por hora é mais prática
que tentativas manuais, mas **não garante capacidade nem prazo**.

A nova implementação usa o SDK Python oficial da Oracle. Configuração fixa:
- shape `VM.Standard.A1.Flex` (ARM64);
- 2 OCPUs, 12 GB RAM, 50 GB boot;
- região `sa-saopaulo-1`, IP público, nome `business-automation-01`;
- sem volumes adicionais, sem deployment, sem acesso público a n8n/API/DB.

Os limites Always Free em 2026 são 1.500 OCPU-h/mês, 9.000 GB-h/mês,
com até 200 GB em volumes em bloco. **Essas franquias são compartilhadas**.
Selecionar shape elegível não garante ausência de custos se a tenancy ultrapassar
os limites gratuitos ou a conta passar a PAYG.

## Descoberta automática dos OCIDs (sem copiar dados manualmente)

Após conectar **cinco** segredos (4 do usuário OCI + chave SSH pública), a
execução descobre automaticamente, pelas APIs de leitura da Oracle:

- compartimento `business-automation` como filho direto da tenancy;
- único AD da região `sa-saopaulo-1`;
- sub-rede pública de nome exato `public subnet-business-automation-vcn`;
- imagem oficial Ubuntu 24.04 `aarch64` compatível com A1, versão recente.

Não solicita OCIDs adicionais ao usuário. Identificadores inconsistentes ou
ambíguos interrompem a execução. Isso depende das **permissões reais de leitura**
do usuário técnico no OCI, a validar em execução read-only.

`workflow_dispatch` aciona **apenas auditoria read-only**: lista recursos e verifica
duplicatas, sem criar VPS, mesmo que a variável de ativação esteja `true`.
O cron horário é a única via para `--apply`, e somente se a variável
`OCI_A1_ENABLED=true` estiver definida.

## Auditoria da tenancy inteira antes de criar

A inspeção por SDK já passou na conta Oracle, incluindo autenticação,
compartimento, imagem ARM64 e sub-rede. Agora o acionamento manual executa
`ops/oracle/oci_sdk_launch.py` **sem --apply**, chamando a auditoria de
`oci_sdk_tenancy_audit.py`. Ela examina instâncias A1 e consumo conjunto
de boot/block volumes (máximo Always Free: 200 GB) na região de origem, no
root e nos compartimentos retornados pela API, usando apenas operações list.
A verificação exige ler a tenancy inteira; se faltar permissão, **falha e
não cria nada**. Com 50 GB previstos para boot, bloqueia se já houver mais
de 150 GB de volumes ativos. Uma A1 existente em qualquer compartimento
também bloqueia nova criação.

Para o grupo técnico, caso a auditoria aponte falha de autorização,
adicionar as seguintes regras *somente leitura* à policy existente:

```text
Allow group 'Default'/'oci-a1-provisioners' to inspect instances in tenancy
Allow group 'Default'/'oci-a1-provisioners' to inspect volume-family in tenancy
```

O script `ops/oracle/oci_sdk_launch.py --apply` exige **também**
`OCI_A1_ENABLED=true`. O cron chama esse script apenas quando a variável
estiver habilitada; execução manual `workflow_dispatch` é sempre auditoria
read-only, inclusive quando a variável estiver habilitada.

A API de lançamento usa modelos tipados do SDK, shape/CPU/RAM/storage
fixados, token de idempotência diário e **sem repetição automática da API**
na mesma execução. Em caso de resultado incerto, nenhuma segunda tentativa
ocorre no job.

**Não habilitar** enquanto não estiverem confirmados: (1) auditoria de root
e todos os compartimentos, (2) controle de custos/conta e cotas hard no OCI,
(3) permissões mínimas efetivas para criação, (4) segurança SSH/rede pública
e (5) aprovação explícita do usuário para provisionamento.

## Segurança e modos de falha

- `ops/oracle/oci_sdk_launch.py` é a rota oficial de produção, com
  inventário global fail-closed e `--apply` protegido pela variável; o antigo
  `a1_once.py` é legado e **não está ligado ao workflow**.
- Antes de criar, consulta instâncias no compartimento selecionado. Se houver
  A1 ou instância com o mesmo nome ainda não terminada, interrompe.
- Somente `Out of capacity` autoriza conclusão normal sem recurso criado;
  falhas de autenticação e resposta ambígua não disparam novo lançamento
  no mesmo processo.
- A auditoria de volumes e A1 cobre os compartimentos visíveis na região
  de origem; contratos, serviços externos e cobranças ainda exigem revisão.
- A credencial para API OCI é uma **API signing key diferente da chave
  privada SSH** da VM. Nenhuma delas deve ser versionada ou enviada pelo chat.
- Use usuário OCI de automação com privilégios mínimos e chaves exclusivas.
  Não conceda autorização de API da conta administradora ao workflow.
- A security list pública pode permitir SSH amplo; restrinja à origem
  administrativa antes de ativar provisionamento automático.
- GitHub Actions de repositório público requerem revisão de segurança
  e do workflow na branch principal antes de receberem secrets.

## Segredos isolados no GitHub Environment

Criar em **Settings → Environments** o ambiente `oci-a1-provisioning`,
selecionar **Deployment branches and tags → Selected branches and tags**,
e adicionar **apenas** a branch `main` (tipo Branch, não Tag). Não marcar
`Required reviewers`: a execução é horária e teria que receber aprovação
a cada tentativa. Os segredos ficam em **Environment secrets**, nunca em
`Repository secrets`. O job também exige `github.ref == 'refs/heads/main'`,
usa `contents: read` e só injeta os segredos na etapa de criação do arquivo
OCI de curta duração (não nas actions externas de checkout/setup).

A variável não secreta `OCI_A1_ENABLED` fica em **Repository variables** e
começa ausente/desativada. Não ativar até confirmar IAM, limites e código.

## Configuração futura — não realizada

1. Confirmar no OCI que a conta terminou de ser ativada e que não há outras
   A1/volumes consumindo o limite gratuito.
2. Criar usuário OCI de automação com menor privilégio e gerar API signing key.
3. Consultar OCIDs reais do compartment, AD, VCN/subnet pública e imagem
   Ubuntu 24.04 ARM64. A rede já existente chama-se
   `business-automation-vcn`.
4. Sob **GitHub → Settings → Environments → oci-a1-provisioning → Environment secrets**,
   cadastrar somente **cinco segredos**:
   `OCI_A1_TENANCY_OCID`, `OCI_A1_USER_OCID`,
   `OCI_A1_API_FINGERPRINT`, `OCI_A1_API_PRIVATE_KEY`,
   `OCI_A1_SSH_PUBLIC_KEY` (somente chave pública .pub).
   O preenchimento desses cinco segredos foi confirmado. Os 4 OCIDs de recursos
   são descobertos em cada execução sem armazenamento de segredos adicionais.
5. Solicitar segunda revisão para a configuração de produção, executar
   uma verificação manual `workflow_dispatch` somente leitura após o merge,
   corrigir IAM se houver negação e aprovar explicitamente a ativação.
6. Definir **Actions repository variable** `OCI_A1_ENABLED=true`. A tarefa tentará
   uma vez por hora. Após `CREATED`, confirmar `RUNNING` no Console,
   desabilitar a variável e iniciar hardening manual.

## Testes offline

```bash
uv run pytest tests/test_oci_a1_once.py
python -m compileall -q ops/oracle tests/test_oci_a1_once.py
```

O SDK de inspeção já consultou a conta real com sucesso. Nenhuma criação
foi executada; a auditoria ampliada ainda requer validação.

Documentação: [Always Free](https://docs.oracle.com/pt-br/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm),
[CLI launch](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/compute/instance/launch.html),
[API signing key](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm).
