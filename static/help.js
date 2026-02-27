// static/help.js
// Buscador + UX mínima para help.html (local, sin dependencias)

(function () {
  function getCsrfToken() {
    return String(document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "").trim();
  }

  // ----------------------------
  // Theme (respeta selección del usuario)
  // ----------------------------
  const THEME_KEY = "theme"; // "light" | "dark" | "system"

  function systemPrefersLight() {
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches);
  }

  function getStoredTheme() {
    try {
      const v = localStorage.getItem(THEME_KEY);
      if (v === "light" || v === "dark" || v === "system") return v;
    } catch (_) {}
    return "system";
  }

  function setStoredTheme(v) {
    try {
      localStorage.setItem(THEME_KEY, v);
    } catch (_) {}
  }

  function effectiveTheme(mode) {
    if (mode === "system") return systemPrefersLight() ? "light" : "dark";
    return mode;
  }

  function updateThemeLabel(mode) {
    const label = document.getElementById("themeLabel");
    if (!label) return;
    const eff = effectiveTheme(mode);
    const nextTxt = eff === "light" ? "Oscuro" : "Claro";
    label.textContent = `Tema: ${nextTxt}`;
  }

  function applyTheme(mode) {
    const root = document.documentElement;
    if (mode === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", mode);
    updateThemeLabel(mode);
  }

  applyTheme(getStoredTheme());

  // Si está en system, reacciona a cambios del sistema
  const mql = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;
  if (mql) {
    const handler = () => {
      if (getStoredTheme() === "system") applyTheme("system");
    };
    if (mql.addEventListener) mql.addEventListener("change", handler);
    else if (mql.addListener) mql.addListener(handler);
  }

  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const stored = getStoredTheme();
      const eff = effectiveTheme(stored);
      const next = eff === "light" ? "dark" : "light";
      setStoredTheme(next);
      applyTheme(next);
    });
    themeToggle.addEventListener("mouseenter", () => {
      const stored = getStoredTheme();
      const eff = effectiveTheme(stored);
      themeToggle.setAttribute("aria-label", eff === "light" ? "Cambiar a oscuro" : "Cambiar a claro");
    });
  }

  // ----------------------------
  // Header menu (mobile)
  // ----------------------------
  const menuToggle = document.getElementById("menuToggle");
  const topActions = document.getElementById("topActions");
  const mobileMenuMql = window.matchMedia ? window.matchMedia("(max-width: 920px)") : null;

  function setTopMenuOpen(open) {
    if (!menuToggle || !topActions) return;
    const next = !!open;
    topActions.classList.toggle("is-open", next);
    menuToggle.classList.toggle("is-open", next);
    menuToggle.setAttribute("aria-expanded", next ? "true" : "false");
    menuToggle.setAttribute("aria-label", next ? "Cerrar menú principal" : "Abrir menú principal");
  }

  function closeTopMenu() {
    setTopMenuOpen(false);
  }

  function syncTopMenuViewport() {
    if (!menuToggle || !topActions) return;
    if (!mobileMenuMql || mobileMenuMql.matches) return;
    topActions.classList.remove("is-open");
    menuToggle.classList.remove("is-open");
    menuToggle.setAttribute("aria-expanded", "false");
    menuToggle.setAttribute("aria-label", "Abrir menú principal");
  }

  if (menuToggle && topActions) {
    menuToggle.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isOpen = topActions.classList.contains("is-open");
      setTopMenuOpen(!isOpen);
    });

    topActions.addEventListener("click", (e) => {
      if (!mobileMenuMql || !mobileMenuMql.matches) return;
      const trigger = e.target.closest(".btn, a");
      if (trigger) closeTopMenu();
    });

    document.addEventListener("click", (e) => {
      if (!mobileMenuMql || !mobileMenuMql.matches) return;
      if (!topActions.classList.contains("is-open")) return;
      const target = e.target;
      if (menuToggle.contains(target) || topActions.contains(target)) return;
      closeTopMenu();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeTopMenu();
    });

    if (mobileMenuMql) {
      const onChange = () => syncTopMenuViewport();
      if (mobileMenuMql.addEventListener) mobileMenuMql.addEventListener("change", onChange);
      else if (mobileMenuMql.addListener) mobileMenuMql.addListener(onChange);
    }
    syncTopMenuViewport();
  }

  // ----------------------------
  // Help UI
  // ----------------------------
  const $ = (id) => document.getElementById(id);
  const logoutBtn = $("btnLogout");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        const token = getCsrfToken();
        const headers = token ? { "X-CSRF-Token": token } : {};
        await fetch("/logout", { method: "POST", headers });
      } catch (_) {}
      window.location.href = "/login";
    });
  }

  const reportBugBtn = $("btnReportBug");
  if (reportBugBtn) {
    reportBugBtn.addEventListener("click", () => {
      window.location.href = "/#data";
    });
  }

  const input = $("helpSearch");
  if (!input) return;

  const panels = Array.from(document.querySelectorAll("details.panel"));

  function norm(s) {
    return (s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function panelText(p) {
    const k = p.getAttribute("data-keywords") || "";
    const t = p.innerText || "";
    return norm(k + " " + t);
  }

  function applyFilter(qRaw) {
    const q = norm(qRaw).trim();
    if (!q) {
      panels.forEach((p) => {
        p.style.display = "";
      });
      return;
    }

    panels.forEach((p) => {
      const hay = panelText(p);
      const ok = hay.includes(q);
      p.style.display = ok ? "" : "none";
      if (ok) p.open = true;
    });
  }

  function openHash() {
    const hash = (location.hash || "").replace("#", "");
    if (!hash) return;

    const target = document.getElementById(hash);
    if (target && target.matches("details.panel")) {
      target.open = true;
      setTimeout(() => {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    }
  }

  window.addEventListener("hashchange", openHash);
  input.addEventListener("input", (e) => applyFilter(e.target.value));

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      input.value = "";
      applyFilter("");
      input.blur();
    }
  });

  openHash();
})();
