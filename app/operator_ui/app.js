"use strict";

// Piloto local: Bearer apenas em memória desta aba. Nunca logar ou persistir.
(() => {
  const $ = (id) => document.getElementById(id);

  let bearer = null;
  let sessionEpoch = 0;
  let reviewEpoch = 0;
  let reviewOffset = 0;
  const reviewPageSize = 50;
  let taskFilter = "";
  let opportunities = [];
  let selectedId = null;
  let activeBrief = null;
  let selectionVersion = 0;
  let conversations = [];
  let selectedConvId = null;

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
  const actionLabels = {
    pending: "Pendente",
    ignore: "Ignorar",
    follow: "Acompanhar",
    prepare_proposal: "Preparar proposta",
    in_progress: "Em andamento",
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
      ["selected-id", "selected-title", "selected-description", "selected-url",
        "selected-budget", "selected-deadline", "selected-requirements"]
    )) {
      $(id).textContent = "";
    }
    $("brief-guide").textContent = "";
    $("brief-status").textContent = "Sem brief";
  }

  function disconnect(message = "Acesso desconectado.") {
    sessionEpoch += 1;
    bearer = null;
    reviewEpoch += 1;
    reviewOffset = 0;
    taskFilter = "";
    $("rq-list").replaceChildren();
    $("rq-count").textContent = "—";
    $("rq-summary").textContent = "Resumo operacional indisponível.";
    $("rq-aging").textContent = "Atrasos: indisponível.";
    $("rq-form").reset();
    $("it-list").replaceChildren();
    $("it-count").textContent = "—";
    $("it-summary").textContent = "Resumo indisponível.";
    $("it-filter").value = "";
    opportunities = [];
    conversations = [];
    selectedConvId = null;
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
    notify(message);
  }

  async function api(path, options = {}) {
    if (!bearer) {
      throw new Error("Conecte uma identidade de operador.");
    }
    // Somente caminhos internos fixos. Não aceitar URLs de anúncio como destino de fetch.
    if (!/^\/(opportunities)(\/\d+(\/triage|\/proposal-brief)?)?$/.test(path)) {
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
    $("brief-status").textContent = exists
      ? brief.status === "ready_for_review" ? "Pronto para revisão" : "Rascunho"
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
    text("selected-title", record.title);
    text("selected-description", record.description);
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
    const result = await api("/opportunities");
    if (!Array.isArray(result)) {
      throw new Error("Resposta de listagem inválida.");
    }
    opportunities = result;
    if (preferId !== null && opportunities.some((item) => item.id === preferId)) {
      await selectOpportunity(preferId);
    } else {
      clearSelection();
      showList();
    }
  }


  // Review queue uses the same in-memory Bearer session, with a strict route allowlist.
  async function reviewApi(path, method = "GET", body) {
    if (!bearer) throw new Error("Conecte um operador.");
    if (typeof path !== "string" || /[\u0000-\u0020\u007f]/.test(path) ||
        !(/^\/review-queue\/(?:\?limit=(?:[1-9]|[1-9][0-9]|100)&offset=(?:0|[1-9][0-9]*))?$/.test(path) ||
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
          await reviewApi("/review-queue/" + item.id + "/decision", "PATCH",
            {decision, operator_note: note.value.trim() || null});
          await refreshReviewQueue();
          notify("Decisão registrada. Nenhuma mensagem enviada.");
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

  // Internal tasks panel — read-only view of internal task state.
  const taskStatusLabels = {queued: "Aguardando", running: "Em execução", succeeded: "Concluída", failed: "Falha"};
  async function taskApi(path) {
    if (!bearer) throw new Error("Conecte um operador.");
    if (typeof path !== "string" || /[\u0000-\u0020\u007f]/.test(path) ||
        !(/^\/internal-tasks\/(?:\?status=(?:queued|running|succeeded|failed))?$/.test(path) ||
          /^\/internal-tasks\/summary$/.test(path))) {
      throw new Error("Rota de tarefas não permitida.");
    }
    const epoch = sessionEpoch;
    const headers = {Authorization: "Bearer " + bearer};
    const response = await fetch(path, {method: "GET", headers,
      credentials: "omit", cache: "no-store", redirect: "error", referrerPolicy: "no-referrer"});
    if (epoch !== sessionEpoch) throw new Error("Sessão encerrada.");
    if (response.status === 401) {
      disconnect("Credencial inválida.");
      throw new ApiFailure(401);
    }
    if (!response.ok) throw new ApiFailure(response.status);
    return response.json();
  }
  async function refreshInternalTasks() {
    const [items, summary] = await Promise.all([
      taskApi("/internal-tasks/" + (taskFilter ? "?status=" + taskFilter : "")),
      taskApi("/internal-tasks/summary"),
    ]);
    if (!Array.isArray(items)) throw new Error("Lista de tarefas inválida.");
    const counts = [
      "Aguardando: " + (summary.queued || 0),
      "Executando: " + (summary.running || 0),
      "Concluídas: " + (summary.succeeded || 0),
      "Falhas: " + (summary.failed || 0),
    ];
    if (summary.overdue_queued > 0) counts.push("Atrasadas: " + summary.overdue_queued);
    if (summary.expired_running > 0) counts.push("Lease expirado: " + summary.expired_running);
    $("it-summary").textContent = counts.join(" · ");
    $("it-count").textContent = items.length + " tarefa(s)";
    const list = $("it-list");
    list.replaceChildren();
    for (const task of items) {
      const card = document.createElement("article");
      card.className = "task-card";
      const heading = document.createElement("strong");
      heading.textContent = "#" + task.id + " · " + (taskStatusLabels[task.status] || task.status);
      const meta = document.createElement("p");
      meta.className = "small";
      const parts = ["Evento: " + (task.event_id || "—")];
      if (task.error_code) parts.push("Erro: " + task.error_code);
      if (task.created_at) parts.push("Criada: " + new Date(task.created_at).toLocaleString("pt-BR"));
      meta.textContent = parts.join(" · ");
      card.append(heading, meta);
      list.append(card);
    }
    if (!items.length) {
      const p = document.createElement("p");
      p.className = "small";
      p.textContent = "Nenhuma tarefa" + (taskFilter ? " com status '" + taskFilter + "'" : "") + ".";
      list.append(p);
    }
  }
  $("it-refresh").addEventListener("click", () => withButton($("it-refresh"), refreshInternalTasks));
  $("it-filter").addEventListener("change", () => {
    taskFilter = $("it-filter").value;
    refreshInternalTasks().catch(() => {
      notify("Falha ao atualizar tarefas.", true);
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
        await Promise.all([refreshList(null), refreshReviewQueue(), refreshInternalTasks()]);
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

  // Conversations — strict allowlist, same pattern as reviewApi/taskApi.
  async function conversationApi(path, method = "GET", body) {
    if (!bearer) throw new Error("Conecte um operador.");
    if (!(/^\/companies\/\d+\/conversations$/.test(path) ||
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

  function showConversationList() {
    const target = $("conv-list");
    target.replaceChildren();
    const ordered = [...conversations].sort((a, b) => b.id - a.id);
    if (!ordered.length) {
      const empty = document.createElement("p");
      empty.className = "small";
      empty.textContent = "Nenhuma conversa registrada.";
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
        conversations = await conversationApi("/companies/" + company + "/conversations");
      } else {
        conversations = [];
      }
    } catch (error) {
      conversations = [];
    }
    showConversationList();
    if (selectedConvId !== null && conversations.some((c) => c.id === selectedConvId)) {
      await selectConversation(selectedConvId);
    } else if (selectedConvId !== null) {
      selectedConvId = null;
      $("conv-detail").hidden = true;
      showConversationList();
    }
  }

  $("conv-refresh").addEventListener("click", () => {
    withButton($("conv-refresh"), async () => {
      await refreshConversations();
      notify("Conversas atualizadas.");
    });
  });

  $("conv-list").replaceChildren();
  $("conv-detail").hidden = true;

  // Integrate conversations into the connect flow.
  const _origAccessSubmit = $("access-form").onsubmit;
  $("access-form").addEventListener("submit", async (event) => {
    // The original handler runs first; we intercept after workspace is shown.
    // Use a MutationObserver to detect when workspace.hidden becomes false.
  }, true);
  // Simpler: just patch the connect success path by wrapping the existing behavior.
  // The access-form submit handler sets workspace.hidden = false on success.
  // We observe that change and load conversations.
  const workspaceObserver = new MutationObserver((records) => {
    for (const record of records) {
      if (record.attributeName === "hidden" && !$("workspace").hidden && bearer) {
        refreshConversations().catch(() => {});
        workspaceObserver.disconnect();
      }
    }
  });
  workspaceObserver.observe($("workspace"), {attributes: true});
})();
