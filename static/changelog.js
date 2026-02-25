// static/changelog.js
// Tema + logout para changelog.html

(function () {
  const THEME_KEY = "theme";

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

  function applyTheme(mode) {
    const root = document.documentElement;
    if (mode === "system") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", mode);
    }
  }

  const mode = getStoredTheme();
  if (mode === "system") {
    applyTheme(systemPrefersLight() ? "light" : "dark");
    const mql = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;
    if (mql) {
      const handler = () => applyTheme(systemPrefersLight() ? "light" : "dark");
      if (mql.addEventListener) mql.addEventListener("change", handler);
      else if (mql.addListener) mql.addListener(handler);
    }
  } else {
    applyTheme(mode);
  }

  const btn = document.getElementById("btnLogout");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    try {
      await fetch("/logout", { method: "POST" });
    } catch (_) {}
    window.location.href = "/login";
  });
})();
