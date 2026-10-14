# Oracle A1 — capacity retry sem ativação implícita

**Estado em 2026-10-14: automação horária ATIVA, mas criação ainda não
confirmada.** O responsável autorizou explicitamente habilitar
`OCI_A1_ENABLED=true` após a auditoria somente leitura de sucesso
(`2 compartimentos / 0 GB / nenhuma A1`, execução GitHub Actions
`38593381293`). O workflow
`.github/workflows/oci-a1-capacity.yml` tenta uma única A1 fixa a cada
hora, no minuto 33 UTC. O acionamento manual permanece somente leitura.
O agendamento pode atrasar; nenhuma capacidade nem hora de criação é garantida.

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
Allow group 'Default'/'oci-a1-provisioners' to read instances in tenancy
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

**Gates remanescentes após a ativação autorizada:** a auditoria de
root/compartimentos foi validada, mas **não há evidência de quota rígida/
orçamento no OCI nem inspeção efetiva de regras de ingresso SSH**.
Priorizar revisão desses controles; desativar `OCI_A1_ENABLED` ao detectar
qualquer custo potencial inesperado. A segurança da rede/SSH deve ser
endurecida antes de publicar qualquer serviço no host.

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
- A security list pública pode permitir SSH amplo; revisar e restringir
  à origem administrativa antes de colocar a VM em uso, sem interromper
  o acesso ao servidor. Nenhum serviço será exposto automaticamente.
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

A variável não secreta `OCI_A1_ENABLED` fica em **Repository variables**.
Após consentimento explícito em 2026-10-14 ela foi configurada como
`true`. Reverter para `false` ou remover a variável interrompe
novas tentativas agendadas (não encerra eventual VM existente).

## Próximos passos operacionais

1. Observar a execução horária em [Actions](https://github.com/fenatodev/business-automation/actions/workflows/oci-a1-capacity.yml).
   A execução manual nunca cria VM; somente `schedule` aciona `--apply`.
2. Se `NO_CAPACITY`, manter as tentativas e não alterar shape/região por
   conveniência. Se `OCI_BLOCKED`, investigar a categoria e não ampliar
   permissões IAM sem necessidade comprovada.
3. Se `CREATED`, conferir a instância em `RUNNING` no OCI Console antes
   de tratar o recurso como funcional. Desativar a variável após confirmação.
4. Executar o [checklist de pós-provisionamento](https://github.com/fenatodev/business-automation/issues/94):
   firewall, SSH somente por chave e origem controlada, atualizações,
   acesso remoto seguro, custos/quotas e backups.
5. `n8n` e a API privada permanecem fora da internet até revisão e
   autorização de um deploy separado; nenhuma publicação automática de site.

**Monitoramento adicional:** uma checagem horária de execução foi criada no
ChatGPT para avisar sobre `CREATED` ou falha nova relevante, sem avisos
repetidos de indisponibilidade de capacidade.

## Testes offline

```bash
uv run pytest tests/test_oci_sdk_probe.py tests/test_oci_tenancy_guarded_launch.py
python -m compileall -q ops/oracle
```

A auditoria completa do SDK consultou a conta real e passou sem mutações
(GitHub Actions `38593381293`). As tentativas de criação **só começaram
a ficar elegíveis no primeiro cron após a ativação**; verificar logs e
console antes de afirmar que alguma VM foi criada.

Documentação: [Always Free](https://docs.oracle.com/pt-br/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm),
[CLI launch](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/compute/instance/launch.html),
[API signing key](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm).
