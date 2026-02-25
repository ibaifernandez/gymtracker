// static/login.js
// Aplica tema guardado en login.

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

  const mode = getStoredTheme();
  const root = document.documentElement;
  if (mode === "system") {
    if (systemPrefersLight()) root.setAttribute("data-theme", "light");
    else root.setAttribute("data-theme", "dark");
  } else {
    root.setAttribute("data-theme", mode);
  }
})();
