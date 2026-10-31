"use strict";

// Piloto local: Bearer apenas em memória desta aba. Nunca logar ou persistir.
(() => {
  const $ = (id) => document.getElementById(id);

  let bearer = null;
  let sessionEpoch = 0;
  let reviewEpoch = 0;
  let reviewOffset = 0;
  const reviewPageSize = 50;
  let reviewTotal = 0;
  let opportunities = [];
  let selectedId = null;
  let oppOffset = 0;
  const oppPageSize = 50;
  let oppTotal = 0;
  let oppPipelineFilter = "all";
  const selectedOpportunityIds = new Set();
  let activeBrief = null;
  let selectionVersion = 0;
  let conversations = [];
  let selectedConvId = null;
  let convFilterChannel = "";
  let convFilterStatus = "";
  let convFilterQuery = "";
  let convFilterSort = "last_message";
  let convFilterFromDate = "";
  let convFilterToDate = "";
  let convOffset = 0;
  const convPageSize = 50;
  let convTotal = 0;
  const selectedConvIds = new Set();
  let msgOffset = 0;
  const msgPageSize = 50;
  let msgTotal = 0;
  let dashboardIntervalId = null;
  // WP-169/170 — Bulk delete state
  const selectedLeadIds = new Set();
  const selectedCustomerIds = new Set();
  // WP-171 — Bulk decision state for review queue
  const selectedRqIds = new Set();
  // WP-172 — Bulk retry state for internal tasks
  const selectedTaskIds = new Set();

  const briefFields = [
    "offer_reference",
    "diagnosis",
    "scope",
    "deliverables",
    "acceptance_criteria",
    "assumptions",
    "risks",
  ];
  const briefInputs = {
    offer_reference: "brief-offer",
    diagnosis: "brief-diagnosis",
    scope: "brief-scope",
    deliverables: "brief-deliverables",
    acceptance_criteria: "brief-acceptance",
    assumptions: "brief-assumptions",
    risks: "brief-risks",
  };
  // WP-092 — actionLabels must cover all OpportunityTriageUpdate values
  const actionLabels = {
    pending: "Pendente",
    ignore: "Ignorar",
    follow: "Acompanhar",
    prepare_proposal: "Preparar proposta",
    in_progress: "Em andamento",
    done: "Concluída",
    lost: "Perdida",
  };

  class ApiFailure extends Error {
    constructor(status) {
      super(
        status === 403 ? "A identidade não possui permissão de operador." :
        status === 409 ? "Conflito: registro duplicado ou transição inválida." :
        status === 422 ? "Dados inválidos. Revise os campos e tente novamente." :
        status === 404 ? "Registro não encontrado." :
        status === 503 ? "Serviço indisponível. Tente novamente depois." :
        "Operação não concluída (HTTP " + status + ")."
      );
      this.status = status;
    }
  }

  function notify(message, failure = false) {
    const notice = $("notice");
    notice.textContent = message;
    notice.classList.toggle("error", failure);
  }

  function clearSelection() {
    selectionVersion += 1;
    selectedId = null;
    activeBrief = null;
    $("selection-panel").hidden = true;
    $("brief-panel").hidden = true;
    $("brief-form").hidden = true;
    $("empty-panel").hidden = false;
    $("brief-form").reset();
    $("triage-form").reset();
    for (const id of (
      ["selected-id", "selected-source", "selected-url",
        "selected-budget", "selected-deadline", "selected-requirements",
        "selected-captured-at", "selected-triage-note"]
    )) {
      $(id).textContent = "";
    }
    // WP-093 — clear edit fields
    $("edit-title").value = "";
    $("edit-description").value = "";
    $("brief-guide").textContent = "";
    $("brief-status").textContent = "Sem brief";
  }

  function disconnect(message = "Acesso desconectado.") {
    sessionEpoch += 1;
    bearer = null;
    reviewEpoch += 1;
    reviewOffset = 0;
    reviewTotal = 0;
    oppOffset = 0;
    oppTotal = 0;
    $("rq-list").replaceChildren();
    $("rq-count").textContent = "—";
    $("rq-summary").textContent = "Resumo operacional indisponível.";
    $("rq-aging").textContent = "Atrasos: indisponível.";
    $("rq-form").reset();
    opportunities = [];
    clearSelection();
    $("workspace").hidden = true;
    $("access-status").textContent = "Desconectado";
    $("access-status").classList.remove("connected");
    $("access-form").reset();
    $("connect-button").hidden = false;
    $("disconnect-button").hidden = true;
    $("opportunity-list").replaceChildren();
    $("list-meta").textContent = "Nenhuma consulta realizada.";
    $("capture-form").reset();
    conversations = [];
    selectedConvId = null;
    convFilterChannel = "";
    convFilterStatus = "";
    convFilterQuery = "";
    convFilterSort = "last_message";
    convOffset = 0;
    convTotal = 0;
    msgOffset = 0;
    msgTotal = 0;
    oppPipelineFilter = "all";
    stopDashboardRefresh();
    stopNotificationRefresh();
    notify(message);
  }

  async function api(path, options = {}) {
    if (!bearer) {
      throw new Error("Conecte uma identidade de operador.");
    }
    // Somente caminhos internos fixos. Não aceitar URLs de anúncio como destino de fetch.
    // WP-093 — allow PATCH /opportunities/{id} for title/description edit
    // WP-094 — allow ?q= search param
    // WP-095 — allow /opportunities/count and sort/limit/offset params
    // WP-139 — allow /opportunities/pipeline-summary
    // WP-142 — allow /opportunities/{id}/conversations
    // WP-143 — allow /opportunities/{id}/timeline
    // WP-144 — allow /opportunities/{id}/leads
    if (!/^\/opportunities(\?[^"]*)?$/.test(path) &&
        !/^\/opportunities\/count(\?[^"]*)?$/.test(path) &&
        !/^\/opportunities\/pipeline-summary$/.test(path) &&
        !/^\/opportunities\/\d+(\/(triage|proposal-brief|conversations|leads|timeline)(\/approve|\/reject)?)?$/.test(path)) {
      throw new Error("Rota não permitida nesta interface.");
    }
    const epoch = sessionEpoch;
    const headers = { Authorization: "Bearer " + bearer };
    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    const response = await fetch(path, {
      method: options.method || "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer",
    });
    if (epoch !== sessionEpoch) {
      throw new Error("Sessão anterior encerrada.");
    }
    if (response.status === 401) {
      disconnect("Credencial inválida ou revogada. Conecte novamente.");
      throw new ApiFailure(401);
    }
    if (!response.ok) {
      throw new ApiFailure(response.status);
    }
    return response.json();
  }

  async function withButton(button, operation) {
    if (button.disabled) return;
    button.disabled = true;
    try {
      await operation();
    } catch (error) {
      notify(
        error instanceof ApiFailure || error instanceof TypeError
          ? (error instanceof TypeError ? "Não foi possível acessar a API local." : error.message)
          : "A operação falhou. Verifique a conexão e os campos.",
        true
      );
    } finally {
      button.disabled = false;
    }
  }

  function text(id, value, fallback = "Não informado") {
    $(id).textContent = value == null || value === "" ? fallback : String(value);
  }

  function showList() {
    const target = $("opportunity-list");
    target.replaceChildren();
    const ordered = [...opportunities].sort((a, b) => b.id - a.id);
    $("list-meta").textContent = ordered.length + " oportunidade(s) da sua empresa.";
    updateBulkTriageBar();
    if (!ordered.length) {
      const empty = document.createElement("p");
      empty.className = "small";
      empty.textContent = "Nenhuma oportunidade registrada.";
      target.append(empty);
      return;
    }
    for (const opportunity of ordered) {
      const wrapper = document.createElement("div");
      wrapper.className = "opp-item-row";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "opp-checkbox";
      checkbox.checked = selectedOpportunityIds.has(opportunity.id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          selectedOpportunityIds.add(opportunity.id);
        } else {
          selectedOpportunityIds.delete(opportunity.id);
        }
        updateBulkTriageBar();
      });
      const button = document.createElement("button");
      button.type = "button";
      button.className = "opportunity-item";
      button.classList.toggle("active", opportunity.id === selectedId);
      button.style.flex = "1";
      button.style.textAlign = "left";
      // WP-156 — Title row with id, title, and status badge
      const titleRow = document.createElement("div");
      titleRow.className = "opp-item-title-row";
      const title = document.createElement("strong");
      title.textContent = "#" + opportunity.id + " · " + opportunity.title;
      const stage = document.createElement("span");
      stage.className = "opp-status-badge opp-status-" + (opportunity.next_action || "unknown");
      stage.textContent = actionLabels[opportunity.next_action] || "Estado desconhecido";
      titleRow.append(title, stage);
      button.append(titleRow);
      // WP-156 — Description preview (truncated)
      if (opportunity.description) {
        const desc = document.createElement("span");
        desc.className = "opp-item-description";
        const truncated = opportunity.description.length > 120
          ? opportunity.description.substring(0, 120) + "…"
          : opportunity.description;
        desc.textContent = truncated;
        button.append(desc);
      }
      // WP-156 — Meta row with budget and deadline
      if (opportunity.budget || opportunity.deadline) {
        const meta = document.createElement("div");
        meta.className = "opp-item-meta";
        if (opportunity.budget) {
          const budgetSpan = document.createElement("span");
          budgetSpan.className = "opp-item-budget";
          budgetSpan.textContent = "💰 " + opportunity.budget;
          meta.append(budgetSpan);
        }
        if (opportunity.deadline) {
          const deadlineSpan = document.createElement("span");
          deadlineSpan.className = "opp-item-deadline";
          deadlineSpan.textContent = "📅 " + opportunity.deadline;
          meta.append(deadlineSpan);
        }
        button.append(meta);
      }
      button.addEventListener("click", (e) => {
        if (e.target === checkbox) return;
        selectOpportunity(opportunity.id).catch(() => {
          notify("Falha ao consultar o brief desta oportunidade.", true);
        });
      });
      wrapper.append(checkbox, button);
      target.append(wrapper);
    }
  }

  function readBriefForm() {
    const body = {};
    for (const name of briefFields) {
      const value = $(briefInputs[name]).value.trim();
      body[name] = value || (["assumptions", "risks"].includes(name) ? null : "");
    }
    return body;
  }

  function displayBrief(brief) {
    activeBrief = brief;
    $("brief-form").reset();
    for (const name of briefFields) {
      $(briefInputs[name]).value = brief?.[name] || "";
    }
    $("brief-form").hidden = false;
    const exists = Boolean(brief);
    $("brief-review-control").hidden = !exists;
    const statusActions = $("brief-actions");
    if (exists) {
      const showActions = brief.status === "ready_for_review" || brief.status === "approved";
      statusActions.hidden = !showActions;
      $("brief-approve").hidden = brief.status !== "ready_for_review";
      $("brief-reject").hidden = false;
    } else {
      statusActions.hidden = true;
    }
    const statusLabels = {
      draft: "Rascunho",
      ready_for_review: "Pronto para revisão",
      approved: "Aprovado",
    };
    $("brief-status").textContent = exists
      ? (statusLabels[brief.status] || brief.status)
      : "Ainda não criado";
    $("save-brief-button").textContent = exists ? "Salvar alterações" : "Criar rascunho";
    $("brief-guide").textContent = exists
      ? "Edite o diagnóstico e prepare a revisão interna."
      : "Preencha um brief interno. A criação inicial será um rascunho.";
    if (exists) {
      $("brief-state").value = brief.status;
    }
  }

  async function loadBrief(id, version) {
    try {
      const brief = await api("/opportunities/" + id + "/proposal-brief");
      if (selectionVersion === version) displayBrief(brief);
    } catch (error) {
      if (selectionVersion !== version) return;
      if (error instanceof ApiFailure && error.status === 404) {
        displayBrief(null);
        return;
      }
      $("brief-form").hidden = true;
      $("brief-status").textContent = "Consulta indisponível";
      notify("Não foi possível consultar o ProposalBrief.", true);
    }
  }

  async function selectOpportunity(id) {
    const record = opportunities.find((item) => item.id === id);
    if (!record) {
      clearSelection();
      showList();
      return;
    }
    selectionVersion += 1;
    const version = selectionVersion;
    selectedId = id;
    activeBrief = null;
    $("empty-panel").hidden = true;
    $("selection-panel").hidden = false;
    $("brief-panel").hidden = false;
    $("brief-form").hidden = true;
    $("brief-form").reset();
    text("selected-id", "#" + id);
    // WP-093 — populate edit fields
    $("edit-title").value = record.title;
    $("edit-description").value = record.description;
    text("selected-source", record.source || "");
    text("selected-captured-at", record.captured_at
      ? new Date(record.captured_at).toLocaleString("pt-BR") : "");
    text("selected-triage-note", record.triage_note || "");
    text("selected-url", record.external_url);
    text("selected-budget", record.budget);
    text("selected-deadline", record.deadline);
    text("selected-requirements", record.requirements);
    $("next-action").value = record.next_action;
    $("triage-note").value = record.triage_note || "";
    // WP-113 — populate standalone note editor
    $("opp-note").value = record.triage_note || "";
    $("brief-status").textContent = "Carregando";
    showList();

    // WP-108 — always attempt to load brief, regardless of status
    await loadBrief(id, version);
    // WP-142 — load related conversations
    await loadOpportunityConversations(id);
    // WP-143 — load activity timeline
    await loadOpportunityTimeline(id);
    // WP-144 — load related leads
    await loadOpportunityLeads(id);
  }

  // WP-142 — Load conversations related to the selected opportunity
  async function loadOpportunityConversations(id) {
    try {
      const conversations = await api("/opportunities/" + id + "/conversations");
      const list = $("opp-conv-list");
      list.replaceChildren();
      if (!conversations || !conversations.length) {
        const empty = document.createElement("p");
        empty.className = "small";
        empty.textContent = "Nenhuma conversa registrada.";
        list.appendChild(empty);
        return;
      }
      // WP-148 — Load message counts in parallel
      const counts = await Promise.all(
        conversations.map(async (conv) => {
          try {
            const result = await conversationApi("/conversations/" + conv.id + "/messages/count");
            return result ? result.total || 0 : 0;
          } catch (e) {
            return 0;
          }
        })
      );
      for (let idx = 0; idx < conversations.length; idx++) {
        const conv = conversations[idx];
        const item = document.createElement("div");
        item.className = "opp-conv-item";
        const title = document.createElement("strong");
        title.textContent = "#" + conv.id + " · " + conv.channel;
        const meta = document.createElement("span");
        meta.className = "small";
        const status = conv.status === "open" ? "Aberta" : "Fechada";
        meta.textContent = " " + status + " · " + counts[idx] + " msg";
        item.append(title, meta);
        item.addEventListener("click", () => {
          workspaceObserver.disconnect();
          selectedConvId = conv.id;
          refreshConversations().catch(() => {});
          selectConversation(conv.id).catch(() => {});
        });
        list.appendChild(item);
      }
    } catch (error) {
      $("opp-conv-list").replaceChildren();
    }
  }

  // WP-143 — Load activity timeline for the selected opportunity
  async function loadOpportunityTimeline(id) {
    try {
      const events = await api("/opportunities/" + id + "/timeline");
      const list = $("opp-timeline-list");
      list.replaceChildren();
      if (!events || !events.length) {
        const empty = document.createElement("p");
        empty.className = "small";
        empty.textContent = "Nenhuma atividade registrada.";
        list.appendChild(empty);
        return;
      }
      for (const event of events) {
        const item = document.createElement("div");
        item.className = "opp-timeline-item";
        const detail = document.createElement("span");
        detail.textContent = event.detail;
        const time = document.createElement("span");
        time.className = "small";
        time.textContent = new Date(event.timestamp).toLocaleString("pt-BR");
        item.append(detail, time);
        list.appendChild(item);
      }
    } catch (error) {
      // Silently fail — timeline is supplementary info
      $("opp-timeline-list").replaceChildren();
    }
  }

  // WP-144 — Load leads related to the selected opportunity
  async function loadOpportunityLeads(id) {
    try {
      const leads = await api("/opportunities/" + id + "/leads");
      const list = $("opp-leads-list");
      list.replaceChildren();
      if (!leads || !leads.length) {
        const empty = document.createElement("p");
        empty.className = "small";
        empty.textContent = "Nenhum lead registrado.";
        list.appendChild(empty);
        return;
      }
      for (const lead of leads) {
        const item = document.createElement("div");
        item.className = "opp-lead-item";
        const title = document.createElement("strong");
        title.textContent = lead.name || "Sem nome";
        const meta = document.createElement("span");
        meta.className = "small";
        const parts = [];
        if (lead.phone) parts.push(lead.phone);
        if (lead.source) parts.push("via " + lead.source);
        if (lead.status) parts.push("(" + lead.status + ")");
        meta.textContent = " " + parts.join(" · ");
        item.append(title, meta);
        item.addEventListener("click", () => {
          // Navigate to the leads section
          workspaceObserver.disconnect();
          refreshLeads().catch(() => {});
        });
        list.appendChild(item);
      }
    } catch (error) {
      // Silently fail — leads are supplementary info
      $("opp-leads-list").replaceChildren();
    }
  }

  async function refreshList(preferId = selectedId) {
    const showArchived = $("show-archived").checked;
    // WP-094 — opportunity search
    const searchQuery = $("opp-search").value.trim();
    // WP-095 — opportunity sort and pagination
    const sort = $("opp-sort").value;
    // WP-150 — date filter
    const fromDate = $("opp-from-date").value || null;
    const toDate = $("opp-to-date").value || null;
    const params = [];
    if (!showArchived) params.push("exclude_archived=true");
    if (oppPipelineFilter !== "all") params.push("next_action=" + encodeURIComponent(oppPipelineFilter));
    if (searchQuery) params.push("q=" + encodeURIComponent(searchQuery));
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    params.push("sort=" + encodeURIComponent(sort));
    params.push("limit=" + oppPageSize);
    params.push("offset=" + oppOffset);
    const query = "?" + params.join("&");
    const countParams = [];
    if (!showArchived) countParams.push("exclude_archived=true");
    if (oppPipelineFilter !== "all") countParams.push("next_action=" + encodeURIComponent(oppPipelineFilter));
    if (searchQuery) countParams.push("q=" + encodeURIComponent(searchQuery));
    if (fromDate) countParams.push("from_date=" + encodeURIComponent(fromDate));
    if (toDate) countParams.push("to_date=" + encodeURIComponent(toDate));
    const [result, countResult, pipelineResult] = await Promise.all([
      api("/opportunities" + query),
      api("/opportunities/count" + (countParams.length ? "?" + countParams.join("&") : "")),
      api("/opportunities/pipeline-summary"),
    ]);
    // WP-139 — update pipeline counts
    for (const [status, count] of Object.entries(pipelineResult || {})) {
      const countEl = document.querySelector('[data-count="' + status + '"]');
      if (countEl) countEl.textContent = count;
    }
    // Highlight active chip
    document.querySelectorAll('.opp-pipeline-chip').forEach((chip) => {
      chip.classList.toggle('active', chip.getAttribute('data-pipeline') === oppPipelineFilter);
    });
    if (!Array.isArray(result)) {
      throw new Error("Resposta de listagem inválida.");
    }
    opportunities = result;
    oppTotal = countResult.total || 0;
    // WP-091 — pending badge
    const pending = result.filter((o) => o.next_action === "pending").length;
    const badge = $("pending-badge");
    if (pending > 0) {
      badge.hidden = false;
      badge.textContent = pending;
    } else {
      badge.hidden = true;
    }
    // WP-095 — update pagination controls
    const pagination = $("opp-pagination");
    if (oppTotal > oppPageSize) {
      pagination.hidden = false;
      $("opp-prev").disabled = oppOffset === 0;
      $("opp-next").disabled = oppOffset + result.length >= oppTotal;
      $("opp-page").textContent = "Página " + (Math.floor(oppOffset / oppPageSize) + 1) + " de " + Math.ceil(oppTotal / oppPageSize);
    } else {
      pagination.hidden = true;
    }
    if (preferId !== null && opportunities.some((item) => item.id === preferId)) {
      await selectOpportunity(preferId);
    } else {
      clearSelection();
      showList();
    }
  }

  // WP-090 — Archive toggle
  $("show-archived").addEventListener("change", () => {
    oppOffset = 0;
    refreshList();
  });

  // WP-094 — Opportunity search
  $("opp-search").addEventListener("input", () => {
    oppOffset = 0;
    refreshList();
  });

  // WP-095 — Opportunity sort
  $("opp-sort").addEventListener("change", () => {
    oppOffset = 0;
    refreshList();
  });

  // WP-150 — Date filter
  $("opp-from-date").addEventListener("change", () => {
    oppOffset = 0;
    refreshList();
  });
  $("opp-to-date").addEventListener("change", () => {
    oppOffset = 0;
    refreshList();
  });

  // WP-150 — Clear all filters
  $("opp-clear-filters").addEventListener("click", () => {
    $("opp-search").value = "";
    $("opp-from-date").value = "";
    $("opp-to-date").value = "";
    $("opp-sort").value = "id";
    $("show-archived").checked = false;
    oppPipelineFilter = "all";
    document.querySelectorAll('.opp-pipeline-chip').forEach((chip) => {
      chip.classList.toggle('active', chip.getAttribute('data-pipeline') === "all");
    });
    oppOffset = 0;
    refreshList();
  });

  // WP-139 — Pipeline filter chips
  document.querySelectorAll('.opp-pipeline-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      oppPipelineFilter = chip.getAttribute('data-pipeline');
      oppOffset = 0;
      refreshList();
    });
  });

  // WP-108 — View brief button scrolls to brief panel
  $("view-brief-button").addEventListener("click", () => {
    const panel = $("brief-panel");
    if (panel) {
      panel.hidden = false;
      panel.scrollIntoView({behavior: "smooth", block: "start"});
    }
  });

  // WP-095 — Opportunity pagination
  $("opp-prev").addEventListener("click", () => withButton($("opp-prev"), async () => {
    oppOffset = Math.max(0, oppOffset - oppPageSize);
    await refreshList();
  }));
  $("opp-next").addEventListener("click", () => withButton($("opp-next"), async () => {
    oppOffset += oppPageSize;
    await refreshList();
  }));

  // WP-113 — Save opportunity note independently
  $("save-opp-note").addEventListener("click", async () => {
    if (selectedId === null) return;
    const triageNote = $("opp-note").value;
    try {
      const updated = await api("/opportunities/" + selectedId, {
        method: "PATCH",
        body: { triage_note: triageNote.trim() || null },
      });
      const idx = opportunities.findIndex((o) => o.id === selectedId);
      if (idx !== -1) {
        opportunities[idx] = updated;
      }
      $("triage-note").value = updated.triage_note || "";
      $("opp-note").value = updated.triage_note || "";
      notify("Nota salva.");
    } catch (error) {
      if (error instanceof ApiFailure) {
        notify(error.message, true);
      } else {
        notify("Falha ao salvar nota.", true);
      }
    }
  });

  // WP-093 — Save opportunity title/description edit
  $("save-edit-button").addEventListener("click", async () => {
    if (selectedId === null) return;
    const title = $("edit-title").value.trim();
    const description = $("edit-description").value.trim();
    if (!title) {
      notify("Título não pode estar vazio.", true);
      return;
    }
    if (!description) {
      notify("Descrição não pode estar vazia.", true);
      return;
    }
    try {
      const updated = await api("/opportunities/" + selectedId, {
        method: "PATCH",
        body: { title, description },
      });
      // Update in-memory list
      const idx = opportunities.findIndex((o) => o.id === selectedId);
      if (idx !== -1) {
        opportunities[idx] = updated;
      }
      $("edit-title").value = updated.title;
      $("edit-description").value = updated.description;
      notify("Oportunidade atualizada.");
      // Re-render list to reflect title changes
      showList();
    } catch (error) {
      if (error instanceof ApiFailure) {
        notify(error.message, true);
      } else {
        notify("Falha ao salvar alterações.", true);
      }
    }
  });


  // Review queue uses the same in-memory Bearer session, with a strict route allowlist.
  async function reviewApi(path, method = "GET", body) {
    if (!bearer) throw new Error("Conecte um operador.");
    const route = path.split("#")[0];
    if (!(/^\/review-queue\/(\?|$)/.test(route) ||
          /^\/review-queue\/summary$/.test(route) ||
          /^\/review-queue\/aging$/.test(route) ||
          /^\/review-queue\/count(\?|$)/.test(route) ||
          /^\/review-queue\/synthetic-trigger$/.test(route) ||
          /^\/review-queue\/bulk-decision$/.test(route) ||
          /^\/review-queue\/\d+\/decision$/.test(route))) {
      throw new Error("Rota de revisão não permitida.");
    }
    const epoch = sessionEpoch;
    const headers = {Authorization: "Bearer " + bearer};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "omit", cache: "no-store", redirect: "error", referrerPolicy: "no-referrer"});
    if (epoch !== sessionEpoch) throw new Error("Sessão encerrada.");
    if (response.status === 401) {
      disconnect("Credencial inválida.");
      throw new ApiFailure(401);
    }
    if (!response.ok) throw new ApiFailure(response.status);
    return response.json();
  }
  function buildReviewUrl() {
    const params = new URLSearchParams();
    params.set("limit", reviewPageSize);
    params.set("offset", reviewOffset);
    const status = $("rq-status-filter")?.value?.trim();
    if (status) params.set("status", status);
    // WP-154 — date filter
    const fromDate = $("rq-from-date")?.value;
    if (fromDate) params.set("from_date", fromDate);
    const toDate = $("rq-to-date")?.value;
    if (toDate) params.set("to_date", toDate);
    const sort = $("rq-sort")?.value?.trim();
    if (sort) params.set("sort", sort);
    return "/review-queue/?" + params.toString();
  }
  function buildReviewCountUrl() {
    const params = [];
    const status = $("rq-status-filter")?.value?.trim();
    if (status) params.push("status=" + encodeURIComponent(status));
    // WP-154 — date filter
    const fromDate = $("rq-from-date")?.value;
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    const toDate = $("rq-to-date")?.value;
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    return "/review-queue/count" + (params.length ? "?" + params.join("&") : "");
  }
  async function refreshReviewQueue() {
    const epoch = ++reviewEpoch;
    const [items, summary, aging, countData] = await Promise.all([
      reviewApi(buildReviewUrl()),
      reviewApi("/review-queue/summary"),
      reviewApi("/review-queue/aging"),
      reviewApi(buildReviewCountUrl()),
    ]);
    if (epoch !== reviewEpoch) return;
    if (!Array.isArray(items)) throw new Error("Fila inválida.");
    reviewTotal = countData?.total || 0;
    $("rq-count").textContent = summary.pending + " pendente(s)";
    $("rq-prev").disabled = reviewOffset === 0;
    $("rq-next").disabled = reviewOffset + items.length >= reviewTotal;
    $("rq-page").textContent = "Página " + (Math.floor(reviewOffset / reviewPageSize) + 1);
    $("rq-summary").textContent = "Pendentes: " + summary.pending +
      " · Aprovados: " + summary.approve + " · Rejeitados: " + summary.reject;
    $("rq-aging").textContent = "Pendentes há mais de 24h: " + aging.overdue_pending;
    // WP-171 — Reset bulk selection on refresh
    selectedRqIds.clear();
    $("rq-bulk-bar").hidden = true;
    const list = $("rq-list");
    list.replaceChildren();
    for (const item of items) {
      const card = document.createElement("article");
      card.className = "review-card";
      // WP-171 — Checkbox for bulk decision
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "rq-checkbox";
      checkbox.checked = selectedRqIds.has(item.id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          selectedRqIds.add(item.id);
        } else {
          selectedRqIds.delete(item.id);
        }
        updateRqBulkBar();
      });
      card.appendChild(checkbox);
      const heading = document.createElement("strong");
      heading.textContent = "#" + item.id + " · " + (item.intent || "Triagem");
      const meta = document.createElement("p");
      meta.className = "small";
      meta.textContent = "Evento: " + item.event_id + " · " + (item.channel || "web");
      const message = document.createElement("p");
      message.className = "readout";
      message.textContent = item.message || "Sem mensagem";
      const label = document.createElement("strong");
      label.textContent = "Rascunho";
      const draft = document.createElement("p");
      draft.className = "readout";
      draft.textContent = item.draft_reply || "Sem rascunho";
      const note = document.createElement("textarea");
      note.maxLength = 2000;
      note.rows = 2;
      note.placeholder = "Nota da decisão (opcional)";
      note.setAttribute("aria-label", "Nota para item " + item.id);
      const actions = document.createElement("div");
      actions.className = "review-actions";
      for (const decision of ["approve", "reject"]) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = decision === "approve" ? "primary" : "secondary";
        button.textContent = decision === "approve" ? "Aprovar internamente" : "Rejeitar";
        button.addEventListener("click", () => withButton(button, async () => {
          const result = await reviewApi("/review-queue/" + item.id + "/decision", "PATCH",
            {decision, operator_note: note.value.trim() || null});
          await refreshReviewQueue();
          if (result.opportunity_id) {
            await refreshList(result.opportunity_id);
            notify("Decisão registrada. Oportunidade #" + result.opportunity_id + " criada.");
          } else {
            notify("Decisão registrada. Nenhuma mensagem enviada.");
          }
        }));
        actions.append(button);
      }
      card.append(heading, meta, message, label, draft, note, actions);
      list.append(card);
    }
    if (!items.length) {
      const p = document.createElement("p");
      p.className = "small";
      p.textContent = "Nenhum item pendente.";
      list.append(p);
    }
  }
  $("rq-refresh").addEventListener("click", () => withButton($("rq-refresh"), refreshReviewQueue));
  $("rq-prev").addEventListener("click", () => withButton($("rq-prev"), async () => {
    reviewOffset = Math.max(0, reviewOffset - reviewPageSize);
    await refreshReviewQueue();
  }));
  $("rq-next").addEventListener("click", () => withButton($("rq-next"), async () => {
    reviewOffset += reviewPageSize;
    await refreshReviewQueue();
  }));
  $("rq-status-filter").addEventListener("change", () => {
    reviewOffset = 0;
    refreshReviewQueue();
  });
  $("rq-sort").addEventListener("change", () => {
    reviewOffset = 0;
    refreshReviewQueue();
  });
  $("rq-clear-filters").addEventListener("click", () => {
    $("rq-status-filter").value = "";
    $("rq-sort").value = "created_at";
    // WP-154 — clear date filters
    $("rq-from-date").value = "";
    $("rq-to-date").value = "";
    reviewOffset = 0;
    refreshReviewQueue();
  });
  // WP-154 — review queue date filter listeners
  $("rq-from-date").addEventListener("change", () => {
    reviewOffset = 0;
    refreshReviewQueue();
  });
  $("rq-to-date").addEventListener("change", () => {
    reviewOffset = 0;
    refreshReviewQueue();
  });
  $("rq-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const button = $("rq-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const event_id = $("rq-event").value.trim();
      const message = $("rq-message").value.trim();
      const channel = $("rq-channel").value;
      if (!event_id || !message) {notify("Preencha os campos.", true); return;}
      await reviewApi("/review-queue/synthetic-trigger", "POST", {event_id, message, channel});
      await refreshReviewQueue();
      notify("Entrada sintética processada; sem envio externo.");
    });
  });
  $("access-form").addEventListener("submit", (event) => {
    event.preventDefault();
    withButton($("connect-button"), async () => {
      const input = $("operator-token");
      const secret = input.value.trim();
      input.value = "";
      if (!secret) {
        notify("Informe um token de operador.", true);
        return;
      }
      sessionEpoch += 1;
      bearer = secret;
      try {
        await Promise.all([refreshList(null), refreshReviewQueue()]);
        $("workspace").hidden = false;
        $("access-status").textContent = "Conectado";
        $("access-status").classList.add("connected");
        $("connect-button").hidden = true;
        $("disconnect-button").hidden = false;
        startDashboardRefresh();
        startNotificationRefresh();
        notify("Conectado. O acesso será descartado ao fechar ou recarregar a aba.");
      } catch (error) {
        disconnect("Não foi possível conectar. Use uma credencial de operador válida.");
      }
    });
  });

  $("disconnect-button").addEventListener("click", () => disconnect());
  window.addEventListener("pagehide", () => disconnect("Sessão encerrada."));

  // WP-163 — Theme toggle (dark/light)
  (function initTheme() {
    const toggle = $("theme-toggle");
    if (!toggle) return;

    function setTheme(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      try { localStorage.setItem("operator-theme", theme); } catch (e) { /* ignore */ }
      toggle.textContent = theme === "light" ? "☀️" : "🌙";
    }

    // Load saved theme or default to dark
    let saved = "dark";
    try { saved = localStorage.getItem("operator-theme") || "dark"; } catch (e) { /* ignore */ }
    setTheme(saved);

    toggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme");
      setTheme(current === "light" ? "dark" : "light");
    });
  })();

  // WP-146, WP-168 — Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    // Don't trigger shortcuts when typing in inputs
    const tag = e.target.tagName;
    const isInput = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";

    // Ctrl+K / Cmd+K: focus opportunity search
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      const searchInput = $("opp-search");
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    }

    // WP-168 — Ctrl+N: show create lead form
    if ((e.ctrlKey || e.metaKey) && e.key === "n" && !isInput) {
      e.preventDefault();
      const createBtn = $("show-create-lead");
      if (createBtn) {
        createBtn.click();
      }
    }

    // WP-168 — Ctrl+L: focus lead search
    if ((e.ctrlKey || e.metaKey) && e.key === "l" && !isInput) {
      e.preventDefault();
      const leadSearch = $("lead-search");
      if (leadSearch) {
        leadSearch.focus();
        leadSearch.select();
      }
    }

    // WP-168 — Ctrl+Shift+C: focus customer search
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "C" && !isInput) {
      e.preventDefault();
      const custSearch = $("customer-search");
      if (custSearch) {
        custSearch.focus();
        custSearch.select();
      }
    }

    // WP-168 — / : focus opportunity search (when not in input)
    if (e.key === "/" && !isInput) {
      e.preventDefault();
      const searchInput = $("opp-search");
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    }

    // Escape: clear selection
    if (e.key === "Escape" && !isInput) {
      clearSelection();
      showList();
    }

    // Enter in triage form: submit triage (handled by form submit, but prevent double-submit)
    if (e.key === "Enter" && isInput) {
      // Let the form handle it naturally
      return;
    }
  });

  $("refresh-button").addEventListener("click", () => {
    withButton($("refresh-button"), async () => {
      await refreshList();
      notify("Oportunidades atualizadas.");
    });
  });

  $("capture-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const button = $("capture-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const form = $("capture-form");
      const fields = Object.fromEntries(new FormData(form).entries());
      const opportunity = await api("/opportunities", {
        method: "POST",
        body: {
          source: fields.source || "manual",
          external_url: fields.external_url.trim(),
          title: fields.title.trim(),
          description: fields.description.trim(),
          requirements: fields.requirements.trim() || null,
          budget: fields.budget.trim() || null,
          deadline: fields.deadline.trim() || null,
          captured_at: new Date().toISOString(),
        },
      });
      form.reset();
      await refreshList(opportunity.id);
      notify("Oportunidade #" + opportunity.id + " registrada. Faça a triagem.");
    });
  });

  $("triage-form").addEventListener("submit", (event) => {
    event.preventDefault();
    withButton($("triage-form").querySelector('button[type="submit"]'), async () => {
      if (selectedId === null) return;
      const id = selectedId;
      await api("/opportunities/" + id + "/triage", {
        method: "PATCH",
        body: {
          next_action: $("next-action").value,
          triage_note: $("triage-note").value.trim() || null,
        },
      });
      await refreshList(id);
      notify("Triagem da oportunidade #" + id + " atualizada.");
    });
  });

  $("brief-form").addEventListener("submit", (event) => {
    event.preventDefault();
    withButton($("save-brief-button"), async () => {
      if (selectedId === null) return;
      const id = selectedId;
      const exists = Boolean(activeBrief);
      const payload = readBriefForm();
      if (exists) {
        payload.status = $("brief-state").value;
      }
      await api("/opportunities/" + id + "/proposal-brief", {
        method: exists ? "PATCH" : "POST",
        body: payload,
      });
      await refreshList(id);
      notify(
        exists ? "Brief atualizado para revisão interna." :
          "Rascunho criado. Revise antes de marcar como pronto."
      );
    });
  });

  // Brief approve — WP-084
  $("brief-approve").addEventListener("click", () => withButton($("brief-approve"), async () => {
    if (selectedId === null) return;
    const id = selectedId;
    await api("/opportunities/" + id + "/proposal-brief/approve", {
      method: "PATCH",
    });
    await refreshList(id);
    notify("Brief aprovado. Oportunidade avançada para em andamento.");
  }));

  // Brief reject — WP-084
  $("brief-reject").addEventListener("click", () => withButton($("brief-reject"), async () => {
    if (selectedId === null) return;
    const id = selectedId;
    await api("/opportunities/" + id + "/proposal-brief/reject", {
      method: "PATCH",
    });
    await refreshList(id);
    notify("Brief rejeitado. Voltado para rascunho.");
  }));

  // Conversations — strict allowlist, same pattern as reviewApi/taskApi.
  async function conversationApi(path, method = "GET", body) {
    if (!bearer) throw new Error("Conecte um operador.");
    if (!(/^\/companies\/\d+\/conversations($|\?)/.test(path) ||
          /^\/companies\/\d+\/conversations\/count($|\?)/.test(path) ||
          /^\/conversations\/$/.test(path) ||
          /^\/conversations\/\d+\/$/.test(path) ||
          /^\/conversations\/\d+\/messages(\/count)?(\?|$)/.test(path) ||
          /^\/conversations\/\d+\/note$/.test(path) ||
          /^\/conversations\/bulk-status$/.test(path))) {
      throw new Error("Rota de conversas não permitida.");
    }
    const epoch = sessionEpoch;
    const headers = {Authorization: "Bearer " + bearer};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "omit", cache: "no-store", redirect: "error", referrerPolicy: "no-referrer"});
    if (epoch !== sessionEpoch) throw new Error("Sessão encerrada.");
    if (response.status === 401) {
      disconnect("Credencial inválida.");
      throw new ApiFailure(401);
    }
    if (!response.ok) throw new ApiFailure(response.status);
    return response.json();
  }

  // Human reply — strict allowlist for conversation messages.
  async function replyApi(path, method = "GET", body) {
    if (!bearer) throw new Error("Conecte um operador.");
    if (!(/^\/conversations\/\d+\/messages$/.test(path))) {
      throw new Error("Rota de resposta não permitida.");
    }
    const epoch = sessionEpoch;
    const headers = {Authorization: "Bearer " + bearer};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "omit", cache: "no-store", redirect: "error", referrerPolicy: "no-referrer"});
    if (epoch !== sessionEpoch) throw new Error("Sessão encerrada.");
    if (response.status === 401) {
      disconnect("Credencial inválida.");
      throw new ApiFailure(401);
    }
    if (!response.ok) throw new ApiFailure(response.status);
    return response.json();
  }

  const channelLabels = {
    whatsapp: "WhatsApp",
    instagram: "Instagram",
    web: "Web",
    telegram: "Telegram",
    email: "E-mail",
  };

  const senderLabels = {
    customer: "Cliente",
    agent: "Agente",
    human: "Humano",
    system: "Sistema",
  };

  function buildConversationUrl(companyId) {
    const params = new URLSearchParams();
    if (convFilterChannel) params.set("channel", convFilterChannel);
    if (convFilterStatus) params.set("status", convFilterStatus);
    if (convFilterQuery) params.set("q", convFilterQuery);
    if (convFilterFromDate) params.set("from_date", convFilterFromDate);
    if (convFilterToDate) params.set("to_date", convFilterToDate);
    params.set("sort", convFilterSort);
    params.set("limit", String(convPageSize));
    params.set("offset", String(convOffset));
    return "/companies/" + companyId + "/conversations?" + params.toString();
  }

  function buildConversationCountUrl(companyId) {
    const params = new URLSearchParams();
    if (convFilterChannel) params.set("channel", convFilterChannel);
    if (convFilterStatus) params.set("status", convFilterStatus);
    if (convFilterQuery) params.set("q", convFilterQuery);
    if (convFilterFromDate) params.set("from_date", convFilterFromDate);
    if (convFilterToDate) params.set("to_date", convFilterToDate);
    const query = params.toString();
    return "/companies/" + companyId + "/conversations/count" + (query ? "?" + query : "");
  }

  function showConversationList() {
    const target = $("conv-list");
    target.replaceChildren();
    // Backend already returns sorted results; no client-side sort needed.
    if (!conversations.length) {
      const empty = document.createElement("p");
      empty.className = "small";
      empty.textContent = convFilterChannel || convFilterStatus || convFilterQuery
        ? "Nenhuma conversa corresponde aos filtros."
        : "Nenhuma conversa registrada.";
      target.append(empty);
      return;
    }
    for (const conv of conversations) {
      const row = document.createElement("div");
      row.className = "conv-item-row";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "conv-checkbox";
      checkbox.checked = selectedConvIds.has(conv.id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          selectedConvIds.add(conv.id);
        } else {
          selectedConvIds.delete(conv.id);
        }
        updateConvBulkBar();
      });
      row.append(checkbox);

      const button = document.createElement("button");
      button.type = "button";
      button.className = "conversation-item";
      button.classList.toggle("active", conv.id === selectedConvId);
      const channel = channelLabels[conv.channel] || conv.channel;
      const title = document.createElement("strong");
      title.textContent = "#" + conv.id + " · " + channel;
      const meta = document.createElement("span");
      meta.className = "conv-status-badge conv-status-" + (conv.status || "unknown");
      meta.textContent = conv.status || "—";
      button.append(title, meta);
      button.addEventListener("click", () => {
        selectConversation(conv.id).catch(() => {
          notify("Falha ao carregar mensagens desta conversa.", true);
        });
      });
      row.append(button);
      target.append(row);
    }
  }

  function updateConvBulkBar() {
    const bar = $("conv-bulk-bar");
    if (selectedConvIds.size > 0) {
      bar.hidden = false;
      $("conv-bulk-count").textContent = selectedConvIds.size + " selecionadas";
    } else {
      bar.hidden = true;
    }
  }

  async function selectConversation(id) {
    selectedConvId = id;
    msgOffset = 0;
    showConversationList();
    $("conv-detail").hidden = false;
    $("conv-reply-toggle").hidden = false;
    $("conv-close-toggle").hidden = false;
    $("conv-note-section").hidden = false;
    // WP-147 — Show create lead button
    $("conv-create-lead").hidden = false;
    $("conv-lead-form").hidden = true;
    $("reply-conv-id").value = id;
    const conv = conversations.find((c) => c.id === id);
    const channel = conv ? (channelLabels[conv.channel] || conv.channel) : "Conversa";
    $("conv-detail-header").textContent = channel + " · #" + id;
    await loadMessages(id);
    // WP-140 — Load internal note
    await loadConversationNote(id);
  }

  async function loadMessages(id) {
    try {
      const [messages, countResult] = await Promise.all([
        conversationApi("/conversations/" + id + "/messages?limit=" + msgPageSize + "&offset=" + msgOffset),
        conversationApi("/conversations/" + id + "/messages/count?limit=" + msgPageSize + "&offset=" + msgOffset),
      ]);
      if (selectedConvId !== id) return;
      msgTotal = countResult.total || 0;
      const target = $("conv-messages");
      target.replaceChildren();
      if (!messages.length) {
        const empty = document.createElement("p");
        empty.className = "small";
        empty.textContent = "Nenhuma mensagem.";
        target.append(empty);
      } else {
        for (const msg of messages) {
          const bubble = document.createElement("div");
          bubble.className = "message-bubble";
          bubble.classList.add(msg.sender_type);
          const header = document.createElement("span");
          header.className = "message-sender";
          header.textContent = senderLabels[msg.sender_type] || msg.sender_type;
          const content = document.createElement("p");
          content.className = "message-content";
          content.textContent = msg.content || "";
          bubble.append(header, content);
          target.append(bubble);
        }
      }
      updateMessagePagination();
    } catch (error) {
      if (selectedConvId !== id) return;
      notify("Não foi possível carregar as mensagens.", true);
    }
  }

  function updateMessagePagination() {
    const pagination = $("msg-pagination");
    if (!pagination) return;
    const totalPages = Math.max(1, Math.ceil(msgTotal / msgPageSize));
    const currentPage = Math.floor(msgOffset / msgPageSize) + 1;
    if (msgTotal <= msgPageSize) {
      pagination.hidden = true;
    } else {
      pagination.hidden = false;
      $("msg-prev").disabled = msgOffset === 0;
      $("msg-next").disabled = msgOffset + msgPageSize >= msgTotal;
      $("msg-page").textContent = "Página " + currentPage + " de " + totalPages + " (" + msgTotal + ")";
    }
  }

  // WP-140 — Conversation internal notes
  async function loadConversationNote(id) {
    try {
      const result = await conversationApi("/conversations/" + id + "/note");
      if (selectedConvId !== id) return;
      $("conv-note-text").value = result.note || "";
      $("conv-note-status").textContent = "";
    } catch (error) {
      $("conv-note-text").value = "";
      $("conv-note-status").textContent = "";
    }
  }

  $("conv-note-save").addEventListener("click", () => withButton($("conv-note-save"), async () => {
    if (selectedConvId === null) return;
    const note = $("conv-note-text").value;
    try {
      await conversationApi("/conversations/" + selectedConvId, "PATCH", { note });
      $("conv-note-status").textContent = "Nota salva.";
      $("conv-note-status").style.color = "var(--success)";
      setTimeout(() => { $("conv-note-status").textContent = ""; }, 3000);
    } catch (error) {
      notify("Falha ao salvar nota.", true);
    }
  }));

  // WP-147 — Create lead from conversation
  $("conv-create-lead").addEventListener("click", () => {
    $("conv-lead-form").hidden = false;
    $("conv-create-lead").hidden = true;
    // Pre-fill source from conversation channel
    const conv = conversations.find((c) => c.id === selectedConvId);
    if (conv) {
      $("conv-lead-source").value = conv.channel || "";
    }
  });

  $("cancel-conv-lead").addEventListener("click", () => {
    $("conv-lead-form").hidden = true;
    $("conv-create-lead").hidden = false;
    $("conv-lead-name").value = "";
    $("conv-lead-phone").value = "";
    $("conv-lead-source").value = "";
    $("conv-lead-interest").value = "";
  });

  $("conv-lead-form").addEventListener("submit", (event) => {
    event.preventDefault();
    withButton(event.submitter, async () => {
      const name = $("conv-lead-name").value.trim();
      const phone = $("conv-lead-phone").value.trim() || null;
      const source = $("conv-lead-source").value.trim() || null;
      const interest = $("conv-lead-interest").value.trim() || null;
      if (!name) { notify("Nome é obrigatório.", true); return; }
      try {
        await leadApi("/leads", "POST", { name, phone, source, interest });
        notify("Lead criado a partir da conversa.");
        $("conv-lead-form").hidden = true;
        $("conv-create-lead").hidden = false;
        $("conv-lead-name").value = "";
        $("conv-lead-phone").value = "";
        $("conv-lead-source").value = "";
        $("conv-lead-interest").value = "";
        await refreshLeads();
      } catch (error) {
        notify("Falha ao criar lead.", true);
      }
    });
  });

  // WP-141 — Bulk conversation status
  $("conv-bulk-apply").addEventListener("click", () => withButton($("conv-bulk-apply"), async () => {
    if (selectedConvIds.size === 0) return;
    const status = $("conv-bulk-action").value;
    try {
      const result = await conversationApi("/conversations/bulk-status", "POST", {
        conversation_ids: Array.from(selectedConvIds),
        status,
      });
      notify(result.updated + " conversa(s) atualizada(s).");
      selectedConvIds.clear();
      updateConvBulkBar();
      await refreshConversations();
    } catch (error) {
      notify("Falha ao atualizar conversas.", true);
    }
  }));

  $("conv-bulk-clear").addEventListener("click", () => {
    selectedConvIds.clear();
    updateConvBulkBar();
    showConversationList();
  });

  async function refreshConversations() {
    try {
      const company = opportunities.length > 0 ? opportunities[0].company_id : null;
      if (company) {
        const [convs, countResult] = await Promise.all([
          conversationApi(buildConversationUrl(company)),
          conversationApi(buildConversationCountUrl(company)),
        ]);
        conversations = convs;
        convTotal = countResult.total || 0;
        // WP-175 — update open conversations badge
        const openConvs = convs.filter((c) => c.status === "open").length;
        const convBadge = $("conv-open-badge");
        if (openConvs > 0) { convBadge.hidden = false; convBadge.textContent = openConvs; }
        else { convBadge.hidden = true; }
      } else {
        conversations = [];
        convTotal = 0;
      }
    } catch (error) {
      conversations = [];
      convTotal = 0;
    }
    showConversationList();
    updateConversationPagination();
    if (selectedConvId !== null && conversations.some((c) => c.id === selectedConvId)) {
      await selectConversation(selectedConvId);
    } else if (selectedConvId !== null) {
      selectedConvId = null;
      $("conv-detail").hidden = true;
      $("conv-reply-toggle").hidden = true;
      $("conv-close-toggle").hidden = true;
      $("human-reply-form").hidden = true;
      $("conv-note-section").hidden = true;
      // WP-147
      $("conv-create-lead").hidden = true;
      $("conv-lead-form").hidden = true;
      selectedConvIds.clear();
      updateConvBulkBar();
      showConversationList();
    }
  }

  function updateConversationPagination() {
    const pagination = $("conv-pagination");
    const totalPages = Math.max(1, Math.ceil(convTotal / convPageSize));
    const currentPage = Math.floor(convOffset / convPageSize) + 1;
    if (convTotal <= convPageSize) {
      pagination.hidden = true;
    } else {
      pagination.hidden = false;
      $("conv-prev").disabled = convOffset === 0;
      $("conv-next").disabled = convOffset + conversations.length >= convTotal;
      $("conv-page").textContent = "Página " + currentPage + " de " + totalPages + " (" + convTotal + ")";
    }
  }

  function clearConversationFilters() {
    convFilterChannel = "";
    convFilterStatus = "";
    convFilterQuery = "";
    convFilterSort = "last_message";
    convFilterFromDate = "";
    convFilterToDate = "";
    convOffset = 0;
    $("conv-filter-channel").value = "";
    $("conv-filter-status").value = "";
    $("conv-search-q").value = "";
    $("conv-filter-sort").value = "last_message";
    $("conv-from-date").value = "";
    $("conv-to-date").value = "";
    refreshConversations().catch(() => {});
  }

  // Filter event listeners (reset offset on filter change)
  $("conv-filter-channel").addEventListener("change", (e) => {
    convFilterChannel = e.target.value;
    convOffset = 0;
    refreshConversations().catch(() => {});
  });

  $("conv-filter-status").addEventListener("change", (e) => {
    convFilterStatus = e.target.value;
    convOffset = 0;
    refreshConversations().catch(() => {});
  });

  $("conv-search-btn").addEventListener("click", () => {
    convFilterQuery = $("conv-search-q").value.trim();
    convOffset = 0;
    refreshConversations().catch(() => {});
  });

  $("conv-search-q").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      convFilterQuery = $("conv-search-q").value.trim();
      convOffset = 0;
      refreshConversations().catch(() => {});
    }
  });

  $("conv-clear-filter").addEventListener("click", () => {
    clearConversationFilters();
  });

  $("conv-filter-sort").addEventListener("change", (e) => {
    convFilterSort = e.target.value;
    convOffset = 0;
    refreshConversations().catch(() => {});
  });

  // WP-151 — Date filter
  $("conv-from-date").addEventListener("change", (e) => {
    convFilterFromDate = e.target.value;
    convOffset = 0;
    refreshConversations().catch(() => {});
  });

  $("conv-to-date").addEventListener("change", (e) => {
    convFilterToDate = e.target.value;
    convOffset = 0;
    refreshConversations().catch(() => {});
  });

  $("conv-refresh").addEventListener("click", () => {
    withButton($("conv-refresh"), async () => {
      await refreshConversations();
      notify("Conversas atualizadas.");
    });
  });

  $("conv-prev").addEventListener("click", () => withButton($("conv-prev"), async () => {
    convOffset = Math.max(0, convOffset - convPageSize);
    await refreshConversations();
  }));

  $("conv-next").addEventListener("click", () => withButton($("conv-next"), async () => {
    convOffset += convPageSize;
    await refreshConversations();
  }));

  $("conv-reply-toggle").addEventListener("click", () => {
    const form = $("human-reply-form");
    form.hidden = !form.hidden;
  });

  // WP-136 — Message pagination
  $("msg-prev").addEventListener("click", () => {
    if (msgOffset >= msgPageSize) {
      msgOffset -= msgPageSize;
      loadMessages(selectedConvId).catch(() => {});
    }
  });

  $("msg-next").addEventListener("click", () => {
    msgOffset += msgPageSize;
    loadMessages(selectedConvId).catch(() => {});
  });

  $("conv-close-toggle").addEventListener("click", () => withButton($("conv-close-toggle"), async () => {
    if (selectedConvId === null) return;
    const newStatus = conversations.find((c) => c.id === selectedConvId)?.status === "closed" ? "open" : "closed";
    await conversationApi("/conversations/" + selectedConvId, "PATCH", { status: newStatus });
    const label = newStatus === "closed" ? "fechada" : "reaberta";
    notify("Conversa #" + selectedConvId + " " + label + ".");
    await refreshConversations();
    if (selectedConvId !== null) await selectConversation(selectedConvId);
  }));

  $("human-reply-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const button = $("human-reply-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const convId = $("reply-conv-id").value;
      const message = $("reply-message").value.trim();
      if (!convId || !message) {notify("Preencha os campos.", true); return;}
      const id = parseInt(convId, 10);
      if (isNaN(id) || id < 1) {notify("ID da conversa inválido.", true); return;}
      await replyApi("/conversations/" + id + "/messages", "POST", {
        sender_type: "human",
        content: message,
      });
      $("human-reply-form").reset();
      $("reply-conv-id").value = id;
      notify("Mensagem enviada na conversa #" + id + ".");
      await selectConversation(id);
    });
  });

  $("conv-list").replaceChildren();
  $("conv-detail").hidden = true;
  $("conv-note-section").hidden = true;
  // WP-147
  $("conv-create-lead").hidden = true;
  $("conv-lead-form").hidden = true;
  selectedConvIds.clear();
  updateConvBulkBar();

  const DASHBOARD_REFRESH_MS = 60000;

  // Dashboard — WP-082
  async function refreshDashboard() {
    if (!bearer) return;
    const res = await fetch("/internal-tasks/dashboard", {
      headers: {"Authorization": "Bearer " + bearer},
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
    if (!res.ok) return;
    const data = await res.json();
    renderDashboard(data);
  }

  function startDashboardRefresh() {
    stopDashboardRefresh();
    refreshDashboard().catch(() => {});
    dashboardIntervalId = setInterval(() => {
      refreshDashboard().catch(() => {});
    }, DASHBOARD_REFRESH_MS);
  }

  function stopDashboardRefresh() {
    if (dashboardIntervalId !== null) {
      clearInterval(dashboardIntervalId);
      dashboardIntervalId = null;
    }
  }

  function renderDashboard(data) {
    // Opportunities
    const opp = data.opportunities || {};
    $("dash-opp-total").textContent = opp.total || 0;
    const oppDetails = $("dash-opp-details");
    oppDetails.replaceChildren();
    for (const [k, v] of Object.entries(opp)) {
      if (k === "total") continue;
      const span = document.createElement("span");
      span.textContent = k + ": " + v;
      oppDetails.appendChild(span);
    }

    // Conversations
    const conv = data.conversations || {};
    $("dash-conv-total").textContent = conv.total || 0;
    const convDetails = $("dash-conv-details");
    convDetails.replaceChildren();
    for (const [k, v] of Object.entries(conv)) {
      if (k === "total") continue;
      const span = document.createElement("span");
      span.textContent = k + ": " + v;
      convDetails.appendChild(span);
    }

    // Leads
    const leads = data.leads || {};
    $("dash-lead-total").textContent = leads.total || 0;
    const leadDetails = $("dash-lead-details");
    leadDetails.replaceChildren();
    for (const [k, v] of Object.entries(leads)) {
      if (k === "total") continue;
      const span = document.createElement("span");
      span.textContent = k + ": " + v;
      leadDetails.appendChild(span);
    }

    // Tasks
    const taskDetails = $("dash-task-details");
    taskDetails.replaceChildren();
    for (const [k, v] of Object.entries(data.tasks || {})) {
      const span = document.createElement("span");
      span.textContent = k + ": " + v;
      taskDetails.appendChild(span);
    }

    // Review queue
    const rq = data.review_queue || {};
    $("dash-rq-total").textContent = rq.total || 0;
    const rqDetails = $("dash-rq-details");
    rqDetails.replaceChildren();
    for (const [k, v] of Object.entries(rq)) {
      if (k === "total") continue;
      const span = document.createElement("span");
      span.textContent = k + ": " + v;
      rqDetails.appendChild(span);
    }

    // WP-161 — Next actions summary
    const nextActionsSection = $("next-actions-section");
    const nextActionsList = $("next-actions-list");
    const nextActions = data.next_actions || [];
    if (nextActions.length > 0) {
      nextActionsSection.hidden = false;
      nextActionsList.replaceChildren();
      for (const action of nextActions) {
        const li = document.createElement("li");
        li.className = "next-action-item";
        li.textContent = action.label;
        li.title = "Seção: " + action.section;
        nextActionsList.appendChild(li);
      }
    } else {
      nextActionsSection.hidden = true;
    }
  }

  $("dashboard-refresh").addEventListener("click", () => withButton($("dashboard-refresh"), async () => {
    await refreshDashboard();
    notify("Dashboard atualizado.");
  }));

  // WP-107 — Notifications polling
  const NOTIFICATION_REFRESH_MS = 30000;
  let notificationIntervalId = null;

  async function updateNotifications() {
    if (!bearer) return;
    try {
      const [oppRes, leadsRes, convRes] = await Promise.all([
        fetch("/opportunities", {headers: {"Authorization": "Bearer " + bearer}}),
        fetch("/leads?status=new&limit=100", {headers: {"Authorization": "Bearer " + bearer}}),
        fetch("/companies/1/conversations?status=open&limit=100", {headers: {"Authorization": "Bearer " + bearer}}),
      ]);
      // Opportunities pending badge
      if (oppRes.ok) {
        const opps = await oppRes.json();
        if (Array.isArray(opps)) {
          const pending = opps.filter((o) => o.next_action === "pending").length;
          const badge = $("pending-badge");
          if (pending > 0) { badge.hidden = false; badge.textContent = pending; }
          else { badge.hidden = true; }
        }
      }
      // Leads new badge
      if (leadsRes.ok) {
        const leads = await leadsRes.json();
        if (Array.isArray(leads)) {
          const badge = $("lead-new-badge");
          if (leads.length > 0) { badge.hidden = false; badge.textContent = leads.length; }
          else { badge.hidden = true; }
        }
      }
      // Conversations open badge — use count endpoint
      if (convRes.ok) {
        const convs = await convRes.json();
        if (Array.isArray(convs)) {
          const badge = $("conv-open-badge");
          if (convs.length > 0) { badge.hidden = false; badge.textContent = convs.length; }
          else { badge.hidden = true; }
        }
      }
    } catch (_e) {
      // Silently ignore background notification errors
    }
  }

  function startNotificationRefresh() {
    stopNotificationRefresh();
    notificationIntervalId = setInterval(() => {
      if (!bearer) return;
      updateNotifications().catch(() => {});
    }, NOTIFICATION_REFRESH_MS);
  }

  function stopNotificationRefresh() {
    if (notificationIntervalId !== null) {
      clearInterval(notificationIntervalId);
      notificationIntervalId = null;
    }
  }

  // Leads — WP-083
  const leadStatusLabels = {
    new: "Novo",
    contacted: "Contatado",
    qualified: "Qualificado",
    proposal: "Proposta",
    won: "Convertido",
    lost: "Perdido",
  };

  const leadStatusOptions = ["new", "contacted", "qualified", "proposal", "won", "lost"];

  // WP-100 — Lead pagination state
  let leadOffset = 0;
  const leadPageSize = 50;
  let leadTotal = 0;

  async function leadApi(path, method, body) {
    // Allow /leads with optional query params, /leads/{status}, /leads/{id}, /leads/count
    if (!(/^\/leads($|\/(new|contacted|qualified|proposal|won|lost)$|\/count$|\/\d+$)/.test(path.split("?")[0]))) {
      console.error("[leadApi] Rota não permitida:", path);
      return;
    }
    const res = await fetch(path, {
      method,
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return null;}
    if (!res.ok) {console.error("[leadApi] Erro:", res.status); return null;}
    return res.json();
  }

  async function refreshLeads() {
    if (!bearer) return;
    const status = $("lead-filter-status").value;
    // WP-177 — source filter
    const source = $("lead-filter-source") ? $("lead-filter-source").value : "";
    const q = $("lead-search") ? $("lead-search").value.trim() : "";
    // WP-152 — date filter
    const fromDate = $("lead-from-date") ? $("lead-from-date").value : "";
    const toDate = $("lead-to-date") ? $("lead-to-date").value : "";
    const sort = $("lead-sort") ? $("lead-sort").value : "id";
    let path = "/leads";
    const params = [];
    if (status) params.push("status=" + encodeURIComponent(status));
    if (source) params.push("source=" + encodeURIComponent(source));
    if (q) params.push("q=" + encodeURIComponent(q));
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    if (sort !== "id") params.push("sort=" + encodeURIComponent(sort));
    params.push("limit=" + leadPageSize);
    params.push("offset=" + leadOffset);
    if (params.length) path += "?" + params.join("&");
    // Count params
    const countParams = [];
    if (status) countParams.push("status=" + encodeURIComponent(status));
    if (source) countParams.push("source=" + encodeURIComponent(source));
    if (q) countParams.push("q=" + encodeURIComponent(q));
    if (fromDate) countParams.push("from_date=" + encodeURIComponent(fromDate));
    if (toDate) countParams.push("to_date=" + encodeURIComponent(toDate));
    const [leads, countResult] = await Promise.all([
      leadApi(path, "GET"),
      leadApi("/leads/count" + (countParams.length ? "?" + countParams.join("&") : ""), "GET")
    ]);
    leadTotal = countResult ? countResult.total || 0 : 0;
    leadListLength = (leads || []).length;
    // WP-175 — update new leads badge
    const newLeads = (leads || []).filter((l) => l.status === "new").length;
    const leadBadge = $("lead-new-badge");
    if (newLeads > 0) { leadBadge.hidden = false; leadBadge.textContent = newLeads; }
    else { leadBadge.hidden = true; }
    renderLeads(leads || []);
    updateLeadPagination();
  }

  function renderLeads(leads) {
    const list = $("leads-list");
    list.replaceChildren();
    if (!leads.length) {
      const p = document.createElement("p");
      p.className = "small";
      p.textContent = "Nenhum lead encontrado.";
      list.appendChild(p);
      return;
    }
    for (const lead of leads) {
      const item = document.createElement("div");
      item.className = "lead-item";
      // WP-170 — Checkbox for bulk delete
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "lead-checkbox";
      checkbox.checked = selectedLeadIds.has(lead.id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          selectedLeadIds.add(lead.id);
        } else {
          selectedLeadIds.delete(lead.id);
        }
        updateLeadBulkBar();
      });
      item.appendChild(checkbox);
      const header = document.createElement("div");
      header.className = "lead-item-header";
      const name = document.createElement("span");
      name.className = "lead-item-name";
      name.textContent = lead.name || "Sem nome";
      const statusTag = document.createElement("span");
      statusTag.className = "lead-status-badge lead-status-" + (lead.status || "unknown");
      statusTag.textContent = leadStatusLabels[lead.status] || lead.status;
      header.appendChild(name);
      header.appendChild(statusTag);
      item.appendChild(header);

      const details = document.createElement("div");
      details.className = "lead-item-details";
      if (lead.phone) {
        const phone = document.createElement("span");
        phone.textContent = "📞 " + lead.phone;
        details.appendChild(phone);
      }
      if (lead.source) {
        const source = document.createElement("span");
        source.textContent = "Fonte: " + lead.source;
        details.appendChild(source);
      }
      if (lead.interest) {
        const interest = document.createElement("span");
        interest.textContent = "Interesse: " + lead.interest;
        details.appendChild(interest);
      }
      item.appendChild(details);

      const select = document.createElement("select");
      select.className = "lead-status-select";
      for (const s of leadStatusOptions) {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = leadStatusLabels[s];
        if (s === lead.status) opt.selected = true;
        select.appendChild(opt);
      }
      select.addEventListener("change", () => {
        updateLeadStatus(lead.id, select.value);
      });
      item.appendChild(select);

      // Convert button — WP-085 (hide for already-converted leads)
      if (lead.status !== "won") {
        const convertBtn = document.createElement("button");
        convertBtn.className = "lead-convert-btn secondary";
        convertBtn.textContent = "Converter";
        convertBtn.type = "button";
        convertBtn.addEventListener("click", () => {
          convertLead(lead.id);
        });
        item.appendChild(convertBtn);
      }

      // Notes textarea — WP-088
      const notesArea = document.createElement("textarea");
      notesArea.className = "lead-notes";
      notesArea.placeholder = "Notas...";
      notesArea.rows = 2;
      notesArea.textContent = lead.interest || "";
      notesArea.addEventListener("change", () => {
        updateLeadNotes(lead.id, notesArea.value);
      });
      item.appendChild(notesArea);

      list.appendChild(item);

      // WP-114 — Click to show detail
      item.style.cursor = "pointer";
      item.addEventListener("click", (e) => {
        if (e.target.tagName === "SELECT" || e.target.tagName === "BUTTON" || e.target.tagName === "TEXTAREA") return;
        showLeadDetail(lead);
      });
    }
  }

  // WP-114 — Lead detail panel
  let currentLeadId = null;

  async function showLeadDetail(lead) {
    currentLeadId = lead.id;
    $("leads-list").hidden = true;
    $("leads-pagination").hidden = true;
    $("lead-detail").hidden = false;
    $("lead-detail-name").textContent = lead.name || "Sem nome";
    $("lead-detail-status").textContent = leadStatusLabels[lead.status] || lead.status;

    const info = $("lead-detail-info");
    info.replaceChildren();
    const fields = [
      ["Telefone", lead.phone],
      ["E-mail", lead.email],
      ["Fonte", lead.source],
      ["Interesse", lead.interest],
      ["Criado em", lead.created_at],
    ];
    for (const [label, value] of fields) {
      if (value) {
        const dt = document.createElement("dt");
        dt.textContent = label;
        info.appendChild(dt);
        const dd = document.createElement("dd");
        dd.textContent = value;
        info.appendChild(dd);
      }
    }

    const convList = $("lead-conversations-list");
    convList.replaceChildren();
    try {
      const convs = await api("/companies/" + company + "/conversations?limit=50");
      const leadConvs = (convs || []).filter((c) => c.lead_id === lead.id);
      if (!leadConvs.length) {
        const p = document.createElement("p");
        p.className = "small";
        p.textContent = "Nenhuma conversa associada.";
        convList.appendChild(p);
      } else {
        for (const conv of leadConvs) {
          const div = document.createElement("div");
          div.className = "conv-item small";
          div.textContent = "#" + conv.id + " · " + (conv.channel || "web") + " · " + conv.status;
          convList.appendChild(div);
        }
      }
    } catch (e) {
      console.error("[showLeadDetail] Falha ao carregar conversas:", e);
    }
  }

  function hideLeadDetail() {
    currentLeadId = null;
    $("leads-list").hidden = false;
    $("lead-detail").hidden = true;
    if (leadTotal > leadPageSize) {
      $("leads-pagination").hidden = false;
    }
  }

  $("lead-detail-back").addEventListener("click", () => {
    hideLeadDetail();
  });

  // WP-176 — Create conversation from lead detail
  $("lead-new-conv").addEventListener("click", () => {
    if (currentLeadId) {
      createConversationFromLead(currentLeadId);
    }
  });

  async function createConversationFromLead(leadId) {
    if (!bearer) return;
    const company = opportunities.length > 0 ? opportunities[0].company_id : null;
    if (!company) {notify("Não é possível determinar a company.", true); return;}
    const channel = prompt("Canal da conversa (whatsapp, instagram, web, telegram, email):");
    if (!channel) return;
    const allowedChannels = ["whatsapp", "instagram", "web", "telegram", "email"];
    if (!allowedChannels.includes(channel.trim().toLowerCase())) {
      notify("Canal inválido.", true);
      return;
    }
    const res = await fetch("/conversations", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        company_id: company,
        channel: channel.trim().toLowerCase(),
        lead_id: leadId,
      }),
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
    if (res.status === 409) {notify("Conversa já existe.", true); return;}
    if (!res.ok) {console.error("[createConversationFromLead] Erro:", res.status); return;}
    notify("Conversa criada.");
    await showLeadDetail(leads.find((l) => l.id === leadId) || {id: leadId});
  }

  async function updateLeadStatus(leadId, status) {
    const path = "/leads/" + leadId;
    const allowed = path.startsWith("/leads/");
    if (!allowed) {
      console.error("[leadApi] Rota não permitida:", path);
      return;
    }
    const res = await fetch(path, {
      method: "PATCH",
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({status}),
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
    if (!res.ok) {console.error("[updateLeadStatus] Erro:", res.status); return;}
    notify("Lead #" + leadId + " atualizado para " + (leadStatusLabels[status] || status) + ".");
  }

  // Update lead notes — WP-088
  async function updateLeadNotes(leadId, notes) {
    const path = "/leads/" + leadId;
    const res = await fetch(path, {
      method: "PATCH",
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({interest: notes}),
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
    if (!res.ok) {console.error("[updateLeadNotes] Erro:", res.status); return;}
    notify("Notas do lead #" + leadId + " salvas.");
  }

  // Convert lead to customer — WP-085
  async function convertLead(leadId) {
    if (!confirm("Converter este lead em customer? O status será alterado para 'Convertido'.")) return;
    const path = "/leads/" + leadId + "/convert";
    const res = await fetch(path, {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
    if (res.status === 409) {notify("Lead já foi convertido em customer."); return;}
    if (!res.ok) {console.error("[convertLead] Erro:", res.status); return;}
    notify("Lead #" + leadId + " convertido em customer.");
    await refreshLeads();
  }

  $("leads-refresh").addEventListener("click", () => withButton($("leads-refresh"), async () => {
    await refreshLeads();
    notify("Leads atualizados.");
  }));

  // WP-099 — Lead search
  const leadSearch = $("lead-search");
  if (leadSearch) {
    leadSearch.addEventListener("input", () => {
      leadOffset = 0;
      refreshLeads().catch(() => {});
    });
  }

  // WP-100 — Lead pagination
  function updateLeadPagination() {
    const pagination = $("leads-pagination");
    const totalPages = Math.max(1, Math.ceil(leadTotal / leadPageSize));
    const currentPage = Math.floor(leadOffset / leadPageSize) + 1;
    if (leadTotal <= leadPageSize) {
      pagination.hidden = true;
    } else {
      pagination.hidden = false;
      $("leads-prev-page").disabled = leadOffset === 0;
      $("leads-next-page").disabled = leadOffset + leadListLength >= leadTotal;
      $("leads-page-info").textContent = "Página " + currentPage + " de " + totalPages + " (" + leadTotal + ")";
    }
  }

  let leadListLength = 0;

  $("lead-filter-status").addEventListener("change", () => {
    leadOffset = 0;
    refreshLeads().catch(() => {});
  });

  // WP-177 — Lead source filter
  $("lead-filter-source").addEventListener("change", () => {
    leadOffset = 0;
    refreshLeads().catch(() => {});
  });

  $("leads-prev-page").addEventListener("click", () => withButton($("leads-prev-page"), async () => {
    leadOffset = Math.max(0, leadOffset - leadPageSize);
    await refreshLeads();
  }));

  $("leads-next-page").addEventListener("click", () => withButton($("leads-next-page"), async () => {
    leadOffset += leadPageSize;
    await refreshLeads();
  }));

  // WP-101 — Lead sorting
  $("lead-sort").addEventListener("change", () => {
    leadOffset = 0;
    refreshLeads().catch(() => {});
  });

  // WP-152 — Lead date filter
  $("lead-from-date").addEventListener("change", () => {
    leadOffset = 0;
    refreshLeads().catch(() => {});
  });
  $("lead-to-date").addEventListener("change", () => {
    leadOffset = 0;
    refreshLeads().catch(() => {});
  });

  // WP-165 — Clear all lead filters
  $("lead-clear-filters").addEventListener("click", () => {
    $("lead-filter-status").value = "";
    $("lead-filter-source").value = "";
    $("lead-search").value = "";
    $("lead-from-date").value = "";
    $("lead-to-date").value = "";
    $("lead-sort").value = "id";
    leadOffset = 0;
    refreshLeads().catch(() => {});
  });

  // Customers — WP-086, WP-104

  // Customer detail state — WP-087
  let currentCustomerId = null;

  // WP-104 — Customer pagination state
  let customerOffset = 0;
  const customerPageSize = 50;
  let customerTotal = 0;

  function buildCustomerUrl() {
    const params = new URLSearchParams();
    const q = $("customer-search")?.value?.trim();
    // WP-153 — date filter
    const fromDate = $("customer-from-date")?.value;
    const toDate = $("customer-to-date")?.value;
    const sort = $("customer-sort")?.value;
    if (q) params.set("q", q);
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);
    if (sort) params.set("sort", sort);
    params.set("limit", String(customerPageSize));
    params.set("offset", String(customerOffset));
    const search = params.toString();
    return "/customers" + (search ? "?" + search : "");
  }

  function buildCustomerCountUrl() {
    const params = new URLSearchParams();
    const q = $("customer-search")?.value?.trim();
    // WP-153 — date filter
    const fromDate = $("customer-from-date")?.value;
    const toDate = $("customer-to-date")?.value;
    if (q) params.set("q", q);
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);
    const search = params.toString();
    return "/customers/count" + (search ? "?" + search : "");
  }

  async function customerApi(path, method, body) {
    if (!bearer) throw new Error("Conecte um operador.");
    const allowedPattern = /^\/customers(\/(count|export\.csv))?(\?.*)?$/;
    if (!allowedPattern.test(path.split("#")[0])) {
      console.error("[customerApi] Rota não permitida:", path);
      return;
    }
    const res = await fetch(path, {
      method,
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return null;}
    if (!res.ok) {console.error("[customerApi] Erro:", res.status); return null;}
    return res.json();
  }

  async function refreshCustomers() {
    if (!bearer) return;
    const [customers, countData] = await Promise.all([
      customerApi(buildCustomerUrl(), "GET"),
      customerApi(buildCustomerCountUrl(), "GET"),
    ]);
    customerTotal = countData?.total || 0;
    renderCustomers(customers || []);
    updateCustomerPagination();
  }

  function updateCustomerPagination() {
    const paginationEl = $("customers-pagination");
    const pageInfo = $("customers-page-info");
    if (!paginationEl || !pageInfo) return;
    if (customerTotal <= customerPageSize) {
      paginationEl.hidden = true;
      return;
    }
    paginationEl.hidden = false;
    const page = Math.floor(customerOffset / customerPageSize) + 1;
    const totalPages = Math.ceil(customerTotal / customerPageSize);
    pageInfo.textContent = `Página ${page} de ${totalPages} (${customerTotal} customers)`;
    $("customers-prev-page").disabled = customerOffset === 0;
    $("customers-next-page").disabled = customerOffset + customerPageSize >= customerTotal;
  }

  function renderCustomers(customers) {
    const list = $("customers-list");
    list.replaceChildren();
    if (!customers.length) {
      const p = document.createElement("p");
      p.className = "small";
      p.textContent = "Nenhum customer encontrado.";
      list.appendChild(p);
      return;
    }
    for (const cust of customers) {
      const item = document.createElement("div");
      item.className = "customer-item";
      // WP-169 — Checkbox for bulk delete
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "customer-checkbox";
      checkbox.checked = selectedCustomerIds.has(cust.id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          selectedCustomerIds.add(cust.id);
        } else {
          selectedCustomerIds.delete(cust.id);
        }
        updateCustomerBulkBar();
      });
      item.appendChild(checkbox);
      item.style.cursor = "pointer";
      item.addEventListener("click", (e) => {
        if (e.target.tagName === "INPUT") return;
        showCustomerDetail(cust);
      });

      const header = document.createElement("div");
      header.className = "customer-item-header";
      const name = document.createElement("span");
      name.className = "customer-item-name";
      name.textContent = cust.name || "Sem nome";
      header.appendChild(name);
      item.appendChild(header);

      const details = document.createElement("div");
      details.className = "customer-item-details";
      if (cust.phone) {
        const phone = document.createElement("span");
        phone.textContent = "📞 " + cust.phone;
        details.appendChild(phone);
      }
      if (cust.email) {
        const email = document.createElement("span");
        email.textContent = "✉️ " + cust.email;
        details.appendChild(email);
      }
      if (cust.lead_id) {
        const lead = document.createElement("span");
        lead.textContent = "Lead #" + cust.lead_id;
        details.appendChild(lead);
      }
      item.appendChild(details);

      list.appendChild(item);
    }
  }

  // Customer detail view — WP-087
  async function showCustomerDetail(cust) {
    currentCustomerId = cust.id;
    $("customers-list").hidden = true;
    $("customer-detail").hidden = false;
    $("customer-detail-name").textContent = cust.name || "Sem nome";

    const info = $("customer-detail-info");
    info.replaceChildren();
    if (cust.phone) {
      const phone = document.createElement("span");
      phone.textContent = "📞 " + cust.phone;
      info.appendChild(phone);
    }
    if (cust.email) {
      const email = document.createElement("span");
      email.textContent = "✉️ " + cust.email;
      info.appendChild(email);
    }
    if (cust.lead_id) {
      const lead = document.createElement("span");
      lead.textContent = "Lead #" + cust.lead_id;
      info.appendChild(lead);
    }

    // WP-110 — Add edit button
    const editBtn = document.createElement("button");
    editBtn.id = "customer-edit-btn";
    editBtn.type = "button";
    editBtn.className = "secondary";
    editBtn.textContent = "✏️ Editar";
    editBtn.style.marginTop = "8px";
    editBtn.addEventListener("click", () => showCustomerEditForm(cust));
    info.appendChild(editBtn);

    hideCustomerEditForm();

    // Load conversations for this customer
    await loadCustomerConversations(cust.id);
  }

  async function loadCustomerConversations(customerId) {
    if (!bearer) return;
    const convList = $("customer-conversations-list");
    convList.replaceChildren();

    try {
      const company = opportunities.length > 0 ? opportunities[0].company_id : null;
      if (!company) {
        const p = document.createElement("p");
        p.className = "small";
        p.textContent = "Não é possível determinar a company.";
        convList.appendChild(p);
        return;
      }
      const params = new URLSearchParams();
      params.set("customer_id", customerId);
      const url = "/companies/" + company + "/conversations?" + params.toString();
      const convs = await conversationApi(url);
      if (!convs || !convs.length) {
        const p = document.createElement("p");
        p.className = "small";
        p.textContent = "Nenhuma conversa encontrada.";
        convList.appendChild(p);
        return;
      }

      for (const conv of convs) {
        const item = document.createElement("div");
        item.className = "customer-conv-item";
        const header = document.createElement("div");
        header.className = "customer-conv-header";
        const channel = document.createElement("span");
        channel.className = "conv-channel-badge";
        channel.textContent = conv.channel || "N/A";
        header.appendChild(channel);
        const status = document.createElement("span");
        status.className = "conv-status-badge";
        status.textContent = conv.status === "open" ? "Aberta" : "Fechada";
        header.appendChild(status);
        item.appendChild(header);
        convList.appendChild(item);
      }
    } catch (e) {
      console.error("[loadCustomerConversations] Erro:", e);
    }
  }

  function hideCustomerDetail() {
    currentCustomerId = null;
    $("customers-list").hidden = false;
    $("customer-detail").hidden = true;
  }

  // WP-110 — Edit customer
  async function showCustomerEditForm(cust) {
    $("customer-edit-form").hidden = false;
    $("customer-edit-name").value = cust.name || "";
    $("customer-edit-phone").value = cust.phone || "";
    $("customer-edit-email").value = cust.email || "";
  }
  function hideCustomerEditForm() {
    $("customer-edit-form").hidden = true;
  }

  async function updateCustomer(customerId, data) {
    if (!bearer) return;
    const path = "/customers/" + customerId;
    const res = await fetch(path, {
      method: "PATCH",
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return null;}
    if (res.status === 404) {notify("Customer não encontrado.", true); return null;}
    if (!res.ok) {notify("Falha ao atualizar customer.", true); return null;}
    return res.json();
  }

  // WP-110 — Edit customer form handlers
  $("customer-edit-cancel").addEventListener("click", () => {
    hideCustomerEditForm();
  });

  $("customer-edit-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const name = $("customer-edit-name").value.trim();
    const phone = $("customer-edit-phone").value.trim() || null;
    const email = $("customer-edit-email").value.trim() || null;
    if (!name) {notify("Nome é obrigatório.", true); return;}
    const data = {name};
    if (phone !== null) data.phone = phone;
    if (email !== null) data.email = email;
    const button = $("customer-edit-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const updated = await updateCustomer(currentCustomerId, data);
      if (updated) {
        hideCustomerEditForm();
        $("customer-detail-name").textContent = updated.name;
        notify("Customer atualizado.");
        await refreshCustomers();
        showCustomerDetail(updated);
      }
    });
  });

  // Create conversation from customer — WP-089
  async function createConversationFromCustomer(customerId) {
    if (!bearer) return;
    const company = opportunities.length > 0 ? opportunities[0].company_id : null;
    if (!company) {notify("Não é possível determinar a company.", true); return;}
    const channel = prompt("Canal da conversa (whatsapp, instagram, web, telegram, email):");
    if (!channel) return;
    const allowedChannels = ["whatsapp", "instagram", "web", "telegram", "email"];
    if (!allowedChannels.includes(channel.trim().toLowerCase())) {
      notify("Canal inválido.", true);
      return;
    }
    const res = await fetch("/conversations", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        company_id: company,
        channel: channel.trim().toLowerCase(),
        customer_id: customerId,
      }),
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
    if (res.status === 409) {notify("Conversa já existe.", true); return;}
    if (!res.ok) {console.error("[createConversationFromCustomer] Erro:", res.status); return;}
    notify("Conversa criada.");
    await loadCustomerConversations(customerId);
  }

  $("customers-refresh").addEventListener("click", () => withButton($("customers-refresh"), async () => {
    customerOffset = 0;
    await refreshCustomers();
    notify("Customers atualizados.");
  }));

  // WP-104 — Customer search, sort, pagination
  $("customer-search").addEventListener("input", () => {
    customerOffset = 0;
    refreshCustomers().catch(() => {});
  });

  $("customer-sort").addEventListener("change", () => {
    customerOffset = 0;
    refreshCustomers().catch(() => {});
  });

  // WP-153 — Customer date filter
  $("customer-from-date").addEventListener("change", () => {
    customerOffset = 0;
    refreshCustomers().catch(() => {});
  });
  $("customer-to-date").addEventListener("change", () => {
    customerOffset = 0;
    refreshCustomers().catch(() => {});
  });

  // WP-165 — Clear all customer filters
  $("customer-clear-filters").addEventListener("click", () => {
    $("customer-search").value = "";
    $("customer-from-date").value = "";
    $("customer-to-date").value = "";
    $("customer-sort").value = "id";
    customerOffset = 0;
    refreshCustomers().catch(() => {});
  });

  $("customers-prev-page").addEventListener("click", () => {
    if (customerOffset > 0) {
      customerOffset -= customerPageSize;
      refreshCustomers().catch(() => {});
    }
  });

  $("customers-next-page").addEventListener("click", () => {
    if (customerOffset + customerPageSize < customerTotal) {
      customerOffset += customerPageSize;
      refreshCustomers().catch(() => {});
    }
  });

  $("customer-detail-back").addEventListener("click", () => {
    hideCustomerDetail();
  });

  $("customer-new-conv").addEventListener("click", () => {
    if (currentCustomerId) {
      createConversationFromCustomer(currentCustomerId);
    }
  });

  // WP-167 — Create opportunity from customer detail
  $("customer-new-opp").addEventListener("click", () => {
    $("customer-opp-form").hidden = false;
    $("customer-opp-title").focus();
  });

  $("cancel-customer-opp").addEventListener("click", () => {
    $("customer-opp-form").hidden = true;
    $("customer-opp-form").reset();
  });

  $("customer-opp-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const button = $("customer-opp-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const title = $("customer-opp-title").value.trim();
      const description = $("customer-opp-description").value.trim();
      const budget = $("customer-opp-budget").value.trim() || null;
      const deadline = $("customer-opp-deadline").value.trim() || null;
      const requirements = $("customer-opp-requirements").value.trim() || null;
      if (!title || !description) {
        notify("Preencha título e descrição.", true);
        return;
      }
      const opp = await api("/opportunities", {
        method: "POST",
        body: JSON.stringify({
          company_id: opportunities.length > 0 ? opportunities[0].company_id : null,
          source: "manual",
          external_url: "customer-" + currentCustomerId,
          title,
          description,
          budget,
          deadline,
          requirements,
          captured_at: new Date().toISOString(),
        }),
      });
      $("customer-opp-form").hidden = true;
      $("customer-opp-form").reset();
      notify("Oportunidade #" + opp.id + " criada.");
      await refreshList(opp.id);
    });
  });

  // WP-096 — Commercial intake API and form handler
  async function intakeApi(path, method, body) {
    if (!bearer) throw new Error("Conecte um operador.");
    if (!(/^\/internal\/commercial-intake\/create$/.test(path))) {
      throw new Error("Rota de intake não permitida.");
    }
    const epoch = sessionEpoch;
    const headers = {Authorization: "Bearer " + bearer};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "omit", cache: "no-store", redirect: "error", referrerPolicy: "no-referrer"});
    if (epoch !== sessionEpoch) throw new Error("Sessão encerrada.");
    if (response.status === 401) {
      disconnect("Credencial inválida.");
      throw new ApiFailure(401);
    }
    if (!response.ok) throw new ApiFailure(response.status);
    return response.json();
  }

  $("intake-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const button = $("intake-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const channel = $("intake-channel").value;
      const eventId = $("intake-event-id").value.trim();
      const message = $("intake-message").value.trim();
      if (!eventId || !message) {notify("Preencha os campos obrigatórios.", true); return;}
      const result = await intakeApi("/internal/commercial-intake/create", "POST", {
        channel,
        event_id: eventId,
        message,
      });
      // Display decision
      $("intake-decision").hidden = false;
      $("intake-decision-intent").textContent = result.intent || "Desconhecida";
      $("intake-decision-review").textContent = result.needs_human_review ? "Sim" : "Não";
      $("intake-decision-flags").textContent = result.flags && result.flags.length
        ? result.flags.join(", ")
        : "Nenhuma";
      $("intake-decision-opp").textContent = "#" + result.opportunity_id;
      // Refresh opportunity list to show the new intake opportunity
      await refreshList(result.opportunity_id);
      notify("Intake avaliado. Oportunidade #" + result.opportunity_id + " criada.");
    });
  });

  // Integrate conversations into the connect flow via MutationObserver.
  const workspaceObserver = new MutationObserver((records) => {
    for (const record of records) {
      if (record.attributeName === "hidden" && !$("workspace").hidden && bearer) {
        refreshDashboard().catch(() => {});
        refreshConversations().catch(() => {});
        refreshLeads().catch(() => {});
        refreshCustomers().catch(() => {});
        refreshTasks().catch(() => {});
        workspaceObserver.disconnect();
      }
    }
  });
  workspaceObserver.observe($("workspace"), {attributes: true});

  // WP-105 — Bulk triage
  function updateBulkTriageBar() {
    const bar = $("bulk-triage-bar");
    const count = selectedOpportunityIds.size;
    $("bulk-selected-count").textContent = count + " selecionada(s)";
    bar.hidden = count === 0;
  }

  $("bulk-triage-clear").addEventListener("click", () => {
    selectedOpportunityIds.clear();
    showList();
  });

  $("bulk-triage-apply").addEventListener("click", () => {
    const button = $("bulk-triage-apply");
    withButton(button, async () => {
      const ids = Array.from(selectedOpportunityIds);
      if (!ids.length) {notify("Nenhuma oportunidade selecionada.", true); return;}
      const action = $("bulk-triage-action").value;
      const note = $("bulk-triage-note").value.trim() || null;
      const result = await api("/opportunities/bulk-triage", {
        method: "POST",
        body: JSON.stringify({
          opportunity_ids: ids,
          next_action: action,
          triage_note: note,
        }),
      });
      selectedOpportunityIds.clear();
      $("bulk-triage-note").value = "";
      notify(result.updated + " oportunidade(s) atualizada(s). " + result.skipped + " ignorada(s).");
      await refreshList();
      showList();
    });
  });

  // WP-106 — Export CSV buttons
  function downloadCsv(url, filename) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  $("opp-export-csv").addEventListener("click", () => {
    // WP-123/150 — Export CSV with current filters
    const params = [];
    const showArchived = $("show-archived").checked;
    if (!showArchived) params.push("exclude_archived=true");
    if (oppPipelineFilter !== "all") params.push("next_action=" + encodeURIComponent(oppPipelineFilter));
    const searchQuery = $("opp-search").value.trim();
    if (searchQuery) params.push("q=" + encodeURIComponent(searchQuery));
    const fromDate = $("opp-from-date").value;
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    const toDate = $("opp-to-date").value;
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    const url = "/opportunities/export.csv" + (params.length ? "?" + params.join("&") : "");
    downloadCsv(url, "opportunities.csv");
    notify("Exportando oportunidades...");
  });

  // WP-159 — Import CSV for opportunities
  $("opp-import-csv").addEventListener("click", () => {
    $("opp-import-file").click();
  });

  $("opp-import-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    if (!bearer) {notify("Não conectado.", true); return;}
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("/opportunities/import.csv", {
        method: "POST",
        headers: {"Authorization": "Bearer " + bearer},
        body: formData,
      });
      if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        notify("Falha ao importar: " + (data.detail || "erro desconhecido"), true);
        return;
      }
      const data = await res.json();
      notify(
        "Importação concluída: " + data.imported + " importado(s), " +
        data.skipped + " duplicata(s), " + data.errors + " erro(s)."
      );
      await refreshList();
    } catch (err) {
      notify("Falha ao importar CSV.", true);
    }
    event.target.value = "";
  });

  // WP-152 — Export CSV with current filters
  $("leads-export-csv").addEventListener("click", () => {
    const params = [];
    const status = $("lead-filter-status").value;
    if (status) params.push("status=" + encodeURIComponent(status));
    // WP-177 — source filter
    const source = $("lead-filter-source") ? $("lead-filter-source").value : "";
    if (source) params.push("source=" + encodeURIComponent(source));
    const q = $("lead-search") ? $("lead-search").value.trim() : "";
    if (q) params.push("q=" + encodeURIComponent(q));
    const fromDate = $("lead-from-date") ? $("lead-from-date").value : "";
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    const toDate = $("lead-to-date") ? $("lead-to-date").value : "";
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    const url = "/leads/export.csv" + (params.length ? "?" + params.join("&") : "");
    downloadCsv(url, "leads.csv");
    notify("Exportando leads...");
  });

  // WP-157 — Import CSV
  $("leads-import-csv").addEventListener("click", () => {
    $("leads-import-file").click();
  });

  $("leads-import-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    if (!bearer) {notify("Não conectado.", true); return;}
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("/leads/import.csv", {
        method: "POST",
        headers: {"Authorization": "Bearer " + bearer},
        body: formData,
      });
      if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        notify("Falha ao importar: " + (data.detail || "erro desconhecido"), true);
        return;
      }
      const data = await res.json();
      notify(
        "Importação concluída: " + data.imported + " importado(s), " +
        data.skipped + " duplicata(s), " + data.errors + " erro(s)."
      );
      await refreshLeads();
    } catch (err) {
      notify("Falha ao importar CSV.", true);
    }
    event.target.value = "";
  });

  // WP-153 — Export CSV with current filters
  $("customers-export-csv").addEventListener("click", () => {
    const params = [];
    const q = $("customer-search")?.value?.trim();
    if (q) params.push("q=" + encodeURIComponent(q));
    const fromDate = $("customer-from-date")?.value;
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    const toDate = $("customer-to-date")?.value;
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    const url = "/customers/export.csv" + (params.length ? "?" + params.join("&") : "");
    downloadCsv(url, "customers.csv");
    notify("Exportando customers...");
  });

  // WP-158 — Import CSV for customers
  $("customers-import-csv").addEventListener("click", () => {
    $("customers-import-file").click();
  });

  $("customers-import-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    if (!bearer) {notify("Não conectado.", true); return;}
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("/customers/import.csv", {
        method: "POST",
        headers: {"Authorization": "Bearer " + bearer},
        body: formData,
      });
      if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        notify("Falha ao importar: " + (data.detail || "erro desconhecido"), true);
        return;
      }
      const data = await res.json();
      notify(
        "Importação concluída: " + data.imported + " importado(s), " +
        data.skipped + " duplicata(s), " + data.errors + " erro(s)."
      );
      await refreshCustomers();
    } catch (err) {
      notify("Falha ao importar CSV.", true);
    }
    event.target.value = "";
  });

  $("rq-export-csv").addEventListener("click", () => {
    // WP-154 — export with filters
    const params = [];
    const status = $("rq-status-filter")?.value?.trim();
    if (status) params.push("status=" + encodeURIComponent(status));
    const fromDate = $("rq-from-date")?.value;
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    const toDate = $("rq-to-date")?.value;
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    const url = "/review-queue/export.csv" + (params.length ? "?" + params.join("&") : "");
    downloadCsv(url, "review-queue.csv");
    notify("Exportando fila de revisão...");
  });

  $("tasks-export-csv").addEventListener("click", () => {
    // WP-155 — export with filters
    const params = [];
    const status = $("task-status-filter").value;
    if (status) params.push("status=" + encodeURIComponent(status));
    const fromDate = $("task-from-date")?.value;
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    const toDate = $("task-to-date")?.value;
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    const url = "/internal-tasks/export.csv" + (params.length ? "?" + params.join("&") : "");
    downloadCsv(url, "internal-tasks.csv");
    notify("Exportando tarefas internas...");
  });

  // WP-111 — Create customer manually
  async function createCustomer(name, phone, email) {
    if (!bearer) return null;
    const company = opportunities.length > 0 ? opportunities[0].company_id : null;
    if (!company) {notify("Empresa não configurada.", true); return null;}
    const res = await fetch("/customers", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({company_id: company, name, phone, email}),
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return null;}
    if (!res.ok) {notify("Falha ao criar customer.", true); return null;}
    return res.json();
  }

  $("show-create-customer").addEventListener("click", () => {
    $("create-customer-form").hidden = false;
    $("new-customer-name").focus();
  });

  $("cancel-create-customer").addEventListener("click", () => {
    $("create-customer-form").hidden = true;
    $("new-customer-name").value = "";
    $("new-customer-phone").value = "";
    $("new-customer-email").value = "";
  });

  $("create-customer-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const name = $("new-customer-name").value.trim();
    const phone = $("new-customer-phone").value.trim() || null;
    const email = $("new-customer-email").value.trim() || null;
    if (!name) {notify("Nome é obrigatório.", true); return;}
    const button = $("create-customer-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const created = await createCustomer(name, phone, email);
      if (created) {
        $("create-customer-form").hidden = true;
        $("new-customer-name").value = "";
        $("new-customer-phone").value = "";
        $("new-customer-email").value = "";
        notify("Customer criado.");
        await refreshCustomers();
      }
    });
  });

  // WP-120 — Internal tasks
  let taskOffset = 0;
  const taskPageSize = 50;
  let taskTotal = 0;

  async function taskApi(path, method = "GET", body) {
    if (!bearer) throw new Error("Conecte um operador.");
    const route = path.split("#")[0];
    if (!(/^\/internal-tasks(\/|$|\?)/.test(route) ||
          /^\/internal-tasks\/bulk-retry$/.test(route))) {
      throw new Error("Rota de tarefas não permitida.");
    }
    const epoch = sessionEpoch;
    const headers = {Authorization: "Bearer " + bearer};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "omit", cache: "no-store", redirect: "error", referrerPolicy: "no-referrer"});
    if (epoch !== sessionEpoch) throw new Error("Sessão encerrada.");
    if (response.status === 401) {
      disconnect("Credencial inválida.");
      throw new ApiFailure(401);
    }
    if (!response.ok) throw new ApiFailure(response.status);
    return response.json();
  }

  function buildTaskUrl() {
    const params = new URLSearchParams();
    params.set("limit", taskPageSize);
    params.set("offset", taskOffset);
    params.set("sort", $("task-sort").value);
    const status = $("task-status-filter").value;
    if (status) params.set("status", status);
    // WP-155 — date filter
    const fromDate = $("task-from-date")?.value;
    if (fromDate) params.set("from_date", fromDate);
    const toDate = $("task-to-date")?.value;
    if (toDate) params.set("to_date", toDate);
    return "/internal-tasks/?" + params.toString();
  }

  function buildTaskCountUrl() {
    const params = [];
    const status = $("task-status-filter").value;
    if (status) params.push("status=" + encodeURIComponent(status));
    // WP-155 — date filter
    const fromDate = $("task-from-date")?.value;
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    const toDate = $("task-to-date")?.value;
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    return "/internal-tasks/count" + (params.length ? "?" + params.join("&") : "");
  }

  async function refreshTasks() {
    if (!bearer) return;
    // WP-172 — Reset bulk selection on refresh
    selectedTaskIds.clear();
    $("task-bulk-bar").hidden = true;
    try {
      const [tasks, count] = await Promise.all([
        taskApi(buildTaskUrl()),
        taskApi(buildTaskCountUrl()),
      ]);
      taskTotal = count;
      renderTasks(tasks);
      updateTaskPagination();
    } catch (e) {
      if (e instanceof ApiFailure && e.status !== 401) {
        notify("Falha ao carregar tarefas.", true);
      }
    }
  }

  function renderTasks(tasks) {
    const list = $("tasks-list");
    while (list.firstChild) list.removeChild(list.firstChild);
    if (!tasks.length) {
      const empty = document.createElement("p");
      empty.className = "small";
      empty.textContent = "Nenhuma tarefa encontrada.";
      list.appendChild(empty);
      return;
    }
    const statusLabels = {queued: "Fila", running: "Executando", succeeded: "Sucesso", failed: "Falha"};
    for (const task of tasks) {
      const item = document.createElement("div");
      item.className = "task-item";
      // WP-172 — Checkbox for bulk retry
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "task-checkbox";
      checkbox.checked = selectedTaskIds.has(task.id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          selectedTaskIds.add(task.id);
        } else {
          selectedTaskIds.delete(task.id);
        }
        updateTaskBulkBar();
      });
      item.appendChild(checkbox);
      const header = document.createElement("div");
      header.className = "task-item-header";
      const name = document.createElement("strong");
      name.textContent = "#" + task.id + " · " + (task.event_id || "—");
      const statusTag = document.createElement("span");
      statusTag.className = "task-status-badge task-status-" + (task.status || "unknown");
      statusTag.textContent = statusLabels[task.status] || task.status || "—";
      header.append(name, statusTag);
      item.appendChild(header);
      const meta = document.createElement("div");
      meta.className = "task-meta small";
      meta.textContent = "Tentativas: " + (task.attempts || 0) + " · " + (task.created_at || "—");
      item.appendChild(meta);
      if (task.error_code) {
        const err = document.createElement("div");
        err.className = "task-error small";
        err.textContent = "Erro: " + task.error_code;
        item.appendChild(err);
      }
      if (task.status === "failed") {
        const retryBtn = document.createElement("button");
        retryBtn.type = "button";
        retryBtn.className = "secondary task-retry-btn";
        retryBtn.textContent = "Retry";
        retryBtn.addEventListener("click", () => {
          withButton(retryBtn, async () => {
            try {
              await taskApi("/internal-tasks/" + task.id + "/retry", "POST");
              notify("Tarefa #" + task.id + " em retry.");
              await refreshTasks();
            } catch (e) {
              notify("Falha ao retry.", true);
            }
          });
        });
        item.appendChild(retryBtn);
      }
      list.appendChild(item);
    }
  }

  function updateTaskPagination() {
    const pag = $("tasks-pagination");
    if (taskTotal <= taskPageSize) {
      pag.hidden = true;
      return;
    }
    pag.hidden = false;
    const page = Math.floor(taskOffset / taskPageSize) + 1;
    const totalPages = Math.ceil(taskTotal / taskPageSize);
    $("tasks-page-info").textContent = "Página " + page + " de " + totalPages;
    $("tasks-prev-page").disabled = taskOffset === 0;
    $("tasks-next-page").disabled = taskOffset + taskPageSize >= taskTotal;
  }

  $("tasks-refresh").addEventListener("click", () => {
    refreshTasks();
  });

  $("task-status-filter").addEventListener("change", () => {
    taskOffset = 0;
    refreshTasks();
  });

  $("task-sort").addEventListener("change", () => {
    taskOffset = 0;
    refreshTasks();
  });

  // WP-155 — task date filter listeners
  $("task-from-date").addEventListener("change", () => {
    taskOffset = 0;
    refreshTasks();
  });
  $("task-to-date").addEventListener("change", () => {
    taskOffset = 0;
    refreshTasks();
  });

  // WP-164 — Clear all task filters
  $("task-clear-filters").addEventListener("click", () => {
    $("task-status-filter").value = "";
    $("task-sort").value = "id";
    $("task-from-date").value = "";
    $("task-to-date").value = "";
    taskOffset = 0;
    refreshTasks();
  });

  $("tasks-prev-page").addEventListener("click", () => {
    if (taskOffset > 0) {
      taskOffset -= taskPageSize;
      refreshTasks();
    }
  });

  $("tasks-next-page").addEventListener("click", () => {
    if (taskOffset + taskPageSize < taskTotal) {
      taskOffset += taskPageSize;
      refreshTasks();
    }
  });

  // WP-112 — Create lead manually
  async function createLead(name, phone, source, interest) {
    if (!bearer) return null;
    const company = opportunities.length > 0 ? opportunities[0].company_id : null;
    if (!company) {notify("Empresa não configurada.", true); return null;}
    const res = await fetch("/leads", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({company_id: company, name, phone, source: source || "manual", interest: interest || null}),
    });
    if (res.status === 403) {disconnect("Permissão de operador necessária."); return null;}
    if (!res.ok) {notify("Falha ao criar lead.", true); return null;}
    return res.json();
  }

  $("show-create-lead").addEventListener("click", () => {
    $("create-lead-form").hidden = false;
    $("new-lead-name").focus();
  });

  $("cancel-create-lead").addEventListener("click", () => {
    $("create-lead-form").hidden = true;
    $("new-lead-name").value = "";
    $("new-lead-phone").value = "";
    $("new-lead-source").value = "";
    $("new-lead-interest").value = "";
  });

  $("create-lead-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const name = $("new-lead-name").value.trim();
    const phone = $("new-lead-phone").value.trim() || null;
    const source = $("new-lead-source").value.trim() || null;
    const interest = $("new-lead-interest").value.trim() || null;
    if (!name) {notify("Nome é obrigatório.", true); return;}
    const button = $("create-lead-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const created = await createLead(name, phone, source, interest);
      if (created) {
        $("create-lead-form").hidden = true;
        $("new-lead-name").value = "";
        $("new-lead-phone").value = "";
        $("new-lead-source").value = "";
        $("new-lead-interest").value = "";
        notify("Lead criado.");
        await refreshLeads();
      }
    });
  });

  // WP-169/170 — Bulk delete handlers
  function updateLeadBulkBar() {
    const bar = $("lead-bulk-bar");
    const count = selectedLeadIds.size;
    $("lead-bulk-selected-count").textContent = count + " selecionado(s)";
    bar.hidden = count === 0;
  }

  function updateCustomerBulkBar() {
    const bar = $("customer-bulk-bar");
    const count = selectedCustomerIds.size;
    $("customer-bulk-selected-count").textContent = count + " selecionado(s)";
    bar.hidden = count === 0;
  }

  $("lead-bulk-clear").addEventListener("click", () => {
    selectedLeadIds.clear();
    refreshLeads();
  });

  $("customer-bulk-clear").addEventListener("click", () => {
    selectedCustomerIds.clear();
    refreshCustomers();
  });

  $("lead-bulk-delete").addEventListener("click", () => {
    const button = $("lead-bulk-delete");
    withButton(button, async () => {
      const ids = Array.from(selectedLeadIds);
      if (!ids.length) {notify("Nenhum lead selecionado.", true); return;}
      try {
        const res = await fetch("/leads/bulk-delete", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + bearer,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({lead_ids: ids}),
        });
        if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
        if (!res.ok) throw new ApiFailure(res.status);
        const result = await res.json();
        selectedLeadIds.clear();
        notify(result.deleted + " lead(s) excluído(s). " + result.skipped.length + " ignorado(s).");
        await refreshLeads();
      } catch (e) {
        if (e instanceof ApiFailure) {notify(e.message, true);}
        else {notify("Falha ao excluir leads.", true);}
      }
    });
  });

  $("customer-bulk-delete").addEventListener("click", () => {
    const button = $("customer-bulk-delete");
    withButton(button, async () => {
      const ids = Array.from(selectedCustomerIds);
      if (!ids.length) {notify("Nenhum customer selecionado.", true); return;}
      try {
        const res = await fetch("/customers/bulk-delete", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + bearer,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({customer_ids: ids}),
        });
        if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
        if (!res.ok) throw new ApiFailure(res.status);
        const result = await res.json();
        selectedCustomerIds.clear();
        notify(result.deleted + " customer(s) excluído(s). " + result.skipped.length + " ignorado(s).");
        await refreshCustomers();
      } catch (e) {
        if (e instanceof ApiFailure) {notify(e.message, true);}
        else {notify("Falha ao excluir customers.", true);}
      }
    });
  });

  // WP-169/170 — Reset selections on refresh
  const origRefreshLeads = refreshLeads;
  refreshLeads = async function(targetId) {
    selectedLeadIds.clear();
    await origRefreshLeads(targetId);
    $("lead-bulk-bar").hidden = true;
  };

  const origRefreshCustomers = refreshCustomers;
  refreshCustomers = async function() {
    selectedCustomerIds.clear();
    await origRefreshCustomers();
    $("customer-bulk-bar").hidden = true;
  };

  // WP-172 — Bulk retry handlers for internal tasks
  function updateTaskBulkBar() {
    const bar = $("task-bulk-bar");
    const count = selectedTaskIds.size;
    $("task-bulk-selected-count").textContent = count + " selecionado(s)";
    bar.hidden = count === 0;
  }

  $("task-bulk-clear").addEventListener("click", () => {
    selectedTaskIds.clear();
    refreshTasks();
  });

  $("task-bulk-retry").addEventListener("click", () => {
    const button = $("task-bulk-retry");
    withButton(button, async () => {
      const ids = Array.from(selectedTaskIds);
      if (!ids.length) {notify("Nenhuma tarefa selecionada.", true); return;}
      try {
        const result = await taskApi("/internal-tasks/bulk-retry", "POST", {task_ids: ids});
        selectedTaskIds.clear();
        notify(result.retried + " tarefa(s) em retry. " + result.skipped.length + " ignorado(s).");
        await refreshTasks();
      } catch (e) {
        notify("Falha ao retry.", true);
      }
    });
  });

  // WP-171 — Bulk decision handlers for review queue
  function updateRqBulkBar() {
    const bar = $("rq-bulk-bar");
    const count = selectedRqIds.size;
    $("rq-bulk-selected-count").textContent = count + " selecionado(s)";
    bar.hidden = count === 0;
  }

  $("rq-bulk-clear").addEventListener("click", () => {
    selectedRqIds.clear();
    refreshReviewQueue();
  });

  $("rq-bulk-approve").addEventListener("click", () => {
    const button = $("rq-bulk-approve");
    withButton(button, async () => {
      const ids = Array.from(selectedRqIds);
      if (!ids.length) {notify("Nenhum item selecionado.", true); return;}
      try {
        const result = await reviewApi("/review-queue/bulk-decision", "POST", {
          item_ids: ids,
          decision: "approve",
        });
        selectedRqIds.clear();
        notify(result.applied + " item(s) aprovado(s). " + result.skipped.length + " ignorado(s).");
        await refreshReviewQueue();
        await refreshList();
      } catch (e) {
        notify("Falha ao aplicar decisão.", true);
      }
    });
  });

  $("rq-bulk-reject").addEventListener("click", () => {
    const button = $("rq-bulk-reject");
    withButton(button, async () => {
      const ids = Array.from(selectedRqIds);
      if (!ids.length) {notify("Nenhum item selecionado.", true); return;}
      try {
        const result = await reviewApi("/review-queue/bulk-decision", "POST", {
          item_ids: ids,
          decision: "reject",
        });
        selectedRqIds.clear();
        notify(result.applied + " item(s) rejeitado(s). " + result.skipped.length + " ignorado(s).");
        await refreshReviewQueue();
      } catch (e) {
        notify("Falha ao aplicar decisão.", true);
      }
    });
  });

  // WP-178/WP-181 — Brief list view with search, sort, pagination
  const briefStatusLabels = {
    draft: "Rascunho",
    ready_for_review: "Pronto para revisão",
    approved: "Aprovado",
  };

  let briefOffset = 0;
  const briefPageSize = 50;
  let briefTotal = 0;
  const selectedBriefIds = new Set();

  async function briefApi(path, method, body) {
    const allowed = path === "/proposal-briefs" || path === "/proposal-briefs/count" ||
      path === "/proposal-briefs/bulk-status" || path === "/proposal-briefs/bulk-delete" ||
      /^\/proposal-briefs\/\d+\/conversations$/.test(path) ||
      /^\/proposal-briefs\/\d+$/.test(path) ||
      path.startsWith("/proposal-briefs?");
    if (!allowed) throw new Error("Path não permitido: " + path);
    const url = path + (path.includes("?") ? "&" : "?") + "t=" + Date.now();
    const res = await fetch(url, {
      method: method || "GET",
      headers: {
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 403) {disconnect("Permissão necessária."); throw new Error("403");}
    if (!res.ok) throw new Error(res.status);
    return res.json();
  }

  function buildBriefUrl() {
    const params = [];
    const status = $("briefs-status-filter") ? $("briefs-status-filter").value : "";
    const q = $("briefs-search") ? $("briefs-search").value.trim() : "";
    const sort = $("briefs-sort") ? $("briefs-sort").value : "created_at";
    const fromDate = $("briefs-from-date") ? $("briefs-from-date").value : "";
    const toDate = $("briefs-to-date") ? $("briefs-to-date").value : "";
    if (status) params.push("status=" + encodeURIComponent(status));
    if (q) params.push("q=" + encodeURIComponent(q));
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    params.push("sort=" + encodeURIComponent(sort));
    params.push("limit=" + briefPageSize);
    params.push("offset=" + briefOffset);
    return "/proposal-briefs" + (params.length ? "?" + params.join("&") : "");
  }

  function buildBriefCountUrl() {
    const params = [];
    const status = $("briefs-status-filter") ? $("briefs-status-filter").value : "";
    const q = $("briefs-search") ? $("briefs-search").value.trim() : "";
    const fromDate = $("briefs-from-date") ? $("briefs-from-date").value : "";
    const toDate = $("briefs-to-date") ? $("briefs-to-date").value : "";
    if (status) params.push("status=" + encodeURIComponent(status));
    if (q) params.push("q=" + encodeURIComponent(q));
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    return "/proposal-briefs/count" + (params.length ? "?" + params.join("&") : "");
  }

  async function refreshBriefs() {
    if (!bearer) return;
    try {
      const [briefs, countData] = await Promise.all([
        briefApi(buildBriefUrl()),
        briefApi(buildBriefCountUrl()),
      ]);
      briefTotal = countData.count || 0;
      renderBriefs(briefs);
      updateBriefPagination();
    } catch (e) {
      console.error("[refreshBriefs]", e);
    }
  }

  function updateBriefPagination() {
    const pag = $("briefs-pagination");
    if (!pag) return;
    if (briefTotal <= briefPageSize) {
      pag.hidden = true;
      return;
    }
    pag.hidden = false;
    const page = Math.floor(briefOffset / briefPageSize) + 1;
    const totalPages = Math.ceil(briefTotal / briefPageSize);
    $("briefs-page-info").textContent = "Página " + page + " de " + totalPages;
    $("briefs-prev-page").disabled = briefOffset === 0;
    $("briefs-next-page").disabled = briefOffset + briefPageSize >= briefTotal;
  }

  function renderBriefs(briefs) {
    const list = $("briefs-list");
    while (list.firstChild) list.removeChild(list.firstChild);
    if (!briefs || briefs.length === 0) {
      const p = document.createElement("p");
      p.className = "small";
      p.textContent = "Nenhum brief encontrado.";
      list.appendChild(p);
      return;
    }
    briefs.forEach((brief) => {
      const item = document.createElement("div");
      item.className = "brief-item";
      item.style.cursor = "pointer";
      // WP-184 — Checkbox for bulk selection
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.className = "briefs-checkbox";
      cb.dataset.id = brief.id;
      cb.addEventListener("change", (e) => {
        e.stopPropagation();
        if (cb.checked) { selectedBriefIds.add(brief.id); }
        else { selectedBriefIds.delete(brief.id); }
        updateBriefBulkBar();
      });
      item.appendChild(cb);
      const title = document.createElement("span");
      title.className = "brief-item-title";
      title.textContent = brief.opportunity_title || "Sem título";
      const ref = document.createElement("span");
      ref.className = "brief-item-ref small";
      ref.textContent = brief.offer_reference || "";
      const status = document.createElement("span");
      status.className = "status-pill";
      status.textContent = briefStatusLabels[brief.status] || brief.status;
      const date = document.createElement("span");
      date.className = "brief-item-date small";
      date.textContent = brief.created_at ? new Date(brief.created_at).toLocaleDateString("pt-BR") : "";
      item.appendChild(title);
      item.appendChild(ref);
      item.appendChild(status);
      item.appendChild(date);
      // WP-187 — Click to show detail panel
      item.addEventListener("click", (e) => {
        if (e.target.type === "checkbox") return;
        selectBrief(brief.id, brief.opportunity_title || "Sem título");
      });
      list.appendChild(item);
    });
  }

  // WP-187 — Load and display brief detail
  async function selectBrief(briefId, title) {
    const detail = $("brief-detail");
    if (!detail) return;
    // Toggle close
    if (!detail.hidden && detail.dataset.briefId == briefId) {
      detail.hidden = true;
      return;
    }
    detail.hidden = false;
    detail.dataset.briefId = briefId;
    const content = $("brief-detail-content");
    if (content) content.textContent = "Carregando...";
    try {
      const [brief, convs] = await Promise.all([
        briefApi("/proposal-briefs/" + briefId),
        briefApi("/proposal-briefs/" + briefId + "/conversations").catch(() => []),
      ]);
      if (content) {
        while (content.firstChild) content.removeChild(content.firstChild);
        const fields = [
          ["Referência", brief.offer_reference],
          ["Status", briefStatusLabels[brief.status] || brief.status],
          ["Oportunidade", title],
          ["Diagnóstico", brief.diagnosis],
          ["Escopo", brief.scope],
          ["Entregáveis", brief.deliverables],
          ["Critérios de aceitação", brief.acceptance_criteria],
        ];
        fields.forEach(([label, value]) => {
          const row = document.createElement("div");
          row.className = "detail-field";
          const labelEl = document.createElement("span");
          labelEl.className = "detail-field-label";
          labelEl.textContent = label + ":";
          const valueEl = document.createElement("span");
          valueEl.className = "detail-field-value";
          valueEl.textContent = value || "—";
          row.appendChild(labelEl);
          row.appendChild(valueEl);
          content.appendChild(row);
        });
        // WP-188 — Related conversations
        if (convs && convs.length > 0) {
          const convHeader = document.createElement("div");
          convHeader.className = "detail-field";
          convHeader.style.marginTop = "10px";
          const convLabel = document.createElement("span");
          convLabel.className = "detail-field-label";
          convLabel.textContent = "Conversas relacionadas:";
          convHeader.appendChild(convLabel);
          content.appendChild(convHeader);
          convs.forEach((c) => {
            const convRow = document.createElement("div");
            convRow.className = "detail-field";
            convRow.style.paddingLeft = "10px";
            const convText = document.createElement("span");
            convText.className = "detail-field-value";
            convText.textContent = c.channel + " — " + c.status;
            convRow.appendChild(convText);
            content.appendChild(convRow);
          });
        }
      }
    } catch (e) {
      if (content) content.textContent = "Falha ao carregar brief.";
    }
  }

  // WP-184 — Bulk status handlers for briefs
  function updateBriefBulkBar() {
    const bar = $("briefs-bulk-bar");
    const count = selectedBriefIds.size;
    $("briefs-bulk-selected-count").textContent = count + " selecionado(s)";
    bar.hidden = count === 0;
  }

  $("briefs-bulk-clear").addEventListener("click", () => {
    selectedBriefIds.clear();
    refreshBriefs().catch(() => {});
  });

  $("briefs-bulk-apply").addEventListener("click", () => {
    const button = $("briefs-bulk-apply");
    withButton(button, async () => {
      const ids = Array.from(selectedBriefIds);
      if (!ids.length) {notify("Nenhum brief selecionado.", true); return;}
      const status = $("briefs-bulk-status").value;
      try {
        const result = await briefApi("/proposal-briefs/bulk-status", "POST", {
          brief_ids: ids,
          status: status,
        });
        selectedBriefIds.clear();
        notify(result.updated + " brief(s) atualizado(s). " + result.skipped.length + " ignorado(s).");
        await refreshBriefs();
      } catch (e) {
        notify("Falha ao atualizar status.", true);
      }
    });
  });

  $("briefs-bulk-delete").addEventListener("click", () => {
    const button = $("briefs-bulk-delete");
    withButton(button, async () => {
      const ids = Array.from(selectedBriefIds);
      if (!ids.length) {notify("Nenhum brief selecionado.", true); return;}
      if (!confirm("Excluir " + ids.length + " brief(s)?")) return;
      try {
        const result = await briefApi("/proposal-briefs/bulk-delete", "POST", {
          brief_ids: ids,
        });
        selectedBriefIds.clear();
        notify(result.deleted + " brief(s) excluído(s). " + result.skipped.length + " ignorado(s).");
        await refreshBriefs();
      } catch (e) {
        notify("Falha ao excluir briefs.", true);
      }
    });
  });

  // Reset brief selection on refresh
  const origRefreshBriefs = refreshBriefs;
  refreshBriefs = async function() {
    selectedBriefIds.clear();
    $("briefs-bulk-bar").hidden = true;
    await origRefreshBriefs();
  };

  $("briefs-refresh").addEventListener("click", () => withButton($("briefs-refresh"), async () => {
    briefOffset = 0;
    await refreshBriefs();
  }));

  $("briefs-status-filter").addEventListener("change", () => {
    briefOffset = 0;
    refreshBriefs().catch(() => {});
  });

  $("briefs-sort").addEventListener("change", () => {
    briefOffset = 0;
    refreshBriefs().catch(() => {});
  });

  $("briefs-search").addEventListener("input", debounce(() => {
    briefOffset = 0;
    refreshBriefs().catch(() => {});
  }, 300));

  $("briefs-from-date").addEventListener("change", () => {
    briefOffset = 0;
    refreshBriefs().catch(() => {});
  });

  $("briefs-to-date").addEventListener("change", () => {
    briefOffset = 0;
    refreshBriefs().catch(() => {});
  });

  $("briefs-prev-page").addEventListener("click", () => {
    briefOffset = Math.max(0, briefOffset - briefPageSize);
    refreshBriefs().catch(() => {});
  });

  $("briefs-next-page").addEventListener("click", () => {
    briefOffset += briefPageSize;
    refreshBriefs().catch(() => {});
  });

  $("briefs-clear-filters").addEventListener("click", () => {
    if ($("briefs-status-filter")) $("briefs-status-filter").value = "";
    if ($("briefs-search")) $("briefs-search").value = "";
    if ($("briefs-sort")) $("briefs-sort").value = "created_at";
    if ($("briefs-from-date")) $("briefs-from-date").value = "";
    if ($("briefs-to-date")) $("briefs-to-date").value = "";
    briefOffset = 0;
    refreshBriefs().catch(() => {});
  });

  $("briefs-export-csv").addEventListener("click", () => {
    const params = [];
    const status = $("briefs-status-filter") ? $("briefs-status-filter").value : "";
    const q = $("briefs-search") ? $("briefs-search").value.trim() : "";
    const fromDate = $("briefs-from-date") ? $("briefs-from-date").value : "";
    const toDate = $("briefs-to-date") ? $("briefs-to-date").value : "";
    if (status) params.push("status=" + encodeURIComponent(status));
    if (q) params.push("q=" + encodeURIComponent(q));
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    const url = "/proposal-briefs/export.csv" + (params.length ? "?" + params.join("&") : "");
    downloadCsv(url, "proposal-briefs.csv");
    notify("Exportando briefs...");
  });

  // Reset brief offset on disconnect
  const origDisconnect = disconnect;
  // (disconnect already handles interval cleanup)

  // Load briefs on workspace visible
  workspaceObserver.observe($("briefs-list") ? $("briefs-list").closest(".panel") : null, {attributes: true});

})();
