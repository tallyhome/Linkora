(() => {
  const form = document.getElementById("extract-form");
  const urlsInput = document.getElementById("urls");
  const hostInput = document.getElementById("host");
  const btnExtract = document.getElementById("btn-extract");
  const btnLabel = btnExtract.querySelector(".btn-label");
  const btnSpinner = btnExtract.querySelector(".btn-spinner");
  const formError = document.getElementById("form-error");
  const results = document.getElementById("results");
  const resultsTitle = document.getElementById("results-title");
  const resultsSummary = document.getElementById("results-summary");
  const pageBlocks = document.getElementById("page-blocks");
  const historyList = document.getElementById("history-list");
  const historyPanel = document.getElementById("history-panel");
  const historyBody = document.getElementById("history-body");
  const historyCount = document.getElementById("history-count");
  const btnHistoryToggle = document.getElementById("btn-history-toggle");
  let historyItemsCount = 0;
  const toast = document.getElementById("toast");
  const providerBadge = document.getElementById("provider-badge");
  const settingsModal = document.getElementById("settings-modal");
  const settingsForm = document.getElementById("settings-form");
  const settingsMessage = document.getElementById("settings-message");
  const activeProviderSelect = document.getElementById("active-provider");
  const uiThemeSelect = document.getElementById("ui-theme");
  const autoUpdateInput = document.getElementById("auto-update");
  const updateManifestInput = document.getElementById("update-manifest-url");
  const renameTemplateSelect = document.getElementById("rename-template");
  const updateStatusHint = document.getElementById("update-status-hint");
  const updateBanner = document.getElementById("update-banner");
  const updateBannerText = document.getElementById("update-banner-text");
  const btnUpdateApply = document.getElementById("btn-update-apply");
  const btnUpdateDismiss = document.getElementById("btn-update-dismiss");
  const btnCheckUpdate = document.getElementById("btn-check-update");
  const btnForceUpdate = document.getElementById("btn-force-update");
  const filterBar = document.getElementById("results-filter-bar");
  const filterStatus = document.getElementById("filter-status");
  const filterText = document.getElementById("filter-text");
  const missingBox = document.getElementById("missing-episodes-box");
  const maxRetriesInput = document.getElementById("max-retries");
  const concurrencyInput = document.getElementById("resolve-concurrency");
  const notifyOnResolveInput = document.getElementById("notify-on-resolve");
  const customAccentInput = document.getElementById("custom-accent");
  const btnResetAccent = document.getElementById("btn-reset-accent");
  const profileSelect = document.getElementById("profile-select");
  const btnProfileSave = document.getElementById("btn-profile-save");
  const btnProfileDelete = document.getElementById("btn-profile-delete");
  const queueList = document.getElementById("queue-list");
  const queueHint = document.getElementById("queue-hint");
  const btnQueueAdd = document.getElementById("btn-queue-add");
  const btnQueueRun = document.getElementById("btn-queue-run");
  const btnQueueClear = document.getElementById("btn-queue-clear");
  const btnBackupExport = document.getElementById("btn-backup-export");
  const backupImportFile = document.getElementById("backup-import-file");
  const keyAlldebrid = document.getElementById("key-alldebrid");
  const keyRealdebrid = document.getElementById("key-realdebrid");
  const hintAlldebrid = document.getElementById("hint-alldebrid");
  const hintRealdebrid = document.getElementById("hint-realdebrid");
  const btnResolve = document.getElementById("btn-resolve");
  const resolveLabel = btnResolve.querySelector(".btn-resolve-label");
  const resolveSpinner = btnResolve.querySelector(".btn-spinner");
  const btnStopResolve = document.getElementById("btn-stop-resolve");
  const resolveProgress = document.getElementById("resolve-progress");
  const resolveProgressText = document.getElementById("resolve-progress-text");
  const resolveProgressCount = document.getElementById("resolve-progress-count");
  const resolveProgressFill = document.getElementById("resolve-progress-fill");

  let resolveAbort = false;
  let workQueue = [];
  let queueRunning = false;

  const PROVIDER_LABELS = {
    alldebrid: "AllDebrid",
    realdebrid: "Real-Debrid",
  };

  let current = null;
  let settings = null;
  let toastTimer = null;

  function getMaxRetries() {
    return Math.max(1, Math.min(8, Number(settings?.max_retries) || 3));
  }

  function getConcurrency() {
    return Math.max(1, Math.min(12, Number(settings?.resolve_concurrency) || 6));
  }

  function showToast(message) {
    toast.textContent = message;
    toast.hidden = false;
    requestAnimationFrame(() => toast.classList.add("show"));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => {
        toast.hidden = true;
      }, 300);
    }, 2600);
  }

  function notifyDesktop(title, body) {
    if (!settings?.notify_on_resolve) return;
    if (!("Notification" in window)) return;
    const show = () => {
      try {
        new Notification(title, {
          body,
          icon: "/static/img/logo.png",
        });
      } catch {
        /* ignore */
      }
    };
    if (Notification.permission === "granted") show();
    else if (Notification.permission !== "denied") {
      Notification.requestPermission().then((p) => {
        if (p === "granted") show();
      });
    }
  }

  function refreshProfileSelect() {
    if (!profileSelect) return;
    const profiles = settings?.profiles || [];
    const active = settings?.active_profile_id || "";
    profileSelect.innerHTML =
      `<option value="">— Aucun profil —</option>` +
      profiles
        .map(
          (p) =>
            `<option value="${escapeHtml(p.id)}"${p.id === active ? " selected" : ""}>${escapeHtml(p.name)}</option>`
        )
        .join("");
  }

  function renderQueue() {
    if (!queueList) return;
    queueList.innerHTML = workQueue
      .map((item, idx) => {
        const st =
          item.status === "running"
            ? "en cours"
            : item.status === "done"
              ? "ok"
              : item.status === "error"
                ? "erreur"
                : "en attente";
        const cls =
          item.status === "running"
            ? "is-running"
            : item.status === "done"
              ? "is-done"
              : item.status === "error"
                ? "is-error"
                : "";
        const short =
          item.url.length > 70 ? `${item.url.slice(0, 67)}…` : item.url;
        return `<li class="queue-item ${cls}" data-qi="${idx}">
          <span class="queue-item-status">${st}</span>
          <span class="queue-item-url" title="${escapeHtml(item.url)}">${escapeHtml(short)}</span>
          <button type="button" class="btn btn-ghost btn-xs" data-queue-remove="${idx}" ${queueRunning ? "disabled" : ""}>×</button>
        </li>`;
      })
      .join("");
    if (queueHint) {
      queueHint.textContent = workQueue.length
        ? `${workQueue.length} page(s) en file — hébergeur : ${hostInput.value.trim() || "…"}`
        : "Ajoutez des pages, puis lancez : extraction puis résolution, une page après l’autre.";
    }
  }

  async function askConfirm(title, text, { confirmText = "Confirmer", icon = "warning" } = {}) {
    const modal = document.getElementById("confirm-modal");
    const titleEl = document.getElementById("confirm-title");
    const textEl = document.getElementById("confirm-text");
    const okBtn = document.getElementById("confirm-ok");
    const iconEl = document.getElementById("confirm-icon");
    if (!modal || !titleEl || !textEl || !okBtn) {
      return window.confirm(`${title}\n\n${text || ""}`);
    }

    titleEl.textContent = title;
    textEl.textContent = text || "";
    okBtn.textContent = confirmText;
    if (iconEl) {
      iconEl.textContent = icon === "question" ? "?" : "!";
      iconEl.className = `confirm-icon ${icon === "question" ? "is-question" : "is-warning"}`;
    }
    modal.hidden = false;

    return new Promise((resolve) => {
      const finish = (value) => {
        modal.hidden = true;
        modal.removeEventListener("click", onClick);
        document.removeEventListener("keydown", onKey);
        resolve(value);
      };
      const onClick = (event) => {
        if (event.target.closest("[data-confirm-cancel]")) finish(false);
        else if (event.target.closest("#confirm-ok")) finish(true);
      };
      const onKey = (event) => {
        if (event.key === "Escape") finish(false);
        if (event.key === "Enter") finish(true);
      };
      modal.addEventListener("click", onClick);
      document.addEventListener("keydown", onKey);
      okBtn.focus();
    });
  }

  async function showAlert(title, text) {
    await askConfirm(title, text, { confirmText: "OK", icon: "question" });
  }

  function setLoading(loading) {
    btnExtract.disabled = loading;
    btnSpinner.hidden = !loading;
    btnLabel.textContent = loading ? "Analyse…" : "Récupérer";
  }

  function setResolving(loading) {
    btnResolve.disabled = loading;
    resolveSpinner.hidden = !loading;
    resolveLabel.textContent = loading ? "Résolution…" : "Résoudre";
    btnStopResolve.hidden = !loading;
    resolveProgress.hidden = !loading;
    if (!loading) {
      resolveProgressFill.style.width = "0%";
    }
  }

  function updateProgress(done, total, label) {
    resolveProgressText.textContent = label;
    resolveProgressCount.textContent = `${done} / ${total}`;
    const pct = total ? Math.round((done / total) * 100) : 0;
    resolveProgressFill.style.width = `${pct}%`;
  }

  function showError(message) {
    if (!message) {
      formError.hidden = true;
      formError.textContent = "";
      return;
    }
    formError.hidden = false;
    formError.textContent = message;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function displayName(link) {
    return link.clean_name || link.resolve_filename || link.label || "—";
  }

  function displayUrl(link) {
    return link.real_url || link.url_display || link.url || "";
  }

  function statusLabel(link) {
    const status = link.resolve_status;
    if (status === "running") return { cls: "running", text: "En cours…" };
    if (!status) return { cls: "pending", text: "En attente" };
    if (status === "ok") return { cls: "ok", text: "Valide" };
    if (status === "dead") return { cls: "dead", text: "Mort" };
    return { cls: "error", text: "Erreur" };
  }

  function normalizeCurrent(data) {
    if (data.batches?.length) {
      return {
        ...data,
        batches: data.batches.map((b) => ({
          ...b,
          links: b.links || [],
          count: (b.links || []).length,
        })),
        links: data.batches.flatMap((b) => b.links || []),
        count: data.batches.reduce((n, b) => n + (b.links || []).length, 0),
        source_urls: data.batches.map((b) => b.source_url),
      };
    }
    // Compat : ancienne entrée historique (une seule page)
    const batch = {
      source_url: data.source_url,
      title: data.title || "Extraction",
      host: data.host,
      count: (data.links || []).length,
      links: data.links || [],
    };
    return {
      ...data,
      batches: [batch],
      source_urls: [data.source_url].filter(Boolean),
    };
  }

  function syncFlatLinks() {
    if (!current?.batches) return;
    current.links = current.batches.flatMap((b) => b.links || []);
    current.count = current.links.length;
    current.source_urls = current.batches.map((b) => b.source_url);
    current.source_url = current.batches[0]?.source_url || current.source_url;
    current.title =
      current.batches.length === 1
        ? current.batches[0].title
        : `${current.batches.length} pages`;
  }

  function rowHtml(link, bi, li) {
    const status = statusLabel(link);
    const source = link.url || "";
    const resolved = displayUrl(link);
    const size = link.resolve_size || link.size || "—";
    const label = link.resolve_filename || link.label || "—";
    const clean = link.clean_name && link.clean_name !== label
      ? `<div class="link-sub clean-name" title="${escapeHtml(link.clean_name)}">→ ${escapeHtml(link.clean_name)}</div>`
      : "";
    const runningClass = status.cls === "running" ? " is-running" : "";
    const rowStatus =
      status.cls === "ok"
        ? " row-ok"
        : status.cls === "dead"
          ? " row-dead"
          : status.cls === "error"
            ? " row-error"
            : "";
    const linkCls = status.cls === "running" ? "pending" : status.cls;
    const attempts = link.resolve_attempts
      ? `<div class="link-sub">${link.resolve_attempts} tentative(s)</div>`
      : "";
    const err = link.resolve_error
      ? `<div class="link-sub">${escapeHtml(link.resolve_error)}</div>`
      : "";
    const showRecheck = status.cls === "dead" || status.cls === "error";
    const recheckBtn = showRecheck
      ? `<button type="button" class="btn btn-ghost btn-recheck" data-batch="${bi}" data-link="${li}" title="Relancer ce lien">Re-vérifier</button>`
      : "";

    return `
      <tr class="${runningClass}${rowStatus}" data-batch="${bi}" data-link="${li}">
        <td class="col-check"><input type="checkbox" class="link-check" data-batch="${bi}" data-link="${li}"></td>
        <td>${li + 1}</td>
        <td><div class="cell-label" title="${escapeHtml(label)}">${escapeHtml(label)}</div>${clean}</td>
        <td><span class="size-pill">${escapeHtml(size)}</span></td>
        <td><span class="status-pill ${status.cls}">${status.text}</span>${attempts}</td>
        <td class="td-source">
          <a class="cell-url pending" href="${escapeHtml(source)}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(source)}">${escapeHtml(source)}</a>
        </td>
        <td class="td-resolved">
          <a class="cell-url ${linkCls}" href="${escapeHtml(resolved)}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(resolved)}">${escapeHtml(resolved)}</a>
          ${err}
        </td>
        <td class="col-actions">${recheckBtn}</td>
      </tr>`;
  }

  function batchSplitHtml(batch, bi) {
    const ok = [];
    const dead = [];
    (batch.links || []).forEach((link, li) => {
      if (link.resolve_status === "ok") ok.push({ link, li });
      else if (link.resolve_status === "dead" || link.resolve_status === "error") {
        dead.push({ link, li });
      }
    });

    if (!ok.length && !dead.length) return "";

    const okRows = ok.length
      ? ok
          .map(
            ({ link }, n) => `
        <tr class="row-ok">
          <td>${n + 1}</td>
          <td>${escapeHtml(link.resolve_filename || link.label || "—")}</td>
          <td><a class="cell-url ok" href="${escapeHtml(displayUrl(link))}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(displayUrl(link))}">${escapeHtml(displayUrl(link))}</a></td>
        </tr>`
          )
          .join("")
      : `<tr><td colspan="3">Aucun valide</td></tr>`;

    const deadRows = dead.length
      ? dead
          .map(
            ({ link, li }, n) => `
        <tr class="row-dead">
          <td>${n + 1}</td>
          <td>${escapeHtml(link.resolve_filename || link.label || "—")}</td>
          <td>${escapeHtml(link.resolve_error || link.resolve_status || "dead")}</td>
          <td><button type="button" class="btn btn-ghost btn-recheck btn-xs" data-batch="${bi}" data-link="${li}">Re-vérifier</button></td>
        </tr>`
          )
          .join("")
      : `<tr><td colspan="4">Aucun mort</td></tr>`;

    return `
      <div class="split-panels">
        <section class="split-panel split-ok">
          <div class="split-head">
            <h3>Valides <span class="split-count">${ok.length}</span></h3>
            <button type="button" class="btn btn-ghost btn-xs" data-copy-batch-ok="${bi}">Copier</button>
          </div>
          <div class="table-wrap table-wrap-sm">
            <table class="links-table links-table-compact">
              <thead><tr><th>#</th><th>Épisode</th><th>Lien résolu</th></tr></thead>
              <tbody>${okRows}</tbody>
            </table>
          </div>
        </section>
        <section class="split-panel split-dead">
          <div class="split-head">
            <h3>Morts / manquants <span class="split-count">${dead.length}</span></h3>
            <button type="button" class="btn btn-ghost btn-xs" data-copy-batch-dead="${bi}">Copier</button>
          </div>
          <div class="table-wrap table-wrap-sm">
            <table class="links-table links-table-compact">
              <thead><tr><th>#</th><th>Épisode</th><th>Erreur</th><th></th></tr></thead>
              <tbody>${deadRows}</tbody>
            </table>
          </div>
        </section>
      </div>`;
  }

  function batchToolbarHtml(batch, bi) {
    return `
      <div class="page-block-toolbar">
        <div class="action-cluster">
          <button type="button" class="btn btn-primary btn-xs" data-resolve-batch="${bi}">Résoudre</button>
          <button type="button" class="btn btn-ghost btn-xs" data-recheck-batch-dead="${bi}">Re-vérifier morts</button>
        </div>
        <div class="action-cluster">
          <button type="button" class="btn btn-ghost btn-xs" data-copy-batch-resolved="${bi}">Copier résolus</button>
          <button type="button" class="btn btn-ghost btn-xs" data-copy-batch-source="${bi}">Copier source</button>
          <button type="button" class="btn btn-ghost btn-xs" data-copy-batch-jd="${bi}">Copier JD</button>
          <button type="button" class="btn btn-ghost btn-xs" data-save-batch="${bi}">Sauvegarder</button>
        </div>
        <div class="action-cluster export-group">
          <div class="export-split">
            <button type="button" class="btn btn-secondary btn-xs" data-export-batch="${bi}" data-format="csv">CSV</button>
            <button type="button" class="btn btn-ghost btn-view btn-xs" data-view-batch="${bi}" data-format="csv">Voir</button>
          </div>
          <div class="export-split">
            <button type="button" class="btn btn-secondary btn-xs" data-export-batch="${bi}" data-format="html">HTML</button>
            <button type="button" class="btn btn-ghost btn-view btn-xs" data-view-batch="${bi}" data-format="html">Voir</button>
          </div>
          <div class="export-split">
            <button type="button" class="btn btn-secondary btn-xs" data-export-batch="${bi}" data-format="pdf">PDF</button>
            <button type="button" class="btn btn-ghost btn-view btn-xs" data-view-batch="${bi}" data-format="pdf">Voir</button>
          </div>
          <div class="export-split">
            <button type="button" class="btn btn-secondary btn-xs" data-export-batch="${bi}" data-format="jdownloader">JD</button>
            <button type="button" class="btn btn-ghost btn-view btn-xs" data-view-batch="${bi}" data-format="jdownloader">Voir</button>
          </div>
        </div>
      </div>`;
  }

  function pageBlockHtml(batch, bi) {
    const ok = (batch.links || []).filter((l) => l.resolve_status === "ok").length;
    const dead = (batch.links || []).filter(
      (l) => l.resolve_status === "dead" || l.resolve_status === "error"
    ).length;
    const err = batch.error
      ? `<p class="form-error">Erreur : ${escapeHtml(batch.error)}</p>`
      : "";
    const rows = (batch.links || []).length
      ? batch.links.map((link, li) => rowHtml(link, bi, li)).join("")
      : `<tr><td colspan="8">Aucun lien trouvé sur cette page.</td></tr>`;

    return `
      <article class="page-block" data-batch-index="${bi}">
        <header class="page-block-head">
          <div>
            <h3 class="page-block-title">${escapeHtml(batch.title || "Page")}</h3>
            <p class="page-block-meta">
              <strong>${batch.links?.length || 0}</strong> lien(s)
              ${ok || dead ? ` · <strong>${ok}</strong> valides · <strong>${dead}</strong> morts` : ""}
              · <a href="${escapeHtml(batch.source_url)}" target="_blank" rel="noopener noreferrer">ouvrir la page</a>
            </p>
          </div>
        </header>
        ${batchToolbarHtml(batch, bi)}
        ${err}
        ${batchSplitHtml(batch, bi)}
        <div class="table-wrap">
          <table class="links-table">
            <colgroup>
              <col class="col-check"><col class="col-num"><col class="col-label"><col class="col-size">
              <col class="col-status"><col class="col-source"><col class="col-resolved"><col class="col-act">
            </colgroup>
            <thead>
              <tr>
                <th></th><th>#</th><th>Label</th><th>Taille</th><th>Statut</th>
                <th>Source</th><th>Résolu</th><th></th>
              </tr>
            </thead>
            <tbody data-batch-body="${bi}">${rows}</tbody>
          </table>
        </div>
      </article>`;
  }

  function updateSummary() {
    if (!current) return;
    syncFlatLinks();
    const resolvedOk = (current.links || []).filter((l) => l.resolve_status === "ok").length;
    const dead = (current.links || []).filter(
      (l) => l.resolve_status === "dead" || l.resolve_status === "error"
    ).length;
    const pages = current.batches?.length || 1;
    resultsSummary.innerHTML =
      `<strong>${current.count}</strong> lien(s) · <strong>${pages}</strong> page(s) · hébergeur <strong>${escapeHtml(current.host)}</strong>` +
      (resolvedOk || dead
        ? ` · <strong>${resolvedOk}</strong> valides · <strong>${dead}</strong> morts`
        : "");
  }

  function renderResults(data, { scroll = true } = {}) {
    current = normalizeCurrent(data);
    syncFlatLinks();
    results.classList.remove("is-closing");
    results.hidden = false;
    resultsTitle.textContent =
      current.batches.length === 1
        ? current.batches[0].title || "Résultats"
        : `${current.batches.length} pages`;
    updateSummary();

    pageBlocks.innerHTML = current.batches
      .map((batch, bi) => pageBlockHtml(batch, bi))
      .join("");

    if (filterBar) filterBar.hidden = !current.links?.length;
    applyResultFilters();

    if (scroll) {
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function linkMatchesFilter(link) {
    const status = filterStatus?.value || "all";
    const q = (filterText?.value || "").trim().toLowerCase();
    const st = link.resolve_status || "";
    if (status === "ok" && st !== "ok") return false;
    if (status === "dead" && st !== "dead" && st !== "error") return false;
    if (status === "pending" && st && st !== "running") return false;
    if (q) {
      const blob = [
        link.label,
        link.resolve_filename,
        link.clean_name,
        link.url,
        displayUrl(link),
      ]
        .join(" ")
        .toLowerCase();
      if (!blob.includes(q)) return false;
    }
    return true;
  }

  function applyResultFilters() {
    if (!pageBlocks) return;
    pageBlocks.querySelectorAll("tr[data-batch][data-link]").forEach((row) => {
      const bi = Number(row.dataset.batch);
      const li = Number(row.dataset.link);
      const link = current?.batches?.[bi]?.links?.[li];
      if (!link) return;
      row.classList.toggle("row-hidden", !linkMatchesFilter(link));
    });
  }

  function selectedLinks() {
    const out = [];
    pageBlocks?.querySelectorAll(".link-check:checked").forEach((cb) => {
      const bi = Number(cb.dataset.batch);
      const li = Number(cb.dataset.link);
      const link = current?.batches?.[bi]?.links?.[li];
      if (link) out.push(link);
    });
    return out;
  }

  function resultsRoot() {
    const openDetail = historyList?.querySelector(
      ".history-item.is-open .history-item-detail:not([hidden])"
    );
    if (openDetail) return openDetail;
    return pageBlocks;
  }

  function refreshBatchChrome(bi) {
    const batch = current?.batches?.[bi];
    const root = resultsRoot();
    const block = root.querySelector(`[data-batch-index="${bi}"]`);
    if (!batch || !block) return;

    const ok = (batch.links || []).filter((l) => l.resolve_status === "ok").length;
    const dead = (batch.links || []).filter(
      (l) => l.resolve_status === "dead" || l.resolve_status === "error"
    ).length;
    const meta = block.querySelector(".page-block-meta");
    if (meta) {
      meta.innerHTML =
        `<strong>${batch.links?.length || 0}</strong> lien(s)` +
        (ok || dead ? ` · <strong>${ok}</strong> valides · <strong>${dead}</strong> morts` : "") +
        ` · <a href="${escapeHtml(batch.source_url)}" target="_blank" rel="noopener noreferrer">ouvrir la page</a>`;
    }

    const existingToolbar = block.querySelector(".page-block-toolbar");
    const toolbarHtml = batchToolbarHtml(batch, bi);
    if (existingToolbar) {
      const wrap = document.createElement("div");
      wrap.innerHTML = toolbarHtml;
      existingToolbar.replaceWith(wrap.firstElementChild);
    }

    const existingSplit = block.querySelector(".split-panels");
    const splitHtml = batchSplitHtml(batch, bi);
    if (splitHtml) {
      const wrap = document.createElement("div");
      wrap.innerHTML = splitHtml;
      const next = wrap.firstElementChild;
      if (existingSplit) existingSplit.replaceWith(next);
      else {
        const head = block.querySelector(".page-block-head");
        const err = block.querySelector(".form-error");
        (err || head)?.after(next);
      }
    } else if (existingSplit) {
      existingSplit.remove();
    }
  }

  function patchLinkCell(bi, li) {
    const link = current?.batches?.[bi]?.links?.[li];
    if (!link) return;
    const root = resultsRoot();
    const tbody = root.querySelector(`[data-batch-body="${bi}"]`);
    const row = tbody?.querySelector(`tr[data-batch="${bi}"][data-link="${li}"]`);
    if (row) row.outerHTML = rowHtml(link, bi, li);
    refreshBatchChrome(bi);
    updateSummary();
  }

  function collectJobs(predicate) {
    const jobs = [];
    (current?.batches || []).forEach((batch, bi) => {
      (batch.links || []).forEach((link, li) => {
        if (predicate(link)) jobs.push({ bi, li });
      });
    });
    return jobs;
  }

  function resetLinkForResolve(link) {
    if (link.resolve_status === "ok") return link;
    return {
      ...link,
      resolve_status: "",
      resolve_error: "",
      real_url: "",
      url_display: link.url,
      resolve_attempts: 0,
    };
  }

  function closeResults() {
    if (results.hidden) return;
    results.classList.add("is-closing");
    window.setTimeout(() => {
      results.hidden = true;
      results.classList.remove("is-closing");
      pageBlocks.innerHTML = "";
      current = null;
      if (filterBar) filterBar.hidden = true;
      if (missingBox) {
        missingBox.hidden = true;
        missingBox.textContent = "";
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    }, 220);
  }

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleString("fr-FR", {
        dateStyle: "short",
        timeStyle: "short",
      });
    } catch {
      return iso;
    }
  }

  function updateProviderBadge() {
    if (!settings) {
      providerBadge.hidden = true;
      return;
    }
    const name = settings.active_provider;
    const conf = settings.providers?.[name];
    const label = PROVIDER_LABELS[name] || name;
    providerBadge.hidden = false;
    if (conf?.configured) {
      providerBadge.classList.remove("is-off");
      providerBadge.textContent = `${label} prêt`;
    } else {
      providerBadge.classList.add("is-off");
      providerBadge.textContent = `${label} : clé manquante`;
    }
  }

  function applyTheme(theme) {
    const value = theme === "alldebrid" ? "alldebrid" : "linkora";
    document.documentElement.setAttribute("data-theme", value);
    document.querySelectorAll("[data-theme-set]").forEach((btn) => {
      const key = btn.dataset.themeSet === "lienlab" ? "linkora" : btn.dataset.themeSet;
      btn.classList.toggle("is-active", key === value);
    });
    if (uiThemeSelect) uiThemeSelect.value = value === "alldebrid" ? "alldebrid" : "linkora";
  }

  async function persistTheme(theme) {
    applyTheme(theme);
    try {
      const res = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme }),
      });
      const data = await res.json();
      if (res.ok) {
        settings = { ...(settings || {}), ...data };
        showToast(theme === "alldebrid" ? "Thème Ambre activé." : "Thème Linkora activé.");
      }
    } catch {
      /* ignore */
    }
  }

  function showUpdateBanner(state) {
    if (!updateBanner || !updateBannerText) return;
    if (state?.restarting) {
      updateBanner.hidden = false;
      updateBannerText.textContent =
        state.message ||
        "Mise à jour en cours — Linkora va redémarrer…";
      if (btnUpdateApply) btnUpdateApply.hidden = true;
      return;
    }
    if (state?.needs_restart || state?.applied) {
      updateBanner.hidden = false;
      updateBannerText.textContent =
        state.message ||
        `Mise à jour ${state.current || ""} installée — redémarrez Linkora.`;
      if (btnUpdateApply) btnUpdateApply.hidden = true;
      return;
    }
    if (state?.update_available) {
      updateBanner.hidden = false;
      updateBannerText.textContent =
        state.message ||
        `Nouvelle version ${state.latest} disponible (actuelle : ${state.current}).`;
      if (btnUpdateApply) btnUpdateApply.hidden = false;
      if (btnForceUpdate) btnForceUpdate.hidden = false;
      return;
    }
    updateBanner.hidden = true;
  }

  async function refreshUpdateStatus() {
    try {
      const res = await fetch("/api/update/status");
      const state = await res.json();
      if (updateStatusHint) {
        updateStatusHint.textContent = state.latest
          ? `Version locale : ${state.current || "?"} · GitHub : ${state.latest}`
          : `Version locale : ${state.current || "?"}`;
      }
      if (btnForceUpdate) {
        btnForceUpdate.hidden = !state.update_available;
      }
      showUpdateBanner(state);
      return state;
    } catch {
      return null;
    }
  }

  function applyCustomBranding(data) {
    const root = document.documentElement;
    const accent = (data?.custom_accent || "").trim();
    if (accent) {
      root.style.setProperty("--accent", accent);
    } else {
      root.style.removeProperty("--accent");
    }
    if (customAccentInput && accent) {
      customAccentInput.value = accent.length === 4
        ? `#${accent[1]}${accent[1]}${accent[2]}${accent[2]}${accent[3]}${accent[3]}`
        : accent;
    }
  }

  async function loadSettings() {
    const res = await fetch("/api/settings");
    settings = await res.json();
    activeProviderSelect.value = settings.active_provider || "alldebrid";
    if (uiThemeSelect) {
      uiThemeSelect.value =
        settings.theme === "alldebrid" ? "alldebrid" : "linkora";
    }
    if (autoUpdateInput) {
      autoUpdateInput.checked = settings.auto_update !== false;
    }
    if (notifyOnResolveInput) {
      notifyOnResolveInput.checked = settings.notify_on_resolve !== false;
    }
    if (updateManifestInput) {
      updateManifestInput.value = settings.update_manifest_url || "";
    }
    if (renameTemplateSelect) {
      renameTemplateSelect.value = settings.rename_template || "simple";
    }
    if (maxRetriesInput) maxRetriesInput.value = String(settings.max_retries || 3);
    if (concurrencyInput) {
      concurrencyInput.value = String(settings.resolve_concurrency || 6);
    }
    applyTheme(settings.theme === "alldebrid" ? "alldebrid" : "linkora");
    applyCustomBranding(settings);
    const adCount = settings.providers?.alldebrid?.key_count || 0;
    const rdCount = settings.providers?.realdebrid?.key_count || 0;
    hintAlldebrid.textContent = settings.providers?.alldebrid?.configured
      ? `${adCount} clé(s) · ${settings.providers.alldebrid.api_key_masked}`
      : "Aucune clé enregistrée.";
    hintRealdebrid.textContent = settings.providers?.realdebrid?.configured
      ? `${rdCount} clé(s) · ${settings.providers.realdebrid.api_key_masked}`
      : "Aucune clé enregistrée.";
    updateProviderBadge();
    refreshProfileSelect();
    refreshUpdateStatus();
  }

  function openSettings() {
    settingsMessage.hidden = true;
    keyAlldebrid.value = "";
    keyRealdebrid.value = "";
    settingsModal.hidden = false;
    loadSettings().catch(() => showToast("Impossible de charger les paramètres."));
  }

  function closeSettings() {
    settingsModal.hidden = true;
  }

  function showSettingsMessage(text, ok) {
    settingsMessage.hidden = false;
    settingsMessage.textContent = text;
    settingsMessage.classList.toggle("ok", !!ok);
    settingsMessage.classList.toggle("err", !ok);
  }

  function updateHistoryCount(n) {
    historyItemsCount = n;
    if (historyCount) {
      historyCount.textContent = n === 1 ? "1 entrée" : `${n} entrée(s)`;
    }
  }

  function setHistoryOpen(open) {
    if (!historyPanel || !historyBody || !btnHistoryToggle) return;
    historyPanel.classList.toggle("is-collapsed", !open);
    historyBody.hidden = !open;
    btnHistoryToggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  btnHistoryToggle?.addEventListener("click", () => {
    const willOpen = historyBody?.hidden;
    setHistoryOpen(!!willOpen);
    if (willOpen) {
      historyBody.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  });

  async function loadHistory() {
    try {
      const res = await fetch("/api/history");
      const items = await res.json();
      if (!Array.isArray(items) || !items.length) {
        updateHistoryCount(0);
        historyList.innerHTML =
          '<li class="history-empty">Aucune sauvegarde pour le moment.</li>';
        return;
      }

      updateHistoryCount(items.length);
      historyList.innerHTML = items
        .map((item) => {
          const url = item.source_url || "";
          const shortUrl =
            url.length > 72 ? `${url.slice(0, 69)}…` : url;
          return `
        <li class="history-item" data-id="${item.id}">
          <div class="history-item-row">
            <button type="button" class="history-item-main" data-action="open">
              <p class="history-item-title">${escapeHtml(item.title || item.host)}</p>
              <p class="history-item-meta">
                ${escapeHtml(item.host)} · ${item.link_count} lien(s) · ${formatDate(item.created_at)}
              </p>
              ${shortUrl ? `<p class="history-item-url" title="${escapeHtml(url)}">${escapeHtml(shortUrl)}</p>` : ""}
            </button>
            <div class="history-item-actions">
              <button type="button" class="btn btn-ghost" data-action="open" style="padding:0.45rem 0.75rem;font-size:0.85rem">Ouvrir</button>
              <button type="button" class="btn btn-danger" data-action="delete">Supprimer</button>
            </div>
          </div>
          <div class="history-item-detail" hidden></div>
        </li>`;
        })
        .join("");
    } catch {
      updateHistoryCount(0);
      historyList.innerHTML =
        '<li class="history-empty">Impossible de charger l’historique.</li>';
    }
  }

  function batchPayload(bi) {
    const batch = current?.batches?.[bi];
    if (!batch) return null;
    return {
      source_url: batch.source_url,
      host: batch.host || current.host,
      title: batch.title,
      links: batch.links || [],
      theme: settings?.theme || "linkora",
    };
  }

  async function fetchExportBlobForPayload(payload, format, view = false) {
    const res = await fetch(`/api/export/${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, view }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Export impossible.");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = /filename="?([^"]+)"?/.exec(disposition);
    const filename = match?.[1] || `liens.${format}`;
    return { blob, filename };
  }

  async function downloadExportForBatch(bi, format) {
    const payload = batchPayload(bi);
    if (!payload?.links?.length) {
      showToast("Rien à exporter pour cette page.");
      return;
    }
    try {
      const { blob, filename } = await fetchExportBlobForPayload(payload, format, false);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
      showToast(`Export ${format.toUpperCase()} — page ${bi + 1}.`);
    } catch (err) {
      showToast(err.message || "Export impossible.");
    }
  }

  async function viewExportForBatch(bi, format) {
    const payload = batchPayload(bi);
    if (!payload?.links?.length) {
      showToast("Rien à afficher pour cette page.");
      return;
    }
    try {
      const { blob } = await fetchExportBlobForPayload(payload, format, true);
      const url = URL.createObjectURL(blob);
      const win = window.open(url, "_blank");
      if (!win) showToast("Autorisez les pop-ups.");
      else showToast(`${format.toUpperCase()} — page ${bi + 1}.`);
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      showToast(err.message || "Affichage impossible.");
    }
  }

  function jdownloaderLines(links) {
    return (links || [])
      .map((l) => {
        const url = displayUrl(l);
        if (!url) return "";
        const name = displayName(l);
        return name && name !== "—" ? `${url} | ${name}` : url;
      })
      .filter(Boolean)
      .join("\n");
  }

  async function saveBatchHistory(bi) {
    const batch = current?.batches?.[bi];
    if (!batch?.links?.length) {
      showToast("Rien à sauvegarder pour cette page.");
      return;
    }
    try {
      const res = await fetch("/api/history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_url: batch.source_url,
          host: batch.host || current.host,
          title: batch.title,
          links: batch.links,
          upsert: true,
        }),
      });
      const saved = await res.json();
      if (!res.ok) {
        showToast(saved.error || "Sauvegarde impossible.");
        return;
      }
      batch.history_id = saved.id;
      await loadHistory();
      showToast(`Page « ${batch.title || bi + 1} » sauvegardée.`);
    } catch {
      showToast("Sauvegarde impossible.");
    }
  }

  async function fetchExportBlob(format, view = false) {
    const res = await fetch(`/api/export/${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...current,
        view,
        theme: settings?.theme || "linkora",
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Export impossible.");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = /filename="?([^"]+)"?/.exec(disposition);
    const filename = match?.[1] || `liens.${format}`;
    return { blob, filename };
  }

  async function downloadExport(format) {
    if (!current || !current.links?.length) {
      showToast("Rien à exporter.");
      return;
    }
    try {
      const { blob, filename } = await fetchExportBlob(format, false);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
      showToast(`Export ${format.toUpperCase()} téléchargé.`);
    } catch (err) {
      showToast(err.message || "Export impossible.");
    }
  }

  async function viewExport(format) {
    if (!current || !current.links?.length) {
      showToast("Rien à afficher.");
      return;
    }
    try {
      const { blob } = await fetchExportBlob(format, true);
      const url = URL.createObjectURL(blob);
      const win = window.open(url, "_blank");
      if (!win) {
        showToast("Autorisez les pop-ups pour voir l’export.");
      } else {
        showToast(`${format.toUpperCase()} ouvert dans un nouvel onglet.`);
      }
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      showToast(err.message || "Affichage impossible.");
    }
  }

  async function autoSaveHistory(payload) {
    const normalized = normalizeCurrent(payload || current || {});
    const batches = (normalized.batches || []).filter((b) => b.links?.length);
    if (!batches.length) return null;

    try {
      let savedCount = 0;
      for (const batch of batches) {
        const res = await fetch("/api/history", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_url: batch.source_url,
            host: batch.host || normalized.host,
            title: batch.title,
            links: batch.links,
            upsert: true,
          }),
        });
        const saved = await res.json();
        if (res.ok) {
          batch.history_id = saved.id;
          savedCount += 1;
        }
      }
      current = normalizeCurrent({
        ...normalized,
        batches: normalized.batches,
        host: normalized.host,
      });
      syncFlatLinks();
      await loadHistory();
      return savedCount;
    } catch {
      return null;
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    setLoading(true);

    try {
      const res = await fetch("/api/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          urls: urlsInput.value,
          host: hostInput.value.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        showError(data.error || "Erreur lors de l’extraction.");
        return;
      }
      renderResults(data);
      if (!data.count) {
        showToast("Aucun lien trouvé.");
      } else {
        const saved = await autoSaveHistory(data);
        const pages = data.batches?.length || data.source_urls?.length || 1;
        showToast(
          `${data.count} lien(s) · ${pages} page(s) — ${saved || pages} entrée(s) dans l’historique.`
        );
      }
    } catch {
      showError("Impossible de contacter le serveur.");
    } finally {
      setLoading(false);
    }
  });

  const CONCURRENCY = () => getConcurrency();
  const MAX_RETRIES = () => getMaxRetries();

  async function resolveSingleLink(provider, link, maxRetries = MAX_RETRIES()) {
    const res = await fetch("/api/resolve/one", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider,
        link,
        max_retries: maxRetries,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      return {
        ...link,
        resolve_status: "error",
        resolve_error: data.error || "Erreur",
        resolve_attempts: maxRetries,
      };
    }
    return data.link;
  }

  async function runResolvePool(jobs, provider, labelPrefix) {
    const total = jobs.length;
    const concurrency = Math.min(CONCURRENCY(), jobs.length || 1);
    let done = 0;
    let ok = 0;
    let failed = 0;
    let next = 0;

    updateProgress(0, total, labelPrefix || "Résolution parallèle…");

    async function worker() {
      while (!resolveAbort) {
        const pos = next++;
        if (pos >= jobs.length) break;
        const { bi, li } = jobs[pos];
        const link = current.batches[bi].links[li];

        current.batches[bi].links[li] = {
          ...link,
          resolve_status: "running",
          resolve_error: "",
        };
        syncFlatLinks();
        patchLinkCell(bi, li);

        try {
          const resolved = await resolveSingleLink(provider, link, MAX_RETRIES());
          current.batches[bi].links[li] = resolved;
          if (resolved.resolve_status === "ok") ok += 1;
          else failed += 1;
        } catch {
          current.batches[bi].links[li] = {
            ...link,
            resolve_status: "error",
            resolve_error: "Erreur réseau",
          };
          failed += 1;
        }

        syncFlatLinks();
        patchLinkCell(bi, li);
        done += 1;
        updateProgress(done, total, `${ok} OK · ${failed} échec(s) · x${concurrency}`);
      }
    }

    const workers = Array.from({ length: concurrency }, () => worker());
    await Promise.all(workers);
    return { ok, failed, total, done };
  }

  async function ensureProviderReady() {
    try {
      await loadSettings();
    } catch {
      /* ignore */
    }
    if (!settings?.providers?.[settings.active_provider]?.configured) {
      showToast("Configurez une clé API dans Paramètres.");
      openSettings();
      return null;
    }
    const provider = settings.active_provider;
    try {
      const testRes = await fetch("/api/settings/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider }),
      });
      const testData = await testRes.json();
      if (!testRes.ok || testData.ok === false) {
        showToast(testData.error || "Clé API invalide.");
        openSettings();
        return null;
      }
      return provider;
    } catch {
      showToast("Impossible de vérifier la clé API.");
      return null;
    }
  }

  btnResolve.addEventListener("click", async () => {
    if (!current?.batches?.length || !current.links?.length) {
      showToast("Aucun lien à résoudre.");
      return;
    }

    const provider = await ensureProviderReady();
    if (!provider) return;

    const providerName = PROVIDER_LABELS[provider] || provider;
    resolveAbort = false;
    setResolving(true);

    current.batches.forEach((batch) => {
      batch.links = (batch.links || []).map(resetLinkForResolve);
    });
    syncFlatLinks();
    refreshCurrentView({ scroll: false });

    const jobs = collectJobs((l) => l.resolve_status !== "ok");

    if (!jobs.length) {
      showToast("Tous les liens sont déjà valides.");
      setResolving(false);
      return;
    }

    showToast(
      `${providerName} — ${jobs.length} lien(s) en parallèle (x${getConcurrency()}, ${getMaxRetries()} essais si dead).`
    );

    const result = await runResolvePool(jobs, provider, "Résolution…");
    syncFlatLinks();
    current.resolved_provider = provider;
    updateSummary();
    await autoSaveHistory(current);
    setResolving(false);

    if (resolveAbort) {
      showToast(`Arrêté : ${result.ok}/${result.total} résolu(s).`);
      notifyDesktop("Linkora — arrêté", `${result.ok}/${result.total} résolu(s)`);
    } else {
      showToast(`${result.ok}/${result.total} lien(s) résolus via ${providerName}.`);
      notifyDesktop(
        "Linkora — résolution terminée",
        `${result.ok}/${result.total} lien(s) via ${providerName}`
      );
    }
  });

  document.getElementById("btn-recheck-dead").addEventListener("click", async () => {
    if (!current?.links?.length) {
      showToast("Aucun lien.");
      return;
    }
    const provider = await ensureProviderReady();
    if (!provider) return;

    const jobs = collectJobs(
      (l) => l.resolve_status === "dead" || l.resolve_status === "error"
    );

    if (!jobs.length) {
      showToast("Aucun lien mort/erreur à re-vérifier.");
      return;
    }

    resolveAbort = false;
    setResolving(true);
    showToast(`Re-vérification de ${jobs.length} lien(s) morts (${getMaxRetries()} essais)…`);
    const result = await runResolvePool(jobs, provider, "Re-vérification…");
    current.resolved_provider = provider;
    updateSummary();
    await autoSaveHistory(current);
    setResolving(false);
    showToast(
      resolveAbort
        ? `Arrêté : ${result.ok} récupéré(s).`
        : `${result.ok}/${result.total} lien(s) récupérés après re-vérification.`
    );
  });

  async function recheckOneLink(bi, li) {
    if (!current?.batches?.[bi]?.links?.[li]) return;
    const provider = await ensureProviderReady();
    if (!provider) return;

    const link = current.batches[bi].links[li];
    current.batches[bi].links[li] = {
      ...link,
      resolve_status: "running",
      resolve_error: "",
    };
    syncFlatLinks();
    patchLinkCell(bi, li);
    showToast(`Re-vérification : ${link.label || "lien " + (li + 1)}…`);

    try {
      const resolved = await resolveSingleLink(provider, link, getMaxRetries());
      current.batches[bi].links[li] = resolved;
      syncFlatLinks();
      patchLinkCell(bi, li);
      updateSummary();
      await autoSaveHistory(current);
      if (resolved.resolve_status === "ok") {
        showToast(`Lien récupéré après ${resolved.resolve_attempts || "?"} essai(s).`);
      } else {
        showToast(
          `Toujours mort/erreur après ${resolved.resolve_attempts || getMaxRetries()} essais.`
        );
      }
    } catch {
      current.batches[bi].links[li] = {
        ...link,
        resolve_status: "error",
        resolve_error: "Erreur réseau",
      };
      syncFlatLinks();
      patchLinkCell(bi, li);
      showToast("Erreur réseau.");
    }
  }

  pageBlocks.addEventListener("click", handlePageBlockClick);
  historyList.addEventListener("click", (event) => {
    if (!event.target.closest(".history-item-detail .page-block")) return;
    handlePageBlockClick(event);
  });

  async function handlePageBlockClick(event) {
    const resolveBatchBtn = event.target.closest("[data-resolve-batch]");
    if (resolveBatchBtn) {
      const bi = Number(resolveBatchBtn.dataset.resolveBatch);
      const batch = current?.batches?.[bi];
      if (!batch?.links?.length) {
        showToast("Aucun lien sur cette page.");
        return;
      }
      const provider = await ensureProviderReady();
      if (!provider) return;

      resolveAbort = false;
      setResolving(true);
      batch.links = batch.links.map(resetLinkForResolve);
      syncFlatLinks();
      refreshCurrentView({ scroll: false });

      const jobs = batch.links
        .map((l, li) => (l.resolve_status === "ok" ? null : { bi, li }))
        .filter(Boolean);

      if (!jobs.length) {
        showToast("Tous les liens de cette page sont déjà valides.");
        setResolving(false);
        return;
      }

      const result = await runResolvePool(jobs, provider, `Page ${bi + 1}…`);
      current.resolved_provider = provider;
      updateSummary();
      await autoSaveHistory(current);
      setResolving(false);
      showToast(`${result.ok}/${result.total} lien(s) résolus sur cette page.`);
      return;
    }

    const recheckBatchDeadBtn = event.target.closest("[data-recheck-batch-dead]");
    if (recheckBatchDeadBtn) {
      const bi = Number(recheckBatchDeadBtn.dataset.recheckBatchDead);
      const batch = current?.batches?.[bi];
      if (!batch?.links?.length) return;
      const provider = await ensureProviderReady();
      if (!provider) return;
      const jobs = batch.links
        .map((l, li) =>
          l.resolve_status === "dead" || l.resolve_status === "error" ? { bi, li } : null
        )
        .filter(Boolean);
      if (!jobs.length) {
        showToast("Aucun mort sur cette page.");
        return;
      }
      resolveAbort = false;
      setResolving(true);
      const result = await runResolvePool(jobs, provider, `Morts page ${bi + 1}…`);
      await autoSaveHistory(current);
      setResolving(false);
      showToast(`${result.ok}/${result.total} récupéré(s) sur cette page.`);
      return;
    }

    const exportBatchBtn = event.target.closest("[data-export-batch]");
    if (exportBatchBtn) {
      downloadExportForBatch(
        Number(exportBatchBtn.dataset.exportBatch),
        exportBatchBtn.dataset.format
      );
      return;
    }

    const viewBatchBtn = event.target.closest("[data-view-batch]");
    if (viewBatchBtn) {
      viewExportForBatch(
        Number(viewBatchBtn.dataset.viewBatch),
        viewBatchBtn.dataset.format
      );
      return;
    }

    const saveBatchBtn = event.target.closest("[data-save-batch]");
    if (saveBatchBtn) {
      await saveBatchHistory(Number(saveBatchBtn.dataset.saveBatch));
      return;
    }

    const copySourceBtn = event.target.closest("[data-copy-batch-source]");
    if (copySourceBtn) {
      const bi = Number(copySourceBtn.dataset.copyBatchSource);
      const text = (current.batches[bi]?.links || [])
        .map((l) => l.url || "")
        .filter(Boolean)
        .join("\n");
      try {
        await navigator.clipboard.writeText(text || "");
        showToast("Sources de cette page copiées.");
      } catch {
        showToast("Copie impossible.");
      }
      return;
    }

    const copyJdBtn = event.target.closest("[data-copy-batch-jd]");
    if (copyJdBtn) {
      const bi = Number(copyJdBtn.dataset.copyBatchJd);
      const text = jdownloaderLines(current.batches[bi]?.links);
      try {
        await navigator.clipboard.writeText(text || "");
        showToast("Format JDownloader copié (page).");
      } catch {
        showToast("Copie impossible.");
      }
      return;
    }

    const recheckBtn = event.target.closest("[data-batch][data-link].btn-recheck, .btn-recheck[data-batch]");
    if (recheckBtn) {
      const bi = Number(recheckBtn.dataset.batch);
      const li = Number(recheckBtn.dataset.link);
      recheckBtn.disabled = true;
      await recheckOneLink(bi, li);
      return;
    }

    const copyOk = event.target.closest("[data-copy-batch-ok]");
    if (copyOk) {
      const bi = Number(copyOk.dataset.copyBatchOk);
      const text = (current.batches[bi]?.links || [])
        .filter((l) => l.resolve_status === "ok")
        .map((l) => displayUrl(l))
        .filter(Boolean)
        .join("\n");
      try {
        await navigator.clipboard.writeText(text || "");
        showToast("Valides de cette page copiés.");
      } catch {
        showToast("Copie impossible.");
      }
      return;
    }

    const copyDead = event.target.closest("[data-copy-batch-dead]");
    if (copyDead) {
      const bi = Number(copyDead.dataset.copyBatchDead);
      const text = (current.batches[bi]?.links || [])
        .filter((l) => l.resolve_status === "dead" || l.resolve_status === "error")
        .map((l) => `${l.label || l.resolve_filename || "?"} — ${l.url || ""}`)
        .join("\n");
      try {
        await navigator.clipboard.writeText(text || "");
        showToast("Morts de cette page copiés.");
      } catch {
        showToast("Copie impossible.");
      }
      return;
    }

    const copyResolved = event.target.closest("[data-copy-batch-resolved]");
    if (copyResolved) {
      const bi = Number(copyResolved.dataset.copyBatchResolved);
      const text = (current.batches[bi]?.links || [])
        .map((l) => displayUrl(l))
        .filter(Boolean)
        .join("\n");
      try {
        await navigator.clipboard.writeText(text || "");
        showToast("Liens de cette page copiés.");
      } catch {
        showToast("Copie impossible.");
      }
    }
  }

  btnStopResolve.addEventListener("click", () => {
    resolveAbort = true;
    showToast("Arrêt demandé…");
  });

  document.getElementById("btn-copy").addEventListener("click", async () => {
    if (!current?.links?.length) return;
    const text = jdownloaderLines(current.links) || current.links.map((l) => displayUrl(l)).filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      showToast("Liens résolus copiés (format JD si dispo).");
    } catch {
      showToast("Copie impossible.");
    }
  });

  document.getElementById("btn-copy-source").addEventListener("click", async () => {
    if (!current?.links?.length) return;
    const text = current.links.map((l) => l.url || "").filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      showToast("Liens source copiés.");
    } catch {
      showToast("Copie impossible.");
    }
  });

  document.getElementById("btn-copy-ok")?.addEventListener("click", async () => {
    if (!current?.links?.length) return;
    const text = current.links
      .filter((l) => l.resolve_status === "ok")
      .map((l) => displayUrl(l))
      .filter(Boolean)
      .join("\n");
    try {
      await navigator.clipboard.writeText(text || "");
      showToast("Liens valides copiés.");
    } catch {
      showToast("Copie impossible.");
    }
  });

  document.getElementById("btn-copy-dead")?.addEventListener("click", async () => {
    if (!current?.links?.length) return;
    const text = current.links
      .filter((l) => l.resolve_status === "dead" || l.resolve_status === "error")
      .map((l) => `${l.label || l.resolve_filename || "?"} — ${l.url || ""}`)
      .join("\n");
    try {
      await navigator.clipboard.writeText(text || "");
      showToast("Liste des morts copiée.");
    } catch {
      showToast("Copie impossible.");
    }
  });

  document.getElementById("btn-close-results").addEventListener("click", closeResults);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (!settingsModal.hidden) {
        closeSettings();
        return;
      }
      if (!results.hidden) closeResults();
    }
  });

  document.getElementById("btn-save").addEventListener("click", async () => {
    if (!current?.links?.length) {
      showToast("Rien à sauvegarder.");
      return;
    }
    const saved = await autoSaveHistory(current);
    if (saved) {
      showToast(`${saved} page(s) sauvegardée(s) séparément.`);
    } else {
      showToast("Sauvegarde impossible.");
    }
  });

  document.querySelectorAll("[data-export]").forEach((btn) => {
    btn.addEventListener("click", () => downloadExport(btn.dataset.export));
  });

  document.querySelectorAll("[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => viewExport(btn.dataset.view));
  });

  document.getElementById("btn-settings").addEventListener("click", openSettings);

  document.querySelectorAll("[data-theme-set]").forEach((btn) => {
    btn.addEventListener("click", () => persistTheme(btn.dataset.themeSet));
  });
  settingsModal.querySelectorAll("[data-close-settings]").forEach((el) => {
    el.addEventListener("click", closeSettings);
  });

  settingsForm.addEventListener("submit", (event) => {
    event.preventDefault();
    event.stopPropagation();
    saveSettings();
  });

  document.getElementById("btn-settings-save")?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    saveSettings();
  });

  async function saveSettings() {
    const payload = {
      active_provider: activeProviderSelect.value,
      theme: uiThemeSelect?.value || "linkora",
      max_retries: Number(maxRetriesInput?.value || 3),
      resolve_concurrency: Number(concurrencyInput?.value || 6),
      auto_update: autoUpdateInput ? !!autoUpdateInput.checked : true,
      notify_on_resolve: notifyOnResolveInput
        ? !!notifyOnResolveInput.checked
        : true,
      custom_accent:
        customAccentInput && !customAccentInput.dataset.reset
          ? customAccentInput.value
          : settings?.custom_accent || "",
      update_manifest_url: updateManifestInput?.value?.trim() || "",
      rename_template: renameTemplateSelect?.value || "simple",
      profiles: settings?.profiles || [],
      active_profile_id: settings?.active_profile_id || "",
      providers: {
        alldebrid: {},
        realdebrid: {},
      },
    };
    if (customAccentInput?.dataset.reset === "1") {
      payload.custom_accent = "";
      delete customAccentInput.dataset.reset;
    }
    if (keyAlldebrid.value.trim()) {
      payload.providers.alldebrid.api_key = keyAlldebrid.value.trim();
    }
    if (keyRealdebrid.value.trim()) {
      payload.providers.realdebrid.api_key = keyRealdebrid.value.trim();
    }

    try {
      const res = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        showSettingsMessage(data.error || "Enregistrement impossible.", false);
        return;
      }
      settings = data;
      applyTheme(data.theme === "alldebrid" ? "alldebrid" : "linkora");
      applyCustomBranding(data);
      updateProviderBadge();
      refreshProfileSelect();
      const adCount = data.providers?.alldebrid?.key_count || 0;
      const rdCount = data.providers?.realdebrid?.key_count || 0;
      hintAlldebrid.textContent = data.providers?.alldebrid?.configured
        ? `${adCount} clé(s) · ${data.providers.alldebrid.api_key_masked}`
        : "Aucune clé enregistrée.";
      hintRealdebrid.textContent = data.providers?.realdebrid?.configured
        ? `${rdCount} clé(s) · ${data.providers.realdebrid.api_key_masked}`
        : "Aucune clé enregistrée.";
      keyAlldebrid.value = "";
      keyRealdebrid.value = "";
      settingsModal.hidden = false;
      showSettingsMessage("Paramètres enregistrés.", true);
      showToast("Paramètres enregistrés.");
      if (data.notify_on_resolve && "Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
      }
    } catch {
      showSettingsMessage("Erreur réseau.", false);
    }
  }

  btnResetAccent?.addEventListener("click", () => {
    if (customAccentInput) {
      customAccentInput.dataset.reset = "1";
      customAccentInput.value = "#2a6df4";
    }
    document.documentElement.style.removeProperty("--accent");
    showToast("Accent réinitialisé (enregistrez pour confirmer).");
  });

  document.querySelectorAll("[data-test-provider]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const provider = btn.dataset.testProvider;
      const typed =
        provider === "alldebrid"
          ? keyAlldebrid.value.trim()
          : keyRealdebrid.value.trim();
      btn.disabled = true;
      try {
        const res = await fetch("/api/settings/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            provider,
            api_key: typed || undefined,
          }),
        });
        const data = await res.json();
        if (!res.ok || data.ok === false) {
          showSettingsMessage(
            data.error || "Test échoué.",
            false
          );
          return;
        }
        const who = data.username ? ` (${data.username})` : "";
        const prem = data.premium ? " · premium" : "";
        showSettingsMessage(
          `${PROVIDER_LABELS[provider] || provider} OK${who}${prem}`,
          true
        );
      } catch {
        showSettingsMessage("Erreur réseau pendant le test.", false);
      } finally {
        btn.disabled = false;
      }
    });
  });

  function refreshCurrentView({ scroll = false } = {}) {
    const openItem = historyList.querySelector(".history-item.is-open");
    if (openItem && current?.batches?.length) {
      const detail = openItem.querySelector(".history-item-detail");
      if (!detail) return;
      const head =
        detail.querySelector(".history-detail-head")?.outerHTML ||
        `<div class="history-detail-head">
          <p>Aperçu sous l’entrée — fermez pour replier.</p>
          <button type="button" class="btn btn-ghost btn-xs" data-action="close-detail">Fermer</button>
        </div>`;
      detail.innerHTML =
        head + current.batches.map((batch, bi) => pageBlockHtml(batch, bi)).join("");
      detail.hidden = false;
      return;
    }
    renderResults(current, { scroll });
  }

  function closeHistoryDetails() {
    historyList.querySelectorAll(".history-item.is-open").forEach((el) => {
      el.classList.remove("is-open");
      const detail = el.querySelector(".history-item-detail");
      if (detail) {
        detail.hidden = true;
        detail.innerHTML = "";
      }
      const openBtn = el.querySelector('[data-action="open"].btn');
      if (openBtn) openBtn.textContent = "Ouvrir";
    });
  }

  function renderHistoryInline(itemEl, data) {
    closeHistoryDetails();
    const detail = itemEl.querySelector(".history-item-detail");
    if (!detail) return;

    current = normalizeCurrent({
      source_url: data.source_url,
      host: data.host,
      title: data.title,
      count: data.links.length,
      links: data.links,
      batches: [
        {
          source_url: data.source_url,
          title: data.title,
          host: data.host,
          count: data.links.length,
          links: data.links,
          history_id: data.id,
        },
      ],
    });
    syncFlatLinks();

    // Ne pas ouvrir le panneau résultats du haut — tout reste sous l’historique
    results.hidden = true;
    pageBlocks.innerHTML = "";

    detail.innerHTML = `
      <div class="history-detail-head">
        <p>Aperçu sous l’entrée — fermez pour replier.</p>
        <button type="button" class="btn btn-ghost btn-xs" data-action="close-detail">Fermer</button>
      </div>
      ${pageBlockHtml(current.batches[0], 0)}
    `;
    detail.hidden = false;
    itemEl.classList.add("is-open");
    const openBtn = itemEl.querySelector('[data-action="open"].btn');
    if (openBtn) openBtn.textContent = "Fermer";

    detail.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  historyList.addEventListener("click", async (event) => {
    const actionBtn = event.target.closest("[data-action]");
    const item = event.target.closest(".history-item");
    if (!item) return;

    // Actions dans le détail (résoudre, copier…) — délégué plus bas
    if (event.target.closest(".history-item-detail") && actionBtn?.dataset.action !== "close-detail") {
      return;
    }

    if (!actionBtn) return;

    const id = item.dataset.id;
    const action = actionBtn.dataset.action;

    if (action === "close-detail") {
      closeHistoryDetails();
      return;
    }

    if (action === "delete") {
      const ok = await askConfirm(
        "Supprimer cette extraction ?",
        "Cette action est définitive.",
        { confirmText: "Supprimer", icon: "warning" }
      );
      if (!ok) return;
      const res = await fetch(`/api/history/${id}`, { method: "DELETE" });
      if (res.ok) {
        showToast("Supprimé.");
        loadHistory();
      }
      return;
    }

    if (action === "open") {
      if (item.classList.contains("is-open")) {
        closeHistoryDetails();
        return;
      }
      const res = await fetch(`/api/history/${id}`);
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || "Introuvable.");
        return;
      }
      urlsInput.value = data.source_url || "";
      hostInput.value = data.host || "";
      renderHistoryInline(item, data);
      showToast("Ouvert sous l’historique.");
    }
  });

  // ─── Onglets ─────────────────────────────────────────────────────────────
  const tabButtons = document.querySelectorAll(".app-tab-btn");
  const tabPanels = {
    extract: document.getElementById("tab-extract"),
    rename: document.getElementById("tab-rename"),
    help: document.getElementById("tab-help"),
  };

  function switchTab(name) {
    tabButtons.forEach((btn) => {
      const active = btn.dataset.tab === name;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-selected", active ? "true" : "false");
    });
    Object.entries(tabPanels).forEach(([key, panel]) => {
      if (!panel) return;
      const active = key === name;
      panel.classList.toggle("is-active", active);
      panel.hidden = !active;
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  document.getElementById("btn-help")?.addEventListener("click", () => {
    switchTab("help");
  });

  document.querySelectorAll('.help-toc a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (event) => {
      const id = a.getAttribute("href")?.slice(1);
      const target = id ? document.getElementById(id) : null;
      if (!target) return;
      event.preventDefault();
      switchTab("help");
      setTimeout(() => target.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    });
  });

  // ─── Renommage local ─────────────────────────────────────────────────────
  const renameForm = document.getElementById("rename-scan-form");
  const renameFolder = document.getElementById("rename-folder");
  const renameRecursive = document.getElementById("rename-recursive");
  const renameError = document.getElementById("rename-error");
  const renameResults = document.getElementById("rename-results");
  const renameBody = document.getElementById("rename-body");
  const renameSummary = document.getElementById("rename-results-summary");
  const btnRenameScan = document.getElementById("btn-rename-scan");
  const renameCheckAll = document.getElementById("rename-check-all");
  let renameItems = [];

  function showRenameError(message) {
    if (!message) {
      renameError.hidden = true;
      renameError.textContent = "";
      return;
    }
    renameError.hidden = false;
    renameError.textContent = message;
  }

  function setRenameLoading(loading) {
    btnRenameScan.disabled = loading;
    const spinner = btnRenameScan.querySelector(".btn-spinner");
    const label = btnRenameScan.querySelector(".btn-label");
    if (spinner) spinner.hidden = !loading;
    if (label) label.textContent = loading ? "Scan…" : "Scanner";
  }

  function syncRenameCheckAll() {
    if (!renameCheckAll || !renameBody) return;
    const boxes = [...renameBody.querySelectorAll(".rename-check")];
    if (!boxes.length) {
      renameCheckAll.checked = false;
      renameCheckAll.indeterminate = false;
      return;
    }
    const n = boxes.filter((b) => b.checked).length;
    renameCheckAll.checked = n === boxes.length;
    renameCheckAll.indeterminate = n > 0 && n < boxes.length;
  }

  function selectedRenameItems() {
    if (!renameBody) return [];
    const selected = new Set();
    renameBody.querySelectorAll(".rename-check:checked").forEach((cb) => {
      const i = Number(cb.dataset.renameIndex);
      if (!Number.isNaN(i)) selected.add(i);
    });
    return renameItems.filter((item, i) => selected.has(i));
  }

  function renameTargetsFromSelection() {
    return selectedRenameItems().filter((i) => !i.unchanged && !i.conflict);
  }

  function renderRenameResults(data) {
    renameItems = data.items || [];
    renameResults.hidden = false;
    const toRename = renameItems.filter((i) => !i.unchanged).length;
    renameSummary.innerHTML =
      `<strong>${renameItems.length}</strong> fichier(s) · ` +
      `<strong>${toRename}</strong> à renommer · ` +
      `<code>${escapeHtml(data.folder)}</code>` +
      `<br><span class="field-hint">Décochez les fichiers à ne pas modifier (tout est coché par défaut).</span>`;

    renameBody.innerHTML = renameItems.length
      ? renameItems
          .map((item, i) => {
            let status = "Prêt";
            let statusCls = "ok";
            if (item.unchanged) {
              status = "Déjà propre";
              statusCls = "pending";
            } else if (item.conflict) {
              status = "Conflit";
              statusCls = "dead";
            }
            return `
        <tr class="${item.unchanged ? "row-muted" : ""}">
          <td class="col-check">
            <input type="checkbox" class="rename-check" data-rename-index="${i}" checked aria-label="Inclure ${escapeHtml(item.original)}">
          </td>
          <td>${i + 1}</td>
          <td class="cell-filename" title="${escapeHtml(item.original)}">${escapeHtml(item.original)}</td>
          <td>→</td>
          <td class="cell-filename" title="${escapeHtml(item.suggested)}">${escapeHtml(item.suggested)}</td>
          <td><span class="size-pill">${escapeHtml(item.type || "—")}</span></td>
          <td><span class="status-pill ${statusCls}">${status}</span></td>
        </tr>`;
          })
          .join("")
      : `<tr><td colspan="7">Aucun fichier vidéo/audio dans ce dossier.</td></tr>`;
    if (renameCheckAll) {
      renameCheckAll.checked = renameItems.length > 0;
      renameCheckAll.indeterminate = false;
    }
    renameResults.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  renameBody?.addEventListener("change", (event) => {
    if (event.target?.classList?.contains("rename-check")) syncRenameCheckAll();
  });

  renameCheckAll?.addEventListener("change", () => {
    const on = !!renameCheckAll.checked;
    renameBody?.querySelectorAll(".rename-check").forEach((cb) => {
      cb.checked = on;
    });
    renameCheckAll.indeterminate = false;
  });

  renameForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    showRenameError("");
    setRenameLoading(true);
    try {
      const res = await fetch("/api/rename/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          folder: renameFolder.value.trim(),
          recursive: renameRecursive?.checked || false,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        showRenameError(data.error || "Scan impossible.");
        return;
      }
      renderRenameResults(data);
      if (!data.count) showToast("Aucun fichier trouvé.");
      else showToast(`${data.to_rename} fichier(s) à renommer sur ${data.count}.`);
    } catch {
      showRenameError("Impossible de contacter le serveur.");
    } finally {
      setRenameLoading(false);
    }
  });

  document.getElementById("btn-rename-apply")?.addEventListener("click", async () => {
    const items = renameTargetsFromSelection();
    if (!items.length) {
      showToast("Aucun fichier coché à renommer.");
      return;
    }
    const ok = await askConfirm(
      `Renommer ${items.length} fichier(s) coché(s) ?`,
      "Seuls les fichiers sélectionnés seront modifiés sur votre PC.",
      { confirmText: "Renommer", icon: "question" }
    );
    if (!ok) return;
    try {
      const res = await fetch("/api/rename/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items, dry_run: false }),
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || "Renommage impossible.");
        return;
      }
      showToast(`${data.count} fichier(s) renommé(s).`);
      if (data.errors?.length) showToast(`${data.errors.length} erreur(s) — voir console.`);
      renameForm.requestSubmit();
    } catch {
      showToast("Renommage impossible.");
    }
  });

  document.getElementById("btn-rename-dry")?.addEventListener("click", async () => {
    const items = renameTargetsFromSelection();
    if (!items.length) {
      showToast("Rien à simuler (cochez des fichiers).");
      return;
    }
    try {
      const res = await fetch("/api/rename/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items, dry_run: true }),
      });
      const data = await res.json();
      showToast(`Simulation : ${data.count} renommage(s) possibles.`);
    } catch {
      showToast("Simulation impossible.");
    }
  });

  document.getElementById("btn-rename-copy")?.addEventListener("click", async () => {
    const items = selectedRenameItems().filter((i) => !i.unchanged);
    const text = items.map((i) => `${i.original} → ${i.suggested}`).join("\n");
    try {
      await navigator.clipboard.writeText(text || "");
      showToast(items.length ? "Liste (sélection) copiée." : "Rien à copier.");
    } catch {
      showToast("Copie impossible.");
    }
  });

  filterStatus?.addEventListener("change", applyResultFilters);
  filterText?.addEventListener("input", applyResultFilters);

  document.getElementById("btn-select-visible")?.addEventListener("click", () => {
    pageBlocks?.querySelectorAll("tr[data-batch][data-link]:not(.row-hidden) .link-check").forEach((cb) => {
      cb.checked = true;
    });
    showToast("Sélection des lignes visibles.");
  });

  document.getElementById("btn-clear-selection")?.addEventListener("click", () => {
    pageBlocks?.querySelectorAll(".link-check").forEach((cb) => {
      cb.checked = false;
    });
  });

  document.getElementById("btn-copy-selection")?.addEventListener("click", async () => {
    const links = selectedLinks();
    if (!links.length) {
      showToast("Aucune sélection.");
      return;
    }
    const text = jdownloaderLines(links) || links.map((l) => displayUrl(l)).filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      showToast(`${links.length} lien(s) copiés.`);
    } catch {
      showToast("Copie impossible.");
    }
  });

  document.getElementById("btn-jd-selection")?.addEventListener("click", async () => {
    const links = selectedLinks();
    if (!links.length) {
      showToast("Aucune sélection.");
      return;
    }
    const text = jdownloaderLines(links);
    try {
      await navigator.clipboard.writeText(text);
      // Fichier crawljob-like pour coller / importer
      const blob = new Blob([text + "\n"], { type: "text/plain;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "linkora-jdownloader.txt";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 30_000);
      showToast("Sélection JD copiée + fichier téléchargé.");
    } catch {
      showToast("Envoi JD impossible.");
    }
  });

  document.getElementById("btn-missing-episodes")?.addEventListener("click", async () => {
    if (!current?.links?.length) {
      showToast("Aucun lien.");
      return;
    }
    try {
      const res = await fetch("/api/episodes/missing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ links: current.links }),
      });
      const data = await res.json();
      if (!missingBox) return;
      missingBox.hidden = false;
      if (!data.missing_labels?.length) {
        missingBox.textContent = data.summary || "Rien à signaler.";
      } else {
        missingBox.innerHTML =
          `<strong>Épisodes manquants</strong> — ${escapeHtml(data.summary)}` +
          ` <button type="button" class="btn btn-ghost btn-xs" id="btn-copy-missing">Copier</button>`;
        document.getElementById("btn-copy-missing")?.addEventListener("click", async () => {
          try {
            await navigator.clipboard.writeText(data.missing_labels.join("\n"));
            showToast("Liste des manquants copiée.");
          } catch {
            showToast("Copie impossible.");
          }
        });
      }
    } catch {
      showToast("Analyse impossible.");
    }
  });

  profileSelect?.addEventListener("change", async () => {
    const id = profileSelect.value;
    if (!id) {
      if (settings) settings.active_profile_id = "";
      try {
        await fetch("/api/settings", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active_profile_id: "" }),
        });
      } catch {
        /* ignore */
      }
      return;
    }
    try {
      const res = await fetch("/api/settings/profiles/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || "Profil impossible.");
        return;
      }
      settings = data.settings;
      const prof = data.profile;
      if (prof?.host) hostInput.value = prof.host;
      if (activeProviderSelect) {
        activeProviderSelect.value = settings.active_provider || "alldebrid";
      }
      if (maxRetriesInput) maxRetriesInput.value = String(settings.max_retries || 3);
      if (concurrencyInput) {
        concurrencyInput.value = String(settings.resolve_concurrency || 6);
      }
      if (renameTemplateSelect) {
        renameTemplateSelect.value = settings.rename_template || "simple";
      }
      updateProviderBadge();
      refreshProfileSelect();
      showToast(`Profil « ${prof.name} » appliqué.`);
    } catch {
      showToast("Impossible d’appliquer le profil.");
    }
  });

  btnProfileSave?.addEventListener("click", async () => {
    const name = window.prompt(
      "Nom du profil (ex. Rapidgator AllDebrid) :",
      profileSelect?.selectedOptions?.[0]?.text?.startsWith("—")
        ? ""
        : profileSelect?.selectedOptions?.[0]?.text || ""
    );
    if (name == null) return;
    const trimmed = name.trim();
    if (!trimmed) {
      showToast("Nom de profil requis.");
      return;
    }
    try {
      await loadSettings();
    } catch {
      /* ignore */
    }
    const profiles = [...(settings?.profiles || [])];
    const existingId = profileSelect?.value || "";
    const payloadProfile = {
      id: existingId || undefined,
      name: trimmed,
      host: hostInput.value.trim(),
      active_provider: settings?.active_provider || activeProviderSelect?.value || "alldebrid",
      max_retries: Number(settings?.max_retries || maxRetriesInput?.value || 3),
      resolve_concurrency: Number(
        settings?.resolve_concurrency || concurrencyInput?.value || 6
      ),
      rename_template: settings?.rename_template || renameTemplateSelect?.value || "simple",
    };
    if (existingId) {
      const idx = profiles.findIndex((p) => p.id === existingId);
      if (idx >= 0) profiles[idx] = { ...profiles[idx], ...payloadProfile, id: existingId };
      else profiles.push(payloadProfile);
    } else {
      profiles.push(payloadProfile);
    }
    try {
      const res = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profiles,
          active_profile_id: existingId || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || "Profil non enregistré.");
        return;
      }
      settings = data;
      // Sélectionner le profil créé / mis à jour
      const match =
        data.profiles?.find((p) => p.name === trimmed) ||
        data.profiles?.[data.profiles.length - 1];
      if (match) {
        await fetch("/api/settings", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active_profile_id: match.id }),
        });
        settings.active_profile_id = match.id;
      }
      refreshProfileSelect();
      showToast(`Profil « ${trimmed} » enregistré.`);
    } catch {
      showToast("Enregistrement du profil impossible.");
    }
  });

  btnProfileDelete?.addEventListener("click", async () => {
    const id = profileSelect?.value;
    if (!id) {
      showToast("Sélectionnez un profil.");
      return;
    }
    const ok = await askConfirm(
      "Supprimer ce profil ?",
      "Les réglages globaux et les clés API ne seront pas effacés."
    );
    if (!ok) return;
    const profiles = (settings?.profiles || []).filter((p) => p.id !== id);
    try {
      const res = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profiles, active_profile_id: "" }),
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || "Suppression impossible.");
        return;
      }
      settings = data;
      refreshProfileSelect();
      showToast("Profil supprimé.");
    } catch {
      showToast("Suppression impossible.");
    }
  });

  queueList?.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-queue-remove]");
    if (!btn || queueRunning) return;
    const idx = Number(btn.getAttribute("data-queue-remove"));
    if (Number.isNaN(idx)) return;
    workQueue.splice(idx, 1);
    renderQueue();
  });

  btnQueueAdd?.addEventListener("click", () => {
    const lines = (urlsInput.value || "")
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean);
    if (!lines.length) {
      showToast("Collez d’abord une ou plusieurs URLs.");
      return;
    }
    const host = hostInput.value.trim();
    if (!host) {
      showToast("Indiquez un hébergeur.");
      return;
    }
    let added = 0;
    for (const url of lines) {
      if (workQueue.some((q) => q.url === url && q.host === host)) continue;
      workQueue.push({ url, host, status: "pending", error: "" });
      added += 1;
    }
    renderQueue();
    showToast(added ? `${added} page(s) ajoutée(s) à la file.` : "Déjà dans la file.");
  });

  btnQueueClear?.addEventListener("click", async () => {
    if (queueRunning) {
      showToast("File en cours — Stop d’abord.");
      return;
    }
    if (!workQueue.length) return;
    const ok = await askConfirm("Vider la file ?", "Les pages en attente seront retirées.");
    if (!ok) return;
    workQueue = [];
    renderQueue();
  });

  async function resolveCurrentBatches() {
    const provider = await ensureProviderReady();
    if (!provider) return null;
    const providerName = PROVIDER_LABELS[provider] || provider;
    resolveAbort = false;
    setResolving(true);
    current.batches.forEach((batch) => {
      batch.links = (batch.links || []).map(resetLinkForResolve);
    });
    syncFlatLinks();
    refreshCurrentView({ scroll: false });
    const jobs = collectJobs((l) => l.resolve_status !== "ok");
    if (!jobs.length) {
      setResolving(false);
      return { ok: 0, total: 0, providerName, skipped: true };
    }
    const result = await runResolvePool(jobs, provider, "File — résolution…");
    syncFlatLinks();
    current.resolved_provider = provider;
    updateSummary();
    await autoSaveHistory(current);
    setResolving(false);
    return { ...result, providerName, skipped: false };
  }

  btnQueueRun?.addEventListener("click", async () => {
    if (queueRunning) {
      showToast("File déjà en cours.");
      return;
    }
    if (!workQueue.length) {
      showToast("File vide — ajoutez des URLs.");
      return;
    }
    const host = hostInput.value.trim();
    if (!host && workQueue.some((q) => !q.host)) {
      showToast("Indiquez un hébergeur.");
      return;
    }
    queueRunning = true;
    btnQueueRun.disabled = true;
    btnQueueAdd.disabled = true;
    let pagesOk = 0;
    let linksOk = 0;
    let linksTotal = 0;
    const allBatches = [];

    try {
      for (let i = 0; i < workQueue.length; i += 1) {
        if (resolveAbort) break;
        const item = workQueue[i];
        item.status = "running";
        renderQueue();
        showToast(`File ${i + 1}/${workQueue.length} — extraction…`);
        try {
          const res = await fetch("/api/extract", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              urls: item.url,
              host: item.host || host,
            }),
          });
          const data = await res.json();
          if (!res.ok) {
            item.status = "error";
            item.error = data.error || "Extraction échouée";
            renderQueue();
            continue;
          }
          const batches = data.batches || [];
          if (!batches.length) {
            item.status = "error";
            item.error = "Aucun lien";
            renderQueue();
            continue;
          }
          // Fusionner pour affichage + résolution page courante
          allBatches.push(...batches);
          current = normalizeCurrent({
            ...data,
            batches: allBatches,
            host: item.host || host,
          });
          syncFlatLinks();
          renderResults(current, { scroll: i === 0 });
          const resolved = await resolveCurrentBatches();
          if (resolved && !resolved.skipped) {
            linksOk += resolved.ok || 0;
            linksTotal += resolved.total || 0;
          }
          item.status = resolveAbort ? "error" : "done";
          if (!resolveAbort) pagesOk += 1;
          renderQueue();
        } catch {
          item.status = "error";
          item.error = "Réseau";
          renderQueue();
        }
      }
      const msg = resolveAbort
        ? `File arrêtée — ${pagesOk} page(s), ${linksOk}/${linksTotal} liens.`
        : `File terminée — ${pagesOk} page(s), ${linksOk}/${linksTotal} liens résolus.`;
      showToast(msg);
      notifyDesktop("Linkora — file d’attente", msg);
    } finally {
      queueRunning = false;
      btnQueueRun.disabled = false;
      btnQueueAdd.disabled = false;
      renderQueue();
    }
  });

  btnBackupExport?.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/data/backup");
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        showToast(data.error || "Export impossible.");
        return;
      }
      const blob = await res.blob();
      const dispo = res.headers.get("Content-Disposition") || "";
      const match = /filename="?([^"]+)"?/i.exec(dispo);
      const name = match?.[1] || "linkora-data.zip";
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = name;
      a.click();
      URL.revokeObjectURL(a.href);
      showToast("Backup téléchargé.");
    } catch {
      showToast("Export impossible.");
    }
  });

  backupImportFile?.addEventListener("change", async () => {
    const file = backupImportFile.files?.[0];
    backupImportFile.value = "";
    if (!file) return;
    const ok = await askConfirm(
      "Restaurer ce backup ?",
      "Cela remplacera l’historique et les réglages locaux actuels."
    );
    if (!ok) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const res = await fetch("/api/data/restore", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || "Import impossible.");
        return;
      }
      if (data.settings) {
        settings = data.settings;
        await loadSettings();
      }
      await loadHistory();
      showToast(data.message || "Backup restauré.");
      closeSettings();
    } catch {
      showToast("Import impossible.");
    }
  });

  loadSettings().catch(() => {});
  loadHistory();
  renderQueue();
  refreshUpdateStatus();
  // Re-vérifie l’état MAJ après le check auto au démarrage serveur
  setTimeout(() => refreshUpdateStatus(), 2500);
  setTimeout(() => refreshUpdateStatus(), 8000);

  btnUpdateDismiss?.addEventListener("click", () => {
    if (updateBanner) updateBanner.hidden = true;
  });

  btnUpdateApply?.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/update/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const data = await res.json();
      showUpdateBanner(data);
      if (data.error) showToast(data.error);
      else showToast(data.message || "Mise à jour appliquée.");
      if (data.restarting) {
        showToast("Fermeture pour appliquer la MAJ…");
      }
      refreshUpdateStatus();
    } catch {
      // Si le serveur s’est fermé pour redémarrer, c’est attendu
      showToast("Mise à jour en cours — redémarrage…");
    }
  });

  btnCheckUpdate?.addEventListener("click", async () => {
    btnCheckUpdate.disabled = true;
    try {
      const res = await fetch("/api/update/check", { method: "POST" });
      const data = await res.json();
      showUpdateBanner(data);
      if (updateStatusHint) {
        updateStatusHint.textContent = data.message || `Version : ${data.current}`;
      }
      if (btnForceUpdate) btnForceUpdate.hidden = !data.update_available;
      showToast(data.message || "Vérification terminée.");
    } catch {
      showToast("Vérification impossible.");
    } finally {
      btnCheckUpdate.disabled = false;
    }
  });

  btnForceUpdate?.addEventListener("click", async () => {
    btnForceUpdate.disabled = true;
    try {
      const res = await fetch("/api/update/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const data = await res.json();
      showUpdateBanner(data);
      showToast(data.error || data.message || "Terminé.");
      if (data.restarting) showToast("Fermeture pour appliquer la MAJ…");
    } catch {
      showToast("Mise à jour en cours — redémarrage…");
    } finally {
      btnForceUpdate.disabled = false;
    }
  });
})();
