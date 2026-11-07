"use strict";

// Piloto local: Bearer apenas em memória desta aba. Nunca logar ou persistir.
(() => {
  const $ = (id) => document.getElementById(id);

  let bearer = null;
  let sessionEpoch = 0;
  let reviewEpoch = 0;
  let briefEpoch = 0;
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
  let opportunityLeadId = null;
  let opportunityCustomerId = null;
  let opportunityContactType = null;
  let opportunityCompanyId = null;
  let selectionVersion = 0;
  let conversations = [];
  let selectedConvId = null;
  let convFilterChannel = "";
  let convFilterStatus = "";
  let convFilterQuery = "";
  let convFilterCustomerId = "";
  let convFilterLeadId = "";
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
  let messageLoadEpoch = 0;
  let conversationNoteVersion = 0;
  let conversationNoteReady = false;
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
  // WP-190 — sourceLabels for opportunity sources
  const sourceLabels = {
    manual: "Manual",
    intake: "Intake comercial",
    review_queue: "Fila de revisão",
    import: "Importação CSV",
    "99freelas": "99Freelas",
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

  // WP-276 — Update opportunity progress bar
  function updateOppProgress(nextAction) {
    const progressMap = {
      pending: 10,
      follow: 25,
      prepare_proposal: 40,
      in_progress: 70,
      done: 100,
      lost: 50,
      ignore: 50,
    };
    const percent = progressMap[nextAction] || 0;
    $("opp-progress-fill").style.width = percent + "%";
    $("opp-progress-fill").setAttribute("aria-valuenow", String(percent));
    $("opp-progress-percent").textContent = percent + "%";
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
    // WP-201 — Reset triage option visibility for next selection
    for (const option of $("next-action").querySelectorAll("option")) {
      option.hidden = false;
      option.disabled = false;
    }
    // WP-238 — Hide triage suggestion panel
    $("triage-suggestion-panel").hidden = true;
    triageSuggestion = null;
    // WP-241 — Hide brief suggestion panel
    $("brief-suggestion-panel").hidden = true;
    briefSuggestion = null;
    // WP-249 — Hide bulk suggestion panel
    $("bulk-suggestion-panel").hidden = true;
    bulkTriageSuggestion = null;
    // WP-278 — Hide create conversation form
    if ($("opp-create-conv")) $("opp-create-conv").hidden = true;
    if ($("opp-conv-form")) $("opp-conv-form").hidden = true;
    if ($("opp-conv-suggestion")) $("opp-conv-suggestion").hidden = true;
    opportunityLeadId = null;
    opportunityCustomerId = null;
    opportunityContactType = null;
    opportunityCompanyId = null;
  }

  function disconnect(message = "Acesso desconectado.") {
    sessionEpoch += 1;
    bearer = null;
    reviewEpoch += 1;
    briefEpoch += 1;
    $("briefs-load-status").textContent = "";
    $("briefs-load-retry").hidden = true;
    $("briefs-list").setAttribute("aria-busy", "false");
    reviewOffset = 0;
    reviewTotal = 0;
    oppOffset = 0;
    oppTotal = 0;
    $("rq-list").replaceChildren();
    $("rq-load-status").textContent = "";
    $("rq-load-retry").hidden = true;
    $("rq-list").setAttribute("aria-busy", "false");
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
    $("opp-load-status").textContent = "";
    $("opp-load-retry").hidden = true;
    $("opportunity-list").setAttribute("aria-busy", "false");
    $("list-meta").textContent = "Nenhuma consulta realizada.";
    $("capture-form").reset();
    conversations = [];
    $("conv-load-status").textContent = "";
    $("conv-load-retry").hidden = true;
    $("conv-list").setAttribute("aria-busy", "false");
    selectedConvId = null;
    convFilterChannel = "";
    convFilterStatus = "";
    convFilterQuery = "";
    convFilterCustomerId = "";
    convFilterLeadId = "";
    convFilterSort = "last_message";
    convOffset = 0;
    convTotal = 0;
    msgOffset = 0;
    msgTotal = 0;
    oppPipelineFilter = "all";
    convCustomerFilterPopulated = false;
    convLeadFilterPopulated = false;
    stopDashboardRefresh();
    stopNotificationRefresh();
    // WP-264 — Hide reply template section
    $("reply-template-section").hidden = true;
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
    // WP-238 — allow /opportunities/priority
    // WP-142 — allow /opportunities/{id}/conversations
    // WP-143 — allow /opportunities/{id}/timeline
    // WP-144 — allow /opportunities/{id}/leads
    // WP-238 — allow POST /opportunities/{id}/suggest-triage
    // WP-241 — allow POST /opportunities/{id}/suggest-brief
    // WP-247 — allow POST /opportunities/bulk-suggest-triage
    if (!/^\/opportunities(\?[^"]*)?$/.test(path) &&
        !/^\/opportunities\/count(\?[^"]*)?$/.test(path) &&
        !/^\/opportunities\/pipeline-summary$/.test(path) &&
        !/^\/opportunities\/priority(\?[^"]*)?$/.test(path) &&
        !/^\/opportunities\/(bulk-triage|bulk-delete|bulk-suggest-triage|import\.csv)$/.test(path) &&
        !/^\/opportunities\/\d+(\/(triage|proposal-brief|conversations|linked-conversations|leads|linked-leads|linked-customers|timeline|suggest-triage|suggest-brief)(\/approve|\/reject)?)?$/.test(path)) {
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
    // Preserve server ordering, including priority and paginated results.
    const ordered = opportunities;
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
      wrapper.setAttribute("role", "listitem");
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
      // WP-238 — Priority badge
      if (opportunity.priority_level) {
        const priorityBadge = document.createElement("span");
        priorityBadge.className = "opp-priority-badge opp-priority-" + opportunity.priority_level;
        const priorityLabels = {high: "🔴 Alta", medium: "🟡 Média", low: "🟢 Baixa"};
        priorityBadge.textContent = priorityLabels[opportunity.priority_level] || "";
        titleRow.append(priorityBadge);
      }
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
    const session = sessionEpoch;
    const isCurrent = () => selectionVersion === version && selectedId === id && sessionEpoch === session;
    const retry = $("brief-load-retry");
    retry.hidden = true;
    retry.disabled = true;
    $("brief-status").textContent = "Carregando";
    try {
      const brief = await api("/opportunities/" + id + "/proposal-brief");
      if (isCurrent()) displayBrief(brief);
    } catch (error) {
      if (!isCurrent()) return;
      if (error instanceof ApiFailure && error.status === 404) {
        displayBrief(null);
        return;
      }
      $("brief-form").hidden = true;
      $("brief-status").textContent = "Consulta indisponível";
      retry.hidden = false;
      notify("Não foi possível consultar o ProposalBrief.", true);
    } finally {
      if (isCurrent()) retry.disabled = false;
    }
  }

  $("brief-load-retry").addEventListener("click", () => {
    if (selectedId === null) return;
    return loadBrief(selectedId, selectionVersion);
  });

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
    $("opp-timeline-list").replaceChildren();
    opportunityLeadId = null;
    opportunityCustomerId = null;
    opportunityContactType = null;
    opportunityCompanyId = null;
    if ($("opp-create-conv")) $("opp-create-conv").hidden = true;
    if ($("opp-conv-form")) $("opp-conv-form").hidden = true;
    if ($("opp-conv-suggestion")) $("opp-conv-suggestion").hidden = true;
    for (const listId of ["opp-conv-list", "opp-leads-list", "opp-customers-list"]) {
      const list = $(listId);
      if (!list) continue;
      list.setAttribute("aria-busy", "true");
      list.replaceChildren();
      const loading = document.createElement("p");
      loading.className = "small";
      loading.setAttribute("role", "status");
      loading.textContent = "Carregando…";
      list.appendChild(loading);
    }
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
    text("selected-source", sourceLabels[record.source] || record.source || "");
    text("selected-captured-at", record.captured_at
      ? new Date(record.captured_at).toLocaleString("pt-BR") : "");
    text("selected-triage-note", record.triage_note || "");
    text("selected-url", record.external_url);
    text("selected-budget", record.budget);
    text("selected-deadline", record.deadline);
    text("selected-requirements", record.requirements);
    // WP-201 — Filter triage options based on valid transitions
    const _VALID_TRANSITIONS = {
      pending: ["pending", "follow", "ignore", "prepare_proposal", "in_progress"],
      ignore: ["ignore"],
      follow: ["pending", "follow", "ignore", "prepare_proposal", "in_progress"],
      prepare_proposal: ["pending", "follow", "prepare_proposal", "in_progress"],
      in_progress: ["in_progress", "done", "lost"],
      done: ["done"],
      lost: ["lost"],
    };
    const allowed = _VALID_TRANSITIONS[record.next_action] || [];
    const nextActionSelect = $("next-action");
    for (const option of nextActionSelect.querySelectorAll("option")) {
      option.hidden = !allowed.includes(option.value);
      option.disabled = !allowed.includes(option.value);
    }
    nextActionSelect.value = record.next_action;
    // WP-276 — Update progress bar
    updateOppProgress(record.next_action);
    $("triage-note").value = record.triage_note || "";
    // WP-113 — populate standalone note editor
    $("opp-note").value = record.triage_note || "";
    $("brief-status").textContent = "Carregando";
    showList();

    // WP-108 — always attempt to load brief, regardless of status
    await loadBrief(id, version);
    // WP-142 — load related conversations
    await loadOpportunityConversations(id, version);
    // WP-143 — load activity timeline
    await loadOpportunityTimeline(id, version);
    // WP-144 — load related leads
    await loadOpportunityLeads(id, version);
    await loadOpportunityCustomers(id, version);
    if (version !== selectionVersion || id !== selectedId) return;
    for (const listId of ["opp-conv-list", "opp-leads-list", "opp-customers-list"]) {
      const list = $(listId);
      if (list) list.setAttribute("aria-busy", "false");
    }
    // WP-278 — Show/hide create conversation button
    if ($("opp-create-conv")) $("opp-create-conv").hidden = opportunityContactType === null;
    if ($("opp-conv-form")) $("opp-conv-form").hidden = true;
    if ($("opp-conv-suggestion")) $("opp-conv-suggestion").hidden = true;
  }

  // WP-142 — Load conversations related to the selected opportunity
  async function loadOpportunityConversations(id, expectedVersion) {
    const expectedSession = sessionEpoch;
    const isCurrent = () => expectedSession === sessionEpoch &&
      expectedVersion === selectionVersion && id === selectedId;
    const status = $("opp-conv-status");
    const retry = $("opp-conv-retry");
    const list = $("opp-conv-list");
    status.textContent = "Carregando conversas…";
    retry.hidden = true;
    retry.disabled = true;
    list.setAttribute("aria-busy", "true");
    try {
      const conversations = await api("/opportunities/" + id + "/linked-conversations");
      if (!isCurrent()) return;
      list.replaceChildren();
      if (!conversations || !conversations.length) {
        status.textContent = "";
        const empty = document.createElement("p");
        empty.className = "small";
        empty.setAttribute("role", "status");
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
      if (!isCurrent()) return;
      status.textContent = "";
      for (let idx = 0; idx < conversations.length; idx++) {
        const conv = conversations[idx];
        const item = document.createElement("div");
        item.className = "opp-conv-item";
        item.setAttribute("role", "listitem");
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
        item.tabIndex = 0;
        item.setAttribute("role", "button");
        item.setAttribute("aria-label", "Abrir conversa #" + conv.id);
        item.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            item.click();
          }
        });
        list.appendChild(item);
      }
    } catch (error) {
      if (!isCurrent()) return;
      list.replaceChildren();
      const errorState = document.createElement("p");
      errorState.className = "small";
      errorState.textContent = "Não foi possível carregar as conversas.";
      list.appendChild(errorState);
      status.textContent = "Falha ao carregar conversas da oportunidade.";
      retry.hidden = false;
    } finally {
      if (isCurrent()) {
        list.setAttribute("aria-busy", "false");
        retry.disabled = false;
      }
    }
  }

  $("opp-conv-retry").addEventListener("click", () => {
    if (selectedId === null) return;
    loadOpportunityConversations(selectedId, selectionVersion).catch(() => {});
  });

  // WP-143 — Load activity timeline for the selected opportunity
  async function loadOpportunityTimeline(id, expectedVersion) {
    const session = sessionEpoch;
    const isCurrent = () => expectedVersion === selectionVersion &&
      id === selectedId && session === sessionEpoch;
    if (!isCurrent()) return;
    const list = $("opp-timeline-list");
    const status = $("opp-timeline-status");
    const retry = $("opp-timeline-retry");
    status.textContent = "Carregando atividades…";
    retry.hidden = true;
    retry.disabled = true;
    list.setAttribute("aria-busy", "true");
    list.replaceChildren();
    try {
      const events = await api("/opportunities/" + id + "/timeline");
      if (!isCurrent()) return;
      list.replaceChildren();
      if (!events || !events.length) {
        status.textContent = "";
        const empty = document.createElement("p");
        empty.className = "small";
        empty.setAttribute("role", "status");
        empty.textContent = "Nenhuma atividade registrada.";
        list.appendChild(empty);
        return;
      }
      status.textContent = "";
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
      if (isCurrent()) {
        list.replaceChildren();
        status.textContent = "Falha ao carregar atividades da oportunidade.";
        retry.hidden = false;
      }
    } finally {
      if (isCurrent()) {
        list.setAttribute("aria-busy", "false");
        retry.disabled = false;
      }
    }
  }

  $("opp-timeline-retry").addEventListener("click", () => {
    if (selectedId === null) return;
    return loadOpportunityTimeline(selectedId, selectionVersion).catch(() => {});
  });

  // WP-144 — Load leads related to the selected opportunity
  async function loadOpportunityLeads(id, expectedVersion) {
    const expectedSession = sessionEpoch;
    const isCurrent = () => expectedSession === sessionEpoch &&
      expectedVersion === selectionVersion && id === selectedId;
    const status = $("opp-leads-status");
    const retry = $("opp-leads-retry");
    const list = $("opp-leads-list");
    status.textContent = "Carregando leads…";
    retry.hidden = true;
    retry.disabled = true;
    list.setAttribute("aria-busy", "true");
    try {
      const leads = await api("/opportunities/" + id + "/linked-leads");
      if (!isCurrent()) return;
      list.replaceChildren();
      if (!leads || !leads.length) {
        status.textContent = "";
        opportunityLeadId = null;
        opportunityContactType = null;
        opportunityCompanyId = null;
        const empty = document.createElement("p");
        empty.className = "small";
        empty.setAttribute("role", "status");
        empty.textContent = "Nenhum lead registrado.";
        list.appendChild(empty);
        return;
      }
      for (const lead of leads) {
        opportunityLeadId = lead.id;
        opportunityContactType = "lead";
        opportunityCompanyId = lead.company_id;
        const item = document.createElement("div");
        item.className = "opp-lead-item";
        item.setAttribute("role", "listitem");
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
          showLeadDetail(lead);
        });
        item.tabIndex = 0;
        item.setAttribute("role", "button");
        item.setAttribute("aria-label", "Abrir lead " + (lead.name || "sem nome"));
        item.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            showLeadDetail(lead);
          }
        });
        list.appendChild(item);
      }
      status.textContent = "";
    } catch (error) {
      if (!isCurrent()) return;
      opportunityLeadId = null;
      opportunityCompanyId = null;
      list.replaceChildren();
      const errorState = document.createElement("p");
      errorState.className = "small";
      errorState.setAttribute("role", "status");
      errorState.textContent = "Não foi possível carregar os leads.";
      list.appendChild(errorState);
      status.textContent = "Falha ao carregar leads da oportunidade.";
      retry.hidden = false;
    } finally {
      if (isCurrent()) {
        list.setAttribute("aria-busy", "false");
        retry.disabled = false;
      }
    }
  }

  $("opp-leads-retry").addEventListener("click", () => {
    if (selectedId === null) return;
    loadOpportunityLeads(selectedId, selectionVersion).catch(() => {});
  });

  async function loadOpportunityCustomers(id, expectedVersion) {
    const expectedSession = sessionEpoch;
    const isCurrent = () => !(expectedSession !== sessionEpoch ||
      expectedVersion !== selectionVersion || id !== selectedId);
    const status = $("opp-customers-status");
    const retry = $("opp-customers-retry");
    const list = $("opp-customers-list");
    status.textContent = "Carregando clientes…";
    retry.hidden = true;
    retry.disabled = true;
    list.setAttribute("aria-busy", "true");
    try {
      const customers = await api("/opportunities/" + id + "/linked-customers");
      if (!isCurrent()) return;
      list.replaceChildren();
      if (!customers || !customers.length) {
        status.textContent = "";
        const empty = document.createElement("p");
        empty.className = "small";
        empty.setAttribute("role", "status");
        empty.textContent = "Nenhum cliente registrado.";
        list.appendChild(empty);
        return;
      }
      for (const customer of customers || []) {
        opportunityCustomerId = customer.id;
        opportunityCompanyId = customer.company_id;
        opportunityContactType = "customer";
        const item = document.createElement("div");
        item.className = "opp-lead-item";
        item.setAttribute("role", "listitem");
        const title = document.createElement("strong");
        title.textContent = customer.name || "Sem nome";
        const meta = document.createElement("span");
        meta.className = "small";
        const parts = ["Cliente"];
        if (customer.phone) parts.push(customer.phone);
        if (customer.status) parts.push("(" + customer.status + ")");
        meta.textContent = " " + parts.join(" · ");
        item.append(title, meta);
        item.tabIndex = 0;
        item.setAttribute("role", "button");
        item.setAttribute("aria-label", "Abrir cliente " + (customer.name || "sem nome"));
        const openCustomer = () => {
          const openDetail = showCustomerDeta\u0069l;
          openDetail(customer);
        };
        item.addEventListener("click", openCustomer);
        item.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openCustomer();
          }
        });
        list.appendChild(item);
      }
      status.textContent = "";
    } catch (error) {
      if (!isCurrent()) return;
      list.replaceChildren();
      const errorState = document.createElement("p");
      errorState.className = "small";
      errorState.setAttribute("role", "status");
      errorState.textContent = "Não foi possível carregar os clientes.";
      list.appendChild(errorState);
      status.textContent = "Falha ao carregar clientes da oportunidade.";
      retry.hidden = false;
    } finally {
      if (isCurrent()) {
        list.setAttribute("aria-busy", "false");
        retry.disabled = false;
      }
    }
  }

  $("opp-customers-retry").addEventListener("click", () => {
    if (selectedId === null) return;
    loadOpportunityCustomers(selectedId, selectionVersion).catch(() => {});
  });

  async function refreshList(preferId = selectedId) {
    const list = $("opportunity-list");
    const status = $("opp-load-status");
    status.textContent = "Carregando oportunidades...";
    $("opp-load-retry").hidden = true;
    list.setAttribute("aria-busy", "true");
    try {
      await loadOpportunityList(preferId);
      $("opp-load-retry").hidden = true;
      status.textContent = "";
      return true;
    } catch (error) {
      status.textContent = "Não foi possível atualizar as oportunidades. Os dados anteriores podem estar desatualizados.";
      $("opp-load-retry").hidden = false;
      return false;
    } finally {
      list.setAttribute("aria-busy", "false");
    }
  }

  async function loadOpportunityList(preferId = selectedId) {
    const showArchived = $("show-archived").checked;
    // WP-094 — opportunity search
    const searchQuery = $("opp-search").value.trim();
    // WP-095 — opportunity sort and pagination
    const sort = $("opp-sort").value;
    // WP-150 — date filter
    const fromDate = $("opp-from-date").value || null;
    const toDate = $("opp-to-date").value || null;
    // WP-189 — source filter
    const source = $("opp-source-filter") ? $("opp-source-filter").value : "";
    // WP-263 — lead and customer filters
    const leadId = $("opp-lead-filter") ? $("opp-lead-filter").value : "";
    const customerId = $("opp-customer-filter") ? $("opp-customer-filter").value : "";
    // WP-266 — priority level filter
    const priorityLevel = $("opp-priority-filter") ? $("opp-priority-filter").value : "";
    // WP-238 — priority sort uses dedicated endpoint
    if (sort === "priority") {
      const result = await api("/opportunities/priority?limit=" + oppPageSize);
      if (!Array.isArray(result)) {
        throw new Error("Resposta de prioridade inválida.");
      }
      opportunities = result.map((item) => ({
        id: item.id,
        title: item.title,
        description: "",
        next_action: item.next_action,
        budget: item.budget,
        deadline: item.deadline,
        source: item.source,
        external_url: "",
        captured_at: "",
        triage_note: "",
        priority_score: item.priority_score,
        priority_level: item.priority_level,
      }));
      oppTotal = opportunities.length;
      // Update pipeline counts from count endpoint
      const countParams = [];
      if (!showArchived) countParams.push("exclude_archived=true");
      const countResult = await api("/opportunities/count" + (countParams.length ? "?" + countParams.join("&") : ""));
      oppTotal = countResult.total || 0;
      const pipelineResult = await api("/opportunities/pipeline-summary");
      for (const [status, count] of Object.entries(pipelineResult || {})) {
        const countEl = document.querySelector('[data-count="' + status + '"]');
        if (countEl) countEl.textContent = count;
      }
      document.querySelectorAll('.opp-pipeline-chip').forEach((chip) => {
        chip.classList.toggle('active', chip.getAttribute('data-pipeline') === oppPipelineFilter);
      });
    } else {
      const params = [];
      if (!showArchived) params.push("exclude_archived=true");
      if (oppPipelineFilter !== "all") params.push("next_action=" + encodeURIComponent(oppPipelineFilter));
      if (source) params.push("source=" + encodeURIComponent(source));
      if (searchQuery) params.push("q=" + encodeURIComponent(searchQuery));
      if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
      if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
      if (leadId) params.push("lead_id=" + encodeURIComponent(leadId));
      if (customerId) params.push("customer_id=" + encodeURIComponent(customerId));
      if (priorityLevel) params.push("priority_level=" + encodeURIComponent(priorityLevel));
      params.push("sort=" + encodeURIComponent(sort));
      params.push("limit=" + oppPageSize);
      params.push("offset=" + oppOffset);
      const query = "?" + params.join("&");
      const countParams = [];
      if (!showArchived) countParams.push("exclude_archived=true");
      if (oppPipelineFilter !== "all") countParams.push("next_action=" + encodeURIComponent(oppPipelineFilter));
      if (source) countParams.push("source=" + encodeURIComponent(source));
      if (searchQuery) countParams.push("q=" + encodeURIComponent(searchQuery));
      if (fromDate) countParams.push("from_date=" + encodeURIComponent(fromDate));
      if (toDate) countParams.push("to_date=" + encodeURIComponent(toDate));
      if (leadId) countParams.push("lead_id=" + encodeURIComponent(leadId));
      if (customerId) countParams.push("customer_id=" + encodeURIComponent(customerId));
      if (priorityLevel) countParams.push("priority_level=" + encodeURIComponent(priorityLevel));
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
    }
    // WP-091 — pending badge
    const pending = opportunities.filter((o) => o.next_action === "pending").length;
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

  // WP-189 — Opportunity source filter
  if ($("opp-source-filter")) {
    $("opp-source-filter").addEventListener("change", () => {
      oppOffset = 0;
      refreshList();
    });
  }

  // WP-150 — Date filter
  $("opp-from-date").addEventListener("change", () => {
    oppOffset = 0;
    refreshList();
  });
  $("opp-to-date").addEventListener("change", () => {
    oppOffset = 0;
    refreshList();
  });

  // WP-263 — Opportunity lead and customer filters
  if ($("opp-lead-filter")) {
    $("opp-lead-filter").addEventListener("change", () => {
      oppOffset = 0;
      refreshList();
    });
  }
  if ($("opp-customer-filter")) {
    $("opp-customer-filter").addEventListener("change", () => {
      oppOffset = 0;
      refreshList();
    });
  }
  // WP-266 — Opportunity priority level filter
  if ($("opp-priority-filter")) {
    $("opp-priority-filter").addEventListener("change", () => {
      oppOffset = 0;
      refreshList();
    });
  }

  // WP-150 — Clear all filters
  $("opp-clear-filters").addEventListener("click", () => {
    $("opp-search").value = "";
    $("opp-from-date").value = "";
    $("opp-to-date").value = "";
    $("opp-sort").value = "id";
    if ($("opp-source-filter")) $("opp-source-filter").value = "";
    if ($("opp-lead-filter")) $("opp-lead-filter").value = "";
    if ($("opp-customer-filter")) $("opp-customer-filter").value = "";
    if ($("opp-priority-filter")) $("opp-priority-filter").value = "";
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

  // WP-238 — AI-assisted triage suggestion
  let triageSuggestion = null;
  // WP-241 — AI-assisted brief suggestion
  let briefSuggestion = null;

  $("suggest-triage-button").addEventListener("click", () => withButton($("suggest-triage-button"), async () => {
    if (selectedId === null) {
      notify("Selecione uma oportunidade.", true);
      return;
    }
    try {
      triageSuggestion = await api("/opportunities/" + selectedId + "/suggest-triage", "POST");
      renderTriageSuggestion();
      $("triage-suggestion-panel").hidden = false;
      $("triage-suggestion-panel").scrollIntoView({behavior: "smooth", block: "center"});
    } catch (error) {
      if (error instanceof ApiFailure) {
        if (error.status === 503) {
          notify("Serviço de agente indisponível.", true);
        } else {
          notify(error.message, true);
        }
      } else {
        notify("Falha ao obter sugestão.", true);
      }
    }
  }));

  $("apply-suggestion-button").addEventListener("click", () => {
    if (!triageSuggestion || !selectedId) return;
    const action = triageSuggestion.suggested_action;
    $("next-action").value = action;
    if (triageSuggestion.reasoning) {
      $("triage-note").value = triageSuggestion.reasoning;
    }
    $("triage-suggestion-panel").hidden = true;
    triageSuggestion = null;
    notify("Sugestão aplicada no formulário de triagem.");
  });

  $("dismiss-suggestion-button").addEventListener("click", () => {
    $("triage-suggestion-panel").hidden = true;
    triageSuggestion = null;
  });

  // WP-241 — AI-assisted brief suggestion
  $("suggest-brief-button").addEventListener("click", () => withButton($("suggest-brief-button"), async () => {
    if (selectedId === null) {
      notify("Selecione uma oportunidade.", true);
      return;
    }
    try {
      briefSuggestion = await api("/opportunities/" + selectedId + "/suggest-brief", "POST");
      renderBriefSuggestion();
      $("brief-suggestion-panel").hidden = false;
      $("brief-suggestion-panel").scrollIntoView({behavior: "smooth", block: "center"});
    } catch (error) {
      if (error instanceof ApiFailure) {
        if (error.status === 503) {
          notify("Serviço de agente indisponível.", true);
        } else {
          notify(error.message, true);
        }
      } else {
        notify("Falha ao obter sugestão.", true);
      }
    }
  }));

  // WP-242 — Apply brief suggestion to form
  $("apply-brief-suggestion-button").addEventListener("click", () => {
    if (!briefSuggestion) return;
    $("brief-offer").value = briefSuggestion.offer_reference || "";
    $("brief-diagnosis").value = briefSuggestion.diagnosis || "";
    $("brief-scope").value = briefSuggestion.scope || "";
    $("brief-deliverables").value = briefSuggestion.deliverables || "";
    $("brief-acceptance").value = briefSuggestion.acceptance_criteria || "";
    $("brief-assumptions").value = briefSuggestion.assumptions || "";
    $("brief-risks").value = briefSuggestion.risks || "";
    $("brief-suggestion-panel").hidden = true;
    briefSuggestion = null;
    // Show and scroll to brief form
    $("brief-form").hidden = false;
    $("brief-panel").hidden = false;
    $("brief-panel").scrollIntoView({behavior: "smooth", block: "start"});
    notify("Brief preenchido com a sugestão.");
  });

  $("dismiss-brief-suggestion-button").addEventListener("click", () => {
    $("brief-suggestion-panel").hidden = true;
    briefSuggestion = null;
  });

  function renderBriefSuggestion() {
    if (!briefSuggestion) return;
    const content = $("brief-suggestion-content");
    content.textContent = "";
    const fields = [
      { key: "offer_reference", label: "Referência" },
      { key: "diagnosis", label: "Diagnóstico" },
      { key: "scope", label: "Escopo" },
      { key: "deliverables", label: "Entregáveis" },
      { key: "acceptance_criteria", label: "Critérios de aceite" },
      { key: "assumptions", label: "Premissas" },
      { key: "risks", label: "Riscos" },
    ];
    for (const field of fields) {
      const val = briefSuggestion[field.key];
      if (val) {
        const p = document.createElement("p");
        const strong = document.createElement("strong");
        strong.textContent = field.label + ": ";
        p.appendChild(strong);
        p.appendChild(document.createTextNode(val));
        content.appendChild(p);
      }
    }
  }

  function renderTriageSuggestion() {
    if (!triageSuggestion) return;
    const actionLabels = {
      pending: "Pendente",
      follow: "Acompanhar",
      ignore: "Ignorar",
      prepare_proposal: "Preparar proposta",
      in_progress: "Em andamento",
      done: "Concluída",
      lost: "Perdida",
    };
    const content = $("triage-suggestion-content");
    content.textContent = "";

    const actionEl = document.createElement("p");
    actionEl.appendChild(document.createTextNode("Ação sugerida: " + (actionLabels[triageSuggestion.suggested_action] || triageSuggestion.suggested_action)));
    content.appendChild(actionEl);

    if (triageSuggestion.reasoning) {
      const reasoningEl = document.createElement("p");
      reasoningEl.appendChild(document.createTextNode("Justificativa: " + triageSuggestion.reasoning));
      content.appendChild(reasoningEl);
    }

    if (triageSuggestion.confidence !== null && triageSuggestion.confidence !== undefined) {
      const confEl = document.createElement("p");
      confEl.appendChild(document.createTextNode("Confiança: " + Math.round(triageSuggestion.confidence * 100) + "%"));
      content.appendChild(confEl);
    }
  }

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
    const id = selectedId, version = selectionVersion, epoch = sessionEpoch;
    const isCurrent = () => id === selectedId && version === selectionVersion && epoch === sessionEpoch;
    const triageNote = $("opp-note").value;
    try {
      const updated = await api("/opportunities/" + id, {
        method: "PATCH",
        body: { triage_note: triageNote.trim() || null },
      });
      if (!isCurrent()) return;
      const idx = opportunities.findIndex((o) => o.id === id);
      if (idx !== -1) {
        opportunities[idx] = updated;
      }
      $("triage-note").value = updated.triage_note || "";
      $("opp-note").value = updated.triage_note || "";
      notify("Nota salva.");
    } catch (error) {
      if (!isCurrent()) return;
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
    const id = selectedId;
    const version = selectionVersion;
    const epoch = sessionEpoch;
    const isCurrent = () => id === selectedId && version === selectionVersion && epoch === sessionEpoch;
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
      const updated = await api("/opportunities/" + id, {
        method: "PATCH",
        body: { title, description },
      });
      // Update in-memory list
      if (!isCurrent()) return;
      const idx = opportunities.findIndex((o) => o.id === id);
      if (idx !== -1) {
        opportunities[idx] = updated;
      }
      $("edit-title").value = updated.title;
      $("edit-description").value = updated.description;
      notify("Oportunidade atualizada.");
      // Re-render list to reflect title changes
      showList();
    } catch (error) {
      if (!isCurrent()) return;
      if (error instanceof ApiFailure) {
        notify(error.message, true);
      } else {
        notify("Falha ao salvar alterações.", true);
      }
    }
  });

  // WP-278 — Create conversation from opportunity
  let oppConvSuggestion = null;

  $("opp-create-conv").addEventListener("click", () => {
    $("opp-create-conv").hidden = true;
    $("opp-conv-form").hidden = false;
    $("opp-conv-suggestion").hidden = true;
    $("opp-conv-form").reset();
    oppConvSuggestion = null;
  });

  $("opp-conv-cancel").addEventListener("click", () => {
    $("opp-conv-form").hidden = true;
    $("opp-conv-suggestion").hidden = true;
    $("opp-create-conv").hidden = false;
    oppConvSuggestion = null;
  });

  $("opp-conv-suggest").addEventListener("click", () => {
    const button = $("opp-conv-suggest");
    const version = selectionVersion;
    withButton(button, async () => {
      if (selectedId === null) return;
      try {
        const result = await conversationApi("/conversations/suggest-message", "POST", {
          company_id: opportunityCompanyId,
          channel: $("opp-conv-channel").value,
          ...(opportunityContactType === "lead"
            ? {lead_id: opportunityLeadId}
            : {customer_id: opportunityCustomerId}),
        });
        if (version !== selectionVersion || selectedId === null) return;
        oppConvSuggestion = {...result, __version: version};
        const content = $("opp-conv-suggestion-content");
        content.textContent = "";
        const msg = document.createElement("p");
        msg.textContent = result.suggested_message || "";
        content.appendChild(msg);
        $("opp-conv-suggestion").hidden = false;
      } catch (err) {
        if (err instanceof ApiFailure && err.status === 503) {
          notify("Agente IA indisponível.", true);
        } else {
          notify("Erro ao sugerir: " + (err.message || err), true);
        }
      }
    });
  });

  $("opp-conv-apply-suggestion").addEventListener("click", () => {
    if (oppConvSuggestion && oppConvSuggestion.__version === selectionVersion && oppConvSuggestion.suggested_message) {
      $("opp-conv-message").value = oppConvSuggestion.suggested_message;
    }
    $("opp-conv-suggestion").hidden = true;
    oppConvSuggestion = null;
  });

  $("opp-conv-dismiss-suggestion").addEventListener("click", () => {
    $("opp-conv-suggestion").hidden = true;
    oppConvSuggestion = null;
  });

  $("opp-conv-submit").addEventListener("click", () => {
    const button = $("opp-conv-submit");
    withButton(button, async () => {
      if (selectedId === null) return;
      const channel = $("opp-conv-channel").value;
      const message = $("opp-conv-message").value.trim();
      if (!channel) {
        notify("Selecione um canal.", true);
        return;
      }
      if (!opportunityContactType || !opportunityCompanyId) {
        notify("Associe um lead ou customer à oportunidade antes de criar conversa.", true); return;
      }
      try {
        const conv = await conversationApi("/conversations/", "POST", {
          channel,
          company_id: opportunityCompanyId,
          ...(opportunityContactType === "lead"
            ? {lead_id: opportunityLeadId}
            : {customer_id: opportunityCustomerId}),
        });
        // If there's an initial message, send it
        if (message) {
          await conversationApi("/conversations/" + conv.id + "/messages", "POST", {
            content: message,
            sender_type: "human",
          });
        }
        $("opp-conv-form").hidden = true;
        $("opp-create-conv").hidden = false;
        $("opp-conv-suggestion").hidden = true;
        oppConvSuggestion = null;
        notify("Conversa #" + conv.id + " criada.");
        // Refresh related conversations
        await loadOpportunityConversations(selectedId, selectionVersion);
      } catch (err) {
        notify("Erro ao criar conversa: " + (err.message || err), true);
      }
    });
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
          /^\/review-queue\/bulk-delete$/.test(route) ||
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
    // WP-224 — keyword search
    const q = $("rq-search")?.value?.trim();
    if (q) params.set("q", q);
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
    // WP-224 — keyword search
    const q = $("rq-search")?.value?.trim();
    if (q) params.push("q=" + encodeURIComponent(q));
    // WP-154 — date filter
    const fromDate = $("rq-from-date")?.value;
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    const toDate = $("rq-to-date")?.value;
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    return "/review-queue/count" + (params.length ? "?" + params.join("&") : "");
  }
  async function refreshReviewQueue() {
    const epoch = ++reviewEpoch;
    if (!bearer) return false;
    $("rq-list").setAttribute("aria-busy", "true");
    $("rq-load-status").textContent = "Carregando fila de revisão...";
    $("rq-load-retry").hidden = true;
    let items, summary, aging, countData;
    try {
      [items, summary, aging, countData] = await Promise.all([
        reviewApi(buildReviewUrl()),
        reviewApi("/review-queue/summary"),
        reviewApi("/review-queue/aging"),
        reviewApi(buildReviewCountUrl()),
      ]);
      if (epoch !== reviewEpoch) return false;
      const validCount = value => Number.isInteger(value) && value >= 0;
      if (!Array.isArray(items) || !validCount(countData?.total) ||
          ![summary?.pending, summary?.approve, summary?.reject,
            aging?.overdue_pending].every(validCount)) {
        throw new Error("Fila inválida.");
      }
    } catch (error) {
      if (epoch === reviewEpoch && bearer) {
        $("rq-load-status").textContent = "Não foi possível atualizar a fila. Os dados anteriores podem estar desatualizados.";
        $("rq-load-retry").hidden = false;
      }
      return false;
    } finally {
      if (epoch === reviewEpoch) $("rq-list").setAttribute("aria-busy", "false");
    }
    $("rq-load-status").textContent = "";
    reviewTotal = countData.total;
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
    return true;
  }
  $("rq-load-retry").addEventListener("click", () => withButton($("rq-load-retry"), refreshReviewQueue));
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
  // WP-224 — review queue search listener
  $("rq-search").addEventListener("input", () => {
    reviewOffset = 0;
    refreshReviewQueue();
  });
  $("rq-clear-filters").addEventListener("click", () => {
    $("rq-status-filter").value = "";
    $("rq-sort").value = "created_at";
    // WP-224 — clear search
    $("rq-search").value = "";
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

    // WP-253 + WP-260 — Ctrl+1 to Ctrl+0: navigate to all sections
    if ((e.ctrlKey || e.metaKey) && !isInput) {
      const sectionShortcutMap = {
        "1": "dashboard-title",
        "2": "opp-title",
        "3": "conv-title",
        "4": "leads-title",
        "5": "customers-title",
        "6": "rq-title",
        "7": "tasks-title",
        "8": "briefs-title",
        "9": "intake-title",
        "0": "agent-config-title",
      };
      const targetId = sectionShortcutMap[e.key];
      if (targetId) {
        e.preventDefault();
        const target = $(targetId);
        if (target) {
          target.scrollIntoView({behavior: "smooth", block: "start"});
          target.focus();
        }
      }
    }

    // Enter in triage form: submit triage (handled by form submit, but prevent double-submit)
    if (e.key === "Enter" && isInput) {
      // Let the form handle it naturally
      return;
    }
  });

  $("refresh-button").addEventListener("click", () => {
    withButton($("refresh-button"), async () => {
      if (await refreshList()) notify("Oportunidades atualizadas.");
    });
  });

  $("opp-load-retry").addEventListener("click", () => {
    withButton($("opp-load-retry"), async () => {
      await refreshList();
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
          /^\/conversations\/suggest-message$/.test(path) ||
          /^\/conversations\/\d+\/$/.test(path) ||
          /^\/conversations\/\d+\/messages(\/count)?(\?|$)/.test(path) ||
          /^\/conversations\/\d+\/note$/.test(path) ||
          /^\/conversations\/\d+\/suggest-lead$/.test(path) ||
          /^\/conversations\/\d+\/suggest-customer$/.test(path) ||
          /^\/conversations\/\d+\/suggest-opportunity$/.test(path) ||
          /^\/conversations\/\d+\/summarize$/.test(path) ||
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

  // WP-264 — Reply templates API with strict allowlist.
  async function templateApi(path, method = "GET", body) {
    if (!bearer) throw new Error("Conecte um operador.");
    if (!/^\/companies\/\d+\/reply-templates(\/\d+)?$/.test(path)) {
      throw new Error("Rota de templates não permitida.");
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
    if (convFilterCustomerId) params.set("customer_id", convFilterCustomerId);
    if (convFilterLeadId) params.set("lead_id", convFilterLeadId);
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
    if (convFilterCustomerId) params.set("customer_id", convFilterCustomerId);
    if (convFilterLeadId) params.set("lead_id", convFilterLeadId);
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
    const noteVersion = ++conversationNoteVersion;
    const noteLoad = loadConversationNote(id, noteVersion);
    msgOffset = 0;
    showConversationList();
    $("conv-detail").hidden = false;
    $("conv-reply-toggle").hidden = false;
    $("conv-suggest-reply").hidden = false;
    $("conv-summarize").hidden = false;
    $("conv-close-toggle").hidden = false;
    $("conv-note-section").hidden = false;
    $("conv-suggestion").hidden = true;
    $("conv-summary-panel").hidden = true;
    // WP-147 — Show create lead button
    $("conv-create-lead").hidden = false;
    $("conv-lead-form").hidden = true;
    // WP-235 — Show create customer button
    $("conv-create-customer").hidden = false;
    $("conv-customer-form").hidden = true;
    // WP-236 — Show create opportunity button
    $("conv-create-opp").hidden = false;
    $("conv-opp-form").hidden = true;
    $("reply-conv-id").value = id;
    const conv = conversations.find((c) => c.id === id);
    const channel = conv ? (channelLabels[conv.channel] || conv.channel) : "Conversa";
    $("conv-detail-header").textContent = channel + " · #" + id;
    await loadMessages(id);
    // WP-140 — Load internal note
    await noteLoad;
    // WP-264 — Load reply templates
    await loadReplyTemplates();
  }

  async function loadMessages(id) {
    const epoch = ++messageLoadEpoch;
    const session = sessionEpoch;
    const isCurrent = () => epoch === messageLoadEpoch &&
      session === sessionEpoch && selectedConvId === id;
    const status = $("conv-messages-status");
    const retry = $("conv-messages-retry");
    const target = $("conv-messages");
    status.textContent = "Carregando mensagens...";
    retry.hidden = true;
    retry.disabled = true;
    target.setAttribute("aria-busy", "true");
    try {
      const [messages, countResult] = await Promise.all([
        conversationApi("/conversations/" + id + "/messages?limit=" + msgPageSize + "&offset=" + msgOffset),
        conversationApi("/conversations/" + id + "/messages/count?limit=" + msgPageSize + "&offset=" + msgOffset),
      ]);
      if (!isCurrent()) return;
      status.textContent = "";
      retry.hidden = true;
      msgTotal = countResult.total || 0;
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
      if (!isCurrent()) return;
      status.textContent = "Não foi possível carregar as mensagens desta conversa.";
      retry.hidden = false;
    } finally {
      if (isCurrent()) {
        retry.disabled = false;
        target.setAttribute("aria-busy", "false");
      }
    }
  }

  $("conv-messages-retry").addEventListener("click", () => {
    if (selectedConvId !== null) loadMessages(selectedConvId);
  });

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
  async function loadConversationNote(id, version) {
    const session = sessionEpoch;
    const isCurrent = () => version === conversationNoteVersion &&
      session === sessionEpoch && selectedConvId === id;
    if (!isCurrent()) return;
    conversationNoteReady = false;
    $("conv-note-text").value = "";
    $("conv-note-text").readOnly = true;
    $("conv-note-save").disabled = true;
    $("conv-note-retry").hidden = true;
    $("conv-note-retry").disabled = true;
    $("conv-note-status").textContent = "Carregando nota...";
    try {
      const result = await conversationApi("/conversations/" + id + "/note");
      if (!isCurrent()) return;
      $("conv-note-text").value = result.note || "";
      $("conv-note-status").textContent = "";
      $("conv-note-text").readOnly = false;
      $("conv-note-save").disabled = false;
      conversationNoteReady = true;
      $("conv-note-retry").hidden = true;
    } catch (error) {
      if (!isCurrent()) return;
      $("conv-note-status").textContent = "Não foi possível carregar a nota.";
      $("conv-note-retry").hidden = false;
    } finally {
      if (isCurrent()) $("conv-note-retry").disabled = false;
    }
  }

  $("conv-note-retry").addEventListener("click", () => {
    if (selectedConvId !== null) {
      return loadConversationNote(selectedConvId, ++conversationNoteVersion);
    }
  });

  // WP-264 — Load reply templates for the current company
  let replyTemplatesLoadVersion = 0;
  async function loadReplyTemplates() {
    const select = $("reply-template-select");
    if (!select) return;
    const version = ++replyTemplatesLoadVersion;
    const status = $("reply-template-status");
    const retry = $("reply-template-retry");
    const isCurrent = () => version === replyTemplatesLoadVersion;
    status.textContent = "Carregando templates de resposta";
    status.setAttribute("aria-busy", "true");
    retry.hidden = true;
    retry.disabled = true;
    try {
      const company = opportunities.length > 0 ? opportunities[0].company_id : null;
      if (!company) {
        $("reply-template-section").hidden = true;
        status.textContent = "";
        status.setAttribute("aria-busy", "false");
        return;
      }
      const templates = await templateApi("/companies/" + company + "/reply-templates", "GET");
      if (!isCurrent()) return;
      select.replaceChildren();
      const allOpt = document.createElement("option");
      allOpt.value = "";
      allOpt.textContent = "Selecione um template...";
      select.appendChild(allOpt);
      for (const t of (templates || [])) {
        const opt = document.createElement("option");
        opt.value = String(t.id);
        opt.textContent = t.name;
        opt.dataset.content = t.content || "";
        select.appendChild(opt);
      }
      $("reply-template-section").hidden = templates.length === 0;
      status.textContent = "";
    } catch (e) {
      if (!isCurrent()) return;
      $("reply-template-section").hidden = false;
      status.textContent = "Não foi possível carregar os templates de resposta.";
      retry.hidden = false;
    } finally {
      if (isCurrent()) {
        status.setAttribute("aria-busy", "false");
        retry.disabled = false;
      }
    }
  }

  $("reply-template-retry")?.addEventListener("click", () => {
    loadReplyTemplates();
  });

  // WP-459 — Insert a template without discarding the current reply draft
  if ($("reply-template-select")) {
    $("reply-template-select").addEventListener("change", (e) => {
      const templateId = e.target.value;
      if (!templateId) return;
      const selectedOption = e.target.options[e.target.selectedIndex];
      const content = selectedOption.dataset.content || "";
      if (content) {
        const reply = $("reply-message");
        const start = reply.selectionStart ?? reply.value.length;
        const end = reply.selectionEnd ?? start;
        reply.value = reply.value.slice(0, start) + content + reply.value.slice(end);
        const cursor = start + content.length;
        reply.setSelectionRange(cursor, cursor);
        reply.focus();
        $("reply-template-insert-status").textContent = `Template "${selectedOption.textContent}" inserido na resposta.`;
        e.target.value = "";
      }
    });
  }

  $("conv-note-save").addEventListener("click", async () => {
    if (selectedConvId === null || !conversationNoteReady || $("conv-note-save").disabled) return;
    const id = selectedConvId;
    const version = conversationNoteVersion;
    const session = sessionEpoch;
    const isCurrent = () => version === conversationNoteVersion &&
      session === sessionEpoch && selectedConvId === id;
    const note = $("conv-note-text").value;
    $("conv-note-save").disabled = true;
    $("conv-note-text").readOnly = true;
    $("conv-note-status").textContent = "Salvando nota...";
    try {
      await conversationApi("/conversations/" + id, "PATCH", { note });
      if (!isCurrent()) return;
      $("conv-note-status").textContent = "Nota salva.";
    } catch (error) {
      if (!isCurrent()) return;
      $("conv-note-status").textContent = "Falha ao salvar nota. Tente novamente.";
    } finally {
      if (isCurrent()) {
        $("conv-note-save").disabled = false;
        $("conv-note-text").readOnly = false;
      }
    }
  });

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
        $("conv-lead-suggestion").hidden = true;
        await refreshLeads();
      } catch (error) {
        notify("Falha ao criar lead.", true);
      }
    });
  });

  // WP-267 — AI-assisted lead suggestion from conversation
  let leadSuggestion = null;
  $("conv-lead-suggest").addEventListener("click", () => {
    withButton($("conv-lead-suggest"), async () => {
      try {
        const res = await conversationApi(
          "/conversations/" + selectedConvId + "/suggest-lead", "POST"
        );
        leadSuggestion = res;
        const content = $("conv-lead-suggestion-content");
        while (content.firstChild) content.removeChild(content.firstChild);
        const p = document.createElement("p");
        p.className = "small";
        p.textContent = res.reasoning || "Sugestão gerada pela IA.";
        content.appendChild(p);
        $("conv-lead-suggestion").hidden = false;
      } catch (error) {
        if (error.status === 503) {
          notify("Agente indisponível.", true);
        } else {
          notify("Falha ao obter sugestão.", true);
        }
      }
    });
  });

  $("apply-conv-lead-suggestion").addEventListener("click", () => {
    if (leadSuggestion) {
      if (leadSuggestion.suggested_name) $("conv-lead-name").value = leadSuggestion.suggested_name;
      if (leadSuggestion.suggested_phone) $("conv-lead-phone").value = leadSuggestion.suggested_phone;
      if (leadSuggestion.suggested_interest) $("conv-lead-interest").value = leadSuggestion.suggested_interest;
    }
    $("conv-lead-suggestion").hidden = true;
    leadSuggestion = null;
  });

  $("dismiss-conv-lead-suggestion").addEventListener("click", () => {
    $("conv-lead-suggestion").hidden = true;
    leadSuggestion = null;
  });

  // WP-235 — Create customer from conversation
  $("conv-create-customer").addEventListener("click", () => {
    $("conv-customer-form").hidden = false;
    $("conv-create-customer").hidden = true;
    const conv = conversations.find((c) => c.id === selectedConvId);
    if (conv) {
      $("conv-customer-source").value = conv.channel || "";
    }
  });

  $("cancel-conv-customer").addEventListener("click", () => {
    $("conv-customer-form").hidden = true;
    $("conv-create-customer").hidden = false;
    $("conv-customer-name").value = "";
    $("conv-customer-phone").value = "";
    $("conv-customer-email").value = "";
    $("conv-customer-source").value = "";
    $("conv-customer-suggestion").hidden = true;
  });

  // WP-268 — AI-assisted customer suggestion from conversation
  let customerSuggestion = null;
  $("conv-customer-suggest").addEventListener("click", () => {
    withButton($("conv-customer-suggest"), async () => {
      try {
        const res = await conversationApi(
          "/conversations/" + selectedConvId + "/suggest-customer", "POST"
        );
        customerSuggestion = res;
        const content = $("conv-customer-suggestion-content");
        while (content.firstChild) content.removeChild(content.firstChild);
        const p = document.createElement("p");
        p.className = "small";
        p.textContent = res.reasoning || "Sugestão gerada pela IA.";
        content.appendChild(p);
        $("conv-customer-suggestion").hidden = false;
      } catch (error) {
        if (error.status === 503) {
          notify("Agente indisponível.", true);
        } else {
          notify("Falha ao obter sugestão.", true);
        }
      }
    });
  });

  $("apply-conv-customer-suggestion").addEventListener("click", () => {
    if (customerSuggestion) {
      if (customerSuggestion.suggested_name) $("conv-customer-name").value = customerSuggestion.suggested_name;
      if (customerSuggestion.suggested_phone) $("conv-customer-phone").value = customerSuggestion.suggested_phone;
      if (customerSuggestion.suggested_email) $("conv-customer-email").value = customerSuggestion.suggested_email;
    }
    $("conv-customer-suggestion").hidden = true;
    customerSuggestion = null;
  });

  $("dismiss-conv-customer-suggestion").addEventListener("click", () => {
    $("conv-customer-suggestion").hidden = true;
    customerSuggestion = null;
  });

  $("conv-customer-form").addEventListener("submit", (event) => {
    event.preventDefault();
    withButton(event.submitter, async () => {
      const name = $("conv-customer-name").value.trim();
      const phone = $("conv-customer-phone").value.trim() || null;
      const email = $("conv-customer-email").value.trim() || null;
      const source = $("conv-customer-source").value.trim() || null;
      if (!name) { notify("Nome é obrigatório.", true); return; }
      try {
        await customerApi("/customers", "POST", { name, phone, email, source });
        notify("Customer criado a partir da conversa.");
        $("conv-customer-form").hidden = true;
        $("conv-create-customer").hidden = false;
        $("conv-customer-name").value = "";
        $("conv-customer-phone").value = "";
        $("conv-customer-email").value = "";
        $("conv-customer-source").value = "";
        $("conv-customer-suggestion").hidden = true;
        await refreshCustomers();
      } catch (error) {
        notify("Falha ao criar customer.", true);
      }
    });
  });

  // WP-236 — Create opportunity from conversation
  $("conv-create-opp").addEventListener("click", () => {
    $("conv-opp-form").hidden = false;
    $("conv-create-opp").hidden = true;
  });

  $("cancel-conv-opp").addEventListener("click", () => {
    $("conv-opp-form").hidden = true;
    $("conv-create-opp").hidden = false;
    $("conv-opp-title").value = "";
    $("conv-opp-description").value = "";
    $("conv-opp-budget").value = "";
    $("conv-opp-deadline").value = "";
    $("conv-opp-requirements").value = "";
    $("conv-opp-suggestion").hidden = true;
  });

  // WP-269 — AI-assisted opportunity suggestion from conversation
  let oppSuggestion = null;
  $("conv-opp-suggest").addEventListener("click", () => {
    withButton($("conv-opp-suggest"), async () => {
      try {
        const res = await conversationApi(
          "/conversations/" + selectedConvId + "/suggest-opportunity", "POST"
        );
        oppSuggestion = res;
        const content = $("conv-opp-suggestion-content");
        while (content.firstChild) content.removeChild(content.firstChild);
        const p = document.createElement("p");
        p.className = "small";
        p.textContent = res.reasoning || "Sugestão gerada pela IA.";
        content.appendChild(p);
        $("conv-opp-suggestion").hidden = false;
      } catch (error) {
        if (error.status === 503) {
          notify("Agente indisponível.", true);
        } else {
          notify("Falha ao obter sugestão.", true);
        }
      }
    });
  });

  $("apply-conv-opp-suggestion").addEventListener("click", () => {
    if (oppSuggestion) {
      if (oppSuggestion.suggested_title) $("conv-opp-title").value = oppSuggestion.suggested_title;
      if (oppSuggestion.suggested_description) $("conv-opp-description").value = oppSuggestion.suggested_description;
      if (oppSuggestion.suggested_budget) $("conv-opp-budget").value = oppSuggestion.suggested_budget;
      if (oppSuggestion.suggested_deadline) $("conv-opp-deadline").value = oppSuggestion.suggested_deadline;
      if (oppSuggestion.suggested_requirements) $("conv-opp-requirements").value = oppSuggestion.suggested_requirements;
    }
    $("conv-opp-suggestion").hidden = true;
    oppSuggestion = null;
  });

  $("dismiss-conv-opp-suggestion").addEventListener("click", () => {
    $("conv-opp-suggestion").hidden = true;
    oppSuggestion = null;
  });

  $("conv-opp-form").addEventListener("submit", (event) => {
    event.preventDefault();
    withButton(event.submitter, async () => {
      const title = $("conv-opp-title").value.trim();
      const description = $("conv-opp-description").value.trim() || null;
      const budget = $("conv-opp-budget").value.trim() || null;
      const deadline = $("conv-opp-deadline").value || null;
      const requirements = $("conv-opp-requirements").value.trim() || null;
      if (!title) { notify("Título é obrigatório.", true); return; }
      try {
        await api("/opportunities", "POST", {
          title,
          description,
          budget,
          deadline,
          requirements,
          source: "manual",
        });
        notify("Oportunidade criada a partir da conversa.");
        $("conv-opp-form").hidden = true;
        $("conv-create-opp").hidden = false;
        $("conv-opp-title").value = "";
        $("conv-opp-description").value = "";
        $("conv-opp-budget").value = "";
        $("conv-opp-deadline").value = "";
        $("conv-opp-requirements").value = "";
        $("conv-opp-suggestion").hidden = true;
        await refreshList();
      } catch (error) {
        notify("Falha ao criar oportunidade.", true);
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

  // WP-195 — Populate customer filter dropdown
  let convCustomerFilterPopulated = false;
  async function populateCustomerFilter() {
    if (convCustomerFilterPopulated) return;
    try {
      const custs = await customerApi("/customers?limit=100&offset=0", "GET");
      const select = $("conv-filter-customer");
      select.replaceChildren();
      const allOpt = document.createElement("option");
      allOpt.value = "";
      allOpt.textContent = "Todos os customers";
      select.appendChild(allOpt);
      for (const c of (custs || [])) {
        const opt = document.createElement("option");
        opt.value = String(c.id);
        opt.textContent = c.name || "Sem nome";
        select.appendChild(opt);
      }
      convCustomerFilterPopulated = true;
    } catch (e) {
      // Silently fail — filter still works without dropdown
    }
  }

  // WP-232 — Populate lead filter dropdown
  let convLeadFilterPopulated = false;
  async function populateLeadFilter() {
    if (convLeadFilterPopulated) return;
    try {
      const leads = await leadApi("/leads?limit=100&offset=0", "GET");
      const select = $("conv-filter-lead");
      select.replaceChildren();
      const allOpt = document.createElement("option");
      allOpt.value = "";
      allOpt.textContent = "Todos os leads";
      select.appendChild(allOpt);
      for (const l of (leads || [])) {
        const opt = document.createElement("option");
        opt.value = String(l.id);
        opt.textContent = l.name || "Sem nome";
        select.appendChild(opt);
      }
      convLeadFilterPopulated = true;
    } catch (e) {
      // Silently fail — filter still works without dropdown
    }
  }

  // WP-234 — Populate brief opportunity filter dropdown
  let briefOppFilterPopulated = false;
  async function populateBriefOpportunityFilter() {
    if (briefOppFilterPopulated) return;
    try {
      const opps = await api("/opportunities?limit=100&offset=0");
      const select = $("briefs-opportunity-filter");
      select.replaceChildren();
      const allOpt = document.createElement("option");
      allOpt.value = "";
      allOpt.textContent = "Todas";
      select.appendChild(allOpt);
      for (const o of (opps || [])) {
        const opt = document.createElement("option");
        opt.value = String(o.id);
        opt.textContent = o.title || "Sem título";
        select.appendChild(opt);
      }
      briefOppFilterPopulated = true;
    } catch (e) {
      // Silently fail — filter still works without dropdown
    }
  }

  // WP-263 — Populate opportunity lead filter dropdown
  let oppLeadFilterPopulated = false;
  async function populateOppLeadFilter() {
    if (oppLeadFilterPopulated) return;
    try {
      const leads = await leadApi("/leads?limit=100&offset=0", "GET");
      const select = $("opp-lead-filter");
      if (!select) return;
      select.replaceChildren();
      const allOpt = document.createElement("option");
      allOpt.value = "";
      allOpt.textContent = "Todos os leads";
      select.appendChild(allOpt);
      for (const l of (leads || [])) {
        const opt = document.createElement("option");
        opt.value = String(l.id);
        opt.textContent = l.name || "Sem nome";
        select.appendChild(opt);
      }
      oppLeadFilterPopulated = true;
    } catch (e) {
      // Silently fail — filter still works without dropdown
    }
  }

  // WP-263 — Populate opportunity customer filter dropdown
  let oppCustomerFilterPopulated = false;
  async function populateOppCustomerFilter() {
    if (oppCustomerFilterPopulated) return;
    try {
      const custs = await customerApi("/customers?limit=100&offset=0", "GET");
      const select = $("opp-customer-filter");
      if (!select) return;
      select.replaceChildren();
      const allOpt = document.createElement("option");
      allOpt.value = "";
      allOpt.textContent = "Todos os customers";
      select.appendChild(allOpt);
      for (const c of (custs || [])) {
        const opt = document.createElement("option");
        opt.value = String(c.id);
        opt.textContent = c.name || "Sem nome";
        select.appendChild(opt);
      }
      oppCustomerFilterPopulated = true;
    } catch (e) {
      // Silently fail — filter still works without dropdown
    }
  }

  let conversationRefreshVersion = 0;

  async function refreshConversations() {
    const version = ++conversationRefreshVersion;
    $("conv-load-status").textContent = "Carregando conversas...";
    $("conv-load-retry").hidden = true;
    $("conv-list").setAttribute("aria-busy", "true");
    try {
      const company = opportunities.length > 0 ? opportunities[0].company_id : null;
      if (company) {
        const [convs, countResult] = await Promise.all([
          conversationApi(buildConversationUrl(company)),
          conversationApi(buildConversationCountUrl(company)),
        ]);
        if (version !== conversationRefreshVersion) return false;
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
      if (version !== conversationRefreshVersion) return false;
      $("conv-load-status").textContent = "Não foi possível atualizar as conversas. Os dados anteriores podem estar desatualizados.";
      $("conv-load-retry").hidden = false;
      return false;
    } finally {
      if (version === conversationRefreshVersion) {
        $("conv-list").setAttribute("aria-busy", "false");
      }
    }
    $("conv-load-status").textContent = "";
    // WP-195 — Populate customer dropdown on first refresh
    populateCustomerFilter().catch(() => {});
    // WP-232 — Populate lead dropdown on first refresh
    populateLeadFilter().catch(() => {});
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
      // WP-147, WP-235, WP-236 & WP-269
      $("conv-create-lead").hidden = true;
      $("conv-lead-form").hidden = true;
      $("conv-lead-suggestion").hidden = true;
      $("conv-create-customer").hidden = true;
      $("conv-customer-form").hidden = true;
      $("conv-customer-suggestion").hidden = true;
      $("conv-create-opp").hidden = true;
      $("conv-opp-form").hidden = true;
      $("conv-opp-suggestion").hidden = true;
      selectedConvIds.clear();
      updateConvBulkBar();
      showConversationList();
    }
    return version === conversationRefreshVersion;
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
    convFilterCustomerId = "";
    convFilterLeadId = "";
    convFilterSort = "last_message";
    convFilterFromDate = "";
    convFilterToDate = "";
    convOffset = 0;
    $("conv-filter-channel").value = "";
    $("conv-filter-status").value = "";
    $("conv-filter-customer").value = "";
    $("conv-filter-lead").value = "";
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

  // WP-195 — Filter conversations by customer
  $("conv-filter-customer").addEventListener("change", (e) => {
    convFilterCustomerId = e.target.value;
    convOffset = 0;
    refreshConversations().catch(() => {});
  });

  // WP-232 — Filter conversations by lead
  $("conv-filter-lead").addEventListener("change", (e) => {
    convFilterLeadId = e.target.value;
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
      if (await refreshConversations() !== false) notify("Conversas atualizadas.");
    });
  });

  $("conv-load-retry").addEventListener("click", () => {
    withButton($("conv-load-retry"), () => refreshConversations());
  });

  // WP-196 — Export CSV with current filters
  $("conv-export-csv").addEventListener("click", () => {
    const params = ["sort=" + encodeURIComponent(convFilterSort)];
    if (convFilterChannel) params.push("channel=" + encodeURIComponent(convFilterChannel));
    if (convFilterStatus) params.push("status=" + encodeURIComponent(convFilterStatus));
    if (convFilterQuery) params.push("q=" + encodeURIComponent(convFilterQuery));
    if (convFilterCustomerId) params.push("customer_id=" + encodeURIComponent(convFilterCustomerId));
    if (convFilterLeadId) params.push("lead_id=" + encodeURIComponent(convFilterLeadId));
    if (convFilterFromDate) params.push("from_date=" + encodeURIComponent(convFilterFromDate));
    if (convFilterToDate) params.push("to_date=" + encodeURIComponent(convFilterToDate));
    const company = opportunities.length > 0 ? opportunities[0].company_id : null;
    const url = "/companies/" + company + "/conversations/export.csv" + (params.length ? "?" + params.join("&") : "");
    downloadCsv(url, "conversations.csv");
    notify("Exportando conversas...");
  });

  $("conv-prev").addEventListener("click", () => withButton($("conv-prev"), async () => {
    convOffset = Math.max(0, convOffset - convPageSize);
    await refreshConversations();
  }));

  $("conv-next").addEventListener("click", () => withButton($("conv-next"), async () => {
    convOffset += convPageSize;
    await refreshConversations();
  }));

  // WP-252 — Auto-suggest reply when opening the reply form
  $("conv-reply-toggle").addEventListener("click", async () => {
    const form = $("human-reply-form");
    form.hidden = !form.hidden;
    if (!form.hidden) {
      // Auto-load suggestion when form is shown
      const convId = $("reply-conv-id").value;
      if (convId) {
        const id = parseInt(convId, 10);
        try {
          const res = await fetch("/conversations/" + id + "/suggest-reply", {
            method: "POST",
            headers: {
              "Authorization": "Bearer " + bearer,
              "Content-Type": "application/json",
            },
          });
          if (res.status === 400 || res.status === 503) {
            // Silently ignore — no customer message or agent unavailable
            return;
          }
          if (res.ok) {
            const data = await res.json();
            $("reply-message").value = data.suggestion;
          }
        } catch (_e) {
          // Silently ignore auto-suggest errors
        }
      }
    }
  });

  // WP-226 — Suggest agent reply
  $("conv-suggest-reply").addEventListener("click", () => {
    const button = $("conv-suggest-reply");
    const convId = $("reply-conv-id").value;
    if (!convId) {notify("Selecione uma conversa.", true); return;}
    const id = parseInt(convId, 10);
    withButton(button, async () => {
      try {
        const res = await fetch("/conversations/" + id + "/suggest-reply", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + bearer,
            "Content-Type": "application/json",
          },
        });
        if (res.status === 400) {
          notify("Nenhuma mensagem do cliente nesta conversa.", true);
          return;
        }
        if (res.status === 503) {
          notify("Agente indisponível.", true);
          return;
        }
        if (!res.ok) {
          notify("Falha ao solicitar sugestão.", true);
          return;
        }
        const data = await res.json();
        $("conv-suggestion-text").textContent = data.suggestion;
        $("conv-suggestion").hidden = false;
        notify("Sugestão gerada.");
      } catch (e) {
        notify("Erro ao solicitar sugestão.", true);
      }
    });
  });

  // WP-226 — Copy suggestion to reply form
  $("conv-suggestion-copy").addEventListener("click", () => {
    const text = $("conv-suggestion-text").textContent;
    if (text) {
      $("reply-message").value = text;
      $("human-reply-form").hidden = false;
      notify("Sugestão copiada para o formulário.");
    }
  });

  // WP-270 — Summarize conversation
  $("conv-summarize").addEventListener("click", () => {
    const button = $("conv-summarize");
    const convId = $("reply-conv-id").value;
    if (!convId) {notify("Selecione uma conversa.", true); return;}
    const id = parseInt(convId, 10);
    withButton(button, async () => {
      try {
        const res = await fetch("/conversations/" + id + "/summarize", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + bearer,
            "Content-Type": "application/json",
          },
        });
        if (res.status === 400) {
          notify("Mensagens insuficientes para resumir.", true);
          return;
        }
        if (res.status === 503) {
          notify("Agente indisponível.", true);
          return;
        }
        if (!res.ok) {
          notify("Falha ao gerar resumo.", true);
          return;
        }
        const data = await res.json();
        renderConversationSummary(data);
        $("conv-summary-panel").hidden = false;
        notify("Resumo gerado.");
      } catch (e) {
        notify("Erro ao gerar resumo.", true);
      }
    });
  });

  // WP-270 — Dismiss summary
  $("conv-dismiss-summary").addEventListener("click", () => {
    $("conv-summary-panel").hidden = true;
  });

  // WP-270 — Render conversation summary
  function renderConversationSummary(data) {
    const target = $("conv-summary-content");
    target.replaceChildren();
    const summaryP = document.createElement("p");
    summaryP.textContent = data.summary || "";
    target.appendChild(summaryP);
    if (data.key_points && data.key_points.length > 0) {
      const h4 = document.createElement("strong");
      h4.textContent = "Pontos-chave:";
      target.appendChild(h4);
      const ul = document.createElement("ul");
      for (const point of data.key_points) {
        const li = document.createElement("li");
        li.textContent = point;
        ul.appendChild(li);
      }
      target.appendChild(ul);
    }
    if (data.action_items && data.action_items.length > 0) {
      const h4 = document.createElement("strong");
      h4.textContent = "Ações pendentes:";
      target.appendChild(h4);
      const ul = document.createElement("ul");
      for (const item of data.action_items) {
        const li = document.createElement("li");
        li.textContent = item;
        ul.appendChild(li);
      }
      target.appendChild(ul);
    }
  }

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
  // WP-147, WP-235, WP-236 & WP-269
  $("conv-create-lead").hidden = true;
  $("conv-lead-form").hidden = true;
  $("conv-lead-suggestion").hidden = true;
  $("conv-create-customer").hidden = true;
  $("conv-customer-form").hidden = true;
  $("conv-customer-suggestion").hidden = true;
  $("conv-create-opp").hidden = true;
  $("conv-opp-form").hidden = true;
  $("conv-opp-suggestion").hidden = true;
  selectedConvIds.clear();
  updateConvBulkBar();

  const DASHBOARD_REFRESH_MS = 60000;

  let dashboardRefreshVersion = 0;

  // Dashboard — WP-082
  async function refreshDashboard() {
    if (!bearer) return;
    const version = ++dashboardRefreshVersion;
    const session = sessionEpoch;
    const isCurrent = () => version === dashboardRefreshVersion && session === sessionEpoch;
    const status = $("dashboard-status");
    status.textContent = "Atualizando dashboard…";
    try {
      const res = await fetch("/internal-tasks/dashboard", {
        headers: {"Authorization": "Bearer " + bearer},
      });
      if (!isCurrent()) return;
      if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
      if (!res.ok) throw new ApiFailure(res.status);
      const data = await res.json();
      if (!isCurrent()) return;
      renderDashboard(data);
      status.textContent = "";
    } catch (error) {
      if (!isCurrent()) throw error;
      status.textContent = "Falha ao atualizar o dashboard. Tente novamente.";
      throw error;
    }
  }

  function startDashboardRefresh() {
    stopDashboardRefresh();
    refreshDashboard().catch(() => {});
    dashboardIntervalId = setInterval(() => {
      refreshDashboard().catch(() => {});
    }, DASHBOARD_REFRESH_MS);
  }

  function stopDashboardRefresh() {
    dashboardRefreshVersion += 1;
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

    // WP-217 — Agent usage
    const agent = data.agent_usage || {};
    $("dash-agent-total").textContent = agent.total_calls || 0;
    const agentDetails = $("dash-agent-details");
    agentDetails.replaceChildren();
    const agentLabels = {
      successful_calls: "✓ Sucesso",
      failed_calls: "✗ Falha",
    };
    for (const [k, v] of Object.entries(agent)) {
      if (k === "total_calls") continue;
      const span = document.createElement("span");
      span.textContent = (agentLabels[k] || k) + ": " + v;
      agentDetails.appendChild(span);
    }

    // WP-244 — Briefs by status
    const briefs = data.briefs || {};
    $("dash-brief-total").textContent = briefs.total || 0;
    const briefDetails = $("dash-brief-details");
    briefDetails.replaceChildren();
    const briefLabels = {
      draft: "Rascunho",
      ready_for_review: "Em revisão",
      approved: "Aprovado",
      rejected: "Rejeitado",
    };
    for (const [k, v] of Object.entries(briefs)) {
      if (k === "total") continue;
      const span = document.createElement("span");
      span.textContent = (briefLabels[k] || k) + ": " + v;
      briefDetails.appendChild(span);
    }

    // WP-198 — Opportunities by source
    const oppSourceSection = $("opp-source-section");
    const oppSourceList = $("opp-source-list");
    const oppSources = data.opportunities_by_source || {};
    oppSourceList.replaceChildren();
    const oppSourceLabels = {
      "manual": "Manual",
      "intake": "Intake comercial",
      "review_queue": "Fila de revisão",
      "import": "Importação CSV",
      "99freelas": "99Freelas",
    };
    let hasOppSources = false;
    for (const [k, v] of Object.entries(oppSources)) {
      if (k === "total") continue;
      hasOppSources = true;
      const li = document.createElement("li");
      li.className = "next-action-item";
      li.textContent = (oppSourceLabels[k] || k) + ": " + v;
      oppSourceList.appendChild(li);
    }
    oppSourceSection.hidden = !hasOppSources;

    // WP-199 — Leads by source
    const leadSourceSection = $("lead-source-section");
    const leadSourceList = $("lead-source-list");
    const leadSources = data.leads_by_source || {};
    leadSourceList.replaceChildren();
    const leadSourceLabels = {
      "site": "Site",
      "manual": "Manual",
      "intake": "Intake comercial",
      "99freelas": "99Freelas",
      "import": "Importação CSV",
    };
    let hasLeadSources = false;
    for (const [k, v] of Object.entries(leadSources)) {
      if (k === "total") continue;
      hasLeadSources = true;
      const li = document.createElement("li");
      li.className = "next-action-item";
      li.textContent = (leadSourceLabels[k] || k) + ": " + v;
      leadSourceList.appendChild(li);
    }
    leadSourceSection.hidden = !hasLeadSources;

    // WP-161 — Next actions summary
    // WP-193 — Clickable next actions that scroll to section
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
        li.title = "Clique para ir para: " + action.section;
        li.style.cursor = "pointer";
        li.addEventListener("click", () => {
          // Map section names to panel headings
          const sectionMap = {
            "Oportunidades": "opp-title",
            "Conversas": "conv-title",
            "Leads": "leads-title",
            "Tarefas internas": "tasks-title",
            "Fila de revisão": "rq-title",
            "briefs": "brief-title",
          };
          const headingId = sectionMap[action.section];
          if (headingId) {
            const heading = $(headingId);
            if (heading) {
              heading.scrollIntoView({behavior: "smooth", block: "start"});
              heading.focus();
            }
          }
        });
        nextActionsList.appendChild(li);
      }
    } else {
      nextActionsSection.hidden = true;
    }

    // WP-239 — High priority opportunities
    const highPrioritySection = $("high-priority-section");
    const highPriorityList = $("high-priority-list");
    const highPriority = data.high_priority_opportunities || [];
    if (highPriority.length > 0) {
      highPrioritySection.hidden = false;
      highPriorityList.replaceChildren();
      for (const opp of highPriority) {
        const li = document.createElement("li");
        li.className = "next-action-item";
        li.textContent = `🎯 ${opp.title} (Score: ${opp.priority_score})`;
        if (opp.deadline) {
          li.textContent += ` | Prazo: ${opp.deadline}`;
        }
        highPriorityList.appendChild(li);
      }
    } else {
      highPrioritySection.hidden = true;
    }

    // WP-228 — Recent activities
    const recentSection = $("recent-activities-section");
    const recentList = $("recent-activities-list");
    const recentActivities = data.recent_activities || [];
    if (recentActivities.length > 0) {
      recentSection.hidden = false;
      recentList.replaceChildren();
      const typeLabels = {
        "opportunity": "🎯 Oportunidade",
        "conversation": "💬 Conversa",
        "lead": "📩 Lead",
      };
      for (const activity of recentActivities) {
        const li = document.createElement("li");
        li.className = "next-action-item";
        const time = activity.created_at ? new Date(activity.created_at).toLocaleString("pt-BR") : "";
        li.textContent = `${typeLabels[activity.type] || activity.type}: ${activity.title} (${time})`;
        recentList.appendChild(li);
      }
    } else {
      recentSection.hidden = true;
    }

    // WP-256 — Performance metrics
    const perfSection = $("performance-metrics-section");
    const perfGrid = $("performance-metrics-grid");
    const metrics = data.performance_metrics;
    if (metrics) {
      perfSection.hidden = false;
      perfGrid.replaceChildren();
      const metricItems = [
        {
          label: "Taxa de conversão (Leads)",
          rate: metrics.lead_conversion_rate,
          count: metrics.lead_conversion_count,
          icon: "📩",
        },
        {
          label: "Taxa de fechamento (Oportunidades)",
          rate: metrics.opportunity_closure_rate,
          count: metrics.opportunity_closure_count,
          icon: "🎯",
        },
        {
          label: "Taxa de aprovação (Briefs)",
          rate: metrics.brief_approval_rate,
          count: metrics.brief_approval_count,
          icon: "📄",
        },
      ];
      for (const item of metricItems) {
        const div = document.createElement("div");
        div.className = "dashboard-card perf-card";
        const titleEl = document.createElement("div");
        titleEl.className = "card-title";
        titleEl.textContent = `${item.icon} ${item.label}`;
        const rateEl = document.createElement("div");
        rateEl.className = "card-value";
        rateEl.textContent = `${item.rate}%`;
        const countEl = document.createElement("div");
        countEl.className = "card-count";
        countEl.textContent = item.count;
        div.appendChild(titleEl);
        div.appendChild(rateEl);
        div.appendChild(countEl);
        perfGrid.appendChild(div);
      }
    } else {
      perfSection.hidden = true;
    }
  }

  $("dashboard-refresh").addEventListener("click", () => withButton($("dashboard-refresh"), async () => {
    await refreshDashboard();
    notify("Dashboard atualizado.");
  }));

  // WP-275 — Export dashboard as CSV
  $("dashboard-export").addEventListener("click", () => {
    if (!bearer) return;
    const link = document.createElement("a");
    link.href = "/internal-tasks/export-dashboard.csv";
    link.download = "dashboard_report.csv";
    fetch("/internal-tasks/export-dashboard.csv", {
      headers: { "Authorization": "Bearer " + bearer },
    }).then((res) => {
      if (!res.ok) throw new Error("Falha ao exportar");
      return res.blob();
    }).then((blob) => {
      const url = URL.createObjectURL(blob);
      link.href = url;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      notify("Relatório exportado.");
    }).catch((e) => {
      notify("Erro ao exportar relatório.", true);
    });
  });

  // WP-107 — Notifications polling
  const NOTIFICATION_REFRESH_MS = 30000;
  let notificationIntervalId = null;

  async function updateNotifications() {
    if (!bearer) return;
    try {
      const response = await fetch("/internal-tasks/notification-summary", {
        headers: {"Authorization": "Bearer " + bearer},
      });
      if (!response.ok) throw new Error("Dashboard indisponível");
      const dashboard = await response.json();
      const pendingCount = dashboard.opportunities?.pending || 0;
      const newLeadCount = dashboard.leads?.new || 0;
      const openConvCount = dashboard.conversations?.open || 0;
      const failedTaskCount = dashboard.tasks?.failed || 0;
      const badgeValues = [
        ["pending-badge", pendingCount],
        ["lead-new-badge", newLeadCount],
        ["conv-open-badge", openConvCount],
        ["task-failed-badge", failedTaskCount],
      ];
      for (const [id, count] of badgeValues) {
        const badge = $(id);
        badge.hidden = count <= 0;
        if (count > 0) badge.textContent = count;
      }
      $("notification-sync-status").textContent = "Atualizado às " + new Date().toLocaleTimeString("pt-BR");
      // WP-251 — Update browser tab title with notification count
      const total = pendingCount + newLeadCount + openConvCount + failedTaskCount;
      if (total > 0) {
        document.title = `(${total}) Operador`;
      } else {
        document.title = "Operador";
      }
    } catch (_e) {
      $("notification-sync-status").textContent = "Atualização indisponível";
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
    // WP-271 — also allow /leads/{id}/suggest-opportunity
    if (!(/^\/leads($|\/(new|contacted|qualified|proposal|won|lost)$|\/count$|\/\d+$|\/\d+\/suggest-opportunity$)/.test(path.split("?")[0]))) {
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

  let leadRefreshVersion = 0;

  async function refreshLeads() {
    if (!bearer) return false;
    const version = ++leadRefreshVersion;
    $("leads-load-status").textContent = "Carregando leads...";
    $("leads-load-retry").hidden = true;
    $("leads-list").setAttribute("aria-busy", "true");
    try {
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
      if (version !== leadRefreshVersion) return false;
      if (!Array.isArray(leads) || !countResult) {
        throw new Error("Lead list unavailable");
      }
      leadTotal = countResult.total || 0;
      leadListLength = (leads || []).length;
      // WP-175 — update new leads badge
      const newLeads = (leads || []).filter((l) => l.status === "new").length;
      const leadBadge = $("lead-new-badge");
      if (newLeads > 0) { leadBadge.hidden = false; leadBadge.textContent = newLeads; }
      else { leadBadge.hidden = true; }
      renderLeads(leads || []);
      updateLeadPagination();
      $("leads-load-status").textContent = "";
      return true;
    } catch (error) {
      if (version !== leadRefreshVersion) return false;
      $("leads-load-status").textContent = "Não foi possível atualizar os leads. Os dados anteriores podem estar desatualizados.";
      $("leads-load-retry").hidden = false;
      return false;
    } finally {
      if (version === leadRefreshVersion) {
        $("leads-list").setAttribute("aria-busy", "false");
      }
    }
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
  let currentLead = null;
  let leadConversationsVersion = 0;

  async function showLeadDetail(lead) {
    currentLeadId = lead.id;
    currentLead = lead;
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

    await loadLeadConversations(lead);
  }

  async function loadLeadConversations(lead) {
    const version = ++leadConversationsVersion;
    const session = sessionEpoch;
    const isCurrent = () => version === leadConversationsVersion &&
      session === sessionEpoch && bearer && currentLeadId === lead.id &&
      !$("lead-detail").hidden;
    const convList = $("lead-conversations-list");
    const status = $("lead-conversations-status");
    const retry = $("lead-conversations-retry");
    retry.hidden = true;
    status.textContent = "";
    convList.replaceChildren();
    try {
      const company = lead.company_id;
      const params = new URLSearchParams({lead_id: lead.id, limit: 50});
      const convs = await conversationApi("/companies/" + company + "/conversations?" + params);
      if (!isCurrent()) return;
      status.textContent = "";
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
      if (isCurrent()) {
        status.textContent = "Não foi possível carregar as conversas. Os dados podem estar desatualizados.";
        retry.hidden = false;
        console.error("[showLeadDetail] Falha ao carregar conversas:", e);
      }
    }
  }

  $("lead-conversations-retry").addEventListener("click", () => {
    if (currentLead && currentLeadId === currentLead.id) return loadLeadConversations(currentLead);
  });

  function hideLeadDetail() {
    leadConversationsVersion += 1;
    currentLeadId = null;
    currentLead = null;
    $("leads-list").hidden = false;
    $("lead-detail").hidden = true;
    if (leadTotal > leadPageSize) {
      $("leads-pagination").hidden = false;
    }
  }

  $("lead-detail-back").addEventListener("click", () => {
    hideLeadDetail();
  });

  // WP-274 — Create conversation from lead detail with form
  $("lead-new-conv").addEventListener("click", () => {
    $("lead-conv-form").hidden = false;
    $("lead-conv-suggestion").hidden = true;
    leadConvSuggestion = null;
  });

  $("cancel-lead-conv").addEventListener("click", () => {
    $("lead-conv-form").hidden = true;
    $("lead-conv-form").reset();
    $("lead-conv-suggestion").hidden = true;
    leadConvSuggestion = null;
  });

  // WP-274 — Suggest message for lead conversation
  $("lead-conv-suggest").addEventListener("click", () => {
    const button = $("lead-conv-suggest");
    if (!currentLeadId) {notify("Selecione um lead.", true); return;}
    withButton(button, async () => {
      try {
        const res = await fetch("/conversations/suggest-message", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + bearer,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            company_id: opportunities.length > 0 ? opportunities[0].company_id : null,
            channel: $("lead-conv-channel").value,
            lead_id: currentLeadId,
          }),
        });
        if (res.status === 503) {notify("Agente indisponível.", true); return;}
        if (!res.ok) {notify("Falha ao gerar sugestão.", true); return;}
        const data = await res.json();
        renderLeadConvSuggestion(data);
        $("lead-conv-suggestion").hidden = false;
        notify("Sugestão gerada.");
      } catch (e) {
        notify("Erro ao gerar sugestão.", true);
      }
    });
  });

  $("lead-conv-dismiss-suggestion").addEventListener("click", () => {
    $("lead-conv-suggestion").hidden = true;
  });

  $("lead-conv-apply-suggestion").addEventListener("click", () => {
    if (leadConvSuggestion && leadConvSuggestion.suggested_message) {
      $("lead-conv-message").value = leadConvSuggestion.suggested_message;
    }
    $("lead-conv-suggestion").hidden = true;
    $("lead-conv-form").hidden = false;
    $("lead-conv-message").focus();
  });

  var leadConvSuggestion = null;
  function renderLeadConvSuggestion(data) {
    leadConvSuggestion = data;
    const target = $("lead-conv-suggestion-content");
    target.replaceChildren();
    if (data.reasoning) {
      const p = document.createElement("p");
      p.textContent = data.reasoning;
      target.appendChild(p);
    }
    if (data.suggested_message) {
      const strong = document.createElement("strong");
      strong.textContent = "Mensagem:";
      target.appendChild(strong);
      const p = document.createElement("p");
      p.textContent = data.suggested_message;
      target.appendChild(p);
    }
  }

  $("lead-conv-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const button = $("lead-conv-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const channel = $("lead-conv-channel").value;
      const message = $("lead-conv-message").value.trim();
      if (!message) {notify("Preencha a mensagem.", true); return;}
      const company = opportunities.length > 0 ? opportunities[0].company_id : null;
      const res = await fetch("/conversations", {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + bearer,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          company_id: company,
          channel,
          lead_id: currentLeadId,
        }),
      });
      if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
      if (res.status === 409) {notify("Conversa já existe.", true); return;}
      if (!res.ok) {console.error("[lead-conv-form] Erro:", res.status); return;}
      const conv = await res.json();
      // Send the first message
      await fetch("/conversations/" + conv.id + "/messages", {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + bearer,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({sender_type: "human", content: message}),
      });
      $("lead-conv-form").hidden = true;
      $("lead-conv-form").reset();
      $("lead-conv-suggestion").hidden = true;
      leadConvSuggestion = null;
      notify("Conversa criada.");
      await showLeadDetail(leads.find((l) => l.id === currentLeadId) || {id: currentLeadId});
    });
  });

  // WP-192 — Create opportunity from lead detail
  $("lead-new-opp").addEventListener("click", () => {
    $("lead-opp-form").hidden = false;
    $("lead-opp-title").focus();
  });

  $("cancel-lead-opp").addEventListener("click", () => {
    $("lead-opp-form").hidden = true;
    $("lead-opp-form").reset();
    $("lead-opp-suggestion").hidden = true;
    leadOppSuggestion = null;
  });

  $("lead-opp-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const button = $("lead-opp-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const title = $("lead-opp-title").value.trim();
      const description = $("lead-opp-description").value.trim();
      const budget = $("lead-opp-budget").value.trim() || null;
      const deadline = $("lead-opp-deadline").value.trim() || null;
      const requirements = $("lead-opp-requirements").value.trim() || null;
      if (!title || !description) {
        notify("Preencha título e descrição.", true);
        return;
      }
      const opp = await api("/opportunities", {
        method: "POST",
        body: JSON.stringify({
          company_id: opportunities.length > 0 ? opportunities[0].company_id : null,
          source: "manual",
          external_url: "lead-" + currentLeadId,
          title,
          description,
          budget,
          deadline,
          requirements,
          lead_id: currentLeadId,
          captured_at: new Date().toISOString(),
        }),
      });
      $("lead-opp-form").hidden = true;
      $("lead-opp-form").reset();
      $("lead-opp-suggestion").hidden = true;
      notify("Oportunidade #" + opp.id + " criada.");
      await refreshList(opp.id);
    });
  });

  // WP-271 — Suggest opportunity from lead
  $("lead-opp-suggest").addEventListener("click", () => {
    const button = $("lead-opp-suggest");
    if (!currentLeadId) {notify("Selecione um lead.", true); return;}
    withButton(button, async () => {
      try {
        const res = await fetch("/leads/" + currentLeadId + "/suggest-opportunity", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + bearer,
            "Content-Type": "application/json",
          },
        });
        if (res.status === 503) {
          notify("Agente indisponível.", true);
          return;
        }
        if (!res.ok) {
          notify("Falha ao gerar sugestão.", true);
          return;
        }
        const data = await res.json();
        renderLeadOppSuggestion(data);
        $("lead-opp-suggestion").hidden = false;
        notify("Sugestão gerada.");
      } catch (e) {
        notify("Erro ao gerar sugestão.", true);
      }
    });
  });

  // WP-271 — Dismiss lead opportunity suggestion
  $("lead-opp-dismiss-suggestion").addEventListener("click", () => {
    $("lead-opp-suggestion").hidden = true;
  });

  // WP-271 — Apply lead opportunity suggestion
  $("lead-opp-apply-suggestion").addEventListener("click", () => {
    if (leadOppSuggestion) {
      if (leadOppSuggestion.suggested_title) $("lead-opp-title").value = leadOppSuggestion.suggested_title;
      if (leadOppSuggestion.suggested_description) $("lead-opp-description").value = leadOppSuggestion.suggested_description;
      if (leadOppSuggestion.suggested_budget) $("lead-opp-budget").value = leadOppSuggestion.suggested_budget;
      if (leadOppSuggestion.suggested_deadline) $("lead-opp-deadline").value = leadOppSuggestion.suggested_deadline;
      if (leadOppSuggestion.suggested_requirements) $("lead-opp-requirements").value = leadOppSuggestion.suggested_requirements;
    }
    $("lead-opp-suggestion").hidden = true;
    $("lead-opp-form").hidden = false;
    $("lead-opp-title").focus();
  });

  // WP-271 — Render lead opportunity suggestion
  var leadOppSuggestion = null;
  function renderLeadOppSuggestion(data) {
    leadOppSuggestion = data;
    const target = $("lead-opp-suggestion-content");
    target.replaceChildren();
    if (data.reasoning) {
      const p = document.createElement("p");
      p.textContent = data.reasoning;
      target.appendChild(p);
    }
    const fields = [
      {key: "suggested_title", label: "Título"},
      {key: "suggested_description", label: "Descrição"},
      {key: "suggested_budget", label: "Orçamento"},
      {key: "suggested_deadline", label: "Prazo"},
      {key: "suggested_requirements", label: "Requisitos"},
    ];
    for (const field of fields) {
      if (data[field.key]) {
        const strong = document.createElement("strong");
        strong.textContent = field.label + ":";
        target.appendChild(strong);
        const p = document.createElement("p");
        p.textContent = data[field.key];
        target.appendChild(p);
      }
    }
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
    if (await refreshLeads()) notify("Leads atualizados.");
  }));

  $("leads-load-retry").addEventListener("click", () => {
    withButton($("leads-load-retry"), () => refreshLeads());
  });

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
  let customerSelectionVersion = 0;

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
    // WP-235 — Allow POST /customers for creating from conversation
    if (!allowedPattern.test(path.split("#")[0]) && !(path === "/customers" && method === "POST")) {
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

  let customerRefreshVersion = 0;

  async function refreshCustomers() {
    if (!bearer) return false;
    const version = ++customerRefreshVersion;
    $("customers-load-status").textContent = "Carregando clientes...";
    $("customers-load-retry").hidden = true;
    $("customers-list").setAttribute("aria-busy", "true");
    try {
      const [customers, countData] = await Promise.all([
        customerApi(buildCustomerUrl(), "GET"),
        customerApi(buildCustomerCountUrl(), "GET"),
      ]);
      if (version !== customerRefreshVersion) return false;
      if (!Array.isArray(customers) || !countData) {
        throw new Error("Customer list unavailable");
      }
      customerTotal = countData.total || 0;
      selectedCustomerIds.clear();
      renderCustomers(customers);
      updateCustomerPagination();
      $("customer-bulk-bar").hidden = true;
      $("customers-load-status").textContent = "";
      return true;
    } catch (error) {
      if (version !== customerRefreshVersion) return false;
      $("customers-load-status").textContent = "Não foi possível atualizar os clientes. Os dados anteriores podem estar desatualizados.";
      $("customers-load-retry").hidden = false;
      return false;
    } finally {
      if (version === customerRefreshVersion) {
        $("customers-list").setAttribute("aria-busy", "false");
      }
    }
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

  let customerConversationsVersion = 0;

  // Customer detail view — WP-087
  async function showCustomerDetail(cust) {
    customerSelectionVersion += 1;
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
    const version = ++customerConversationsVersion;
    const session = sessionEpoch;
    const isCurrent = () => version === customerConversationsVersion &&
      session === sessionEpoch && bearer && currentCustomerId === customerId &&
      !$("customer-detail").hidden;
    const convList = $("customer-conversations-list");
    const status = $("customer-conversations-status");
    const retry = $("customer-conversations-retry");
    retry.hidden = true;
    retry.disabled = true;
    status.textContent = "Carregando conversas...";
    convList.replaceChildren();

    try {
      const company = opportunities.length > 0 ? opportunities[0].company_id : null;
      if (!company) {
        status.textContent = "";
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
      if (!isCurrent()) return;
      if (!Array.isArray(convs)) throw new Error("Resposta inválida ao carregar conversas.");
      status.textContent = "";
      if (!convs.length) {
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
      if (isCurrent()) {
        status.textContent = "Não foi possível carregar as conversas. Os dados podem estar desatualizados.";
        retry.hidden = false;
        console.error("[loadCustomerConversations] Erro:", e);
      }
    } finally {
      if (isCurrent()) retry.disabled = false;
    }
  }

  $("customer-conversations-retry").addEventListener("click", () => {
    const detail = $("customer-detail");
    if (currentCustomerId !== null && !detail.hidden) {
      loadCustomerConversations(currentCustomerId);
    }
  });

  function hideCustomerDetail() {
    customerConversationsVersion += 1;
    customerSelectionVersion += 1;
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

  async function updateCustomer(customerId, data, isCurrent = () => true) {
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
    if (res.status === 403) {if (isCurrent()) disconnect("Permissão de operador necessária."); return null;}
    if (res.status === 404) {if (isCurrent()) notify("Customer não encontrado.", true); return null;}
    if (!res.ok) {if (isCurrent()) notify("Falha ao atualizar customer.", true); return null;}
    return res.json();
  }

  // WP-110 — Edit customer form handlers
  $("customer-edit-cancel").addEventListener("click", () => {
    hideCustomerEditForm();
  });

  $("customer-edit-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const customerId = currentCustomerId;
    const selectionVersion = customerSelectionVersion;
    const session = sessionEpoch;
    if (customerId === null || customerId === undefined) return;
    const name = $("customer-edit-name").value.trim();
    const phone = $("customer-edit-phone").value.trim() || null;
    const email = $("customer-edit-email").value.trim() || null;
    if (!name) {notify("Nome é obrigatório.", true); return;}
    const data = {name};
    if (phone !== null) data.phone = phone;
    if (email !== null) data.email = email;
    const button = $("customer-edit-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const isCurrent = () => selectionVersion === customerSelectionVersion && currentCustomerId === customerId && session === sessionEpoch && bearer;
      let updated;
      try {
        updated = await updateCustomer(customerId, data, isCurrent);
      } catch (error) {
        if (!isCurrent()) return;
        throw error;
      }
      if (!isCurrent()) return;
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
    if (await refreshCustomers()) notify("Customers atualizados.");
  }));

  $("customers-load-retry").addEventListener("click", () => {
    withButton($("customers-load-retry"), () => refreshCustomers());
  });

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

  // WP-274 — Create conversation from customer detail with form
  $("customer-new-conv").addEventListener("click", () => {
    $("customer-conv-form").hidden = false;
    $("customer-conv-suggestion").hidden = true;
    customerConvSuggestion = null;
  });

  $("cancel-customer-conv").addEventListener("click", () => {
    $("customer-conv-form").hidden = true;
    $("customer-conv-form").reset();
    $("customer-conv-suggestion").hidden = true;
    customerConvSuggestion = null;
  });

  // WP-274 — Suggest message for customer conversation
  $("customer-conv-suggest").addEventListener("click", () => {
    const button = $("customer-conv-suggest");
    if (!currentCustomerId) {notify("Selecione um customer.", true); return;}
    withButton(button, async () => {
      try {
        const res = await fetch("/conversations/suggest-message", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + bearer,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            company_id: opportunities.length > 0 ? opportunities[0].company_id : null,
            channel: $("customer-conv-channel").value,
            customer_id: currentCustomerId,
          }),
        });
        if (res.status === 503) {notify("Agente indisponível.", true); return;}
        if (!res.ok) {notify("Falha ao gerar sugestão.", true); return;}
        const data = await res.json();
        renderCustomerConvSuggestion(data);
        $("customer-conv-suggestion").hidden = false;
        notify("Sugestão gerada.");
      } catch (e) {
        notify("Erro ao gerar sugestão.", true);
      }
    });
  });

  $("customer-conv-dismiss-suggestion").addEventListener("click", () => {
    $("customer-conv-suggestion").hidden = true;
  });

  $("customer-conv-apply-suggestion").addEventListener("click", () => {
    if (customerConvSuggestion && customerConvSuggestion.suggested_message) {
      $("customer-conv-message").value = customerConvSuggestion.suggested_message;
    }
    $("customer-conv-suggestion").hidden = true;
    $("customer-conv-form").hidden = false;
    $("customer-conv-message").focus();
  });

  var customerConvSuggestion = null;
  function renderCustomerConvSuggestion(data) {
    customerConvSuggestion = data;
    const target = $("customer-conv-suggestion-content");
    target.replaceChildren();
    if (data.reasoning) {
      const p = document.createElement("p");
      p.textContent = data.reasoning;
      target.appendChild(p);
    }
    if (data.suggested_message) {
      const strong = document.createElement("strong");
      strong.textContent = "Mensagem:";
      target.appendChild(strong);
      const p = document.createElement("p");
      p.textContent = data.suggested_message;
      target.appendChild(p);
    }
  }

  $("customer-conv-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const button = $("customer-conv-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const channel = $("customer-conv-channel").value;
      const message = $("customer-conv-message").value.trim();
      if (!message) {notify("Preencha a mensagem.", true); return;}
      const company = opportunities.length > 0 ? opportunities[0].company_id : null;
      const res = await fetch("/conversations", {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + bearer,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          company_id: company,
          channel,
          customer_id: currentCustomerId,
        }),
      });
      if (res.status === 403) {disconnect("Permissão de operador necessária."); return;}
      if (res.status === 409) {notify("Conversa já existe.", true); return;}
      if (!res.ok) {console.error("[customer-conv-form] Erro:", res.status); return;}
      const conv = await res.json();
      await fetch("/conversations/" + conv.id + "/messages", {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + bearer,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({sender_type: "human", content: message}),
      });
      $("customer-conv-form").hidden = true;
      $("customer-conv-form").reset();
      $("customer-conv-suggestion").hidden = true;
      customerConvSuggestion = null;
      notify("Conversa criada.");
      await loadCustomerConversations(currentCustomerId);
    });
  });

  // WP-167 — Create opportunity from customer detail
  $("customer-new-opp").addEventListener("click", () => {
    $("customer-opp-form").hidden = false;
    $("customer-opp-title").focus();
  });

  $("cancel-customer-opp").addEventListener("click", () => {
    $("customer-opp-form").hidden = true;
    $("customer-opp-form").reset();
    $("customer-opp-suggestion").hidden = true;
    customerOppSuggestion = null;
  });

  // WP-272 — Suggest opportunity from customer
  $("customer-opp-suggest").addEventListener("click", () => {
    const button = $("customer-opp-suggest");
    if (!currentCustomerId) {notify("Selecione um customer.", true); return;}
    withButton(button, async () => {
      try {
        const res = await fetch("/customers/" + currentCustomerId + "/suggest-opportunity", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + bearer,
            "Content-Type": "application/json",
          },
        });
        if (res.status === 503) {
          notify("Agente indisponível.", true);
          return;
        }
        if (!res.ok) {
          notify("Falha ao gerar sugestão.", true);
          return;
        }
        const data = await res.json();
        renderCustomerOppSuggestion(data);
        $("customer-opp-suggestion").hidden = false;
        notify("Sugestão gerada.");
      } catch (e) {
        notify("Erro ao gerar sugestão.", true);
      }
    });
  });

  // WP-272 — Dismiss customer opportunity suggestion
  $("customer-opp-dismiss-suggestion").addEventListener("click", () => {
    $("customer-opp-suggestion").hidden = true;
  });

  // WP-272 — Apply customer opportunity suggestion
  $("customer-opp-apply-suggestion").addEventListener("click", () => {
    if (customerOppSuggestion) {
      if (customerOppSuggestion.suggested_title) $("customer-opp-title").value = customerOppSuggestion.suggested_title;
      if (customerOppSuggestion.suggested_description) $("customer-opp-description").value = customerOppSuggestion.suggested_description;
      if (customerOppSuggestion.suggested_budget) $("customer-opp-budget").value = customerOppSuggestion.suggested_budget;
      if (customerOppSuggestion.suggested_deadline) $("customer-opp-deadline").value = customerOppSuggestion.suggested_deadline;
      if (customerOppSuggestion.suggested_requirements) $("customer-opp-requirements").value = customerOppSuggestion.suggested_requirements;
    }
    $("customer-opp-suggestion").hidden = true;
    $("customer-opp-form").hidden = false;
    $("customer-opp-title").focus();
  });

  // WP-272 — Render customer opportunity suggestion
  var customerOppSuggestion = null;
  function renderCustomerOppSuggestion(data) {
    customerOppSuggestion = data;
    const target = $("customer-opp-suggestion-content");
    target.replaceChildren();
    if (data.reasoning) {
      const p = document.createElement("p");
      p.textContent = data.reasoning;
      target.appendChild(p);
    }
    const fields = [
      {key: "suggested_title", label: "Título"},
      {key: "suggested_description", label: "Descrição"},
      {key: "suggested_budget", label: "Orçamento"},
      {key: "suggested_deadline", label: "Prazo"},
      {key: "suggested_requirements", label: "Requisitos"},
    ];
    for (const field of fields) {
      if (data[field.key]) {
        const strong = document.createElement("strong");
        strong.textContent = field.label + ":";
        target.appendChild(strong);
        const p = document.createElement("p");
        p.textContent = data[field.key];
        target.appendChild(p);
      }
    }
  }

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
          customer_id: currentCustomerId,
          captured_at: new Date().toISOString(),
        }),
      });
      $("customer-opp-form").hidden = true;
      $("customer-opp-form").reset();
      notify("Oportunidade #" + opp.id + " criada.");
      await refreshList(opp.id);
    });
  });

  // WP-273 — Create lead from customer detail
  $("customer-new-lead").addEventListener("click", () => {
    $("customer-lead-form").hidden = false;
    $("customer-lead-suggestion").hidden = true;
    customerLeadSuggestion = null;
  });

  $("cancel-customer-lead").addEventListener("click", () => {
    $("customer-lead-form").hidden = true;
    $("customer-lead-form").reset();
    $("customer-lead-suggestion").hidden = true;
    customerLeadSuggestion = null;
  });

  // WP-273 — Suggest lead from customer
  $("customer-lead-suggest").addEventListener("click", () => {
    const button = $("customer-lead-suggest");
    if (!currentCustomerId) {notify("Selecione um customer.", true); return;}
    withButton(button, async () => {
      try {
        const res = await fetch("/customers/" + currentCustomerId + "/suggest-lead", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + bearer,
            "Content-Type": "application/json",
          },
        });
        if (res.status === 503) {
          notify("Agente indisponível.", true);
          return;
        }
        if (!res.ok) {
          notify("Falha ao gerar sugestão.", true);
          return;
        }
        const data = await res.json();
        renderCustomerLeadSuggestion(data);
        $("customer-lead-suggestion").hidden = false;
        notify("Sugestão gerada.");
      } catch (e) {
        notify("Erro ao gerar sugestão.", true);
      }
    });
  });

  // WP-273 — Dismiss customer lead suggestion
  $("customer-lead-dismiss-suggestion").addEventListener("click", () => {
    $("customer-lead-suggestion").hidden = true;
  });

  // WP-273 — Apply customer lead suggestion
  $("customer-lead-apply-suggestion").addEventListener("click", () => {
    if (customerLeadSuggestion) {
      if (customerLeadSuggestion.suggested_name) $("customer-lead-name").value = customerLeadSuggestion.suggested_name;
      if (customerLeadSuggestion.suggested_phone) $("customer-lead-phone").value = customerLeadSuggestion.suggested_phone;
      if (customerLeadSuggestion.suggested_interest) $("customer-lead-interest").value = customerLeadSuggestion.suggested_interest;
    }
    $("customer-lead-suggestion").hidden = true;
    $("customer-lead-form").hidden = false;
    $("customer-lead-name").focus();
  });

  // WP-273 — Render customer lead suggestion
  var customerLeadSuggestion = null;
  function renderCustomerLeadSuggestion(data) {
    customerLeadSuggestion = data;
    const target = $("customer-lead-suggestion-content");
    target.replaceChildren();
    if (data.reasoning) {
      const p = document.createElement("p");
      p.textContent = data.reasoning;
      target.appendChild(p);
    }
    const fields = [
      {key: "suggested_name", label: "Nome"},
      {key: "suggested_phone", label: "Telefone"},
      {key: "suggested_interest", label: "Interesse"},
    ];
    for (const field of fields) {
      if (data[field.key]) {
        const strong = document.createElement("strong");
        strong.textContent = field.label + ":";
        target.appendChild(strong);
        const p = document.createElement("p");
        p.textContent = data[field.key];
        target.appendChild(p);
      }
    }
  }

  $("customer-lead-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const button = $("customer-lead-form").querySelector('button[type="submit"]');
    withButton(button, async () => {
      const name = $("customer-lead-name").value.trim();
      const phone = $("customer-lead-phone").value.trim();
      const interest = $("customer-lead-interest").value.trim() || null;
      if (!name) {
        notify("Preencha o nome.", true);
        return;
      }
      const company_id = customers.length > 0 ? customers[0].company_id : null;
      const lead = await api("/leads", {
        method: "POST",
        body: JSON.stringify({
          company_id,
          name,
          phone,
          source: "manual",
          interest,
        }),
      });
      $("customer-lead-form").hidden = true;
      $("customer-lead-form").reset();
      $("customer-lead-suggestion").hidden = true;
      customerLeadSuggestion = null;
      notify("Lead #" + lead.id + " criado.");
      await refreshLeads();
    });
  });

  // WP-096 — Commercial intake API and form handler
  async function intakeApi(path, method, body) {
    if (!bearer) throw new Error("Conecte um operador.");
    if (!(/^\/internal\/commercial-intake\/(create|suggest)$/.test(path))) {
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

  // WP-190 — Clear intake form and hide decision
  $("intake-clear").addEventListener("click", () => {
    $("intake-form").reset();
    $("intake-decision").hidden = true;
    $("intake-suggestion").hidden = true;
  });

  // WP-259 — AI-assisted intake suggestion
  $("intake-suggest").addEventListener("click", () => {
    const button = $("intake-suggest");
    withButton(button, async () => {
      const channel = $("intake-channel").value;
      const eventId = $("intake-event-id").value.trim();
      const message = $("intake-message").value.trim();
      if (!eventId || !message) {
        notify("Preencha ID e mensagem para sugerir.", true);
        return;
      }
      try {
        const result = await intakeApi("/internal/commercial-intake/suggest", "POST", {
          channel,
          event_id: eventId,
          message,
        });
        $("intake-suggestion").hidden = false;
        $("intake-decision").hidden = true;
        $("intake-suggest-intent").textContent = result.suggested_intent || "Desconhecida";
        $("intake-suggest-category").textContent = result.suggested_category || "N/A";
        $("intake-suggest-reasoning").textContent = result.reasoning || "";
      } catch (err) {
        if (err.message && err.message.includes("503")) {
          notify("Agente IA indisponível. Use o botão normal para criar.", true);
        } else {
          notify("Erro ao sugerir: " + err.message, true);
        }
      }
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
        // WP-263 — Populate opportunity lead/customer filter dropdowns
        populateOppLeadFilter().catch(() => {});
        populateOppCustomerFilter().catch(() => {});
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

  // WP-249 — AI-assisted bulk triage suggestion
  let bulkTriageSuggestion = null;

  $("bulk-suggest-triage").addEventListener("click", () => withButton($("bulk-suggest-triage"), async () => {
    const ids = Array.from(selectedOpportunityIds);
    if (!ids.length) {notify("Selecione oportunidades primeiro.", true); return;}
    try {
      const result = await api("/opportunities/bulk-suggest-triage", {
        method: "POST",
        body: JSON.stringify({opportunity_ids: ids}),
      });
      bulkTriageSuggestion = result;
      renderBulkSuggestion();
      $("bulk-suggestion-panel").hidden = false;
      $("bulk-suggestion-panel").scrollIntoView({behavior: "smooth"});
    } catch (err) {
      if (err.status === 503) {
        notify("Serviço de agente indisponível.", true);
      } else {
        notify("Falha ao obter sugestão.", true);
      }
    }
  }));

  function renderBulkSuggestion() {
    const content = $("bulk-suggestion-content");
    content.textContent = "";
    if (!bulkTriageSuggestion) return;
    const actionLabels = {
      pending: "Pendente",
      follow: "Acompanhar",
      ignore: "Ignorar",
      prepare_proposal: "Preparar proposta",
      in_progress: "Em andamento",
      done: "Concluída",
      lost: "Perdida",
    };
    const action = document.createElement("p");
    action.textContent = "Ação sugerida: " + (actionLabels[bulkTriageSuggestion.suggested_action] || bulkTriageSuggestion.suggested_action);
    content.appendChild(action);
    const reasoning = document.createElement("p");
    reasoning.textContent = "Motivo: " + bulkTriageSuggestion.reasoning;
    content.appendChild(reasoning);
    const match = document.createElement("p");
    match.textContent = bulkTriageSuggestion.matching_count + "/" + bulkTriageSuggestion.total_count + " oportunidades compatíveis";
    content.appendChild(match);
  }

  $("apply-bulk-suggestion").addEventListener("click", () => {
    if (!bulkTriageSuggestion) return;
    $("bulk-triage-action").value = bulkTriageSuggestion.suggested_action;
    $("bulk-suggestion-panel").hidden = true;
    bulkTriageSuggestion = null;
    notify("Ação definida no seletor. Clique 'Aplicar' para confirmar.");
  });

  $("dismiss-bulk-suggestion").addEventListener("click", () => {
    $("bulk-suggestion-panel").hidden = true;
    bulkTriageSuggestion = null;
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
    // WP-123/150/189/266 — Export CSV with current filters
    const params = ["sort=" + encodeURIComponent($("opp-sort").value)];
    const showArchived = $("show-archived").checked;
    if (!showArchived) params.push("exclude_archived=true");
    if (oppPipelineFilter !== "all") params.push("next_action=" + encodeURIComponent(oppPipelineFilter));
    const source = $("opp-source-filter") ? $("opp-source-filter").value : "";
    if (source) params.push("source=" + encodeURIComponent(source));
    const searchQuery = $("opp-search").value.trim();
    if (searchQuery) params.push("q=" + encodeURIComponent(searchQuery));
    const fromDate = $("opp-from-date").value;
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    const toDate = $("opp-to-date").value;
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    const priorityLevel = $("opp-priority-filter") ? $("opp-priority-filter").value : "";
    if (priorityLevel) params.push("priority_level=" + encodeURIComponent(priorityLevel));
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
    const sort = $("lead-sort")?.value;
    if (sort) params.push("sort=" + encodeURIComponent(sort));
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
    const sort = $("customer-sort")?.value;
    if (sort) params.push("sort=" + encodeURIComponent(sort));
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
    const sort = $("rq-sort")?.value || "created_at";
    params.push("sort=" + encodeURIComponent(sort));
    const status = $("rq-status-filter")?.value?.trim();
    if (status) params.push("status=" + encodeURIComponent(status));
    // WP-224 — export with search
    const q = $("rq-search")?.value?.trim();
    if (q) params.push("q=" + encodeURIComponent(q));
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
    params.push("sort=" + encodeURIComponent($("task-sort").value));
    const status = $("task-status-filter").value;
    if (status) params.push("status=" + encodeURIComponent(status));
    // WP-225 — export with search
    const q = $("task-search")?.value?.trim();
    if (q) params.push("q=" + encodeURIComponent(q));
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
    // WP-225 — keyword search
    const q = $("task-search")?.value?.trim();
    if (q) params.set("q", q);
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
    // WP-225 — keyword search
    const q = $("task-search")?.value?.trim();
    if (q) params.push("q=" + encodeURIComponent(q));
    // WP-155 — date filter
    const fromDate = $("task-from-date")?.value;
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    const toDate = $("task-to-date")?.value;
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    return "/internal-tasks/count" + (params.length ? "?" + params.join("&") : "");
  }

  let taskRefreshVersion = 0;

  async function refreshTasks() {
    if (!bearer) return false;
    const version = ++taskRefreshVersion;
    const taskList = $("tasks-list");
    taskList.setAttribute("aria-busy", "true");
    $("tasks-load-status").textContent = "Carregando tarefas...";
    $("tasks-load-retry").hidden = true;
    try {
      const [tasks, count] = await Promise.all([
        taskApi(buildTaskUrl()),
        taskApi(buildTaskCountUrl()),
      ]);
      if (version !== taskRefreshVersion) return false;
      if (!Array.isArray(tasks) || !Number.isInteger(count) || count < 0) {
        throw new Error("Task list unavailable");
      }
      taskTotal = count;
      selectedTaskIds.clear();
      $("task-bulk-bar").hidden = true;
      renderTasks(tasks);
      updateTaskPagination();
      $("tasks-load-status").textContent = "";
      return true;
    } catch (error) {
      if (version !== taskRefreshVersion) return false;
      if (bearer) {
        $("tasks-load-status").textContent = "Não foi possível atualizar as tarefas. Os dados anteriores podem estar desatualizados.";
        $("tasks-load-retry").hidden = false;
      }
      return false;
    } finally {
      if (version === taskRefreshVersion) {
        taskList.setAttribute("aria-busy", "false");
      }
    }
  }

  function renderTasks(tasks) {
    const list = $("tasks-list");
    while (list.firstChild) list.removeChild(list.firstChild);
    if (!tasks.length) {
      const empty = document.createElement("p");
      empty.className = "small";
      empty.setAttribute("role", "status");
      empty.textContent = "Nenhuma tarefa encontrada.";
      list.appendChild(empty);
      return;
    }
    const statusLabels = {queued: "Fila", running: "Executando", succeeded: "Sucesso", failed: "Falha"};
    for (const task of tasks) {
      const item = document.createElement("div");
      item.className = "task-item";
      item.setAttribute("role", "listitem");
      // WP-172 — Checkbox for bulk retry
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "task-checkbox";
      checkbox.setAttribute("aria-label", "Selecionar tarefa #" + task.id);
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
        err.setAttribute("role", "alert");
        err.textContent = "Erro: " + task.error_code;
        item.appendChild(err);
      }
      if (task.status === "failed") {
        const retryBtn = document.createElement("button");
        retryBtn.type = "button";
        retryBtn.className = "secondary task-retry-btn";
        retryBtn.textContent = "Tentar novamente";
        retryBtn.setAttribute("aria-label", "Tentar novamente a tarefa #" + task.id);
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

  $("tasks-load-retry").addEventListener("click", () => {
    withButton($("tasks-load-retry"), () => refreshTasks());
  });

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

  // WP-225 — task search listener
  $("task-search").addEventListener("input", () => {
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
    // WP-225 — clear search
    $("task-search").value = "";
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

  // WP-230 — Bulk delete review queue items
  $("rq-bulk-delete").addEventListener("click", () => {
    const button = $("rq-bulk-delete");
    withButton(button, async () => {
      const ids = Array.from(selectedRqIds);
      if (!ids.length) {notify("Nenhum item selecionado.", true); return;}
      if (!confirm("Excluir " + ids.length + " item(s) da fila de revisão?")) return;
      try {
        const result = await reviewApi("/review-queue/bulk-delete", "POST", {
          item_ids: ids,
        });
        selectedRqIds.clear();
        notify(result.deleted + " item(s) excluído(s). " + result.skipped.length + " ignorado(s).");
        await refreshReviewQueue();
      } catch (e) {
        notify("Falha ao excluir itens.", true);
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
      path.startsWith("/proposal-briefs?") ||
      path.startsWith("/proposal-briefs/export.csv");
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
    const opportunityId = $("briefs-opportunity-filter") ? $("briefs-opportunity-filter").value : "";
    const q = $("briefs-search") ? $("briefs-search").value.trim() : "";
    const sort = $("briefs-sort") ? $("briefs-sort").value : "created_at";
    const fromDate = $("briefs-from-date") ? $("briefs-from-date").value : "";
    const toDate = $("briefs-to-date") ? $("briefs-to-date").value : "";
    if (status) params.push("status=" + encodeURIComponent(status));
    if (opportunityId) params.push("opportunity_id=" + encodeURIComponent(opportunityId));
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
    const opportunityId = $("briefs-opportunity-filter") ? $("briefs-opportunity-filter").value : "";
    const q = $("briefs-search") ? $("briefs-search").value.trim() : "";
    const fromDate = $("briefs-from-date") ? $("briefs-from-date").value : "";
    const toDate = $("briefs-to-date") ? $("briefs-to-date").value : "";
    if (status) params.push("status=" + encodeURIComponent(status));
    if (opportunityId) params.push("opportunity_id=" + encodeURIComponent(opportunityId));
    if (q) params.push("q=" + encodeURIComponent(q));
    if (fromDate) params.push("from_date=" + encodeURIComponent(fromDate));
    if (toDate) params.push("to_date=" + encodeURIComponent(toDate));
    return "/proposal-briefs/count" + (params.length ? "?" + params.join("&") : "");
  }

  async function refreshBriefs() {
    if (!bearer) return false;
    const epoch = ++briefEpoch;
    const list = $("briefs-list");
    list.setAttribute("aria-busy", "true");
    $("briefs-load-status").textContent = "Carregando briefs...";
    $("briefs-load-retry").hidden = true;
    try {
      populateBriefOpportunityFilter();
      const [briefs, countData] = await Promise.all([
        briefApi(buildBriefUrl()),
        briefApi(buildBriefCountUrl()),
      ]);
      if (epoch !== briefEpoch) return false;
      if (!Array.isArray(briefs) || !Number.isInteger(countData?.count) || countData.count < 0) {
        throw new Error("Brief list unavailable");
      }
      briefTotal = countData.count;
      selectedBriefIds.clear();
      $("briefs-bulk-bar").hidden = true;
      renderBriefs(briefs);
      updateBriefPagination();
      $("briefs-load-status").textContent = "";
      return true;
    } catch (e) {
      if (epoch === briefEpoch && bearer) {
        $("briefs-load-status").textContent = "Não foi possível carregar os briefs. Os dados anteriores podem estar desatualizados.";
        $("briefs-load-retry").hidden = false;
      }
      return false;
    } finally {
      if (epoch === briefEpoch) list.setAttribute("aria-busy", "false");
    }
  }

  $("briefs-load-retry").addEventListener("click", () => {
    withButton($("briefs-load-retry"), () => refreshBriefs());
  });

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
      p.setAttribute("role", "status");
      p.textContent = "Nenhum brief encontrado.";
      list.appendChild(p);
      return;
    }
    briefs.forEach((brief) => {
      const item = document.createElement("div");
      item.className = "brief-item";
      item.style.cursor = "pointer";
      item.tabIndex = 0;
      item.setAttribute("role", "button");
      item.setAttribute("aria-label", "Abrir brief de " + (brief.opportunity_title || "Sem título"));
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
      item.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectBrief(brief.id, brief.opportunity_title || "Sem título");
        }
      });
      list.appendChild(item);
    });
  }

  // WP-187 — Load and display brief detail
  let briefDetailVersion = 0;
  async function selectBrief(briefId, title) {
    const detail = $("brief-detail");
    if (!detail) return;
    const version = ++briefDetailVersion;
    const session = sessionEpoch;
    const isCurrent = () => version === briefDetailVersion && session === sessionEpoch &&
      bearer && !detail.hidden && String(detail.dataset.briefId) === String(briefId);
    // Toggle close
    if (!detail.hidden && detail.dataset.briefId == briefId) {
      detail.hidden = true;
      return;
    }
    detail.hidden = false;
    detail.dataset.briefId = briefId;
    const titleEl = $("brief-detail-title");
    if (titleEl) titleEl.textContent = "Brief: " + title;
    const content = $("brief-detail-content");
    if (content) content.textContent = "Carregando...";
    try {
      const [brief, convs] = await Promise.all([
        briefApi("/proposal-briefs/" + briefId),
        briefApi("/proposal-briefs/" + briefId + "/conversations").catch(() => []),
      ]);
      if (!isCurrent()) return;
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
      if (isCurrent() && content) content.textContent = "Falha ao carregar brief.";
    }
  }

  // WP-211 — Back button for brief detail
  $("brief-detail-back")?.addEventListener("click", () => {
    briefDetailVersion += 1;
    const detail = $("brief-detail");
    if (detail) detail.hidden = true;
  });

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

  $("briefs-refresh").addEventListener("click", () => withButton($("briefs-refresh"), async () => {
    briefOffset = 0;
    await refreshBriefs();
  }));

  $("briefs-status-filter").addEventListener("change", () => {
    briefOffset = 0;
    refreshBriefs().catch(() => {});
  });

  // WP-234 — Opportunity filter change
  $("briefs-opportunity-filter").addEventListener("change", () => {
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
    if ($("briefs-opportunity-filter")) $("briefs-opportunity-filter").value = "";
    if ($("briefs-search")) $("briefs-search").value = "";
    if ($("briefs-sort")) $("briefs-sort").value = "created_at";
    if ($("briefs-from-date")) $("briefs-from-date").value = "";
    if ($("briefs-to-date")) $("briefs-to-date").value = "";
    briefOffset = 0;
    refreshBriefs().catch(() => {});
  });

  $("briefs-export-csv").addEventListener("click", () => {
    const sort = $("briefs-sort") ? $("briefs-sort").value : "created_at";
    const params = ["sort=" + encodeURIComponent(sort)];
    const status = $("briefs-status-filter") ? $("briefs-status-filter").value : "";
    const opportunityId = $("briefs-opportunity-filter") ? $("briefs-opportunity-filter").value : "";
    const q = $("briefs-search") ? $("briefs-search").value.trim() : "";
    const fromDate = $("briefs-from-date") ? $("briefs-from-date").value : "";
    const toDate = $("briefs-to-date") ? $("briefs-to-date").value : "";
    if (status) params.push("status=" + encodeURIComponent(status));
    if (opportunityId) params.push("opportunity_id=" + encodeURIComponent(opportunityId));
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

  // Agent configuration loading
  let agentConfigLoadVersion = 0;
  async function loadAgentConfig() {
    if (!bearer || !company) return;
    const version = ++agentConfigLoadVersion;
    const status = $("agent-config-status");
    const retry = $("agent-config-load-retry");
    const isCurrent = () => version === agentConfigLoadVersion;
    status.textContent = "Carregando configuração do agente";
    retry.hidden = true;
    retry.disabled = true;
    try {
      const res = await api(`/companies/${company}/agent-config`);
      if (!isCurrent()) return;
      $("agent-system-prompt").value = res.system_prompt || "";
      $("agent-temperature").value = res.temperature ?? "";
      $("agent-max-tokens").value = res.max_tokens ?? "";
      $("agent-model").value = res.model ?? "";
      status.textContent = "";
    } catch {
      if (!isCurrent()) return;
      status.textContent = "Não foi possível carregar a configuração do agente.";
      retry.hidden = false;
    } finally {
      if (isCurrent()) retry.disabled = false;
    }
  }

  $("agent-config-load-retry")?.addEventListener("click", () => {
    loadAgentConfig();
  });

  // WP-205 — Agent configuration save
  let agentConfigSaving = false;
  $("agent-config-save")?.addEventListener("click", async () => {
    const body = {};
    const prompt = $("agent-system-prompt").value.trim();
    const temp = $("agent-temperature").value;
    const maxTokens = $("agent-max-tokens").value;
    const model = $("agent-model").value;
    if (prompt) body.system_prompt = prompt;
    if (temp !== "") body.temperature = parseFloat(temp);
    if (maxTokens !== "") body.max_tokens = parseInt(maxTokens, 10);
    if (model !== "") body.model = model;
    if (!bearer || !company || agentConfigSaving) return;
    agentConfigSaving = true;
    const saveButton = $("agent-config-save");
    saveButton.disabled = true;

    try {
      await api(`/companies/${company}/agent-config`, "PUT", body);
      $("agent-config-status").textContent = "✓ Salvo com sucesso";
      $("agent-config-status").style.color = "var(--success)";
    } catch (e) {
      $("agent-config-status").textContent = "Erro ao salvar";
      $("agent-config-status").style.color = "var(--danger)";
    } finally {
      agentConfigSaving = false;
      saveButton.disabled = false;
    }
  });

  // Load agent config on connect
  const origConnect = connect;
  // (connect is defined above, we hook into workspaceObserver instead)
  workspaceObserver.observe($("agent-config-title") ? $("agent-config-title").closest(".panel") : null, {attributes: true});

  // Load config when workspace becomes visible
  const origRefreshList = refreshList;
  // Load agent config after initial connection
  const loadAgentConfigOnConnect = () => {
    if (bearer && company) {
      loadAgentConfig();
      loadReplyTemplateList();
    }
  };
  // Call after a short delay to ensure connection is established
  setTimeout(loadAgentConfigOnConnect, 1000);

  // WP-265 — Reply templates management
  let replyTemplateLoadVersion = 0;
  function updateReplyTemplateCharacterCount(inputId, countId, maxLength) {
    const input = $(inputId);
    const count = $(countId);
    if (!input || !count) return;
    const value = typeof input.value === "string" ? input.value : "";
    const characters = Array.from(value);
    if (characters.length > maxLength) {
      input.value = characters.slice(0, maxLength).join("");
    }
    count.textContent = `${Math.min(characters.length, maxLength)}/${maxLength} caracteres`;
  }

  function normalizeReplyTemplateSearchText(value) {
    return String(value || "")
      .toLocaleLowerCase()
      .normalize("NFD")
      .replace(/\p{M}/gu, "")
      .replace(/\s+/gu, " ")
      .trim();
  }

  $("reply-template-name")?.addEventListener("input", () => {
    updateReplyTemplateCharacterCount("reply-template-name", "reply-template-name-count", 100);
  });
  $("reply-template-content")?.addEventListener("input", () => {
    updateReplyTemplateCharacterCount("reply-template-content", "reply-template-content-count", 4000);
  });
  updateReplyTemplateCharacterCount("reply-template-name", "reply-template-name-count", 100);
  updateReplyTemplateCharacterCount("reply-template-content", "reply-template-content-count", 4000);

  function applyReplyTemplateFilter() {
    const search = $("reply-template-search");
    const clearSearch = $("reply-template-search-clear");
    const filterStatus = $("reply-template-filter-status");
    const listEl = $("reply-template-list");
    if (!search || !filterStatus || !listEl) return;
    const query = normalizeReplyTemplateSearchText(search.value);
    if (clearSearch) clearSearch.disabled = query === "";
    const items = Array.from(listEl.children).filter(item => item.className === "reply-template-item");
    let visible = 0;
    for (const item of items) {
      const searchText = normalizeReplyTemplateSearchText(item.dataset?.searchText || "");
      item.hidden = query !== "" && !searchText.includes(query);
      if (!item.hidden) visible++;
    }
    if (!query || items.length === 0) {
      filterStatus.textContent = "";
    } else if (visible === 0) {
      filterStatus.textContent = "Nenhum template corresponde à busca.";
    } else {
      filterStatus.textContent = visible === 1
        ? "1 template corresponde à busca."
        : `${visible} templates correspondem à busca.`;
    }
  }

  $("reply-template-search")?.addEventListener("input", applyReplyTemplateFilter);
  $("reply-template-search")?.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !(event.currentTarget?.value || "").trim()) return;
    event.preventDefault();
    event.currentTarget.value = "";
    applyReplyTemplateFilter();
  });
  $("reply-template-search-clear")?.addEventListener("click", () => {
    const search = $("reply-template-search");
    if (!search) return;
    search.value = "";
    applyReplyTemplateFilter();
    search.focus();
  });

  async function loadReplyTemplateList() {
    if (!bearer || !company) return;
    const listEl = $("reply-template-list");
    if (!listEl) return;
    const version = ++replyTemplateLoadVersion;
    const loadStatus = $("reply-template-load-status");
    const retry = $("reply-template-load-retry");
    const isCurrent = () => version === replyTemplateLoadVersion;
    listEl.setAttribute("aria-busy", "true");
    loadStatus.textContent = "Carregando templates";
    retry.hidden = true;
    retry.disabled = true;
    try {
      const templates = await templateApi(`/companies/${company}/reply-templates`, "GET");
      if (!isCurrent()) return;
      listEl.replaceChildren();
      if (!templates || templates.length === 0) {
        const empty = document.createElement("p");
        empty.className = "small";
        empty.setAttribute("role", "status");
        empty.textContent = "Nenhum template salvo.";
        listEl.appendChild(empty);
        const search = $("reply-template-search");
        if (search) search.value = "";
        applyReplyTemplateFilter();
        loadStatus.textContent = "";
        return;
      }
      for (const t of templates) {
        const item = document.createElement("div");
        item.className = "reply-template-item";
        if (item.dataset) {
          item.dataset.templateId = String(t.id);
          item.dataset.templateName = t.name;
        }
        const info = document.createElement("div");
        const name = document.createElement("span");
        name.className = "reply-template-item-name";
        name.textContent = t.name;
        const preview = document.createElement("span");
        preview.className = "reply-template-item-preview";
        preview.textContent = t.content;
        if (item.dataset) item.dataset.searchText = normalizeReplyTemplateSearchText(`${t.name} ${t.content}`);
        info.appendChild(name);
        info.appendChild(preview);
        item.appendChild(info);
        const deleteBtn = document.createElement("button");
        const editBtn = document.createElement("button");
        const duplicateBtn = document.createElement("button");
        editBtn.type = "button";
        editBtn.className = "secondary reply-template-edit";
        editBtn.textContent = "Editar";
        editBtn.addEventListener("click", () => beginReplyTemplateEdit(t, editBtn));
        item.appendChild(editBtn);
        duplicateBtn.type = "button";
        duplicateBtn.className = "secondary";
        duplicateBtn.textContent = "Duplicar";
        duplicateBtn.addEventListener("click", () => duplicateReplyTemplate(t, duplicateBtn));
        item.appendChild(duplicateBtn);
        deleteBtn.type = "button";
        deleteBtn.className = "danger";
        deleteBtn.textContent = "Excluir";
        deleteBtn.addEventListener("click", () => deleteReplyTemplate(t.id, item, deleteBtn));
        item.appendChild(deleteBtn);
        listEl.appendChild(item);
      }
      applyReplyTemplateFilter();
      loadStatus.textContent = "";
    } catch {
      if (!isCurrent()) return;
      loadStatus.textContent = "Não foi possível carregar os templates.";
      retry.hidden = false;
    } finally {
      if (isCurrent()) {
        listEl.setAttribute("aria-busy", "false");
        retry.disabled = false;
      }
    }
  }

  $("reply-template-load-retry")?.addEventListener("click", () => {
    loadReplyTemplateList();
  });

  let replyTemplateDuplicating = false;
  function suggestReplyTemplateDuplicateName(template) {
    const listEl = $("reply-template-list");
    const names = new Set(Array.from(listEl?.children || [])
      .filter(item => item.className === "reply-template-item")
      .map(item => normalizeReplyTemplateSearchText(item.dataset?.templateName || "")));
    const original = Array.from(String(template.name || ""));
    for (let copyNumber = 1; ; copyNumber++) {
      const suffix = copyNumber === 1 ? " (cópia)" : ` (cópia ${copyNumber})`;
      const prefix = original.slice(0, 100 - Array.from(suffix).length).join("");
      const candidate = `${prefix}${suffix}`;
      if (!names.has(normalizeReplyTemplateSearchText(candidate))) return candidate;
    }
  }

  function setReplyTemplateDuplicateButtonsDisabled(disabled) {
    const listEl = $("reply-template-list");
    if (!listEl) return;
    for (const item of Array.from(listEl.children || [])) {
      if (item.className !== "reply-template-item") continue;
      const duplicateButton = Array.from(item.children || []).find(
        child => child.textContent === "Duplicar"
      );
      if (duplicateButton) {
        duplicateButton.disabled = disabled || editingReplyTemplateId === Number(item.dataset?.templateId);
      }
    }
  }

  async function duplicateReplyTemplate(template, duplicateBtn) {
    if (!bearer || !company || replyTemplateDuplicating || duplicateBtn.disabled || editingReplyTemplateId === template.id) return;
    const proposedName = suggestReplyTemplateDuplicateName(template);
    const name = prompt("Nome do novo template:", proposedName);
    if (name === null) return;
    const trimmedName = name.trim();
    const loadStatus = $("reply-template-load-status");
    if (!trimmedName || Array.from(trimmedName).length > 100) {
      if (loadStatus) loadStatus.textContent = "Informe um nome de até 100 caracteres.";
      return;
    }
    replyTemplateDuplicating = true;
    setReplyTemplateDuplicateButtonsDisabled(true);
    if (loadStatus) loadStatus.textContent = "Duplicando template";
    try {
      const createdTemplate = await templateApi(`/companies/${company}/reply-templates`, "POST", {
        name: trimmedName,
        content: template.content,
      });
      if (loadStatus) loadStatus.textContent = "Template duplicado.";
      notify("Template duplicado.");
      await loadReplyTemplateList();
      if (editingReplyTemplateId !== null) {
        setReplyTemplateEditButtonsDisabled(true);
        setReplyTemplateDeleteButtonDisabled(editingReplyTemplateId, true);
        setReplyTemplateDuplicateButtonDisabled(editingReplyTemplateId, true);
      }
      loadReplyTemplates();
      const createdItem = Array.from($("reply-template-list")?.children || []).find(
        item => item.className === "reply-template-item" &&
          createdTemplate?.id != null && item.dataset?.templateId === String(createdTemplate.id)
      );
      if (createdItem?.hidden) {
        const search = $("reply-template-search");
        if (search) search.value = "";
        applyReplyTemplateFilter();
      }
      const createdEditButton = Array.from(createdItem?.children || []).find(
        child => child.className === "secondary reply-template-edit"
      );
      createdEditButton?.focus();
    } catch {
      if (loadStatus) loadStatus.textContent = "Não foi possível duplicar o template.";
      notify("Erro ao duplicar template.");
    } finally {
      replyTemplateDuplicating = false;
      setReplyTemplateDuplicateButtonsDisabled(false);
    }
  }

  async function deleteReplyTemplate(templateId, itemEl, deleteBtn) {
    if (!bearer || !company || deleteBtn.disabled || editingReplyTemplateId === templateId) return;
    if (!confirm("Excluir este template?")) return;
    deleteBtn.disabled = true;
    const loadStatus = $("reply-template-load-status");
    if (loadStatus) loadStatus.textContent = "Excluindo template";
    try {
      await templateApi(`/companies/${company}/reply-templates/${templateId}`, "DELETE");
      if (editingReplyTemplateId === templateId) resetReplyTemplateForm();
      itemEl.remove();
      const listEl = $("reply-template-list");
      const nextVisibleItem = listEl && Array.from(listEl.children).find(
        item => item.className === "reply-template-item" && !item.hidden
      );
      const nextDeleteButton = nextVisibleItem?.querySelector(".danger");
      if (nextDeleteButton) nextDeleteButton.focus();
      else $("reply-template-search")?.focus();
      if (listEl && listEl.children.length === 0) {
        const search = $("reply-template-search");
        if (search) search.value = "";
        const empty = document.createElement("p");
        empty.className = "small";
        empty.setAttribute("role", "status");
        empty.textContent = "Nenhum template salvo.";
        listEl.appendChild(empty);
      }
      applyReplyTemplateFilter();
      if (loadStatus) loadStatus.textContent = "Template excluído.";
      notify("Template excluído.");
      // Refresh the reply template selector in conversation reply
      loadReplyTemplates();
    } catch {
      if (loadStatus) loadStatus.textContent = "Não foi possível excluir o template.";
      notify("Erro ao excluir template.");
    } finally {
      deleteBtn.disabled = false;
    }
  }

  let editingReplyTemplateId = null;
  let editingReplyTemplateTrigger = null;
  let editingReplyTemplateOriginal = null;
  function setReplyTemplateEditButtonsDisabled(disabled) {
    const listEl = $("reply-template-list");
    if (!listEl) return;
    for (const item of Array.from(listEl.children || [])) {
      if (item.className !== "reply-template-item") continue;
      for (const button of Array.from(item.children || [])) {
        if (button.className === "secondary reply-template-edit") button.disabled = disabled;
      }
    }
  }

  function setReplyTemplateDeleteButtonDisabled(templateId, disabled) {
    const listEl = $("reply-template-list");
    const item = Array.from(listEl?.children || []).find(
      child => child.className === "reply-template-item" && child.dataset?.templateId === String(templateId)
    );
    const deleteButton = Array.from(item?.children || []).find(child => child.className === "danger");
    if (deleteButton) deleteButton.disabled = disabled;
  }

  function setReplyTemplateDuplicateButtonDisabled(templateId, disabled) {
    const listEl = $("reply-template-list");
    const item = Array.from(listEl?.children || []).find(
      child => child.className === "reply-template-item" && child.dataset?.templateId === String(templateId)
    );
    const duplicateButton = Array.from(item?.children || []).find(
      child => child.textContent === "Duplicar"
    );
    if (duplicateButton) duplicateButton.disabled = disabled;
  }

  function beginReplyTemplateEdit(template, trigger = null) {
    if (editingReplyTemplateId !== null) return;
    editingReplyTemplateId = template.id;
    editingReplyTemplateTrigger = trigger;
    editingReplyTemplateOriginal = {name: template.name, content: template.content};
    setReplyTemplateEditButtonsDisabled(true);
    setReplyTemplateDeleteButtonDisabled(template.id, true);
    setReplyTemplateDuplicateButtonDisabled(template.id, true);
    $("reply-template-name").value = template.name;
    $("reply-template-content").value = template.content;
    updateReplyTemplateCharacterCount("reply-template-name", "reply-template-name-count", 100);
    updateReplyTemplateCharacterCount("reply-template-content", "reply-template-content-count", 4000);
    $("reply-template-save").textContent = "Salvar alterações";
    $("reply-template-cancel-edit").hidden = false;
    $("reply-template-save-status").textContent = `Editando: ${template.name}`;
    $("reply-template-name").focus();
  }

  function resetReplyTemplateForm() {
    const editedTemplateId = editingReplyTemplateId;
    editingReplyTemplateId = null;
    editingReplyTemplateTrigger = null;
    editingReplyTemplateOriginal = null;
    setReplyTemplateEditButtonsDisabled(false);
    if (editedTemplateId !== null) setReplyTemplateDeleteButtonDisabled(editedTemplateId, false);
    if (editedTemplateId !== null) setReplyTemplateDuplicateButtonDisabled(editedTemplateId, false);
    $("reply-template-form")?.reset();
    updateReplyTemplateCharacterCount("reply-template-name", "reply-template-name-count", 100);
    updateReplyTemplateCharacterCount("reply-template-content", "reply-template-content-count", 4000);
    $("reply-template-save").textContent = "Salvar template";
    $("reply-template-cancel-edit").hidden = true;
    $("reply-template-save-status").textContent = "";
  }

  function cancelReplyTemplateEdit() {
    if (replyTemplateSaving) return;
    if (editingReplyTemplateOriginal && (
      $("reply-template-name").value !== editingReplyTemplateOriginal.name ||
      $("reply-template-content").value !== editingReplyTemplateOriginal.content
    ) && !confirm("Descartar as alterações não salvas deste template?")) return;
    const trigger = editingReplyTemplateTrigger;
    resetReplyTemplateForm();
    $("reply-template-save-status").textContent = "Edição cancelada.";
    if (trigger?.isConnected) trigger.focus();
    else $("reply-template-name").focus();
  }

  globalThis.addEventListener?.("beforeunload", event => {
    if (editingReplyTemplateId === null || !editingReplyTemplateOriginal) return;
    const changed = $("reply-template-name").value !== editingReplyTemplateOriginal.name ||
      $("reply-template-content").value !== editingReplyTemplateOriginal.content;
    if (!changed) return;
    event.preventDefault();
    event.returnValue = "";
  });

  $("reply-template-cancel-edit")?.addEventListener("click", cancelReplyTemplateEdit);
  ["reply-template-name", "reply-template-content"].forEach(id => {
    $(id)?.addEventListener("keydown", event => {
      if (event.key !== "Escape" || editingReplyTemplateId === null) return;
      if (replyTemplateSaving) return;
      event.preventDefault();
      cancelReplyTemplateEdit();
    });
  });

  let replyTemplateSaving = false;
  $("reply-template-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!bearer || !company || replyTemplateSaving) return;
    const saveStatus = $("reply-template-save-status");
    const name = $("reply-template-name").value.trim();
    const content = $("reply-template-content").value.trim();
    if (!name || !content) {
      saveStatus.textContent = "Preencha o nome e o conteúdo do template.";
      $(name ? "reply-template-content" : "reply-template-name").focus();
      return;
    }
    replyTemplateSaving = true;
    const saveButton = $("reply-template-save");
    const cancelButton = $("reply-template-cancel-edit");
    saveButton.disabled = true;
    if (cancelButton) cancelButton.disabled = true;
    saveStatus.setAttribute("aria-busy", "true");
    saveStatus.textContent = "Salvando template";
    try {
      const editingId = editingReplyTemplateId;
      const savedTemplate = await templateApi(editingId
        ? `/companies/${company}/reply-templates/${editingId}`
        : `/companies/${company}/reply-templates`, editingId ? "PUT" : "POST", {name, content});
      resetReplyTemplateForm();
      saveStatus.textContent = editingId ? "Template atualizado." : "Template salvo.";
      $("reply-template-name").focus();
      notify(editingId ? "Template atualizado." : "Template salvo.");
      await loadReplyTemplateList();
      if (!editingId && savedTemplate?.id != null) {
        const createdItem = Array.from($("reply-template-list")?.children || []).find(
          item => item.className === "reply-template-item" &&
            item.dataset?.templateId === String(savedTemplate.id)
        );
        if (createdItem?.hidden) {
          const search = $("reply-template-search");
          if (search) search.value = "";
          applyReplyTemplateFilter();
        }
        const createdEditButton = Array.from(createdItem?.children || []).find(
          child => child.className === "secondary reply-template-edit"
        );
        createdEditButton?.focus();
      }
      // Refresh the reply template selector in conversation reply
      loadReplyTemplates();
    } catch (err) {
      saveStatus.textContent = "Não foi possível salvar o template.";
      notify("Erro ao salvar template.");
    } finally {
      replyTemplateSaving = false;
      saveButton.disabled = false;
      if (cancelButton) cancelButton.disabled = false;
      saveStatus.setAttribute("aria-busy", "false");
    }
  });

})();
