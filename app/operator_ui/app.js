"use strict";

// Piloto local: Bearer apenas em memória desta aba. Nunca logar ou persistir.
(() => {
  const $ = (id) => document.getElementById(id);

  let bearer = null;
  let sessionEpoch = 0;
  let reviewEpoch = 0;
  let reviewOffset = 0;
  const reviewPageSize = 50;
  let opportunities = [];
  let selectedId = null;
  let oppOffset = 0;
  const oppPageSize = 50;
  let oppTotal = 0;
  let activeBrief = null;
  let selectionVersion = 0;
  let conversations = [];
  let selectedConvId = null;
  let convFilterChannel = "";
  let convFilterStatus = "";
  let convFilterQuery = "";
  let convFilterSort = "last_message";
  let convOffset = 0;
  const convPageSize = 50;
  let convTotal = 0;

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
      ["selected-id", "selected-url",
        "selected-budget", "selected-deadline", "selected-requirements"]
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
    if (!/^\/opportunities(\?[^"]*)?$/.test(path) &&
        !/^\/opportunities\/count(\?[^"]*)?$/.test(path) &&
        !/^\/opportunities\/\d+(\/(triage|proposal-brief)(\/approve|\/reject)?)?$/.test(path)) {
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
    if (!ordered.length) {
      const empty = document.createElement("p");
      empty.className = "small";
      empty.textContent = "Nenhuma oportunidade registrada.";
      target.append(empty);
      return;
    }
    for (const opportunity of ordered) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "opportunity-item";
      button.classList.toggle("active", opportunity.id === selectedId);
      const title = document.createElement("strong");
      title.textContent = "#" + opportunity.id + " · " + opportunity.title;
      const stage = document.createElement("span");
      stage.textContent = actionLabels[opportunity.next_action] || "Estado desconhecido";
      button.append(title, stage);
      button.addEventListener("click", () => {
        selectOpportunity(opportunity.id).catch(() => {
          notify("Falha ao consultar o brief desta oportunidade.", true);
        });
      });
      target.append(button);
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
    text("selected-url", record.external_url);
    text("selected-budget", record.budget);
    text("selected-deadline", record.deadline);
    text("selected-requirements", record.requirements);
    $("next-action").value = record.next_action;
    $("triage-note").value = record.triage_note || "";
    $("brief-status").textContent = "Carregando";
    showList();

    if (record.next_action === "prepare_proposal") {
      await loadBrief(id, version);
    } else {
      $("brief-status").textContent = "Não aplicável";
      $("brief-guide").textContent =
        "Registre 'Preparar proposta' na triagem para habilitar o brief.";
    }
  }

  async function refreshList(preferId = selectedId) {
    const showArchived = $("show-archived").checked;
    // WP-094 — opportunity search
    const searchQuery = $("opp-search").value.trim();
    // WP-095 — opportunity sort and pagination
    const sort = $("opp-sort").value;
    const params = [];
    if (!showArchived) params.push("exclude_archived=true");
    if (searchQuery) params.push("q=" + encodeURIComponent(searchQuery));
    params.push("sort=" + encodeURIComponent(sort));
    params.push("limit=" + oppPageSize);
    params.push("offset=" + oppOffset);
    const query = "?" + params.join("&");
    const [result, countResult] = await Promise.all([
      api("/opportunities" + query),
      api("/opportunities/count" + (showArchived ? "" : "?exclude_archived=true") + (searchQuery ? "&q=" + encodeURIComponent(searchQuery) : "")),
    ]);
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

  // WP-095 — Opportunity pagination
  $("opp-prev").addEventListener("click", () => withButton($("opp-prev"), async () => {
    oppOffset = Math.max(0, oppOffset - oppPageSize);
    await refreshList();
  }));
  $("opp-next").addEventListener("click", () => withButton($("opp-next"), async () => {
    oppOffset += oppPageSize;
    await refreshList();
  }));

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
    if (!(/^\/review-queue\/$/.test(path) ||
          /^\/review-queue\/summary$/.test(path) ||
          /^\/review-queue\/aging$/.test(path) ||
          /^\/review-queue\/synthetic-trigger$/.test(path) ||
          /^\/review-queue\/\d+\/decision$/.test(path))) {
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
  async function refreshReviewQueue() {
    const epoch = ++reviewEpoch;
    const [items, summary, aging] = await Promise.all([
      reviewApi("/review-queue/?limit=" + reviewPageSize + "&offset=" + reviewOffset),
      reviewApi("/review-queue/summary"),
      reviewApi("/review-queue/aging"),
    ]);
    if (epoch !== reviewEpoch) return;
    if (!Array.isArray(items)) throw new Error("Fila inválida.");
    $("rq-count").textContent = summary.pending + " pendente(s)";
    $("rq-prev").disabled = reviewOffset === 0;
    $("rq-next").disabled = reviewOffset + items.length >= summary.pending;
    $("rq-page").textContent = "Página " + (Math.floor(reviewOffset / reviewPageSize) + 1);
    $("rq-summary").textContent = "Pendentes: " + summary.pending +
      " · Aprovados: " + summary.approve + " · Rejeitados: " + summary.reject;
    $("rq-aging").textContent = "Pendentes há mais de 24h: " + aging.overdue_pending;
    const list = $("rq-list");
    list.replaceChildren();
    for (const item of items) {
      const card = document.createElement("article");
      card.className = "review-card";
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
        notify("Conectado. O acesso será descartado ao fechar ou recarregar a aba.");
      } catch (error) {
        disconnect("Não foi possível conectar. Use uma credencial de operador válida.");
      }
    });
  });

  $("disconnect-button").addEventListener("click", () => disconnect());
  window.addEventListener("pagehide", () => disconnect("Sessão encerrada."));

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
          source: "99freelas",
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
          /^\/conversations\/\d+\/messages$/.test(path))) {
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
    const query = params.toString();
    return "/companies/" + companyId + "/conversations/count" + (query ? "?" + query : "");
  }

  function showConversationList() {
    const target = $("conv-list");
    target.replaceChildren();
    const ordered = [...conversations].sort((a, b) => b.id - a.id);
    if (!ordered.length) {
      const empty = document.createElement("p");
      empty.className = "small";
      empty.textContent = convFilterChannel || convFilterStatus || convFilterQuery
        ? "Nenhuma conversa corresponde aos filtros."
        : "Nenhuma conversa registrada.";
      target.append(empty);
      return;
    }
    for (const conv of ordered) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "conversation-item";
      button.classList.toggle("active", conv.id === selectedConvId);
      const channel = channelLabels[conv.channel] || conv.channel;
      const title = document.createElement("strong");
      title.textContent = "#" + conv.id + " · " + channel;
      const meta = document.createElement("span");
      meta.textContent = conv.status || "—";
      button.append(title, meta);
      button.addEventListener("click", () => {
        selectConversation(conv.id).catch(() => {
          notify("Falha ao carregar mensagens desta conversa.", true);
        });
      });
      target.append(button);
    }
  }

  async function selectConversation(id) {
    selectedConvId = id;
    showConversationList();
    $("conv-detail").hidden = false;
    $("conv-reply-toggle").hidden = false;
    $("conv-close-toggle").hidden = false;
    $("reply-conv-id").value = id;
    const conv = conversations.find((c) => c.id === id);
    const channel = conv ? (channelLabels[conv.channel] || conv.channel) : "Conversa";
    $("conv-detail-header").textContent = channel + " · #" + id;
    try {
      const messages = await conversationApi("/conversations/" + id + "/messages");
      if (selectedConvId !== id) return;
      const target = $("conv-messages");
      target.replaceChildren();
      if (!messages.length) {
        const empty = document.createElement("p");
        empty.className = "small";
        empty.textContent = "Nenhuma mensagem.";
        target.append(empty);
        return;
      }
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
    } catch (error) {
      if (selectedConvId !== id) return;
      notify("Não foi possível carregar as mensagens.", true);
    }
  }

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
    convOffset = 0;
    $("conv-filter-channel").value = "";
    $("conv-filter-status").value = "";
    $("conv-search-q").value = "";
    $("conv-filter-sort").value = "last_message";
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
  }

  $("dashboard-refresh").addEventListener("click", () => withButton($("dashboard-refresh"), async () => {
    await refreshDashboard();
    notify("Dashboard atualizado.");
  }));

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
    const q = $("lead-search") ? $("lead-search").value.trim() : "";
    const sort = $("lead-sort") ? $("lead-sort").value : "id";
    let path = "/leads";
    const params = [];
    if (status) params.push("status=" + encodeURIComponent(status));
    if (q) params.push("q=" + encodeURIComponent(q));
    if (sort !== "id") params.push("sort=" + encodeURIComponent(sort));
    params.push("limit=" + leadPageSize);
    params.push("offset=" + leadOffset);
    if (params.length) path += "?" + params.join("&");
    const [leads, countResult] = await Promise.all([
      leadApi(path, "GET"),
      leadApi("/leads/count" + (status ? "?status=" + encodeURIComponent(status) : "") + (q ? "&q=" + encodeURIComponent(q) : ""), "GET")
    ]);
    leadTotal = countResult ? countResult.total || 0 : 0;
    leadListLength = (leads || []).length;
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
      const header = document.createElement("div");
      header.className = "lead-item-header";
      const name = document.createElement("span");
      name.className = "lead-item-name";
      name.textContent = lead.name || "Sem nome";
      const statusTag = document.createElement("span");
      statusTag.className = "tag";
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
    await refreshLeads();
    notify("Leads atualizados.");
  }));

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
    const sort = $("customer-sort")?.value;
    if (q) params.set("q", q);
    if (sort) params.set("sort", sort);
    params.set("limit", String(customerPageSize));
    params.set("offset", String(customerOffset));
    const search = params.toString();
    return "/customers" + (search ? "?" + search : "");
  }

  function buildCustomerCountUrl() {
    const params = new URLSearchParams();
    const q = $("customer-search")?.value?.trim();
    if (q) params.set("q", q);
    const search = params.toString();
    return "/customers/count" + (search ? "?" + search : "");
  }

  async function customerApi(path, method, body) {
    if (!bearer) throw new Error("Conecte um operador.");
    const allowedPattern = /^\/customers(\/count)?(\?.*)?$/;
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
      item.style.cursor = "pointer";
      item.addEventListener("click", () => {
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
        workspaceObserver.disconnect();
      }
    }
  });
  workspaceObserver.observe($("workspace"), {attributes: true});
})();
