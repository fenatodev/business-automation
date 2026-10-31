#!/usr/bin/env bash
# =============================================================================
# Demo: Ciclo Completo Client 0
# =============================================================================
#
# Este script executa o ciclo comercial completo F2 usando apenas a API.
# Não depende de dados reais, n8n, Ollama ou serviços externos.
#
# Pré-requisitos:
#   1. API rodando em http://127.0.0.1:8000
#   2. Variáveis de ambiente configuradas:
#      - BA_ACCESS_IDENTITIES_JSON (tokens admin + operator)
#      - DATABASE_URL (PostgreSQL ou SQLite)
#      - BA_INTAKE_GENERATOR=static (para não depender do Ollama)
#
# Uso:
#   ./scripts/demo_client0_cycle.sh
#
# Ou, com API local:
#   BA_ACCESS_IDENTITIES_JSON='[...]' \
#   BA_INTAKE_GENERATOR=static \
#   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &
#   ./scripts/demo_client0_cycle.sh
#
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-demo-admin-token}"
OPERATOR_TOKEN="${OPERATOR_TOKEN:-demo-operator-token}"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ $1${NC}"
}

ok() {
    echo -e "  ${GREEN}✓ $1${NC}"
}

info() {
    echo -e "  ${YELLOW}ℹ $1${NC}"
}

fail() {
    echo -e "  ${RED}✗ $1${NC}"
    exit 1
}

# Helper: curl com tratamento de erro
curl_step() {
    local method="$1"
    local url="$2"
    local label="$3"
    shift 3
    local extra_args=("$@")

    local response
    response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$url" "${extra_args[@]}" 2>/dev/null) || {
        fail "Falha na conexão com $BASE_URL. A API está rodando?"
    }

    local http_code
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
        ok "$label (HTTP $http_code)"
        echo "$body"
    else
        fail "$label (HTTP $http_code): $body"
    fi
}

# =============================================================================
# Verificação inicial
# =============================================================================
step "VERIFICAÇÃO INICIAL"

HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" 2>/dev/null) || {
    fail "Não foi possível conectar a $BASE_URL. Inicie a API primeiro:"
    echo ""
    echo "  uv run uvicorn app.main:app --host 127.0.0.1 --port 8000"
    echo ""
    echo "Com tokens configurados:"
    echo "  export BA_ACCESS_IDENTITIES_JSON='[...]'  # ver README.md"
    echo "  export BA_INTAKE_GENERATOR=static"
}

if [[ "$HEALTH" == "200" ]]; then
    ok "API respondendo em $BASE_URL"
else
    fail "API retornou HTTP $HEALTH em /"
fi

# =============================================================================
# PASSO 1: Criar Company (Admin)
# =============================================================================
step "PASSO 1: CRIAR COMPANY (Admin)"

COMPANY_RESPONSE=$(curl_step POST "/companies" "Criar company 'Demo Client 0'" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "Demo Client 0", "slug": "demo-client-0"}')

COMPANY_ID=$(echo "$COMPANY_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
info "Company ID: $COMPANY_ID"

# =============================================================================
# PASSO 2: Criar Lead via Operator
# =============================================================================
step "PASSO 2: CRIAR LEAD (Operator)"

LEAD_RESPONSE=$(curl_step POST "/leads" "Criar lead 'Joia Automação Ltda'" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "company_id": '"$COMPANY_ID"',
        "name": "Joia Automação Ltda",
        "phone": "11999887766",
        "source": "website",
        "interest": "Automação de linha de produção com visão computacional"
    }')

LEAD_ID=$(echo "$LEAD_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
info "Lead ID: $LEAD_ID"

# =============================================================================
# PASSO 3: Criar Conversa vinculada ao Lead
# =============================================================================
step "PASSO 3: CRIAR CONVERSA (Operator)"

CONV_RESPONSE=$(curl_step POST "/conversations" "Criar conversa no WhatsApp" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "company_id": '"$COMPANY_ID"',
        "channel": "whatsapp",
        "lead_id": '"$LEAD_ID"'
    }')

CONV_ID=$(echo "$CONV_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
info "Conversation ID: $CONV_ID"

# =============================================================================
# PASSO 4: Adicionar Mensagens à Conversa
# =============================================================================
step "PASSO 4: ADICIONAR MENSAGENS (Operator)"

curl_step POST "/conversations/$CONV_ID/messages" "Mensagem do cliente" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"sender_type": "customer", "content": "Olá, preciso de uma cotação para automação da minha linha de montagem. Temos 3 máquinas que precisam de inspeção visual."}'

curl_step POST "/conversations/$CONV_ID/messages" "Resposta humana do operador" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"sender_type": "human", "content": "Olá! Vamos preparar uma proposta personalizada. Posso agendar uma visita técnica para entender melhor suas necessidades?"}'

# Listar mensagens
step "PASSO 4.1: LISTAR MENSAGENS"
MESSAGES=$(curl_step GET "/conversations/$CONV_ID/messages" "Listar mensagens da conversa" \
    -H "Authorization: Bearer $OPERATOR_TOKEN")

MSG_COUNT=$(echo "$MESSAGES" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
info "Total de mensagens: $MSG_COUNT"

# =============================================================================
# PASSO 5: Criar Oportunidade via Intake Comercial
# =============================================================================
step "PASSO 5: CRIAR OPORTUNIDADE VIA INTAKE (Operator)"

INTAKE_RESPONSE=$(curl_step POST "/internal/commercial-intake/create" "Intake: cotação automação" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "channel": "whatsapp",
        "message": "Cliente solicita cotação para automação de linha de produção com inspeção visual em 3 máquinas. Orçamento estimado R$50.000. Prazo: 60 dias.",
        "event_id": "demo-client0-001"
    }')

OPP_ID=$(echo "$INTAKE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['opportunity_id'])")
info "Opportunity ID: $OPP_ID"

# =============================================================================
# PASSO 6: Listar Oportunidades
# =============================================================================
step "PASSO 6: LISTAR OPORTUNIDADES (Operator)"

OPPS=$(curl_step GET "/opportunities" "Listar oportunidades" \
    -H "Authorization: Bearer $OPERATOR_TOKEN")

OPP_COUNT=$(echo "$OPPS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
info "Total de oportunidades: $OPP_COUNT"

# =============================================================================
# PASSO 7: Triagem — Marcar como "Preparar Proposta"
# =============================================================================
step "PASSO 7: TRIAGEM — PREPARAR PROPOSTA (Operator)"

curl_step PATCH "/opportunities/$OPP_ID/triage" "Triage: prepare_proposal" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "next_action": "prepare_proposal",
        "triage_note": "Cliente qualificado. Orçamento compatível com nossa faixa. Agendar visita técnica."
    }'

# =============================================================================
# PASSO 8: Criar Proposal Brief
# =============================================================================
step "PASSO 8: CRIAR PROPOSAL BRIEF (Operator)"

BRIEF_RESPONSE=$(curl_step POST "/opportunities/$OPP_ID/proposal-brief" "Criar proposal brief" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "offer_reference": "AUTO-2024-001",
        "diagnosis": "Linha de produção manual com 3 pontos de inspeção visual. Taxa de defeitos: 3.2%. Cliente busca redução para <0.5%.",
        "scope": "Instalação de sistema de visão computacional em 3 máquinas. Inclui câmeras, iluminação, processador e software de análise.",
        "deliverables": "1) Sistema de inspeção em 3 máquinas. 2) Dashboard de qualidade em tempo real. 3) Treinamento da equipe. 4) Suporte 90 dias.",
        "acceptance_criteria": "Taxa de defeitos <0.5% após 30 dias de operação. Tempo de inspeção <2s por peça.",
        "assumptions": "Cliente fornece acesso às máquinas em horário comercial. Infraestrutura elétrica existente.",
        "risks": "Compatibilidade com máquinas legadas. Necessidade de adaptação mecânica."
    }')

# =============================================================================
# PASSO 9: Colocar Brief para Revisão
# =============================================================================
step "PASSO 9: BRIEF PARA REVISÃO (Operator)"

curl_step PATCH "/opportunities/$OPP_ID/proposal-brief" "Brief: ready_for_review" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "offer_reference": "AUTO-2024-001",
        "diagnosis": "Linha de produção manual com 3 pontos de inspeção visual. Taxa de defeitos: 3.2%. Cliente busca redução para <0.5%.",
        "scope": "Instalação de sistema de visão computacional em 3 máquinas. Inclui câmeras, iluminação, processador e software de análise.",
        "deliverables": "1) Sistema de inspeção em 3 máquinas. 2) Dashboard de qualidade em tempo real. 3) Treinamento da equipe. 4) Suporte 90 dias.",
        "acceptance_criteria": "Taxa de defeitos <0.5% após 30 dias de operação. Tempo de inspeção <2s por peça.",
        "assumptions": "Cliente fornece acesso às máquinas em horário comercial. Infraestrutura elétrica existente.",
        "risks": "Compatibilidade com máquinas legadas. Necessidade de adaptação mecânica.",
        "status": "ready_for_review"
    }'

# =============================================================================
# PASSO 10: Aprovar Brief → Avança para In Progress
# =============================================================================
step "PASSO 10: APROVAR BRIEF → IN PROGRESS (Operator)"

curl_step PATCH "/opportunities/$OPP_ID/proposal-brief/approve" "Aprovar brief" \
    -H "Authorization: Bearer $OPERATOR_TOKEN"

# Verificar status da oportunidade
OPP_STATUS=$(curl -s -H "Authorization: Bearer $OPERATOR_TOKEN" "$BASE_URL/opportunities/$OPP_ID" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['next_action'])")
info "Opportunity next_action: $OPP_STATUS"

# =============================================================================
# PASSO 11: Converter Lead em Customer
# =============================================================================
step "PASSO 11: CONVERTER LEAD EM CUSTOMER (Operator)"

CUSTOMER_RESPONSE=$(curl_step POST "/leads/$LEAD_ID/convert" "Converter lead em customer" \
    -H "Authorization: Bearer $OPERATOR_TOKEN")

CUSTOMER_ID=$(echo "$CUSTOMER_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
info "Customer ID: $CUSTOMER_ID"

# =============================================================================
# PASSO 12: Criar Nova Conversa vinculada ao Customer
# =============================================================================
step "PASSO 12: CRIAR CONVERSA COM CUSTOMER (Operator)"

CONV2_RESPONSE=$(curl_step POST "/conversations" "Criar conversa com customer" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "company_id": '"$COMPANY_ID"',
        "channel": "email",
        "customer_id": '"$CUSTOMER_ID"'
    }')

CONV2_ID=$(echo "$CONV2_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
info "Conversation ID: $CONV2_ID"

curl_step POST "/conversations/$CONV2_ID/messages" "Mensagem de follow-up" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"sender_type": "human", "content": "Proposta AUTO-2024-001 enviada por email. Aguardando retorno do cliente."}'

# =============================================================================
# PASSO 13: Pipeline Summary
# =============================================================================
step "PASSO 13: PIPELINE SUMMARY (Operator)"

PIPELINE=$(curl_step GET "/opportunities/pipeline-summary" "Pipeline summary" \
    -H "Authorization: Bearer $OPERATOR_TOKEN")

info "Pipeline: $PIPELINE"

# =============================================================================
# PASSO 14: Fechar Oportunidade como Concluída
# =============================================================================
step "PASSO 14: FECHAR OPORTUNIDADE COMO CONCLUÍDA (Operator)"

curl_step PATCH "/opportunities/$OPP_ID/triage" "Triage: done" \
    -H "Authorization: Bearer $OPERATOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "next_action": "in_progress",
        "triage_note": "Projeto em execução. Instalação agendada para próxima semana."
    }'

# Nota: O schema atual não tem "done" no OpportunityTriageUpdate.
# Se "done" estiver disponível, descomentar:
# curl_step PATCH "/opportunities/$OPP_ID/triage" "Triage: done" \
#     -H "Authorization: Bearer $OPERATOR_TOKEN" \
#     -H "Content-Type: application/json" \
#     -d '{"next_action": "done", "triage_note": "Projeto concluído com sucesso. Taxa de defeitos: 0.3%."}'

# =============================================================================
# PASSO 15: Dashboard de Métricas
# =============================================================================
step "PASSO 15: DASHBOARD DE MÉTRICAS (Operator)"

DASHBOARD=$(curl -s -H "Authorization: Bearer $OPERATOR_TOKEN" "$BASE_URL/internal-tasks/dashboard" 2>/dev/null) || {
    info "Dashboard endpoint não disponível nesta versão"
}

if [[ -n "$DASHBOARD" ]]; then
    info "Dashboard: $DASHBOARD"
fi

# =============================================================================
# Resumo Final
# =============================================================================
step "RESUMO DO CICLO CLIENT 0"

echo -e "  ${GREEN}Company:${NC}     ID $COMPANY_ID — Demo Client 0"
echo -e "  ${GREEN}Lead:${NC}        ID $LEAD_ID — Joia Automação Ltda → convertido"
echo -e "  ${GREEN}Customer:${NC}    ID $CUSTOMER_ID — Joia Automação Ltda"
echo -e "  ${GREEN}Conversation:${NC} ID $CONV_ID — WhatsApp, $MSG_COUNT mensagens"
echo -e "  ${GREEN}Conversation:${NC} ID $CONV2_ID — Email, follow-up"
echo -e "  ${GREEN}Opportunity:${NC} ID $OPP_ID — Intake → Triage → Brief → Aprovado → In Progress"
echo ""
echo -e "  ${GREEN}Fluxo completo:${NC} Intake → Opportunity → Triage → Brief → Approve → In Progress"
echo -e "  ${GREEN}Lead flow:${NC}    Lead → Convert → Customer → Conversation"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Ciclo Client 0 concluído com sucesso!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
