# WP-026 — Destino MXQ4K reservado para depois, sem tocar no aparelho

**Estado:** site estático com pacote portátil pronto para validação em CI.
**Hospedagem MXQ4K:** **adiada por decisão do responsável**. Não houve
conexão, acesso, alteração, instalação, configuração de rede ou publicação
no TV Box. A F2 continua aberta e a prospecção permanece pausada.

## A. Decisão de arquitetura agora

A vitrine FenatoDev é estática (HTML, CSS, SVG). Portanto **não depende
de CPU x86, Python, Qwen, PostgreSQL, ERPNext ou API na hospedagem**.
O host definitivo é substituível: preservar apenas os arquivos públicos,
não acoplar o core privado ao aparelho.

O pipeline mantém **duas versões verificáveis**:

| Target | Artefato | Arquivos públicos |
| --- | --- | --- |
| `cloudflare-pages` (default WP-025) | `fenatodev-site-candidate-<commit>` | `index.html`, `styles.css`, `favicon.svg`, `_headers` (somente Cloudflare) |
| `portable-static` (WP-026) | `fenatodev-portable-static-<commit>` | **Somente** `index.html`, `styles.css`, `favicon.svg` |

**Por que retirar `_headers` do pacote portátil:** esse arquivo
é uma convenção da Cloudflare Pages. Num servidor web comum,
pode ser oferecido aos visitantes como arquivo estático e **não**
configura os cabeçalhos de segurança. O servidor escolhido deverá
declarar CSP, `frame-ancestors`, `nosniff`, políticas de
referrer e permissões na sua **configuração própria**.

Comandos locais futuros opcionais, **sem realizar deploy**:

```bash
# Rodar em um checkout descartável com uv:
uv run python -m site_release.prepare \
  --target portable-static --output /tmp/fenatodev-static-candidate-novo

# O alvo precisa ser uma pasta ainda INEXISTENTE.
# O relatório JSON mantém publication_authorized=false.
```

O GitHub Actions executa este comando e os testes automaticamente.
Nenhum prompt ao Continue é necessário enquanto CI estiver funcionando.

## B. MXQ4K: por que não adivinhar hardware nem sistema

"MXQ 4K" pode identificar aparelhos de fabricantes, SoCs, RAM e
memória flash diferentes, com firmware/bootloader incompatíveis.
**Não** escolher imagem de Armbian nem instrução de flash apenas pelo
nome da carcaça.

No **futuro**, em sessão específica autorizada, o primeiro WP do
hardware será apenas **inventário read-only**, sem root, flash ou
exposição pública: modelo/placa, SoC real, RAM, armazenamento,
tipo de flash, versão do Android ou Linux, capacidade de boot
reversível, Ethernet, temperatura, fonte de alimentação e consumo.

Gates que permanecem abertos:

1. **Compatibilidade**: boot Linux suportado e recuperável para
   o SoC/placa exatos; testar sem gravar eMMC/NAND primeiro, se
   tecnicamente possível. Falta de suporte => **STOP**.
2. **Estabilidade**: duração de teste local com servidor estático,
   temperatura, reinícios e comportamento após queda de energia.
3. **Operação**: atualizações de segurança, serviço não privilegiado,
   usuário de deploy, leitura de arquivos, logs/rotação, recovery.
4. **Rede pública**: domínio ou túnel/edge escolhido conscientemente;
   HTTPS real e headers HTTP verificados. Não fazer port-forward,
   UPnP, DMZ ou exibir IP doméstico por consequência desse pacote.
5. **Separação**: nada de API privada, PostgreSQL, chaves, ERP ou
   console administrativo no box público. O host recebe **somente
   os três assets permitidos**, se algum dia for aprovado.
6. **Fallback**: se o box for instável, antigo ou inseguro, usar
   hospedagem estática gerenciada; não bloquear a atividade comercial
   por insistir num dispositivo inadequado.

Não gerar `Caddyfile`, serviço systemd, firmware, Docker Compose,
`iptables`, Cloudflare Tunnel, configurações de DNS ou credenciais
antes de conhecer o SO e aprovar a topologia. Uma opção eventual
é Caddy ou Nginx em Linux suportado, com headers configurados fora
da raiz pública; **não** são instalados agora.

Referências de contexto (não instruções de flash):
- [Discussão Armbian: placas RK322x com variantes do mesmo modelo](https://forum.armbian.com/topic/34923-csc-armbian-for-rk322x-tv-box-boards/page/26/).
- [Caddy: servir arquivos estáticos](https://caddyserver.com/docs/caddyfile/directives/file_server).
- [Caddy: configurar cabeçalhos de resposta](https://caddyserver.com/docs/caddyfile/directives/header).

## C. O que falta para a operação comercial antes de leads

O hardware fica em espera. O próximo pacote **não é implantação**:
resolver primeiro o bloqueio real de F2/O02 — índice privado do serviço,
back-office efetivo (ERPNext ou fallback documentado) e backup/restore
isolado **com evidências**, sem usar dados de cliente nos testes.
Condições comerciais, preços, tributação, branding, destino e
autorização de publicação ainda requerem decisões do responsável.
O Qwen local deve receber só o comando específico que for realmente
indispensável; nenhuma configuração do TV Box por antecipação.

**Critério final:** pacote portátil CI verde prova somente que os
arquivos estão separados e íntegros. Não prova que o MXQ4K suporta
Linux, Caddy/HTTP, TLS, acesso externo ou uptime adequado.
