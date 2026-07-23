/**
 * Linkora i18n — chargement JSON + application DOM (data-i18n*).
 */
(function (global) {
  const SUPPORTED = ["fr", "en"];
  const DEFAULT_LOCALE = "fr";

  let catalog = {};
  let current = DEFAULT_LOCALE;

  function getByPath(obj, path) {
    if (!obj || !path) return undefined;
    const parts = String(path).split(".");
    let cur = obj;
    for (const p of parts) {
      if (cur == null || typeof cur !== "object") return undefined;
      cur = cur[p];
    }
    return cur;
  }

  function interpolate(str, vars) {
    if (!vars || typeof str !== "string") return str;
    return str.replace(/\{(\w+)\}/g, (_, key) =>
      vars[key] != null ? String(vars[key]) : `{${key}}`
    );
  }

  function t(key, vars) {
    const raw = getByPath(catalog, key);
    if (typeof raw !== "string") return key;
    return interpolate(raw, vars);
  }

  function applyAttrs(el) {
    const textKey = el.getAttribute("data-i18n");
    if (textKey) {
      const val = t(textKey);
      if (val !== textKey) el.textContent = val;
    }
    const htmlKey = el.getAttribute("data-i18n-html");
    if (htmlKey) {
      const val = t(htmlKey);
      if (val !== htmlKey) el.innerHTML = val;
    }
    const titleKey = el.getAttribute("data-i18n-title");
    if (titleKey) {
      const val = t(titleKey);
      if (val !== titleKey) el.setAttribute("title", val);
    }
    const phKey = el.getAttribute("data-i18n-placeholder");
    if (phKey) {
      const val = t(phKey);
      if (val !== phKey) el.setAttribute("placeholder", val);
    }
    const ariaKey = el.getAttribute("data-i18n-aria");
    if (ariaKey) {
      const val = t(ariaKey);
      if (val !== ariaKey) el.setAttribute("aria-label", val);
    }
  }

  function applyDom(root) {
    const scope = root || document;
    scope.querySelectorAll(
      "[data-i18n], [data-i18n-html], [data-i18n-title], [data-i18n-placeholder], [data-i18n-aria]"
    ).forEach(applyAttrs);

    document.documentElement.lang = current === "en" ? "en" : "fr";
    document.querySelectorAll("[data-locale-set]").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.localeSet === current);
    });
  }

  async function loadLocale(locale) {
    const loc = SUPPORTED.includes(locale) ? locale : DEFAULT_LOCALE;
    const res = await fetch(`/static/i18n/${loc}.json`, { cache: "no-cache" });
    if (!res.ok) throw new Error(`i18n ${loc}: ${res.status}`);
    catalog = await res.json();
    current = loc;
    return catalog;
  }

  async function setLocale(locale, { apply = true } = {}) {
    await loadLocale(locale);
    if (apply) applyDom();
    return current;
  }

  function getLocale() {
    return current;
  }

  global.LinkoraI18n = {
    SUPPORTED,
    DEFAULT_LOCALE,
    t,
    applyDom,
    loadLocale,
    setLocale,
    getLocale,
  };
})(typeof window !== "undefined" ? window : globalThis);
