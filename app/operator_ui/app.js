"use strict";

// Piloto local: Bearer apenas em memória desta aba. Nunca logar ou persistir.
(() => {
  const $ = (id) => document.getElementById(id);

  let bearer = null;
  let sessionEpoch = 0;
  let opportunities = [];
  let selectedId = null;
  let activeBrief = null;
  let selectionVersion = 0;

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
  }

  function disconnect(message = "Acesso desconectado.") {
    sessionEpoch += 1;
    bearer = null;
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
        await refreshList(null);
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
})();
