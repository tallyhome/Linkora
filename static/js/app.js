(() => {
  const form = document.getElementById("extract-form");
  const urlsInput = document.getElementById("urls");
  const hostInput = document.getElementById("host");
  const hostsList = document.getElementById("hosts-list");
  const btnAddHost = document.getElementById("btn-add-host");
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
  const updateProgressModal = document.getElementById("update-progress-modal");
  const updateProgressText = document.getElementById("update-progress-text");
  const updateProgressFill = document.getElementById("update-progress-fill");
  const updateProgressPct = document.getElementById("update-progress-pct");
  let updateProgressTimer = null;
  const filterBar = document.getElementById("results-filter-bar");
  const filterStatus = document.getElementById("filter-status");
  const filterText = document.getElementById("filter-text");
  const missingBox = document.getElementById("missing-episodes-box");
  const maxRetriesInput = document.getElementById("max-retries");
  const concurrencyInput = document.getElementById("resolve-concurrency");
  const notifyOnResolveInput = document.getElementById("notify-on-resolve");
  const sslIgnoreErrorsInput = document.getElementById("ssl-ignore-errors");
  const nasHostInput = document.getElementById("nas-host");
  const nasShareInput = document.getElementById("nas-share");
  const nasUsernameInput = document.getElementById("nas-username");
  const nasPasswordInput = document.getElementById("nas-password");
  const hintNas = document.getElementById("hint-nas");
  let nasClearRequested = false;
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

  const MAX_HOSTS = 6;

  function getHostInputs() {
    return [...document.querySelectorAll("[data-host-input]")];
  }

  function getHosts() {
    const out = [];
    const seen = new Set();
    for (const input of getHostInputs()) {
      const value = (input.value || "").trim();
      if (!value) continue;
      const key = value.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(value);
      if (out.length >= MAX_HOSTS) break;
    }
    return out;
  }

  function hostsLabel(hosts) {
    const list = hosts || getHosts();
    return list.join(" + ");
  }

  function parseHostsValue(value) {
    if (Array.isArray(value)) {
      return value.map((h) => String(h || "").trim()).filter(Boolean).slice(0, MAX_HOSTS);
    }
    const text = String(value || "").trim();
    if (!text) return [];
    if (text.includes(" + ")) {
      return text
        .split(" + ")
        .map((h) => h.trim())
        .filter(Boolean)
        .slice(0, MAX_HOSTS);
    }
    return [text];
  }

  function syncAddHostButton() {
    if (!btnAddHost || !hostsList) return;
    const count = hostsList.querySelectorAll("[data-host-row]").length;
    btnAddHost.hidden = count >= MAX_HOSTS;
  }

  function addHostRow(value = "") {
    if (!hostsList) return;
    const count = hostsList.querySelectorAll("[data-host-row]").length;
    if (count >= MAX_HOSTS) return;
    const row = document.createElement("div");
    row.className = "host-row";
    row.setAttribute("data-host-row", "");
    row.innerHTML = `
      <label class="field field-host">
        <span class="field-label">Hébergeur ${count + 1}</span>
        <div class="host-input-row">
          <input
            type="text"
            data-host-input
            list="host-suggestions"
            placeholder="ex. nitroflare"
            spellcheck="false"
            value="${escapeHtml(value)}"
          >
          <button type="button" class="btn btn-ghost host-remove" data-remove-host title="Retirer">×</button>
        </div>
      </label>`;
    hostsList.appendChild(row);
    syncAddHostButton();
    row.querySelector("[data-host-input]")?.focus();
  }

  function setHosts(hosts) {
    const list = parseHostsValue(hosts);
    const primary = list[0] || "";
    if (hostInput) hostInput.value = primary;
    if (!hostsList) return;
    hostsList.querySelectorAll("[data-host-row]").forEach((row, idx) => {
      if (idx > 0) row.remove();
    });
    list.slice(1).forEach((h) => addHostRow(h));
    const firstLabel = hostsList.querySelector("[data-host-row] .field-label");
    if (firstLabel) firstLabel.textContent = "Hébergeur";
    syncAddHostButton();
  }

  function currentHostsList() {
    if (current?.hosts?.length) return current.hosts;
    return parseHostsValue(current?.host || getHosts());
  }

  function isMultiHostSession() {
    return currentHostsList().length >= 2;
  }

  function episodeKey(link) {
    if (link?.media_season != null && link?.media_episode != null) {
      const title = String(link.media_title || link.clean_name || link.label || "")
        .toLowerCase()
        .replace(/s\d{1,2}e\d{1,3}.*$/i, "")
        .replace(/[^a-z0-9]+/g, "")
        .slice(0, 40);
      return `${title}|s${link.media_season}e${link.media_episode}`;
    }
    const base = String(
      link?.clean_name || link?.label || link?.resolve_filename || link?.url || ""
    )
      .toLowerCase()
      .replace(/\.[a-z0-9]{2,4}$/i, "")
      .replace(/[^a-z0-9]+/g, "");
    return base || String(link?.url || Math.random());
  }

  function hostRank(link, hosts) {
    const h = String(link?.matched_host || "").toLowerCase();
    const idx = (hosts || []).findIndex((x) => String(x).toLowerCase() === h);
    return idx >= 0 ? idx : 999;
  }

  function assignMultiHostRoles() {
    if (!current?.batches) return;
    const hosts = currentHostsList();
    if (hosts.length < 2) {
      current.batches.forEach((batch) => {
        (batch.links || []).forEach((link) => {
          delete link.is_primary;
          delete link.is_mirror;
        });
      });
      return;
    }

    current.batches.forEach((batch) => {
      const groups = new Map();
      (batch.links || []).forEach((link) => {
        const key = episodeKey(link);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(link);
      });

      for (const items of groups.values()) {
        items.sort((a, b) => hostRank(a, hosts) - hostRank(b, hosts));
        const oks = items
          .filter((l) => l.resolve_status === "ok")
          .sort((a, b) => hostRank(a, hosts) - hostRank(b, hosts));

        let winner = null;
        if (oks.length) {
          winner = oks[0];
        } else {
          // Priorité hébergeur 1 ; si mort/erreur → prochain miroir non encore tenté, sinon le 1er
          const untried = items.find(
            (l) => !l.resolve_status || l.resolve_status === "" || l.resolve_status === "running"
          );
          const failedFirst =
            items[0] &&
            (items[0].resolve_status === "dead" || items[0].resolve_status === "error");
          if (failedFirst) {
            winner =
              items.find(
                (l) =>
                  l !== items[0] &&
                  (!l.resolve_status ||
                    (l.resolve_status !== "dead" && l.resolve_status !== "error"))
              ) || items[0];
          } else {
            winner = untried || items[0];
          }
        }

        items.forEach((link) => {
          link.is_primary = link === winner;
          link.is_mirror = link !== winner;
        });
      }
    });
  }

  function hasUntriedMirrorsForDeadPrimaries() {
    if (!isMultiHostSession()) return false;
    for (const batch of current?.batches || []) {
      const groups = new Map();
      (batch.links || []).forEach((link) => {
        const key = episodeKey(link);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(link);
      });
      for (const items of groups.values()) {
        const primary = items.find((l) => l.is_primary) || items[0];
        if (!primary) continue;
        if (primary.resolve_status === "ok") continue;
        if (primary.resolve_status !== "dead" && primary.resolve_status !== "error") {
          continue;
        }
        const untried = items.find(
          (l) => l !== primary && (!l.resolve_status || l.resolve_status === "")
        );
        if (untried) return true;
      }
    }
    return false;
  }

  async function resolveWithMultiHostFallback(provider, labelPrefix, onlyBi = null) {
    assignMultiHostRoles();
    refreshCurrentView({ scroll: false });

    let ok = 0;
    let failed = 0;
    let done = 0;
    let rounds = 0;

    while (!resolveAbort && rounds < MAX_HOSTS + 1) {
      rounds += 1;
      assignMultiHostRoles();
      const jobs = [];
      (current?.batches || []).forEach((batch, bi) => {
        if (onlyBi != null && bi !== onlyBi) return;
        (batch.links || []).forEach((link, li) => {
          if (isMultiHostSession() && link.is_mirror) return;
          if (link.resolve_status === "ok") return;
          jobs.push({ bi, li });
        });
      });
      if (!jobs.length) break;

      const result = await runResolvePool(
        jobs,
        provider,
        rounds === 1
          ? labelPrefix || "Résolution…"
          : `Fallback hébergeur (passe ${rounds})…`
      );
      ok += result.ok;
      failed += result.failed;
      done += result.done;

      assignMultiHostRoles();
      if (!hasUntriedMirrorsForDeadPrimaries()) break;
    }

    assignMultiHostRoles();
    refreshCurrentView({ scroll: false });
    return { ok, failed, total: done, done };
  }

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
        ? `${workQueue.length} page(s) en file — hébergeur : ${hostsLabel() || "…"}`
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
    const hostBadge = link.matched_host
      ? `<div class="host-pill" title="Hébergeur détecté">${escapeHtml(link.matched_host)}</div>`
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
        <td><div class="cell-label" title="${escapeHtml(label)}">${escapeHtml(label)}</div>${clean}${hostBadge}</td>
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
      if (isMultiHostSession() && link.is_mirror) return;
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
    const multi = isMultiHostSession();
    const indexed = (batch.links || []).map((link, li) => ({ link, li }));
    const mainItems = multi ? indexed.filter((x) => !x.link.is_mirror) : indexed;
    const mirrorItems = multi ? indexed.filter((x) => x.link.is_mirror) : [];

    const ok = mainItems.filter((x) => x.link.resolve_status === "ok").length;
    const dead = mainItems.filter(
      (x) => x.link.resolve_status === "dead" || x.link.resolve_status === "error"
    ).length;
    const err = batch.error
      ? `<p class="form-error">Erreur : ${escapeHtml(batch.error)}</p>`
      : "";
    const rows = mainItems.length
      ? mainItems.map(({ link, li }) => rowHtml(link, bi, li)).join("")
      : `<tr><td colspan="8">Aucun lien trouvé sur cette page.</td></tr>`;

    const mirrorRows = mirrorItems.length
      ? mirrorItems.map(({ link, li }) => rowHtml(link, bi, li)).join("")
      : "";

    const mirrorBlock =
      multi && mirrorItems.length
        ? `
        <details class="mirrors-block">
          <summary>
            Miroirs / doublons
            <span class="split-count">${mirrorItems.length}</span>
            <span class="field-hint">— non inclus dans le téléchargement principal</span>
          </summary>
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
              <tbody>${mirrorRows}</tbody>
            </table>
          </div>
        </details>`
        : "";

    const hostNote = multi
      ? ` · multi-hébergeurs · <strong>${mainItems.length}</strong> épisode(s) principal(aux)`
      : "";

    return `
      <article class="page-block" data-batch-index="${bi}">
        <header class="page-block-head">
          <div>
            <h3 class="page-block-title">${escapeHtml(batch.title || "Page")}</h3>
            <p class="page-block-meta">
              <strong>${batch.links?.length || 0}</strong> lien(s)${hostNote}
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
        ${mirrorBlock}
      </article>`;
  }

  function updateSummary() {
    if (!current) return;
    syncFlatLinks();
    const multi = isMultiHostSession();
    const mainLinks = multi
      ? (current.links || []).filter((l) => !l.is_mirror)
      : current.links || [];
    const resolvedOk = mainLinks.filter((l) => l.resolve_status === "ok").length;
    const dead = mainLinks.filter(
      (l) => l.resolve_status === "dead" || l.resolve_status === "error"
    ).length;
    const mirrors = multi
      ? (current.links || []).filter((l) => l.is_mirror).length
      : 0;
    const pages = current.batches?.length || 1;
    resultsSummary.innerHTML = multi
      ? `<strong>${mainLinks.length}</strong> lien(s) principal(aux)` +
        (mirrors ? ` · <strong>${mirrors}</strong> miroir(s)` : "") +
        ` · <strong>${pages}</strong> page(s) · hébergeur <strong>${escapeHtml(current.host)}</strong>` +
        (resolvedOk || dead
          ? ` · <strong>${resolvedOk}</strong> valides · <strong>${dead}</strong> morts`
          : "")
      : `<strong>${current.count}</strong> lien(s) · <strong>${pages}</strong> page(s) · hébergeur <strong>${escapeHtml(current.host)}</strong>` +
        (resolvedOk || dead
          ? ` · <strong>${resolvedOk}</strong> valides · <strong>${dead}</strong> morts`
          : "");
  }

  function renderResults(data, { scroll = true } = {}) {
    current = normalizeCurrent(data);
    if (data?.hosts?.length) current.hosts = data.hosts;
    else if (!current.hosts?.length) current.hosts = parseHostsValue(current.host);
    assignMultiHostRoles();
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

  const THEME_LABELS = {
    linkora: "Linkora",
    alldebrid: "Ambre",
    nocturne: "Pro (sombre)",
  };

  function normalizeTheme(theme) {
    if (theme === "lienlab") return "linkora";
    return THEME_LABELS[theme] ? theme : "linkora";
  }

  function applyTheme(theme) {
    const value = normalizeTheme(theme);
    document.documentElement.setAttribute("data-theme", value);
    document.querySelectorAll("[data-theme-set]").forEach((btn) => {
      const key = btn.dataset.themeSet === "lienlab" ? "linkora" : btn.dataset.themeSet;
      btn.classList.toggle("is-active", key === value);
    });
    if (uiThemeSelect) uiThemeSelect.value = value;
  }

  async function persistTheme(theme) {
    const value = normalizeTheme(theme);
    applyTheme(value);
    try {
      const res = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme: value }),
      });
      const data = await res.json();
      if (res.ok) {
        settings = { ...(settings || {}), ...data };
        showToast(`Thème ${THEME_LABELS[value]} activé.`);
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
      uiThemeSelect.value = normalizeTheme(settings.theme);
    }
    if (autoUpdateInput) {
      autoUpdateInput.checked = settings.auto_update !== false;
    }
    if (notifyOnResolveInput) {
      notifyOnResolveInput.checked = settings.notify_on_resolve !== false;
    }
    if (sslIgnoreErrorsInput) {
      sslIgnoreErrorsInput.checked = settings.ssl_ignore_errors === true;
    }
    const nasEntry = (settings.network_shares || [])[0] || null;
    if (nasHostInput) nasHostInput.value = nasEntry?.host || "";
    if (nasShareInput) nasShareInput.value = nasEntry?.share || "";
    if (nasUsernameInput) nasUsernameInput.value = nasEntry?.username || "";
    if (nasPasswordInput) nasPasswordInput.value = "";
    nasClearRequested = false;
    if (hintNas) {
      hintNas.textContent = nasEntry?.configured
        ? `Identifiants enregistrés · ${nasEntry.username}${nasEntry.password_masked ? " · " + nasEntry.password_masked : ""}`
        : "Aucun identifiant NAS enregistré.";
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
    applyTheme(normalizeTheme(settings.theme));
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
    const hosts = getHosts();
    if (!hosts.length) {
      showError("Veuillez indiquer au moins un hébergeur.");
      return;
    }
    setLoading(true);

    try {
      const res = await fetch("/api/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          urls: urlsInput.value,
          hosts,
          host: hosts[0] || "",
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
    assignMultiHostRoles();
    syncFlatLinks();
    refreshCurrentView({ scroll: false });

    const jobs = collectJobs(
      (l) => (!isMultiHostSession() || !l.is_mirror) && l.resolve_status !== "ok"
    );

    if (!jobs.length) {
      showToast("Tous les liens principaux sont déjà valides.");
      setResolving(false);
      return;
    }

    showToast(
      `${providerName} — résolution` +
        (isMultiHostSession() ? " (1er hébergeur + fallback miroirs)" : "") +
        ` (x${getConcurrency()}, ${getMaxRetries()} essais si dead).`
    );

    const result = await resolveWithMultiHostFallback(provider, "Résolution…");
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
      assignMultiHostRoles();
      syncFlatLinks();
      refreshCurrentView({ scroll: false });

      const result = await resolveWithMultiHostFallback(provider, `Page ${bi + 1}…`, bi);
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
        .filter((l) => !isMultiHostSession() || !l.is_mirror)
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
      const links = (current.batches[bi]?.links || []).filter(
        (l) => !isMultiHostSession() || !l.is_mirror
      );
      const text = jdownloaderLines(links);
      try {
        await navigator.clipboard.writeText(text || "");
        showToast("Format JDownloader copié (principaux).");
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
        .filter((l) => l.resolve_status === "ok" && (!isMultiHostSession() || !l.is_mirror))
        .map((l) => displayUrl(l))
        .filter(Boolean)
        .join("\n");
      try {
        await navigator.clipboard.writeText(text || "");
        showToast("Valides principaux de cette page copiés.");
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
        .filter((l) => !isMultiHostSession() || !l.is_mirror)
        .map((l) => displayUrl(l))
        .filter(Boolean)
        .join("\n");
      try {
        await navigator.clipboard.writeText(text || "");
        showToast("Liens principaux de cette page copiés.");
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
    const links = current.links.filter((l) => !isMultiHostSession() || !l.is_mirror);
    const text = jdownloaderLines(links) || links.map((l) => displayUrl(l)).filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      showToast("Liens principaux copiés (format JD si dispo).");
    } catch {
      showToast("Copie impossible.");
    }
  });

  document.getElementById("btn-copy-source").addEventListener("click", async () => {
    if (!current?.links?.length) return;
    const text = current.links
      .filter((l) => !isMultiHostSession() || !l.is_mirror)
      .map((l) => l.url || "")
      .filter(Boolean)
      .join("\n");
    try {
      await navigator.clipboard.writeText(text);
      showToast("Liens source principaux copiés.");
    } catch {
      showToast("Copie impossible.");
    }
  });

  document.getElementById("btn-copy-ok")?.addEventListener("click", async () => {
    if (!current?.links?.length) return;
    const text = current.links
      .filter((l) => l.resolve_status === "ok" && (!isMultiHostSession() || !l.is_mirror))
      .map((l) => displayUrl(l))
      .filter(Boolean)
      .join("\n");
    try {
      await navigator.clipboard.writeText(text || "");
      showToast("Liens valides principaux copiés.");
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
      ssl_ignore_errors: sslIgnoreErrorsInput
        ? !!sslIgnoreErrorsInput.checked
        : false,
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
    if (nasClearRequested) {
      payload.network_shares = [];
    } else {
      const nasUser = (nasUsernameInput?.value || "").trim();
      const nasHost = (nasHostInput?.value || "").trim();
      if (nasUser || nasHost || (settings?.network_shares || []).length) {
        payload.network_shares = [
          {
            host: nasHost,
            share: (nasShareInput?.value || "").trim(),
            username: nasUser || settings?.network_shares?.[0]?.username || "",
            password: nasPasswordInput?.value || "",
          },
        ].filter((e) => e.username);
      }
    }
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
      applyTheme(normalizeTheme(data.theme));
      applyCustomBranding(data);
      updateProviderBadge();
      refreshProfileSelect();
      if (nasPasswordInput) nasPasswordInput.value = "";
      nasClearRequested = false;
      const nasEntry = (data.network_shares || [])[0] || null;
      if (hintNas) {
        hintNas.textContent = nasEntry?.configured
          ? `Identifiants enregistrés · ${nasEntry.username}${nasEntry.password_masked ? " · " + nasEntry.password_masked : ""}`
          : "Aucun identifiant NAS enregistré.";
      }
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

  document.getElementById("btn-nas-clear")?.addEventListener("click", () => {
    nasClearRequested = true;
    if (nasHostInput) nasHostInput.value = "";
    if (nasShareInput) nasShareInput.value = "";
    if (nasUsernameInput) nasUsernameInput.value = "";
    if (nasPasswordInput) nasPasswordInput.value = "";
    if (hintNas) hintNas.textContent = "Identifiants effacés (enregistrez pour confirmer).";
    showToast("Identifiants NAS marqués pour suppression.");
  });

  document.getElementById("btn-nas-test")?.addEventListener("click", async () => {
    const host = (nasHostInput?.value || "").trim();
    const share = (nasShareInput?.value || "").trim();
    const username = (nasUsernameInput?.value || "").trim();
    const password = nasPasswordInput?.value || "";
    if (!host || !share || !username) {
      showSettingsMessage("Pour tester : hôte, partage et utilisateur sont requis.", false);
      return;
    }
    showSettingsMessage("Test de connexion NAS…", true);
    try {
      const res = await fetch("/api/network/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ host, share, username, password }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showSettingsMessage(data.error || "Connexion NAS impossible.", false);
        return;
      }
      showSettingsMessage(data.message || "Connexion NAS OK.", true);
      showToast("Connexion NAS OK.");
    } catch (err) {
      showSettingsMessage(`Erreur réseau : ${err?.message || "échec"}`, false);
    }
  });

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
      setHosts(data.hosts || data.host || "");
      renderHistoryInline(item, data);
      showToast("Ouvert sous l’historique.");
    }
  });

  // ─── Onglets ─────────────────────────────────────────────────────────────
  const tabButtons = document.querySelectorAll(".app-tab-btn");
  const tabPanels = {
    extract: document.getElementById("tab-extract"),
    rename: document.getElementById("tab-rename"),
    library: document.getElementById("tab-library"),
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
    if (name === "help") loadChangelog();
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  document.getElementById("btn-help")?.addEventListener("click", () => {
    switchTab("help");
  });

  let changelogLoaded = false;
  async function loadChangelog(force = false) {
    const box = document.getElementById("changelog-content");
    if (!box) return;
    if (changelogLoaded && !force) return;
    try {
      const res = await fetch("/api/changelog");
      const data = await res.json();
      if (!res.ok || !data.html) {
        box.innerHTML = `<p class="library-empty">${escapeHtml(data.error || "Changelog indisponible.")}</p>`;
        return;
      }
      box.innerHTML = data.html;
      changelogLoaded = true;
    } catch {
      box.innerHTML = `<p class="library-empty">Impossible de charger le changelog.</p>`;
    }
  }

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

  // ─── Bibliothèque (phase 1–2 — inventaire + vue arbre) ───────────────────
  const libraryForm = document.getElementById("library-scan-form");
  const libraryFolder = document.getElementById("library-folder");
  const libraryRecursive = document.getElementById("library-recursive");
  const libraryError = document.getElementById("library-error");
  const libraryResults = document.getElementById("library-results");
  const libraryBody = document.getElementById("library-body");
  const librarySummary = document.getElementById("library-results-summary");
  const libraryTree = document.getElementById("library-tree");
  const libraryDupes = document.getElementById("library-dupes");
  const libraryFlatWrap = document.getElementById("library-flat-wrap");
  const librarySearch = document.getElementById("library-search");
  const btnLibraryScan = document.getElementById("btn-library-scan");
  let libraryItems = [];
  let libraryTreeData = null;
  let libraryDupesData = null;
  let libraryFilter = "all";
  let libraryView = "tree";

  function showLibraryError(message) {
    if (!libraryError) return;
    if (!message) {
      libraryError.hidden = true;
      libraryError.textContent = "";
      return;
    }
    libraryError.hidden = false;
    libraryError.textContent = message;
  }

  function setLibraryLoading(loading) {
    if (!btnLibraryScan) return;
    btnLibraryScan.disabled = loading;
    const spinner = btnLibraryScan.querySelector(".btn-spinner");
    const label = btnLibraryScan.querySelector(".btn-label");
    if (spinner) spinner.hidden = !loading;
    if (label) label.textContent = loading ? "Scan…" : "Scanner";
  }

  function formatSe(item) {
    if (item.type === "archive" && item.season_pack && item.season != null && item.episode == null) {
      return `S${String(item.season).padStart(2, "0")} (pack)`;
    }
    if (item.season != null && item.episode != null) {
      return `S${String(item.season).padStart(2, "0")}E${String(item.episode).padStart(2, "0")}`;
    }
    if (item.episode != null) return `E${item.episode}`;
    if (item.season != null) return `S${String(item.season).padStart(2, "0")}`;
    return "—";
  }

  function typeLabel(t, item) {
    if (t === "tv") return "Série";
    if (t === "anime") return "Anime";
    if (t === "movie") return "Film";
    if (t === "archive") {
      const fmt = (item?.archive_format || "zip").toUpperCase();
      if (item?.season_pack) return `Archive ${fmt} (saison)`;
      return `Archive ${fmt}`;
    }
    return "Autre";
  }

  function matchesLibrarySearch(text) {
    const q = (librarySearch?.value || "").trim().toLowerCase();
    if (!q) return true;
    return String(text || "").toLowerCase().includes(q);
  }

  function filteredFlatItems() {
    return libraryItems.filter((item) => {
      if (libraryFilter === "series" && item.type !== "tv" && item.type !== "anime") return false;
      if (libraryFilter === "movies" && item.type !== "movie") return false;
      if (libraryFilter === "archives" && item.type !== "archive") return false;
      const blob = [item.title, item.filename, item.identity, formatSe(item)].join(" ");
      return matchesLibrarySearch(blob);
    });
  }

  function renderLibraryFlat() {
    const rows = filteredFlatItems();
    if (libraryBody) {
      libraryBody.innerHTML = rows.length
        ? rows
            .map(
              (item, i) => `
        <tr class="${item.type === "archive" ? "is-archive" : ""}">
          <td>${i + 1}</td>
          <td>${escapeHtml(typeLabel(item.type, item))}</td>
          <td>${escapeHtml(item.title || "—")}</td>
          <td>${escapeHtml(formatSe(item))}</td>
          <td>${item.year != null ? escapeHtml(String(item.year)) : "—"}</td>
          <td title="${escapeHtml(item.path || "")}">${escapeHtml(item.filename || "")}</td>
          <td><code class="identity-key">${escapeHtml(item.identity || "")}</code></td>
        </tr>`
            )
            .join("")
        : `<tr><td colspan="7" class="library-empty">Aucun résultat pour ce filtre.</td></tr>`;
    }
  }

  function renderLibraryTree() {
    if (!libraryTree) return;
    const tree = libraryTreeData || { series: [], movies: [], archives: [], other: [] };
    const q = (librarySearch?.value || "").trim().toLowerCase();
    const parts = [];

    const showSeries = libraryFilter === "all" || libraryFilter === "series";
    const showMovies = libraryFilter === "all" || libraryFilter === "movies";
    const showArchives = libraryFilter === "all" || libraryFilter === "archives";

    if (showSeries) {
      const series = (tree.series || []).filter((s) => {
        if (!q) return true;
        if ((s.title || "").toLowerCase().includes(q)) return true;
        return (s.seasons || []).some((season) =>
          (season.episodes || []).some((ep) =>
            [ep.filename, ep.identity, formatSe(ep)].join(" ").toLowerCase().includes(q)
          )
        );
      });
      if (series.length) {
        parts.push(`<h3 class="library-section-title">Séries (${series.length})</h3>`);
        for (const s of series) {
          const sid = `lib-ser-${escapeHtml(s.key)}`;
          parts.push(`
            <details class="library-series" open>
              <summary class="library-series-head">
                <span><strong>${escapeHtml(s.title || "Série")}</strong></span>
                <span class="library-series-meta">${s.season_count || 0} saison(s) · ${s.episode_count || 0} ép. · ${s.file_count || 0} fichier(s)</span>
              </summary>
              <div class="library-series-body" id="${sid}">
                ${(s.seasons || [])
                  .map((season) => {
                    const eps = (season.episodes || []).filter((ep) => {
                      if (!q) return true;
                      if ((s.title || "").toLowerCase().includes(q)) return true;
                      return [ep.filename, ep.identity, formatSe(ep)].join(" ").toLowerCase().includes(q);
                    });
                    if (!eps.length && q && !(s.title || "").toLowerCase().includes(q)) return "";
                    const list = eps.length ? eps : season.episodes || [];
                    return `
                    <details class="library-season" open>
                      <summary class="library-season-head">
                        <span>${escapeHtml(season.label || "Saison")}</span>
                        <span class="library-series-meta">${list.length} fichier(s)</span>
                      </summary>
                      <ul class="library-episode-list">
                        ${list
                          .map(
                            (ep) => `
                          <li title="${escapeHtml(ep.path || "")}">
                            <span>${escapeHtml(formatSe(ep))}</span>
                            <span class="ep-file">${escapeHtml(ep.filename || "")}</span>
                          </li>`
                          )
                          .join("")}
                      </ul>
                    </details>`;
                  })
                  .join("")}
              </div>
            </details>`);
        }
      }
    }

    if (showMovies) {
      const movies = (tree.movies || []).filter((m) =>
        matchesLibrarySearch([m.title, m.filename, m.year, m.identity].join(" "))
      );
      if (movies.length) {
        parts.push(`<h3 class="library-section-title">Films (${movies.length})</h3>`);
        for (const m of movies) {
          parts.push(`
            <div class="library-movie-card" title="${escapeHtml(m.path || "")}">
              <div>
                <strong>${escapeHtml(m.title || m.filename || "Film")}</strong>
                ${m.year != null ? ` <span class="library-item-meta">(${escapeHtml(String(m.year))})</span>` : ""}
              </div>
              <span class="library-item-meta">${escapeHtml(m.filename || "")}</span>
            </div>`);
        }
      }
    }

    if (showArchives) {
      const archives = (tree.archives || []).filter((a) =>
        matchesLibrarySearch([a.title, a.filename, formatSe(a), a.identity].join(" "))
      );
      if (archives.length) {
        parts.push(`<h3 class="library-section-title">Archives (${archives.length})</h3>`);
        for (const a of archives) {
          parts.push(`
            <div class="library-archive-card" title="${escapeHtml(a.path || "")}">
              <div>
                <strong>${escapeHtml(a.title || a.filename || "Archive")}</strong>
                <span class="library-item-meta"> · ${escapeHtml(typeLabel("archive", a))} · ${escapeHtml(formatSe(a))}</span>
              </div>
              <span class="library-item-meta">${escapeHtml(a.filename || "")}</span>
            </div>`);
        }
      }
    }

    if (libraryFilter === "all") {
      const others = (tree.other || []).filter((o) =>
        matchesLibrarySearch([o.title, o.filename, o.identity].join(" "))
      );
      if (others.length) {
        parts.push(`<h3 class="library-section-title">Autres (${others.length})</h3>`);
        for (const o of others) {
          parts.push(`
            <div class="library-movie-card" title="${escapeHtml(o.path || "")}">
              <strong>${escapeHtml(o.filename || "Fichier")}</strong>
              <span class="library-item-meta">${escapeHtml(o.title || "")}</span>
            </div>`);
        }
      }
    }

    libraryTree.innerHTML = parts.length
      ? parts.join("")
      : `<p class="library-empty">Aucun résultat pour ce filtre / recherche.</p>`;
  }

  function renderLibraryDupes() {
    if (!libraryDupes) return;
    const data = libraryDupesData || { groups: [], group_count: 0 };
    let groups = data.groups || [];
    const q = (librarySearch?.value || "").trim().toLowerCase();

    groups = groups.filter((g) => {
      if (libraryFilter === "series" && g.type !== "tv" && g.type !== "anime") return false;
      if (libraryFilter === "movies" && g.type !== "movie") return false;
      if (libraryFilter === "archives" && g.type !== "archive") return false;
      if (!q) return true;
      const blob = [
        g.title,
        g.identity,
        ...(g.files || []).map((f) => `${f.filename} ${f.path}`),
      ]
        .join(" ")
        .toLowerCase();
      return blob.includes(q);
    });

    if (!groups.length) {
      libraryDupes.innerHTML = `<p class="library-empty">${
        (data.group_count || 0) === 0
          ? "Aucun doublon détecté — chaque identité n’apparaît qu’une fois."
          : "Aucun doublon pour ce filtre / recherche."
      }</p>`;
      return;
    }

    libraryDupes.innerHTML = `
      <p class="results-summary">${groups.length} groupe(s) · ${groups.reduce((n, g) => n + (g.count || 0), 0)} fichier(s)</p>
      ${groups
        .map((g) => {
          const files = g.files || [];
          return `
        <article class="library-dupe-group ${g.ambiguous ? "is-ambiguous" : ""}">
          <header class="library-dupe-head">
            <div>
              <strong>${escapeHtml(g.title || "Sans titre")}</strong>
              <span class="library-item-meta"> · ${escapeHtml(typeLabel(g.type, files[0]))} · <code class="identity-key">${escapeHtml(g.identity || "")}</code></span>
              ${g.ambiguous ? `<span class="library-dupe-badge" title="Parsing incertain — vérifiez manuellement">À vérifier</span>` : ""}
            </div>
            <span class="library-series-meta">${g.count} fichiers</span>
          </header>
          <ul class="library-dupe-list">
            ${files
              .map(
                (f) => `
              <li>
                <span class="library-dupe-size">${escapeHtml(f.size_label || "—")}</span>
                <div>
                  <div>${escapeHtml(f.filename || "")}${f.ambiguous ? " · <em>ambigu</em>" : ""}</div>
                  <div class="library-dupe-path">${escapeHtml(f.path || "")}</div>
                </div>
              </li>`
              )
              .join("")}
          </ul>
        </article>`;
        })
        .join("")}`;
  }

  function refreshLibraryView() {
    if (libraryView === "tree") {
      if (libraryTree) libraryTree.hidden = false;
      if (libraryDupes) libraryDupes.hidden = true;
      if (libraryFlatWrap) libraryFlatWrap.hidden = true;
      renderLibraryTree();
    } else if (libraryView === "dupes") {
      if (libraryTree) libraryTree.hidden = true;
      if (libraryDupes) libraryDupes.hidden = false;
      if (libraryFlatWrap) libraryFlatWrap.hidden = true;
      renderLibraryDupes();
    } else {
      if (libraryTree) libraryTree.hidden = true;
      if (libraryDupes) libraryDupes.hidden = true;
      if (libraryFlatWrap) libraryFlatWrap.hidden = false;
      renderLibraryFlat();
    }
  }

  function renderLibrary(data) {
    libraryItems = data.items || [];
    libraryTreeData = data.tree || null;
    libraryDupesData = data.duplicates || null;
    const by = data.by_type || {};
    const tree = data.tree || {};
    const dupes = data.duplicates || {};
    if (librarySummary) {
      const arch = data.archive_count || by.archive || 0;
      const packs = data.season_pack_count || 0;
      const dupeGroups = dupes.group_count || 0;
      librarySummary.textContent =
        `${data.count || 0} fichier(s) · ${tree.series_count || 0} série(s) · ${tree.movie_count || by.movie || 0} film(s) · ` +
        `${arch} archive(s)` +
        (packs ? ` (${packs} pack saison)` : "") +
        ` · ${dupeGroups} groupe(s) de doublons` +
        ` · ${data.folder || ""}`;
    }
    if (libraryResults) libraryResults.hidden = false;
    refreshLibraryView();
  }

  document.querySelectorAll(".library-filter").forEach((btn) => {
    btn.addEventListener("click", () => {
      libraryFilter = btn.dataset.libFilter || "all";
      document.querySelectorAll(".library-filter").forEach((b) => {
        b.classList.toggle("is-active", b === btn);
      });
      refreshLibraryView();
    });
  });

  document.querySelectorAll(".library-view").forEach((btn) => {
    btn.addEventListener("click", () => {
      libraryView = btn.dataset.libView || "tree";
      document.querySelectorAll(".library-view").forEach((b) => {
        b.classList.toggle("is-active", b === btn);
      });
      refreshLibraryView();
    });
  });

  librarySearch?.addEventListener("input", () => refreshLibraryView());

  libraryForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const folder = (libraryFolder?.value || "").trim();
    if (!folder) {
      showLibraryError("Indiquez un dossier.");
      return;
    }
    showLibraryError("");
    setLibraryLoading(true);
    const progressEl = document.getElementById("library-scan-progress");
    const progressText = document.getElementById("library-scan-progress-text");
    const progressPct = document.getElementById("library-scan-progress-pct");
    const progressFill = document.getElementById("library-scan-progress-fill");
    const setProg = (percent, message) => {
      const pct = Math.max(0, Math.min(100, Number(percent) || 0));
      if (progressEl) progressEl.hidden = false;
      if (progressFill) progressFill.style.width = `${pct}%`;
      if (progressPct) progressPct.textContent = `${Math.round(pct)} %`;
      if (progressText) progressText.textContent = message || "Scan…";
    };
    const hideProg = () => {
      if (progressEl) progressEl.hidden = true;
      if (progressFill) progressFill.style.width = "0%";
    };
    let pollTimer = null;
    const stopPoll = () => {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };
    setProg(1, "Démarrage du scan…");
    try {
      const res = await fetch("/api/library/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          folder,
          recursive: !!libraryRecursive?.checked,
          background: true,
        }),
      });
      const startData = await res.json().catch(() => ({}));
      if (!res.ok) {
        showLibraryError(startData.error || "Scan impossible.");
        if (libraryResults) libraryResults.hidden = true;
        hideProg();
        setLibraryLoading(false);
        return;
      }
      setProg(startData.percent || 2, startData.message || "Scan en cours…");

      const finish = (state) => {
        stopPoll();
        setLibraryLoading(false);
        if (state?.error) {
          showLibraryError(state.error);
          hideProg();
          if (libraryResults) libraryResults.hidden = true;
          return;
        }
        if (state?.result) {
          setProg(100, "Scan terminé.");
          renderLibrary(state.result);
          showToast(`${state.result.count || 0} média(s) inventorié(s).`);
          setTimeout(hideProg, 800);
        } else {
          showLibraryError("Résultat vide.");
          hideProg();
        }
      };

      pollTimer = setInterval(async () => {
        try {
          const progRes = await fetch("/api/library/scan/progress");
          const state = await progRes.json();
          setProg(state.percent || 0, state.message || "Scan en cours…");
          if (state.done) finish(state);
        } catch (err) {
          stopPoll();
          setLibraryLoading(false);
          showLibraryError(
            `Erreur pendant le suivi du scan : ${err?.message || "réseau"}. ` +
              "Si le NAS demande un login, renseignez-le dans Paramètres → Accès NAS."
          );
          hideProg();
        }
      }, 400);
    } catch (err) {
      showLibraryError(
        `Erreur réseau : ${err?.message || "échec"}. ` +
          "Vérifiez que Linkora tourne, et les identifiants NAS si besoin."
      );
      hideProg();
      setLibraryLoading(false);
    }
  });

  document.getElementById("btn-library-copy")?.addEventListener("click", async () => {
    let text = "";
    if (libraryView === "dupes") {
      const groups = libraryDupesData?.groups || [];
      if (!groups.length) {
        showToast("Aucun doublon à copier.");
        return;
      }
      const blocks = groups.map((g) => {
        const lines = (g.files || []).map(
          (f) => `  ${f.size_label || "-"}\t${f.filename || ""}\t${f.path || ""}`
        );
        return `${g.title || ""} [${g.identity || ""}] (${g.count})\n${lines.join("\n")}`;
      });
      text = blocks.join("\n\n");
    } else {
      const rows = filteredFlatItems();
      if (!rows.length) {
        showToast("Rien à copier.");
        return;
      }
      const lines = rows.map((item) => {
        const se = formatSe(item);
        return [
          typeLabel(item.type, item),
          item.title || "",
          se === "—" ? "" : se,
          item.year != null ? String(item.year) : "",
          item.identity || "",
          item.path || "",
        ].join("\t");
      });
      const header = ["Type", "Titre", "S/E", "Année", "Identité", "Chemin"].join("\t");
      text = [header, ...lines].join("\n");
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast("Liste copiée.");
    } catch {
      showToast("Copie impossible.");
    }
  });

  // ─── Diff PC ↔ NAS (multi-dossiers + progression) ────────────────────────
  const btnLibraryDiff = document.getElementById("btn-library-diff");
  const libraryDiffPcList = document.getElementById("library-diff-pc-list");
  const libraryDiffNasList = document.getElementById("library-diff-nas-list");
  const libraryDiffRecursive = document.getElementById("library-diff-recursive");
  const libraryDiffError = document.getElementById("library-diff-error");
  const libraryDiffResults = document.getElementById("library-diff-results");
  const libraryDiffSummary = document.getElementById("library-diff-summary");
  const libraryDiffBody = document.getElementById("library-diff-body");
  const libraryDiffProgress = document.getElementById("library-diff-progress");
  const libraryDiffProgressText = document.getElementById("library-diff-progress-text");
  const libraryDiffProgressPct = document.getElementById("library-diff-progress-pct");
  const libraryDiffProgressFill = document.getElementById("library-diff-progress-fill");
  let libraryDiffData = null;
  let libraryDiffTab = "missing_b";
  let libraryDiffPollTimer = null;

  function showLibraryDiffError(message) {
    if (!libraryDiffError) return;
    if (!message) {
      libraryDiffError.hidden = true;
      libraryDiffError.textContent = "";
      return;
    }
    libraryDiffError.hidden = false;
    libraryDiffError.textContent = message;
  }

  function setLibraryDiffLoading(loading) {
    if (!btnLibraryDiff) return;
    btnLibraryDiff.disabled = loading;
    const spinner = btnLibraryDiff.querySelector(".btn-spinner");
    const label = btnLibraryDiff.querySelector(".btn-label");
    if (spinner) spinner.hidden = !loading;
    if (label) label.textContent = loading ? "Comparaison…" : "Comparer";
    document.querySelectorAll(".library-path-row input, .library-path-row button, #btn-library-diff-add-pc, #btn-library-diff-add-nas").forEach((el) => {
      el.disabled = loading;
    });
  }

  function setLibraryDiffProgress(percent, message) {
    const pct = Math.max(0, Math.min(100, Number(percent) || 0));
    if (libraryDiffProgress) libraryDiffProgress.hidden = false;
    if (libraryDiffProgressFill) libraryDiffProgressFill.style.width = `${pct}%`;
    if (libraryDiffProgressPct) libraryDiffProgressPct.textContent = `${Math.round(pct)} %`;
    if (libraryDiffProgressText) {
      libraryDiffProgressText.textContent = message || "Comparaison…";
    }
  }

  function hideLibraryDiffProgress() {
    if (libraryDiffProgress) libraryDiffProgress.hidden = true;
    if (libraryDiffProgressFill) libraryDiffProgressFill.style.width = "0%";
  }

  function stopLibraryDiffPoll() {
    if (libraryDiffPollTimer) {
      clearInterval(libraryDiffPollTimer);
      libraryDiffPollTimer = null;
    }
  }

  function addLibraryPathRow(listEl, value = "", placeholder = "") {
    if (!listEl) return;
    const row = document.createElement("div");
    row.className = "library-path-row";
    const input = document.createElement("input");
    input.type = "text";
    input.spellcheck = false;
    input.placeholder = placeholder;
    input.value = value;
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn btn-ghost btn-xs btn-path-remove";
    removeBtn.title = "Retirer";
    removeBtn.setAttribute("aria-label", "Retirer");
    removeBtn.textContent = "×";
    removeBtn.addEventListener("click", () => {
      const rows = listEl.querySelectorAll(".library-path-row");
      if (rows.length <= 1) {
        input.value = "";
        return;
      }
      row.remove();
    });
    row.appendChild(input);
    row.appendChild(removeBtn);
    listEl.appendChild(row);
    return row;
  }

  function collectLibraryPaths(listEl) {
    if (!listEl) return [];
    const paths = [];
    const seen = new Set();
    listEl.querySelectorAll("input").forEach((input) => {
      const value = (input.value || "").trim();
      if (!value) return;
      const key = value.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      paths.push(value);
    });
    return paths;
  }

  function initLibraryDiffPaths() {
    if (libraryDiffPcList && !libraryDiffPcList.children.length) {
      addLibraryPathRow(libraryDiffPcList, "", "D:\\Media\\Series");
    }
    if (libraryDiffNasList && !libraryDiffNasList.children.length) {
      addLibraryPathRow(libraryDiffNasList, "", "\\\\NAS\\Volume1\\Series");
      addLibraryPathRow(libraryDiffNasList, "", "\\\\NAS\\Volume2\\Series");
    }
  }

  document.getElementById("btn-library-diff-add-pc")?.addEventListener("click", () => {
    addLibraryPathRow(libraryDiffPcList, "", "D:\\Media");
  });
  document.getElementById("btn-library-diff-add-nas")?.addEventListener("click", () => {
    addLibraryPathRow(libraryDiffNasList, "", "\\\\NAS\\Media");
  });
  initLibraryDiffPaths();

  function formatDiffLabel(item) {
    const se = formatSe(item);
    const bits = [item.title || item.filename || "—"];
    if (se !== "—") bits.push(se);
    if (item.year != null) bits.push(String(item.year));
    return bits.join(" · ");
  }

  function currentDiffList() {
    if (!libraryDiffData) return [];
    if (libraryDiffTab === "missing_a") return libraryDiffData.missing_on_a || [];
    if (libraryDiffTab === "common") return libraryDiffData.common || [];
    return libraryDiffData.missing_on_b || [];
  }

  function applyLibraryDiffResult(data) {
    libraryDiffData = data;
    const nPc = (data.folders_a || []).length || 1;
    const nNas = (data.folders_b || []).length || 1;
    const warns = [...(data.errors_a || []), ...(data.errors_b || [])];
    if (libraryDiffSummary) {
      libraryDiffSummary.textContent =
        `${nPc} dossier(s) PC · ${nNas} NAS · ` +
        `${data.identities_a || 0} identité(s) PC · ${data.identities_b || 0} NAS · ` +
        `${data.missing_on_b_count || 0} manquant(s) sur NAS · ` +
        `${data.missing_on_a_count || 0} manquant(s) sur PC · ` +
        `${data.common_count || 0} commun(s)` +
        (warns.length ? ` · ${warns.length} avertissement(s)` : "");
    }
    if (warns.length) {
      showLibraryDiffError("Certains dossiers n’ont pas pu être scannés : " + warns.join(" | "));
    }
    if (libraryDiffResults) libraryDiffResults.hidden = false;
    renderLibraryDiff();
  }

  function renderLibraryDiff() {
    if (!libraryDiffBody || !libraryDiffData) return;
    const labelA = libraryDiffData.label_a || "PC";
    const labelB = libraryDiffData.label_b || "NAS";
    const list = currentDiffList();

    if (libraryDiffTab === "common") {
      libraryDiffBody.innerHTML = list.length
        ? list
            .map((row) => {
              const a = row.a || {};
              const b = row.b || {};
              return `
            <div class="library-diff-row">
              <span class="library-dupe-size">OK</span>
              <div>
                <strong>${escapeHtml(row.title || row.identity || "")}</strong>
                <div class="diff-meta">${escapeHtml(labelA)}: ${escapeHtml(a.path || a.filename || "")}</div>
                <div class="diff-meta">${escapeHtml(labelB)}: ${escapeHtml(b.path || b.filename || "")}</div>
                <div class="diff-meta"><code class="identity-key">${escapeHtml(row.identity || "")}</code></div>
              </div>
            </div>`;
            })
            .join("")
        : `<p class="library-empty">Aucun élément commun.</p>`;
      return;
    }

    const sideLabel = libraryDiffTab === "missing_a" ? labelB : labelA;
    libraryDiffBody.innerHTML = list.length
      ? list
          .map(
            (item) => `
          <div class="library-diff-row" title="${escapeHtml(item.path || "")}">
            <span class="library-dupe-size">${escapeHtml(item.size_label || "—")}</span>
            <div>
              <strong>${escapeHtml(formatDiffLabel(item))}</strong>
              <div class="diff-meta">${escapeHtml(typeLabel(item.type, item))} · ${escapeHtml(sideLabel)}</div>
              <div class="diff-meta">${escapeHtml(item.path || "")}</div>
              <div class="diff-meta"><code class="identity-key">${escapeHtml(item.identity || "")}</code></div>
            </div>
          </div>`
          )
          .join("")
      : `<p class="library-empty">Aucun élément dans cette liste.</p>`;
  }

  document.querySelectorAll(".library-diff-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      libraryDiffTab = btn.dataset.diffTab || "missing_b";
      document.querySelectorAll(".library-diff-tab").forEach((b) => {
        b.classList.toggle("is-active", b === btn);
      });
      renderLibraryDiff();
    });
  });

  btnLibraryDiff?.addEventListener("click", async () => {
    const foldersA = collectLibraryPaths(libraryDiffPcList);
    const foldersB = collectLibraryPaths(libraryDiffNasList);
    if (!foldersA.length || !foldersB.length) {
      showLibraryDiffError("Indiquez au moins un dossier PC et un dossier NAS.");
      return;
    }
    showLibraryDiffError("");
    stopLibraryDiffPoll();
    setLibraryDiffLoading(true);
    setLibraryDiffProgress(1, "Démarrage de la comparaison…");
    if (libraryDiffResults) libraryDiffResults.hidden = true;

    try {
      const res = await fetch("/api/library/diff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          folders_a: foldersA,
          folders_b: foldersB,
          recursive: !!libraryDiffRecursive?.checked,
          label_a: "PC",
          label_b: "NAS",
          background: true,
        }),
      });
      const startData = await res.json();
      if (!res.ok) {
        showLibraryDiffError(startData.error || "Comparaison impossible.");
        hideLibraryDiffProgress();
        setLibraryDiffLoading(false);
        return;
      }
      setLibraryDiffProgress(startData.percent || 2, startData.message || "Scan en cours…");

      const finish = (state) => {
        stopLibraryDiffPoll();
        setLibraryDiffLoading(false);
        if (state?.error) {
          showLibraryDiffError(state.error);
          hideLibraryDiffProgress();
          return;
        }
        if (state?.result) {
          setLibraryDiffProgress(100, "Comparaison terminée.");
          applyLibraryDiffResult(state.result);
          showToast("Comparaison terminée.");
          setTimeout(hideLibraryDiffProgress, 800);
        } else {
          showLibraryDiffError("Résultat vide.");
          hideLibraryDiffProgress();
        }
      };

      libraryDiffPollTimer = setInterval(async () => {
        try {
          const progRes = await fetch("/api/library/diff/progress");
          const state = await progRes.json();
          setLibraryDiffProgress(state.percent || 0, state.message || "Scan en cours…");
          if (state.done) finish(state);
        } catch {
          stopLibraryDiffPoll();
          setLibraryDiffLoading(false);
          showLibraryDiffError("Erreur réseau pendant le suivi de progression.");
          hideLibraryDiffProgress();
        }
      }, 400);
    } catch {
      showLibraryDiffError("Erreur réseau.");
      hideLibraryDiffProgress();
      setLibraryDiffLoading(false);
    }
  });

  document.getElementById("btn-library-diff-copy")?.addEventListener("click", async () => {
    const list = currentDiffList();
    if (!list.length) {
      showToast("Rien à copier.");
      return;
    }
    let text = "";
    if (libraryDiffTab === "common") {
      text = list
        .map((row) => {
          const a = row.a || {};
          const b = row.b || {};
          return `${row.title || ""}\t${row.identity || ""}\t${a.path || ""}\t${b.path || ""}`;
        })
        .join("\n");
    } else {
      text = list
        .map((item) => `${formatDiffLabel(item)}\t${item.identity || ""}\t${item.path || ""}`)
        .join("\n");
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast("Liste diff copiée.");
    } catch {
      showToast("Copie impossible.");
    }
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
          <td>${i + 1}</td>
          <td class="cell-filename" title="${escapeHtml(item.original)}">${escapeHtml(item.original)}</td>
          <td>→</td>
          <td class="cell-filename" title="${escapeHtml(item.suggested)}">${escapeHtml(item.suggested)}</td>
          <td><span class="size-pill">${escapeHtml(item.type || "—")}</span></td>
          <td><span class="status-pill ${statusCls}">${status}</span></td>
          <td class="col-check">
            <input type="checkbox" class="rename-check" data-rename-index="${i}" checked aria-label="Inclure ${escapeHtml(item.original)}">
          </td>
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

  btnAddHost?.addEventListener("click", () => addHostRow(""));
  hostsList?.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-remove-host]");
    if (!btn) return;
    const row = btn.closest("[data-host-row]");
    if (!row || !hostsList.contains(row)) return;
    if (hostsList.querySelectorAll("[data-host-row]").length <= 1) return;
    row.remove();
    hostsList.querySelectorAll("[data-host-row]").forEach((r, idx) => {
      const label = r.querySelector(".field-label");
      if (label) label.textContent = idx === 0 ? "Hébergeur" : `Hébergeur ${idx + 1}`;
    });
    syncAddHostButton();
  });
  syncAddHostButton();

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
      if (prof?.hosts?.length) setHosts(prof.hosts);
      else if (prof?.host) setHosts(prof.host);
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
    const hosts = getHosts();
    const payloadProfile = {
      id: existingId || undefined,
      name: trimmed,
      host: hosts[0] || "",
      hosts,
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
    const hosts = getHosts();
    if (!hosts.length) {
      showToast("Indiquez au moins un hébergeur.");
      return;
    }
    const host = hostsLabel(hosts);
    let added = 0;
    for (const url of lines) {
      if (workQueue.some((q) => q.url === url && q.host === host)) continue;
      workQueue.push({ url, host, hosts, status: "pending", error: "" });
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
    assignMultiHostRoles();
    syncFlatLinks();
    refreshCurrentView({ scroll: false });
    const result = await resolveWithMultiHostFallback(provider, "File — résolution…");
    syncFlatLinks();
    current.resolved_provider = provider;
    updateSummary();
    await autoSaveHistory(current);
    setResolving(false);
    if (!result.total) {
      return { ok: 0, total: 0, providerName, skipped: true };
    }
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
    const hosts = getHosts();
    if (!hosts.length && workQueue.some((q) => !(q.hosts?.length || q.host))) {
      showToast("Indiquez au moins un hébergeur.");
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
          const itemHosts = item.hosts?.length
            ? item.hosts
            : parseHostsValue(item.host || hosts);
          const res = await fetch("/api/extract", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              urls: item.url,
              hosts: itemHosts,
              host: itemHosts[0] || "",
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
            host: data.host || hostsLabel(itemHosts),
            hosts: itemHosts,
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

  function openUpdateProgress() {
    if (updateBanner) updateBanner.hidden = true;
    if (updateProgressModal) updateProgressModal.hidden = false;
    setUpdateProgressUI({ percent: 1, progress_message: "Démarrage…" });
  }

  function closeUpdateProgress() {
    if (updateProgressModal) updateProgressModal.hidden = true;
    if (updateProgressTimer) {
      clearInterval(updateProgressTimer);
      updateProgressTimer = null;
    }
  }

  function setUpdateProgressUI(state) {
    const pct = Math.max(0, Math.min(100, Number(state?.percent) || 0));
    const text =
      state?.progress_message ||
      state?.message ||
      state?.error ||
      "Mise à jour…";
    if (updateProgressText) updateProgressText.textContent = text;
    if (updateProgressFill) updateProgressFill.style.width = `${pct}%`;
    if (updateProgressPct) updateProgressPct.textContent = `${Math.round(pct)} %`;
  }

  async function runUpdateWithProgress() {
    openUpdateProgress();
    try {
      await fetch("/api/update/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
    } catch {
      /* le serveur peut couper à la fin — on continue le poll */
    }

    if (updateProgressTimer) clearInterval(updateProgressTimer);
    updateProgressTimer = setInterval(async () => {
      try {
        const res = await fetch("/api/update/progress");
        const state = await res.json();
        setUpdateProgressUI(state);
        if (state.error && state.done) {
          clearInterval(updateProgressTimer);
          updateProgressTimer = null;
          showToast(state.error);
          closeUpdateProgress();
          showUpdateBanner(state);
          return;
        }
        if (state.restarting) {
          setUpdateProgressUI({
            percent: 100,
            progress_message: "Redémarrage de Linkora…",
          });
          // L’app va se fermer toute seule
          return;
        }
        if (state.done && !state.busy) {
          clearInterval(updateProgressTimer);
          updateProgressTimer = null;
          closeUpdateProgress();
          showUpdateBanner(state);
          showToast(state.message || "Mise à jour terminée.");
        }
      } catch {
        // Serveur coupé = redémarrage en cours
        setUpdateProgressUI({
          percent: 100,
          progress_message: "Redémarrage de Linkora…",
        });
      }
    }, 350);
  }

  btnUpdateApply?.addEventListener("click", () => {
    runUpdateWithProgress();
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

  btnForceUpdate?.addEventListener("click", () => {
    runUpdateWithProgress();
  });
})();
