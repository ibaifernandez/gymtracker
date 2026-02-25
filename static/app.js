// static/app.js
(() => {
  const $ = (id) => document.getElementById(id);
  const on = (id, event, handler, opts) => {
    const node = $(id);
    if (node) node.addEventListener(event, handler, opts);
    return node;
  };

  // ----------------------------
  // Theme toggle (GUI)
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
    const label = $("themeLabel");
    if (!label) return;

    const eff = effectiveTheme(mode);
    const nextTxt = eff === "light" ? "Oscuro" : "Claro";
    label.textContent = `Tema: ${nextTxt}`;
  }

  function applyTheme(mode) {
    const root = document.documentElement;
    const eff = effectiveTheme(mode);
    root.setAttribute("data-theme", eff);
    root.setAttribute("data-theme-mode", mode);
    updateThemeLabel(mode);
  }

  const initialTheme = getStoredTheme();
  applyTheme(initialTheme);

  const mql = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;
  if (mql) {
    const handler = () => {
      if (getStoredTheme() === "system") applyTheme("system");
    };
    if (mql.addEventListener) mql.addEventListener("change", handler);
    else if (mql.addListener) mql.addListener(handler);
  }

  const themeToggle = on("themeToggle", "click", () => {
    const stored = getStoredTheme();
    const eff = effectiveTheme(stored);
    const next = eff === "light" ? "dark" : "light";
    setStoredTheme(next);
    applyTheme(next);
  });

  if (themeToggle) {
    themeToggle.addEventListener("mouseenter", () => {
      const stored = getStoredTheme();
      const eff = effectiveTheme(stored);
      themeToggle.setAttribute("aria-label", eff === "light" ? "Cambiar a oscuro" : "Cambiar a claro");
    });
  }

  // ----------------------------
  // Guard clause: index only
  // ----------------------------
  const initialStateNode = $("initial-state");
  if (!initialStateNode) return;

  let INITIAL_STATE = { summary: {}, diet: [], workout: [] };
  try {
    const raw = (initialStateNode.textContent || "").trim();
    if (raw) INITIAL_STATE = JSON.parse(raw);
  } catch (_) {}

  // ----------------------------
  // Nodes / state
  // ----------------------------
  const dietModal = $("dietModal");
  const workoutModal = $("workoutModal");
  const importDietModal = $("importDietModal");
  const planImportModal = $("planImportModal");
  const planAiWorkflowModal = $("planAiWorkflowModal");
  const photoLightbox = $("photoLightbox");
  const replaceConfirmModal = $("replaceConfirmModal");

  const toast = $("toast");
  const toastT1 = $("toastT1");
  const toastT2 = $("toastT2");
  const toastHomeParent = toast ? toast.parentElement : null;
  const toastHomeNext = toast ? toast.nextSibling : null;

  const dietTable = $("dietTable");
  const workTable = $("workTable");
  const dietCountMeta = $("dietCountMeta");
  const workCountMeta = $("workCountMeta");

  const dietForm = $("dietForm");
  const workForm = $("workForm");
  const workSessionType = $("work_session_type");
  const workDoneSelect = $("work_done_select");
  const workClassField = $("workClassField");
  const workClassLabel = $("workClassLabel");
  const workStrengthBlock = $("workStrengthBlock");
  const workSessionId = $("workSessionId");
  const workExercisesJson = $("workExercisesJson");
  const workExerciseList = $("workExerciseList");
  const workExerciseTemplate = $("workExerciseTemplate");
  const workAddExerciseBtn = $("workAddExerciseBtn");
  const workDoneButtons = Array.from(document.querySelectorAll("[data-work-done-value]"));
  const summaryFrom = $("summaryFrom");
  const summaryTo = $("summaryTo");
  const summaryModeSelect = $("summaryModeSelect");
  const summaryRangeFields = $("summaryRangeFields");
  const summaryApplyBtn = $("summaryApplyBtn");
  const summaryCaption = $("summaryCaption");
  const menuToggle = $("menuToggle");
  const topActions = $("topActions");
  const trendTitle = $("trendTitle");
  const trendText = $("trendText");
  const trendDelta = $("trendDelta");
  const perfChart = $("perfChart");
  const perfChartWrap = perfChart ? perfChart.closest(".performance-chart-wrap") : null;
  const perfEmpty = $("perfEmpty");
  const perfFoot = $("perfFoot");
  const perfSub = $("perfSub");
  const perfMetricTabs = $("perfMetricTabs");
  const perfModeSelect = $("perfModeSelect");
  const perfRangeFields = $("perfRangeFields");
  const perfFrom = $("perfFrom");
  const perfTo = $("perfTo");
  const perfApplyBtn = $("perfApplyBtn");
  const shareReportBtn = $("shareReportBtn");
  const exportReportBtn = $("exportReportBtn");
  const exportReportPdfBtn = $("exportReportPdfBtn");
  const copyReportBtn = $("copyReportBtn");
  const syncStatus = $("syncStatus");
  const kpiSleepTitle = $("kpiSleepTitle");
  const kpiStepsTitle = $("kpiStepsTitle");
  const kpiWeightTitle = $("kpiWeightTitle");
  const kpiWHRTitle = $("kpiWHRTitle");
  const kSleepPeriod = $("kSleepPeriod");
  const kStepsPeriod = $("kStepsPeriod");
  const kWeightPeriod = $("kWeightPeriod");
  const kWHRPeriod = $("kWHRPeriod");
  const kSleepDelta = $("kSleepDelta");
  const kStepsDelta = $("kStepsDelta");
  const kWeightDelta = $("kWeightDelta");
  const kWHRDelta = $("kWHRDelta");

  const photoFile = $("photoFile");
  const photoPreview = $("photoPreview");
  const photoMeta = $("photoMeta");
  const photoClear = $("photoClear");
  const photoYN = $("photoYN");
  const photoReplaceConfirm = $("photoReplaceConfirm");
  const dietEntryMode = $("dietEntryMode");
  const dietDeleteBtn = $("dietDeleteBtn");
  const workEntryMode = $("workEntryMode");
  const workDeleteBtn = $("workDeleteBtn");
  const photoExistingWrap = $("photoExistingWrap");
  const photoExistingBtn = $("photoExistingBtn");
  const dietFormAlert = $("dietFormAlert");

  const lightboxImg = $("lightboxImg");
  const lightboxCaption = $("lightboxCaption");
  const lightboxThumbs = $("lightboxThumbs");
  const lightboxCount = $("lightboxCount");
  const lightboxPrev = $("lightboxPrev");
  const lightboxNext = $("lightboxNext");
  const lightboxDownload = $("lightboxDownload");
  const lightboxMetaTag = $("lightboxMetaTag");
  const lightboxMetaDetails = $("lightboxMetaDetails");
  const lightboxCompareToggle = $("lightboxCompareToggle");
  const lightboxCompareWrap = $("lightboxCompareWrap");
  const lightboxCompareLabel = $("lightboxCompareLabel");
  const lightboxCompareSelect = $("lightboxCompareSelect");
  const compareBeforeImg = $("compareBeforeImg");
  const compareBeforeLabel = $("compareBeforeLabel");
  const compareAfterImg = $("compareAfterImg");
  const compareAfterLabel = $("compareAfterLabel");
  const lightboxShell = photoLightbox ? photoLightbox.querySelector(".lightbox-shell") : null;

  const replaceConfirmText = $("replaceConfirmText");
  const replaceConfirmImg = $("replaceConfirmImg");

  const importDietForm = $("importDietForm");
  const importDietFile = $("importDietFile");
  const importDietSummary = $("importDietSummary");
  const importPreviewWrap = $("importPreviewWrap");
  const importPreviewBody = $("importPreviewBody");
  const importApplyBtn = $("importApplyBtn");
  const planImportSummary = $("planImportSummary");
  const planImportFeedback = $("planImportFeedback");
  const planImportHuman = $("planImportHuman");
  const planImportGroups = $("planImportGroups");
  const planImportDetailWrap = $("planImportDetailWrap");
  const planImportDetailBody = $("planImportDetailBody");
  const planImportDownloadDetailBtn = $("planImportDownloadDetailBtn");
  const planDietFile = $("planDietFile");
  const planWorkoutFile = $("planWorkoutFile");
  const planAiPromptText = $("planAiPromptText");

  const planDayDate = $("planDayDate");
  const planHubSub = $("planHubSub");
  const planDietMacros = $("planDietMacros");
  const planDietMeals = $("planDietMeals");
  const planWorkoutSummary = $("planWorkoutSummary");
  const planWorkoutSessions = $("planWorkoutSessions");
  const planDeleteDietDayBtn = $("planDeleteDietDayBtn");
  const planFlushDietBtn = $("planFlushDietBtn");
  const planFlushWorkoutBtn = $("planFlushWorkoutBtn");
  const planDietActualPill = $("planDietActualPill");
  const planWorkoutActualPill = $("planWorkoutActualPill");
  const planDietScore = $("planDietScore");
  const planWorkoutScore = $("planWorkoutScore");
  const planAdherenceNotes = $("planAdherenceNotes");
  const planAdherenceWindow = $("planAdherenceWindow");
  const planAdherencePeriod = $("planAdherencePeriod");
  const planAdherenceHistoryList = $("planAdherenceHistoryList");

  const suppCatalogForm = $("suppCatalogForm");
  const suppCatalogTable = $("suppCatalogTable");
  const suppDayForm = $("suppDayForm");
  const suppDayTable = $("suppDayTable");
  const suppDayDate = $("suppDayDate");
  const suppDayTotals = $("suppDayTotals");
  const suppCancelEditBtn = $("suppCancelEditBtn");
  const suppHistoryTable = $("suppHistoryTable");
  const suppLimitSelect = $("suppLimitSelect");
  const suppLimitLabel = $("suppLimitLabel");
  const suppCountMeta = $("suppCountMeta");
  const suppSearch = $("suppSearch");
  const suppDayModal = $("suppDayModal");
  const suppCatalogModal = $("suppCatalogModal");
  const suppDayDeleteBtn = $("suppDayDeleteBtn");
  const suppCatalogAlert = $("suppCatalogAlert");

  const backupRestoreModal = $("backupRestoreModal");
  const backupRestoreForm = $("backupRestoreForm");
  const backupRestoreFile = $("backupRestoreFile");
  const backupRestoreConfirm = $("backupRestoreConfirm");
  const reportBugModal = $("reportBugModal");
  const reportBugText = $("reportBugText");
  const dietLimitSelect = $("dietLimitSelect");
  const workLimitSelect = $("workLimitSelect");
  const fabMain = $("fabMain");
  const fabMenu = $("fabMenu");
  const viewButtons = Array.from(document.querySelectorAll("[data-view-target]"));
  const appViews = Array.from(document.querySelectorAll(".app-view[data-view]"));
  const helpTipPopover = $("helpTipPopover");
  const helpTipTitle = $("helpTipTitle");
  const helpTipText = $("helpTipText");
  const helpTipLink = $("helpTipLink");
  const helpTipTriggers = Array.from(document.querySelectorAll("[data-help-tip]"));

  const LIMIT_CHOICES = [7, 15, 30, 60, 90];
  const PLAN_ADHERENCE_WINDOW_CHOICES = [7, 15, 30];
  function parseLimitValue(raw, fallback = 15) {
    const n = Number(raw);
    if (Number.isInteger(n) && LIMIT_CHOICES.includes(n)) return n;
    return fallback;
  }
  function parsePlanAdherenceWindow(raw, fallback = 15) {
    const n = Number(raw);
    if (Number.isInteger(n) && PLAN_ADHERENCE_WINDOW_CHOICES.includes(n)) return n;
    if (PLAN_ADHERENCE_WINDOW_CHOICES.includes(Number(fallback))) return Number(fallback);
    return 15;
  }
  function isSummaryCustomMode() {
    return String(summaryModeSelect?.value || "7") === "custom";
  }
  function isPerfCustomMode() {
    return String(perfModeSelect?.value || "7") === "custom";
  }
  function syncSummaryAnalysisUI() {
    const custom = isSummaryCustomMode();
    if (summaryRangeFields) summaryRangeFields.hidden = !custom;
    if (summaryFrom) summaryFrom.required = custom;
    if (summaryTo) summaryTo.required = custom;
    if (summaryApplyBtn) {
      summaryApplyBtn.hidden = !custom;
      summaryApplyBtn.disabled = !custom;
      summaryApplyBtn.setAttribute("aria-hidden", custom ? "false" : "true");
    }
  }
  function syncPerfAnalysisUI() {
    const custom = isPerfCustomMode();
    if (perfRangeFields) perfRangeFields.hidden = !custom;
    if (perfFrom) perfFrom.required = custom;
    if (perfTo) perfTo.required = custom;
    if (perfApplyBtn) {
      perfApplyBtn.hidden = !custom;
      perfApplyBtn.disabled = !custom;
      perfApplyBtn.setAttribute("aria-hidden", custom ? "false" : "true");
    }
  }
  let dietLimit = parseLimitValue(dietLimitSelect?.value, 15);
  let workLimit = parseLimitValue(workLimitSelect?.value, 15);
  let summaryWindowDays = parseLimitValue(summaryModeSelect?.value, 7);
  let currentDietRows = Array.isArray(INITIAL_STATE.diet) ? [...INITIAL_STATE.diet] : [];
  let currentWorkoutRows = Array.isArray(INITIAL_STATE.workout) ? [...INITIAL_STATE.workout] : [];
  let previewObjectURL = "";
  let pendingReplaceAction = null;
  let importPreviewRows = [];
  let suppCatalogRows = [];
  let suppDayRows = [];
  let suppHistoryRows = [];
  let suppLimit = parseLimitValue(suppLimitSelect?.value, 15);
  let currentPlanDay = INITIAL_STATE.plan_today || null;
  let planAdherenceWindowDays = parsePlanAdherenceWindow(
    INITIAL_STATE.plan_today?.adherence_history?.window_days,
    15
  );
  let planImportDetailRows = [];
  let summaryRangeFrom = "";
  let summaryRangeTo = "";
  let latestSummary = INITIAL_STATE.summary || {};
  let chartMetric = "weight_kg";
  let perfTooltipBound = false;
  let activePerfDot = null;
  let lightboxItems = [];
  let lightboxIndex = -1;
  let lightboxCompareOpen = false;
  let lightboxCompareTargetDate = "";
  let toastTimer = null;
  let activeView = "home";
  let activeHelpTipTrigger = null;
  const mobileMenuMql = window.matchMedia ? window.matchMedia("(max-width: 920px)") : null;
  const hoverCapableMql = window.matchMedia ? window.matchMedia("(hover: hover)") : null;
  const PLAN_AI_PROMPT = [
    "Te adjunto 5 archivos oficiales de Gym Tracker para generar mis planes:",
    "1) plan_diet_template.csv",
    "2) plan_workout_template.csv",
    "3) PLAN_CSV_AI_INSTRUCTIONS_DIET.md",
    "4) PLAN_CSV_AI_INSTRUCTIONS_WORKOUT.md",
    "5) PLAN_CSV_AI_SYSTEM_PROMPT.md",
    "",
    "Qué necesito de ti:",
    "- Lee primero los 5 archivos completos.",
    "- Si falta información importante, pregúntamela antes de generar nada.",
    "- Cuando tengas todo, devuélveme en un único mensaje estos 2 archivos en CSV crudo (sin Markdown ni texto adicional):",
    "  A) plan_diet.csv",
    "  B) plan_workout.csv",
    "",
    "Reglas obligatorias:",
    "- Mantén exactamente las cabeceras y el orden de columnas de las plantillas oficiales.",
    "- No añadas columnas nuevas, comentarios, títulos ni bloques de código.",
    "- Formato de fecha: AAAA-MM-DD.",
    "- session_type solo puede ser clase o pesas.",
    "- Si session_type=clase, deja vacías todas las columnas exercise_*.",
    "- exercise_*_sets debe ser entero de 1 a 12 (no rangos, no formatos tipo 3x10).",
  ].join("\n");
  if (planAiPromptText) planAiPromptText.value = PLAN_AI_PROMPT;

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

  function setFabOpen(open) {
    if (!fabMain || !fabMenu) return;
    const next = !!open;
    fabMain.classList.toggle("is-open", next);
    fabMain.setAttribute("aria-expanded", next ? "true" : "false");
    fabMain.setAttribute("aria-label", next ? "Cerrar accesos rápidos" : "Abrir accesos rápidos");
    fabMenu.hidden = !next;
    fabMenu.classList.toggle("is-open", next);
  }

  function closeFab() {
    setFabOpen(false);
  }

  const VIEW_KEY = "gt_active_view";

  function allowedView(target) {
    const next = String(target || "").trim().toLowerCase();
    if (!next) return "";
    const exists = appViews.some((node) => String(node.dataset.view || "").toLowerCase() === next);
    return exists ? next : "";
  }

  function readInitialView() {
    // UX decision: cada carga de la app debe arrancar siempre en Inicio.
    return "home";
  }

  function setActiveView(target, opts = {}) {
    const next = allowedView(target) || "home";
    activeView = next;

    appViews.forEach((node) => {
      const same = String(node.dataset.view || "").toLowerCase() === next;
      node.classList.toggle("is-active", same);
    });
    viewButtons.forEach((btn) => {
      const same = String(btn.dataset.viewTarget || "").toLowerCase() === next;
      btn.classList.toggle("is-active", same);
    });
    document.body.setAttribute("data-active-view", next);

    if (opts.persist !== false) {
      try {
        localStorage.setItem(VIEW_KEY, next);
      } catch (_) {}
    }
    if (opts.syncHash !== false) {
      const hash = `#${next}`;
      if (window.location.hash !== hash) {
        try {
          window.history.replaceState(null, "", hash);
        } catch (_) {}
      }
    }
  }

  function closeHelpTip() {
    if (!helpTipPopover) return;
    helpTipPopover.hidden = true;
    helpTipPopover.setAttribute("aria-hidden", "true");
    activeHelpTipTrigger = null;
  }

  function positionHelpTip(trigger) {
    if (!helpTipPopover || !trigger || helpTipPopover.hidden) return;
    const rect = trigger.getBoundingClientRect();
    const popRect = helpTipPopover.getBoundingClientRect();
    const gap = 10;
    const viewportLeft = window.scrollX + 12;
    const viewportTop = window.scrollY + 12;
    const viewportRight = window.scrollX + window.innerWidth - 12;
    const viewportBottom = window.scrollY + window.innerHeight - 12;
    const desktop = window.innerWidth > 920;
    let left = viewportLeft;
    let top = viewportTop;

    if (desktop) {
      left = window.scrollX + rect.right + gap;
      top = window.scrollY + rect.top + (rect.height / 2) - (popRect.height / 2);

      if (left + popRect.width > viewportRight) {
        left = window.scrollX + rect.left - popRect.width - gap;
      }
      if (left < viewportLeft) {
        left = window.scrollX + rect.left + (rect.width / 2) - (popRect.width / 2);
      }
      left = Math.max(viewportLeft, Math.min(viewportRight - popRect.width, left));
      top = Math.max(viewportTop, Math.min(viewportBottom - popRect.height, top));
    } else {
      const maxLeft = viewportRight - popRect.width;
      const preferredLeft = window.scrollX + rect.left + (rect.width / 2) - (popRect.width / 2);
      left = Math.max(viewportLeft, Math.min(maxLeft, preferredLeft));
      top = window.scrollY + rect.bottom + gap;
      const overBottom = top + popRect.height > viewportBottom;
      if (overBottom) {
        top = Math.max(viewportTop, window.scrollY + rect.top - popRect.height - gap);
      }
    }

    helpTipPopover.style.left = `${Math.round(left)}px`;
    helpTipPopover.style.top = `${Math.round(top)}px`;
  }

  function openHelpTip(trigger) {
    if (!helpTipPopover || !trigger) return;
    const title = String(trigger.dataset.tipTitle || "Información");
    const text = String(trigger.dataset.tipText || "Sin detalle.")
      .replace(/\\n/g, "\n");
    if (helpTipTitle) helpTipTitle.textContent = title;
    if (helpTipText) helpTipText.textContent = text;
    if (helpTipLink) {
      const href = String(trigger.dataset.tipLink || "/help");
      helpTipLink.setAttribute("href", href || "/help");
    }
    helpTipPopover.hidden = false;
    helpTipPopover.setAttribute("aria-hidden", "false");
    activeHelpTipTrigger = trigger;
    requestAnimationFrame(() => positionHelpTip(trigger));
  }

  function isoToday() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  function formatLocaleNumber(value, digits = 0) {
    const num = Number(value);
    if (!Number.isFinite(num)) return "—";
    return num.toLocaleString("es-ES", {
      useGrouping: "always",
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }
  function fmt1(x) {
    return x == null || Number.isNaN(x) ? "—" : formatLocaleNumber(Math.round(x * 10) / 10, 1);
  }
  function fmt0(x) {
    return x == null || Number.isNaN(x) ? "—" : formatLocaleNumber(Math.round(x), 0);
  }
  function fmtGrams(x) {
    const num = Number(x);
    if (!Number.isFinite(num)) return "—";
    return `${formatLocaleNumber(Math.round(num), 0)} g`;
  }
  function fmt3(x) {
    return x == null || Number.isNaN(x) ? "—" : formatLocaleNumber(Math.round(x * 1000) / 1000, 3);
  }
  function fmtDelta(x, digits = 1) {
    if (x == null || Number.isNaN(x)) return "—";
    const val = Number(x);
    const sign = val > 0 ? "+" : "";
    return `${sign}${formatLocaleNumber(val, digits)}`;
  }

  function clockNow() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  function setSyncStatus(text, tone = "ok") {
    if (!syncStatus) return;
    syncStatus.textContent = String(text || "Sin estado");
    syncStatus.classList.remove("ok", "warn", "bad");
    if (tone === "warn" || tone === "bad") syncStatus.classList.add(tone);
    else syncStatus.classList.add("ok");
  }

  function syncOkStatus(dietRows, workoutRows) {
    return `Última sincronización: ${clockNow()}`;
  }

  function renderViewCounts() {
    const dietCount = Array.isArray(currentDietRows) ? currentDietRows.length : 0;
    const workoutCount = Array.isArray(currentWorkoutRows) ? currentWorkoutRows.length : 0;
    if (dietCountMeta) {
      dietCountMeta.textContent = dietCount
        ? `${dietCount} check-ins cargados.`
        : "Sin check-ins en esta vista.";
    }
    if (workCountMeta) {
      workCountMeta.textContent = workoutCount
        ? `${workoutCount} sesiones cargadas.`
        : "Sin sesiones en esta vista.";
    }
  }

  function humanDate(iso) {
    const s = String(iso || "");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return s || "—";
    const [yyyy, mm, dd] = s.split("-");
    return `${dd}/${mm}/${yyyy}`;
  }

  function humanDateDash(iso) {
    const s = String(iso || "");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return s || "—";
    const [yyyy, mm, dd] = s.split("-");
    return `${dd}-${mm}-${yyyy}`;
  }

  function humanDateTime(isoLikeText) {
    const s = String(isoLikeText || "").trim();
    const m = s.match(/^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})(?::\d{2})?/);
    if (m) {
      return `${m[3]}-${m[2]}-${m[1]} ${m[4]}:${m[5]}`;
    }
    return s || "—";
  }

  function asDisplay(v) {
    return v == null || v === "" ? "—" : escapeHtml(String(v));
  }

  function displayInt(v) {
    const num = Number(v);
    if (!Number.isFinite(num)) return "—";
    return escapeHtml(formatLocaleNumber(Math.round(num), 0));
  }

  function displayFloat(v, digits = 1) {
    const num = Number(v);
    if (!Number.isFinite(num)) return "—";
    return escapeHtml(formatLocaleNumber(num, digits));
  }

  function setDietFormAlert(text = "") {
    if (!dietFormAlert) return;
    const msg = String(text || "").trim();
    if (!msg) {
      dietFormAlert.hidden = true;
      dietFormAlert.textContent = "";
      return;
    }
    dietFormAlert.hidden = false;
    dietFormAlert.textContent = msg;
  }

  function isoLike(v) {
    const s = String(v || "").trim();
    return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : "";
  }

  function findPhotoByDate(logDate) {
    const d = isoLike(logDate);
    if (!d) return null;
    return lightboxItems.find((p) => String(p.log_date || "") === d) || null;
  }

  function normalizePhotoItems(rawPhotos, dietRows) {
    const map = new Map();

    const put = (item) => {
      if (!item || !item.photo_url) return;
      const date = isoLike(item.log_date);
      if (!date) return;
      const key = `${date}|${item.photo_url}`;
      if (map.has(key)) return;
      map.set(key, {
        log_date: date,
        photo_url: String(item.photo_url),
        label: String(item.label || `Foto ${date}`),
        original_name: String(item.original_name || ""),
        weight_kg: item.weight_kg == null ? null : Number(item.weight_kg),
        whr: item.whr == null ? null : Number(item.whr),
      });
    };

    if (Array.isArray(rawPhotos)) rawPhotos.forEach(put);

    if (Array.isArray(dietRows)) {
      dietRows.forEach((r) => {
        if (!r || !r.photo_url) return;
        const whrRaw = Number(computeWHR(r));
        put({
          log_date: r.log_date,
          photo_url: r.photo_url,
          label: `Foto ${r.log_date || ""}`.trim(),
          weight_kg: r.weight_kg,
          whr: Number.isFinite(whrRaw) ? whrRaw : null,
        });
      });
    }

    return Array.from(map.values()).sort((a, b) => {
      if (a.log_date === b.log_date) return 0;
      return a.log_date > b.log_date ? -1 : 1;
    });
  }

  function valueLabel(metric) {
    if (metric === "weight_kg") return { title: "Peso", unit: "kg", digits: 1 };
    if (metric === "whr") return { title: "WHR", unit: "", digits: 3 };
    if (metric === "sleep_hours") return { title: "Sueño", unit: "h", digits: 1 };
    return { title: "Pasos", unit: "", digits: 0 };
  }

  function summarySeries(metric) {
    const points = Array.isArray(latestSummary?.series?.points) ? latestSummary.series.points : [];
    return points
      .map((p) => {
        const value = Number(p?.[metric]);
        if (!Number.isFinite(value)) return null;
        return { date: String(p.log_date || ""), value };
      })
      .filter(Boolean);
  }

  function ensurePerfPointTooltip() {
    if (!perfChartWrap) return null;
    let tip = perfChartWrap.querySelector(".chart-point-tooltip");
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "chart-point-tooltip";
      tip.hidden = true;
      perfChartWrap.appendChild(tip);
    }
    return tip;
  }

  function clearPerfActiveDot() {
    if (activePerfDot) activePerfDot.classList.remove("is-active");
    activePerfDot = null;
  }

  function hidePerfPointTooltip() {
    const tip = perfChartWrap?.querySelector(".chart-point-tooltip");
    if (tip) tip.hidden = true;
    clearPerfActiveDot();
  }

  function bindPerfTooltipDismiss() {
    if (perfTooltipBound) return;
    if (perfChartWrap) {
      perfChartWrap.addEventListener("mouseleave", hidePerfPointTooltip);
    }
    document.addEventListener("click", (ev) => {
      if (!perfChartWrap) return;
      if (perfChartWrap.contains(ev.target)) return;
      hidePerfPointTooltip();
    });
    perfTooltipBound = true;
  }

  function showPerfPointTooltip(dotNode, point, idx, plot, info) {
    if (!perfChart || !perfChartWrap || !point || !info) return;
    const tip = ensurePerfPointTooltip();
    if (!tip) return;

    const unit = info.unit ? ` ${info.unit}` : "";
    const formatValue = (val) =>
      info.digits === 0 ? formatLocaleNumber(Math.round(val), 0) : formatLocaleNumber(val, info.digits);
    const label = `${escapeHtml(info.title)}: ${escapeHtml(formatValue(point.value))}${escapeHtml(unit)}`;
    const date = escapeHtml(humanDate(point.date));
    let deltaHtml = "";
    if (idx > 0 && plot[idx - 1]) {
      const prev = plot[idx - 1];
      const d = Number(point.value) - Number(prev.value);
      if (Number.isFinite(d)) {
        const sign = d > 0 ? "+" : "";
        deltaHtml = `<div class="chart-point-tooltip-delta">Δ vs anterior: ${escapeHtml(`${sign}${formatValue(d)}`)}${escapeHtml(unit)}</div>`;
      }
    }
    tip.innerHTML = `
      <div class="chart-point-tooltip-date">${date}</div>
      <div class="chart-point-tooltip-value">${label}</div>
      ${deltaHtml}
    `;
    tip.hidden = false;

    clearPerfActiveDot();
    if (dotNode) {
      activePerfDot = dotNode;
      activePerfDot.classList.add("is-active");
    }

    const vb = perfChart.viewBox?.baseVal;
    const vbW = vb?.width || 1000;
    const vbH = vb?.height || 260;
    const svgRect = perfChart.getBoundingClientRect();
    const wrapRect = perfChartWrap.getBoundingClientRect();
    const relX = ((Number(point.x) / vbW) * svgRect.width) + (svgRect.left - wrapRect.left);
    const relY = ((Number(point.y) / vbH) * svgRect.height) + (svgRect.top - wrapRect.top);

    tip.style.left = `${relX}px`;
    tip.style.top = `${Math.max(0, relY - 10)}px`;
    tip.dataset.place = "above";
    tip.style.transform = "translate(-50%, -100%)";

    const tipW = tip.offsetWidth || 190;
    const tipH = tip.offsetHeight || 64;
    const margin = 10;

    let left = relX;
    left = Math.max(margin + tipW / 2, Math.min(left, wrapRect.width - margin - tipW / 2));
    let top = relY - 10;
    let place = "above";
    if (top - tipH < margin) {
      top = relY + 12;
      place = "below";
    }
    tip.dataset.place = place;
    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
    tip.style.transform = place === "above" ? "translate(-50%, -100%)" : "translate(-50%, 0)";
  }

  function renderPerformanceChart(metric = chartMetric) {
    if (!perfChart || !perfEmpty || !perfFoot) return;
    hidePerfPointTooltip();
    chartMetric = metric;
    const info = valueLabel(metric);
    const points = summarySeries(metric);

    if (perfMetricTabs) {
      perfMetricTabs.querySelectorAll("[data-chart-metric]").forEach((btn) => {
        const active = String(btn.dataset.chartMetric || "") === metric;
        btn.classList.toggle("active", active);
      });
    }

    const parseDayMs = (isoDate) => {
      const d = String(isoDate || "");
      if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return NaN;
      return Date.parse(`${d}T00:00:00Z`);
    };

    const firstTs = parseDayMs(points[0]?.date);
    const lastTs = parseDayMs(points[points.length - 1]?.date);
    const spanMs = Number.isFinite(firstTs) && Number.isFinite(lastTs) ? Math.max(1, lastTs - firstTs) : 0;
    const spanDays = spanMs > 0 ? Math.round(spanMs / 86400000) + 1 : points.length;
    const missingDays = Math.max(0, spanDays - points.length);

    if (perfSub) {
      const baseDays = parseLimitValue(latestSummary?.window_days, summaryWindowDays);
      const mode = latestSummary?.mode === "range" ? "periodo seleccionado" : `ultimos ${baseDays} dias`;
      const coverageTxt = missingDays > 0
        ? ` Cobertura ${points.length}/${spanDays} dias (${missingDays} sin registro).`
        : ` Cobertura ${points.length}/${spanDays} dias.`;
      perfSub.textContent = `${info.title} en ${mode}.${coverageTxt}`;
    }

    if (points.length < 2) {
      perfChart.innerHTML = "";
      perfEmpty.style.display = "block";
      perfFoot.textContent = "Necesitamos al menos 2 puntos para dibujar tendencia.";
      return;
    }

    perfEmpty.style.display = "none";

    const width = 1000;
    const height = 260;
    const padX = 12;
    const padTop = 16;
    const padBottom = 32;
    const innerW = width - padX * 2;
    const innerH = height - padTop - padBottom;

    let min = Math.min(...points.map((p) => p.value));
    let max = Math.max(...points.map((p) => p.value));
    if (min === max) {
      min -= 1;
      max += 1;
    }
    const span = max - min;

    const plot = points.map((p, idx) => {
      let x = padX + (innerW * idx) / (points.length - 1);
      if (spanMs > 0) {
        const ts = parseDayMs(p.date);
        if (Number.isFinite(ts)) {
          x = padX + ((ts - firstTs) / spanMs) * innerW;
        }
      }
      const y = padTop + (max - p.value) / span * innerH;
      return { ...p, x, y };
    });

    const poly = plot.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const first = plot[0].value;
    const last = plot[plot.length - 1].value;
    const delta = last - first;
    const sign = delta > 0 ? "+" : "";
    const unit = info.unit ? ` ${info.unit}` : "";
    const format = (val) =>
      info.digits === 0 ? `${formatLocaleNumber(Math.round(val), 0)}` : `${formatLocaleNumber(val, info.digits)}`;

    const ticks = [0, 0.5, 1].map((t) => {
      const y = padTop + innerH * t;
      return `<line x1="${padX}" y1="${y.toFixed(1)}" x2="${(width - padX).toFixed(1)}" y2="${y.toFixed(1)}" class="chart-grid"/>`;
    }).join("");

    const area = `${plot[0].x.toFixed(1)},${(padTop + innerH).toFixed(1)} ${poly} ${plot[plot.length - 1].x.toFixed(1)},${(padTop + innerH).toFixed(1)}`;
    const dots = plot.map((p, idx) => {
      const aria = `${info.title} ${format(p.value)}${unit} en ${humanDate(p.date)}`;
      return `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="6.0" class="chart-dot" data-point-idx="${idx}" tabindex="0" role="button" aria-label="${escapeHtml(aria)}"/>`;
    }).join("");
    const yformat = (v) => info.digits === 0 ? `${formatLocaleNumber(Math.round(v), 0)}` : `${formatLocaleNumber(v, info.digits)}`;
    const yTop = `${yformat(max)}${info.unit ? ` ${info.unit}` : ""}`;
    const yBottom = `${yformat(min)}${info.unit ? ` ${info.unit}` : ""}`;
    const ylabels = [
      `<text x="${(width - 8).toFixed(1)}" y="${(padTop + 10).toFixed(1)}" text-anchor="end" class="chart-y">${escapeHtml(yTop)}</text>`,
      `<text x="${(width - 8).toFixed(1)}" y="${(padTop + innerH - 4).toFixed(1)}" text-anchor="end" class="chart-y">${escapeHtml(yBottom)}</text>`,
    ].join("");
    const xlabels = [
      `<text x="${plot[0].x.toFixed(1)}" y="${(height - 10).toFixed(1)}" text-anchor="start" class="chart-x">${escapeHtml(humanDate(plot[0].date))}</text>`,
      `<text x="${plot[plot.length - 1].x.toFixed(1)}" y="${(height - 10).toFixed(1)}" text-anchor="end" class="chart-x">${escapeHtml(humanDate(plot[plot.length - 1].date))}</text>`,
    ].join("");

    perfChart.innerHTML = `
      <g class="chart-layer">
        ${ticks}
        <polygon points="${area}" class="chart-area"/>
        <polyline points="${poly}" class="chart-line"/>
        ${dots}
        ${ylabels}
        ${xlabels}
      </g>
    `;
    const dotNodes = Array.from(perfChart.querySelectorAll(".chart-dot[data-point-idx]"));
    dotNodes.forEach((node) => {
      const idx = Number(node.dataset.pointIdx);
      const point = plot[idx];
      if (!point) return;
      const openTip = () => showPerfPointTooltip(node, point, idx, plot, info);
      node.addEventListener("mouseenter", openTip);
      node.addEventListener("focus", openTip);
      node.addEventListener("click", (ev) => {
        ev.stopPropagation();
        openTip();
      });
      node.addEventListener("keydown", (ev) => {
        if (ev.key === "Escape") {
          hidePerfPointTooltip();
          return;
        }
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          ev.stopPropagation();
          openTip();
        }
      });
    });
    bindPerfTooltipDismiss();

    perfFoot.textContent =
      `${info.title}: ${format(first)}${unit} -> ${format(last)}${unit} (Δ ${sign}${format(delta)}${unit})`;
  }

  function drawSparkline(ctx, points, x, y, w, h, color) {
    if (!Array.isArray(points) || points.length < 2) return;
    const vals = points.map((p) => Number(p.value)).filter((v) => Number.isFinite(v));
    if (vals.length < 2) return;
    let min = Math.min(...vals);
    let max = Math.max(...vals);
    if (min === max) {
      min -= 1;
      max += 1;
    }
    const span = max - min;
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.beginPath();
    points.forEach((p, idx) => {
      const px = x + (w * idx) / (points.length - 1);
      const py = y + h - ((Number(p.value) - min) / span) * h;
      if (idx === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.stroke();
    ctx.restore();
  }

  function reportSummaryText() {
    const period = latestSummary?.period_label || "Periodo no definido";
    const lines = [
      "Gym Tracker · Informe",
      `Periodo: ${period}`,
      "",
      `Sueño: ${$("kSleep")?.textContent || "—"}`,
      `Pasos: ${$("kSteps")?.textContent || "—"}`,
      `Peso: ${$("kWeight")?.textContent || "—"}`,
      `WHR: ${$("kWHR")?.textContent || "—"}`,
      "",
      `Tendencia: ${$("trendText")?.textContent || "Sin tendencia"}`,
      `${$("trendDelta")?.textContent || ""}`,
      "",
      `Métrica activa: ${valueLabel(chartMetric).title}`,
      `Detalle: ${$("perfFoot")?.textContent || "—"}`,
      `Generado: ${new Date().toLocaleString("es-ES")}`,
    ];
    return lines.join("\n").trim();
  }

  function buildReportCanvas() {
    const canvas = document.createElement("canvas");
    canvas.width = 1400;
    canvas.height = 900;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    const rootTheme = document.documentElement.getAttribute("data-theme");
    const lightMode = rootTheme === "light";
    const bg = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    if (lightMode) {
      bg.addColorStop(0, "#f2f7fb");
      bg.addColorStop(1, "#e6f0f8");
    } else {
      bg.addColorStop(0, "#031f1c");
      bg.addColorStop(1, "#062a25");
    }
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const fg = lightMode ? "#102535" : "#e8f5f2";
    const sub = lightMode ? "#335067" : "#9dc7bd";
    const accent = lightMode ? "#0f8d80" : "#23e5cf";

    ctx.fillStyle = fg;
    ctx.font = "700 50px system-ui, -apple-system, Segoe UI, sans-serif";
    ctx.fillText("Gym Tracker · Informe rápido", 72, 88);
    ctx.fillStyle = sub;
    ctx.font = "400 26px system-ui, -apple-system, Segoe UI, sans-serif";
    const period = latestSummary?.period_label || "Periodo no definido";
    ctx.fillText(`Periodo: ${period}`, 72, 128);

    const kpis = [
      ["Sueño", $("kSleep")?.textContent || "—"],
      ["Pasos", $("kSteps")?.textContent || "—"],
      ["Peso", $("kWeight")?.textContent || "—"],
      ["WHR", $("kWHR")?.textContent || "—"],
    ];

    let y = 200;
    kpis.forEach(([name, value]) => {
      ctx.fillStyle = sub;
      ctx.font = "600 26px system-ui, -apple-system, Segoe UI, sans-serif";
      ctx.fillText(name, 80, y);
      ctx.fillStyle = fg;
      ctx.font = "700 36px system-ui, -apple-system, Segoe UI, sans-serif";
      ctx.fillText(value, 260, y);
      y += 70;
    });

    ctx.fillStyle = accent;
    ctx.font = "700 30px system-ui, -apple-system, Segoe UI, sans-serif";
    ctx.fillText("Resumen", 80, 520);
    ctx.fillStyle = fg;
    ctx.font = "500 28px system-ui, -apple-system, Segoe UI, sans-serif";
    const trendLine = String($("trendText")?.textContent || "Sin tendencia");
    const trendDeltaLine = String($("trendDelta")?.textContent || "");
    ctx.fillText(trendLine.slice(0, 90), 80, 565);
    ctx.fillStyle = sub;
    ctx.font = "400 24px system-ui, -apple-system, Segoe UI, sans-serif";
    ctx.fillText(trendDeltaLine.slice(0, 110), 80, 604);

    const chartPoints = summarySeries(chartMetric);
    drawSparkline(ctx, chartPoints, 80, 650, 1240, 170, accent);
    return canvas;
  }

  function reportFilename(ext = "png") {
    const filenameDate = (latestSummary?.date_to || isoToday()).replaceAll("/", "-");
    return `gym-tracker-informe-${filenameDate}.${ext}`;
  }

  function canvasToBlob(canvas, type = "image/png", quality = 0.92) {
    return new Promise((resolve) => {
      if (!canvas || !canvas.toBlob) {
        resolve(null);
        return;
      }
      canvas.toBlob((blob) => resolve(blob || null), type, quality);
    });
  }

  function exportReportPNG() {
    const canvas = buildReportCanvas();
    if (!canvas) {
      showToast("Informe", "No se pudo generar el canvas del informe.");
      return;
    }
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = reportFilename("png");
    link.click();
    showToast("Informe listo", "Descargado en PNG.");
  }

  function exportReportPDF() {
    const win = window.open("", "_blank");
    if (!win) {
      showToast("Informe PDF", "Tu navegador bloqueó la ventana emergente.");
      return;
    }
    const canvas = buildReportCanvas();
    if (!canvas) {
      win.document.write("<!doctype html><html><body><p>No se pudo preparar el informe para PDF.</p></body></html>");
      win.document.close();
      showToast("Informe", "No se pudo preparar el informe para PDF.");
      return;
    }
    const dataUrl = canvas.toDataURL("image/png");
    const summaryText = reportSummaryText()
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
    win.document.write(`<!doctype html>
<html lang="es"><head><meta charset="utf-8"/><title>Informe Gym Tracker</title>
<style>
body{font-family:Inter,Segoe UI,Arial,sans-serif;background:#f3f6f9;color:#0f172a;margin:20px}
.card{max-width:980px;margin:0 auto;background:#fff;border:1px solid #dbe5ef;border-radius:14px;padding:16px}
img{width:100%;height:auto;border-radius:10px;border:1px solid #dbe5ef}
pre{white-space:pre-wrap;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px}
</style></head><body><div class="card">
<h1>Gym Tracker · Informe</h1>
<p>Usa \"Guardar como PDF\" desde el diálogo de impresión.</p>
<img src="${dataUrl}" alt="Informe Gym Tracker"/>
<pre>${summaryText}</pre>
</div></body></html>`);
    win.document.close();
    win.focus();
    setTimeout(() => {
      try {
        win.print();
      } catch (_) {}
    }, 280);
    showToast("Informe PDF", "Abierto para imprimir/guardar como PDF.");
  }

  async function copyTextToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (_) {
        // fallback a execCommand
      }
    }
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      return !!document.execCommand("copy");
    } catch (_) {
      return false;
    } finally {
      ta.remove();
    }
  }

  async function copyReportSummary(showSuccessToast = true) {
    const text = reportSummaryText();
    if (!text) {
      if (showSuccessToast) showToast("Resumen", "No hay datos para copiar.");
      return false;
    }
    const ok = await copyTextToClipboard(text);
    if (showSuccessToast) {
      if (ok) showToast("Resumen copiado", "Puedes pegarlo donde quieras.");
      else showToast("Resumen", "No se pudo copiar automaticamente.");
    }
    return ok;
  }

  async function shareReportQuick() {
    const canvas = buildReportCanvas();
    if (!canvas) {
      showToast("Compartir", "No se pudo preparar el informe.");
      return;
    }
    const summary = reportSummaryText();
    const blob = await canvasToBlob(canvas, "image/png", 0.95);
    if (!blob) {
      showToast("Compartir", "No se pudo generar la imagen para compartir.");
      return;
    }
    const filename = reportFilename("png");
    const basePayload = {
      title: "Gym Tracker · Informe",
      text: summary,
    };

    const isAbortError = (err) => String(err?.name || "").toLowerCase() === "aborterror";
    const supportsShare = typeof navigator !== "undefined" && typeof navigator.share === "function";
    if (supportsShare) {
      let filePayload = null;
      if (typeof File !== "undefined") {
        try {
          const file = new File([blob], filename, { type: "image/png" });
          filePayload = { ...basePayload, files: [file] };
        } catch (_) {
          filePayload = null;
        }
      }

      if (filePayload) {
        const canShareFiles = typeof navigator.canShare === "function"
          ? !!navigator.canShare({ files: filePayload.files })
          : true;
        if (canShareFiles) {
          try {
            await navigator.share(filePayload);
            showToast("Compartido", "Informe enviado con PNG adjunto.");
            return;
          } catch (err) {
            if (isAbortError(err)) return;
          }
        }
      }

      try {
        await navigator.share(basePayload);
        showToast("Compartido", "Resumen enviado.");
        return;
      } catch (err) {
        if (isAbortError(err)) return;
      }
    }

    const copied = await copyReportSummary(false);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1200);
    if (copied) showToast("Compartir no disponible", "Copié resumen y descargué PNG.");
    else showToast("Compartir no disponible", "Descargué PNG para compartir manualmente.");
  }

  function showToast(t1, t2) {
    if (!toast || !toastT1 || !toastT2) return;
    placeToastHost();
    toastT1.textContent = t1;
    toastT2.textContent = t2;
    toast.classList.add("show");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.remove("show");
      restoreToastHome();
    }, 2400);
    if (String(t1 || "").toLowerCase().startsWith("error")) {
      setSyncStatus("Incidencia detectada", "warn");
    }
  }

  function getTopOpenDialog() {
    const opened = Array.from(document.querySelectorAll("dialog[open]"));
    return opened.length ? opened[opened.length - 1] : null;
  }

  function restoreToastHome() {
    if (!toast || !toastHomeParent) return;
    if (toast.parentElement !== toastHomeParent) {
      if (toastHomeNext && toastHomeNext.parentNode === toastHomeParent) {
        toastHomeParent.insertBefore(toast, toastHomeNext);
      } else {
        toastHomeParent.appendChild(toast);
      }
    }
    toast.classList.remove("in-dialog");
  }

  function placeToastHost() {
    if (!toast) return;
    const topDialog = getTopOpenDialog();
    if (!topDialog) {
      restoreToastHome();
      return;
    }
    if (toast.parentElement !== topDialog) {
      topDialog.appendChild(toast);
    }
    toast.classList.add("in-dialog");
  }

  function userErrorMessage(raw) {
    const msg = String(raw || "").replace(/^Error:\s*/i, "").trim();
    if (!msg) return "Error inesperado. Intenta de nuevo.";
    const low = msg.toLowerCase();

    if (low.includes("ese día ya existe") || low.includes("ese dia ya existe")) {
      return "Ese día ya existe. Haz click en la fila para editarlo.";
    }
    if (low.includes("log_date inválida") || low.includes("log_date invalida")) {
      return "Fecha inválida. Usa formato AAAA-MM-DD.";
    }
    if (low.includes("extensión de archivo no permitida") || low.includes("extension de archivo no permitida")) {
      return "Formato de foto no permitido. Usa JPG, PNG o WEBP.";
    }
    if (low.includes("archivo demasiado grande")) {
      return msg;
    }
    if (low.includes("failed to fetch") || low.includes("networkerror")) {
      return "No se pudo conectar con la app local. Revisa que siga corriendo en 127.0.0.1.";
    }
    return msg.slice(0, 180);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }

  function safeClose(dialog) {
    if (!dialog || !dialog.open || !dialog.close) return;
    dialog.close();
    syncModalScrollLock();
  }

  function safeOpen(dialog) {
    if (!dialog || dialog.open || !dialog.showModal) return;
    dialog.showModal();
    syncModalScrollLock();
  }

  function syncModalScrollLock() {
    const hasOpenDialog = !!document.querySelector("dialog[open]");
    document.documentElement.classList.toggle("modal-open", hasOpenDialog);
    document.body.classList.toggle("modal-open", hasOpenDialog);
  }

  function setupBackdropClose(dialog) {
    if (!dialog || !dialog.addEventListener) return;
    dialog.addEventListener("click", (e) => {
      const rect = dialog.getBoundingClientRect();
      const inDialog =
        rect.top <= e.clientY &&
        e.clientY <= rect.bottom &&
        rect.left <= e.clientX &&
        e.clientX <= rect.right;
      if (!inDialog) safeClose(dialog);
    });
  }

  function buildBugReportText() {
    const now = new Date();
    const ts = `${now.toISOString()} | local ${now.toLocaleString("es-ES")}`;
    const themeMode = getStoredTheme();
    const themeEff = effectiveTheme(themeMode);
    const range = (summaryRangeFrom && summaryRangeTo)
      ? `${summaryRangeFrom} -> ${summaryRangeTo}`
      : "auto (ultimos 7 dias)";
    const lines = [
      "# Gym Tracker - Reporte de bug",
      "",
      `Fecha/Hora: ${ts}`,
      `URL: ${window.location.href}`,
      `Tema: modo=${themeMode} | efectivo=${themeEff}`,
      `Rango KPI activo: ${range}`,
      `Ventana check-ins: ${dietLimit} dias`,
      `Ventana entrenos: ${workLimit} dias`,
      `Ventana suplementos: ${suppLimit} dias`,
      `Estado sync footer: ${String(syncStatus?.textContent || "").trim() || "N/D"}`,
      "",
      "## Qué pasó",
      "- Describe aquí qué intentaste hacer.",
      "- Describe aquí qué esperabas que pasara.",
      "- Describe aquí qué pasó realmente.",
      "",
      "## Contexto técnico",
      `- userAgent: ${navigator.userAgent}`,
      `- viewport: ${window.innerWidth}x${window.innerHeight}`,
      `- timestamp_ms: ${Date.now()}`,
    ];
    return lines.join("\n");
  }

  function openBugReportModal() {
    if (!reportBugModal) return;
    if (reportBugText) reportBugText.value = buildBugReportText();
    safeOpen(reportBugModal);
  }

  async function copyBugReport() {
    const text = String(reportBugText?.value || buildBugReportText());
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      showToast("Bug report", "Diagnóstico copiado.");
      return;
    }
    const ta = reportBugText;
    if (ta) {
      ta.focus();
      ta.select();
      const ok = document.execCommand("copy");
      showToast("Bug report", ok ? "Diagnóstico copiado." : "No se pudo copiar automáticamente.");
    }
  }

  function openBugMail() {
    const subject = "[Gym Tracker] Reporte de bug";
    const bodyRaw = String(reportBugText?.value || buildBugReportText());
    const body = bodyRaw.slice(0, 1600);
    window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  }

  function setFormValue(form, name, value) {
    if (!form) return;
    const node = form.querySelector(`[name="${name}"]`);
    if (node) node.value = value == null ? "" : String(value);
  }

  function setSuppCatalogAlert(text = "") {
    if (!suppCatalogAlert) return;
    const msg = String(text || "").trim();
    if (!msg) {
      suppCatalogAlert.hidden = true;
      suppCatalogAlert.textContent = "";
      return;
    }
    suppCatalogAlert.hidden = false;
    suppCatalogAlert.textContent = msg;
  }

  function pillYN(v) {
    if (!v) return `<span class="pill warn">—</span>`;
    const u = String(v).toUpperCase();
    if (u === "Y") return `<span class="pill good">Y</span>`;
    if (u === "N") return `<span class="pill bad">N</span>`;
    return `<span class="pill warn">${escapeHtml(u)}</span>`;
  }

  function pillDone(v) {
    return pillYN(v);
  }

  function normalizeSessionType(v) {
    const type = String(v || "").trim().toLowerCase();
    if (type === "mixta") return "pesas";
    if (type === "pesas") return "pesas";
    return "clase";
  }

  function sessionTypeMeta(v) {
    const type = normalizeSessionType(v);
    if (type === "pesas") return { key: "pesas", label: "Pesas", cls: "type-strength" };
    return { key: "clase", label: "Clase", cls: "type-class" };
  }

  function pillType(v) {
    const meta = sessionTypeMeta(v);
    return `<span class="pill ${meta.cls}">${meta.label}</span>`;
  }

  function pillSession(order) {
    const num = Number(order || 0);
    if (!num || Number.isNaN(num)) return `<span class="pill warn">S?</span>`;
    return `<span class="pill">S${escapeHtml(String(num))}</span>`;
  }

  function formatExerciseTopset(ex) {
    if (!ex || typeof ex !== "object") return "—";
    if (ex.topset_text) return String(ex.topset_text);
    const parts = [];
    const weight = Number(ex.weight_kg);
    const reps = Number(ex.reps);
    const rpe = Number(ex.rpe);
    if (ex.weight_kg != null && ex.weight_kg !== "") {
      parts.push(Number.isFinite(weight) ? `${formatLocaleNumber(weight, 1)} kg` : `${ex.weight_kg} kg`);
    }
    if (ex.reps != null && ex.reps !== "") {
      parts.push(Number.isFinite(reps) ? `${formatLocaleNumber(Math.round(reps), 0)} reps` : `${ex.reps} reps`);
    }
    if (ex.rpe != null && ex.rpe !== "") {
      parts.push(Number.isFinite(rpe) ? `RPE ${formatLocaleNumber(rpe, 1)}` : `RPE ${ex.rpe}`);
    }
    return parts.length ? parts.join(" · ") : "—";
  }

  function formatExerciseDelta(ex) {
    const out = [];
    const dw = Number(ex?.delta_weight);
    const dr = Number(ex?.delta_reps);
    if (ex?.delta_weight != null && !Number.isNaN(dw)) {
      out.push(`${dw > 0 ? "+" : ""}${formatLocaleNumber(dw, 1)} kg`);
    }
    if (ex?.delta_reps != null && !Number.isNaN(dr)) {
      out.push(`${dr > 0 ? "+" : ""}${formatLocaleNumber(Math.round(dr), 0)} reps`);
    }
    return out.join(" · ");
  }

  function workoutExercisesCell(row) {
    const list = Array.isArray(row?.exercises) ? row.exercises : [];
    if (!list.length) return "—";
    return list
      .map((ex) => {
        const name = escapeHtml(String(ex.exercise_name || "Ejercicio"));
        const topset = escapeHtml(formatExerciseTopset(ex));
        const delta = formatExerciseDelta(ex);
        const deltaHtml = delta ? `<div class="lift-delta mono">Δ ${escapeHtml(delta)}</div>` : "";
        return `<div class="lift-main"><strong>${name}</strong>: ${topset}</div>${deltaHtml}`;
      })
      .join("");
  }

  function renderSummary(summary) {
    const kSleep = $("kSleep");
    const kSteps = $("kSteps");
    const kWeight = $("kWeight");
    const kWHR = $("kWHR");
    if (!kSleep || !kSteps || !kWeight || !kWHR) return;

    kSleep.textContent = summary?.avg_sleep == null ? "—" : `${fmt1(summary.avg_sleep)} h`;
    kSteps.textContent = summary?.avg_steps == null ? "—" : `${fmt0(summary.avg_steps)}`;
    kWeight.textContent = summary?.avg_weight == null ? "—" : `${fmt1(summary.avg_weight)} kg`;
    kWHR.textContent = summary?.avg_whr == null ? "—" : `${fmt3(summary.avg_whr)}`;

    const isRange = summary?.mode === "range";
    const dateFrom = String(summary?.date_from || "");
    const dateTo = String(summary?.date_to || "");
    const windowDays = parseLimitValue(summary?.window_days, summaryWindowDays);
    summaryWindowDays = windowDays;
    if (summaryModeSelect) summaryModeSelect.value = isRange ? "custom" : String(windowDays);
    if (perfModeSelect) perfModeSelect.value = isRange ? "custom" : String(windowDays);
    if (isRange) {
      if (summaryFrom) summaryFrom.value = dateFrom;
      if (summaryTo) summaryTo.value = dateTo;
      if (perfFrom) perfFrom.value = dateFrom;
      if (perfTo) perfTo.value = dateTo;
    } else {
      if (summaryFrom) summaryFrom.value = "";
      if (summaryTo) summaryTo.value = "";
      if (perfFrom) perfFrom.value = "";
      if (perfTo) perfTo.value = "";
    }
    syncSummaryAnalysisUI();
    syncPerfAnalysisUI();
    if (kpiSleepTitle) kpiSleepTitle.textContent = "SUEÑO";
    if (kpiStepsTitle) kpiStepsTitle.textContent = "PASOS";
    if (kpiWeightTitle) kpiWeightTitle.textContent = "PESO";
    if (kpiWHRTitle) kpiWHRTitle.textContent = "WHR";

    const periodFromText = humanDateDash(dateFrom);
    const periodToText = humanDateDash(dateTo);
    const periodHtml = `
      <span class="kpi-period-line">Del: ${escapeHtml(periodFromText)}</span>
      <span class="kpi-period-line">Al: ${escapeHtml(periodToText)}</span>
    `;
    if (kSleepPeriod) kSleepPeriod.innerHTML = periodHtml;
    if (kStepsPeriod) kStepsPeriod.innerHTML = periodHtml;
    if (kWeightPeriod) kWeightPeriod.innerHTML = periodHtml;
    if (kWHRPeriod) kWHRPeriod.innerHTML = periodHtml;

    const coverage = summary?.coverage || {};
    const currentCount = Number(coverage.current_count || 0);
    const currentTarget = Number(coverage.current_target || 0);
    const baselineCount = Number(coverage.baseline_count || 0);
    const baselineTarget = Number(coverage.baseline_target || 0);
    if (summaryCaption) {
      summaryCaption.textContent = `${currentCount} días con datos de un total de ${currentTarget} en el período.`;
    }

    const relative = summary?.relative || {};
    let baselineFrom = "";
    let baselineTo = "";
    const baselineMatch = String(relative.baseline_label || "").match(
      /^(\d{4}-\d{2}-\d{2})\s*->\s*(\d{4}-\d{2}-\d{2})$/
    );
    if (baselineMatch) {
      baselineFrom = baselineMatch[1];
      baselineTo = baselineMatch[2];
    }

    function buildKpiMetaHtml() {
      const sections = [];
      if (baselineFrom && baselineTo) {
        sections.push(
          `<span class="kpi-delta-meta-section">` +
            `<span class="kpi-delta-meta-title">Período comparado:</span>` +
            `<span class="kpi-delta-meta-line">Del: ${escapeHtml(humanDateDash(baselineFrom))}</span>` +
            `<span class="kpi-delta-meta-line">Al: ${escapeHtml(humanDateDash(baselineTo))}</span>` +
          `</span>`
        );
      }
      sections.push(
        `<span class="kpi-delta-meta-section">` +
          `<span class="kpi-delta-meta-line">Solo se computan días con actividad sobre el total de días calendario del período.</span>` +
        `</span>`
      );
      if (!sections.length) {
        sections.push(
          `<span class="kpi-delta-meta-section">` +
            `<span class="kpi-delta-meta-line">Aun no hay período previo comparable.</span>` +
          `</span>`
        );
      }
      return `<span class="kpi-delta-meta">${sections.join("")}</span>`;
    }

    function drawKpiDelta(node, delta, digits, unit, preferLower, stableEps) {
      if (!node) return;
      node.classList.remove("good", "warn", "bad", "muted", "state-better", "state-equal", "state-worse", "state-muted");
      node.innerHTML = "";
      if (delta == null || Number.isNaN(Number(delta))) {
        node.textContent = "Sin comparativa previa";
        node.classList.add("state-muted");
        return;
      }

      const value = Number(delta);
      const isStable = Math.abs(value) <= stableEps;
      if (isStable) {
        node.innerHTML = `<span class="kpi-delta-main">Igual: sin cambios relevantes</span>${buildKpiMetaHtml()}`;
        node.classList.add("state-equal");
        return;
      }

      const sign = value > 0 ? "+" : "";
      const textVal = digits === 0 ? `${sign}${formatLocaleNumber(Math.round(value), 0)}` : `${sign}${formatLocaleNumber(value, digits)}`;
      const upIsGood = !preferLower;
      const isGood = value > 0 ? upIsGood : !upIsGood;
      const label = isGood ? "Mejor" : "Peor";
      node.innerHTML = `<span class="kpi-delta-main">${label}: ${textVal}${unit}</span>${buildKpiMetaHtml()}`;
      node.classList.add(isGood ? "state-better" : "state-worse");
    }

    drawKpiDelta(kSleepDelta, relative.sleep_delta, 1, " h", false, 0.1);
    drawKpiDelta(kStepsDelta, relative.steps_delta, 0, "", false, 100);
    drawKpiDelta(kWeightDelta, relative.weight_delta, 1, " kg", true, 0.1);
    drawKpiDelta(kWHRDelta, relative.whr_delta, 3, "", true, 0.002);

    const trend = summary?.trend || {};
    const periodLabel = trend.from && trend.to
      ? `${humanDate(trend.from)} al ${humanDate(trend.to)}`
      : (dateFrom && dateTo ? `${humanDate(dateFrom)} al ${humanDate(dateTo)}` : "actual");
    if (trendTitle) trendTitle.textContent = `Resumen del período ${periodLabel}`;

    if (trendText) {
      trendText.textContent = trend.text || "Aun no hay datos suficientes para mostrar tendencia.";
      trendText.classList.remove("good", "warn", "muted");
      trendText.classList.add(trend.tone || "muted");
    }
    if (trendDelta) {
      const parts = [];
      if (trend.delta_weight != null && !Number.isNaN(Number(trend.delta_weight))) {
        parts.push(`Peso: ${fmtDelta(trend.delta_weight, 1)} kg`);
      }
      if (trend.delta_whr != null && !Number.isNaN(Number(trend.delta_whr))) {
        parts.push(`Cintura/cadera: ${fmtDelta(trend.delta_whr, 3)}`);
      }
      if (trend.delta_sleep != null && !Number.isNaN(Number(trend.delta_sleep))) {
        parts.push(`Sueño: ${fmtDelta(trend.delta_sleep, 1)} h`);
      }
      if (trend.delta_steps != null && !Number.isNaN(Number(trend.delta_steps))) {
        parts.push(`Pasos: ${fmtDelta(trend.delta_steps, 0)}`);
      }
      if (Array.isArray(trend.extra_changes)) {
        trend.extra_changes.forEach((row) => {
          const label = String(row?.label || "").trim();
          const value = String(row?.value || "").trim();
          if (label && value) parts.push(`${label}: ${value}`);
        });
      }

      if (!parts.length) {
        trendDelta.textContent = "Necesitamos al menos dos registros comparables para calcular cambios.";
      } else {
        trendDelta.innerHTML = `<span class="trend-delta-label">Cambios en el período:</span><ol class="trend-delta-list">${parts
          .map((line) => `<li class="trend-delta-item">${escapeHtml(line)}</li>`)
          .join("")}</ol>`;
      }
    }
  }

  function computeWHR(r) {
    const w = Number(r.waist_cm);
    const h = Number(r.hip_cm);
    if (!Number.isFinite(w) || !Number.isFinite(h) || h <= 0) return "—";
    return fmt3(w / h);
  }

  function importStatusPill(status) {
    const map = {
      valid: ["good", "Valida"],
      imported: ["good", "Importada"],
      conflict: ["warn", "Conflicto"],
      invalid: ["bad", "Invalida"],
    };
    const item = map[String(status || "").toLowerCase()] || ["warn", "—"];
    return `<span class="pill ${item[0]}">${item[1]}</span>`;
  }

  function importSafeVal(v) {
    return v == null || v === "" ? "—" : escapeHtml(String(v));
  }

  function renderImportSummary(summary) {
    if (!importDietSummary) return;
    const total = Number(summary?.total || 0);
    const valid = Number(summary?.valid || 0);
    const conflict = Number(summary?.conflict || 0);
    const invalid = Number(summary?.invalid || 0);
    const imported = Number(summary?.imported || 0);

    if (imported > 0) {
      importDietSummary.textContent =
        `total: ${total} | importadas: ${imported} | conflictos: ${conflict} | invalidas: ${invalid}`;
    } else {
      importDietSummary.textContent =
        `total: ${total} | validas: ${valid} | conflictos: ${conflict} | invalidas: ${invalid}`;
    }
    importDietSummary.hidden = false;
  }

  function clearImportPreview() {
    importPreviewRows = [];
    if (importPreviewBody) importPreviewBody.innerHTML = "";
    if (importPreviewWrap) importPreviewWrap.hidden = true;
    if (importDietSummary) {
      importDietSummary.hidden = true;
      importDietSummary.textContent = "";
    }
    if (importApplyBtn) importApplyBtn.disabled = true;
  }

  function renderImportPreview(payload) {
    const rows = Array.isArray(payload?.preview) ? payload.preview : [];
    const summary = payload?.summary || {};
    importPreviewRows = rows;
    renderImportSummary(summary);

    if (!importPreviewBody || !importPreviewWrap) return;
    if (!rows.length) {
      importPreviewWrap.hidden = false;
      importPreviewBody.innerHTML = `<tr><td colspan="8" class="mono">Sin filas para mostrar</td></tr>`;
      if (importApplyBtn) importApplyBtn.disabled = true;
      return;
    }

    importPreviewBody.innerHTML = rows
      .map((item) => {
        const row = item?.row || {};
        const status = String(item?.status || "").toLowerCase();
        const reason = item?.reason ? escapeHtml(String(item.reason)) : "—";
        return `
          <tr>
            <td class="mono">${importSafeVal(item?.row_number)}</td>
            <td>${importStatusPill(status)}</td>
            <td class="mono">${importSafeVal(row.log_date)}</td>
            <td>${displayFloat(row.sleep_hours, 1)}</td>
            <td>${displayInt(row.steps)}</td>
            <td>${displayFloat(row.weight_kg, 1)}</td>
            <td class="mono">${computeWHR(row)}</td>
            <td>${reason}</td>
          </tr>
        `;
      })
      .join("");

    importPreviewWrap.hidden = false;
    const validCount = rows.filter((r) => String(r?.status || "").toLowerCase() === "valid").length;
    if (importApplyBtn) importApplyBtn.disabled = validCount === 0;
  }

  function setPlanPill(node, label, tone = "") {
    if (!node) return;
    node.textContent = String(label || "—");
    node.className = "pill";
    if (tone) node.classList.add(tone);
  }

  function scoreMatches(value, expected) {
    return Math.abs(Number(value) - Number(expected)) < 0.001;
  }

  function planPillFromAdherenceScore(scoreValue, hasPlan) {
    if (!hasPlan) return { label: "Sin plan", tone: "warn" };
    if (scoreValue == null || scoreValue === "") return { label: "Pendiente", tone: "warn" };
    if (scoreMatches(scoreValue, 1)) return { label: "Cumplida", tone: "good" };
    if (scoreMatches(scoreValue, 0.5)) return { label: "Parcial", tone: "warn" };
    if (scoreMatches(scoreValue, 0)) return { label: "No cumplida", tone: "bad" };
    return { label: "Pendiente", tone: "warn" };
  }

  function planScoreLabel(v) {
    const num = Number(v);
    if (!Number.isFinite(num)) return "—";
    if (Math.abs(num - 1) < 0.001) return "Hecho";
    if (Math.abs(num - 0.5) < 0.001) return "Parcial";
    if (Math.abs(num - 0) < 0.001) return "No hecho";
    return `${num}`;
  }

  function formatPlanScore(v) {
    const num = Number(v);
    if (!Number.isFinite(num)) return "—";
    return formatLocaleNumber(num, 2);
  }

  function renderPlanAdherenceHistory(day) {
    const history = day?.adherence_history || {};
    const windowDays = parsePlanAdherenceWindow(history.window_days, planAdherenceWindowDays);
    planAdherenceWindowDays = windowDays;
    if (planAdherenceWindow) planAdherenceWindow.value = String(windowDays);

    const items = Array.isArray(history.items) ? history.items : [];
    const scoredValues = items
      .map((item) => Number(item?.total_score))
      .filter((num) => Number.isFinite(num));
    const scoredDays = Number(history.scored_days || 0);
    const totalDays = Number(history.total_days || windowDays);
    const periodFrom = humanDateDash(history.from || "");
    const periodTo = humanDateDash(history.to || "");
    const periodAvg = scoredValues.length
      ? formatPlanScore(scoredValues.reduce((acc, num) => acc + num, 0) / scoredValues.length)
      : "—";

    if (planAdherencePeriod) {
      planAdherencePeriod.textContent =
        `Resumen del período (${totalDays} días): ${periodFrom} al ${periodTo} · ${scoredDays}/${totalDays} días con puntuación · media diaria combinada ${periodAvg}.`;
    }

    if (!planAdherenceHistoryList) return;

    if (!items.length) {
      planAdherenceHistoryList.innerHTML =
        `<div class="plan-empty">Sin puntuaciones guardadas del ${escapeHtml(periodFrom)} al ${escapeHtml(periodTo)}.</div>`;
      return;
    }

    const rows = items.map((item) => {
      const diet = item.diet_score == null ? "—" : planScoreLabel(item.diet_score);
      const workout = item.workout_score == null ? "—" : planScoreLabel(item.workout_score);
      const total = item.total_score == null ? "—" : formatPlanScore(item.total_score);
      const updatedText = item.updated_at ? humanDateTime(item.updated_at) : "";
      const noteLine = item.notes
        ? `<div class="plan-adherence-item-note">${escapeHtml(item.notes)}</div>`
        : "";
      return `
        <article class="plan-adherence-item">
          <div class="plan-adherence-item-head">
            <span class="mono">${escapeHtml(humanDateDash(item.log_date || ""))}</span>
            <span class="mono">${updatedText ? `actualizado ${escapeHtml(updatedText)}` : ""}</span>
          </div>
          <div class="plan-adherence-item-body">
            <span>Dieta: <strong>${escapeHtml(diet)}</strong></span>
            <span>Entreno: <strong>${escapeHtml(workout)}</strong></span>
            <span>Media diaria combinada: <strong>${escapeHtml(total)}</strong></span>
          </div>
          ${noteLine}
        </article>
      `;
    });

    planAdherenceHistoryList.innerHTML = rows.join("");
  }

  function renderPlanMeals(diet) {
    if (!planDietMeals) return;
    if (!diet) {
      planDietMeals.innerHTML =
        `<div class="plan-empty">Importa <code>plan_diet_template.csv</code> y verás aquí tus comidas objetivo.</div>`;
      return;
    }
    const items = [
      ["Desayuno", diet.breakfast],
      ["Snack 1", diet.snack_1],
      ["Comida", diet.lunch],
      ["Snack 2", diet.snack_2],
      ["Cena", diet.dinner],
    ];
    planDietMeals.innerHTML = items
      .map(([k, v]) => `<div class="plan-meal-item"><strong>${escapeHtml(k)}:</strong> ${asDisplay(v)}</div>`)
      .join("");
  }

  function renderPlanWorkoutSessions(day) {
    if (!planWorkoutSessions) return;
    const sessions = Array.isArray(day?.workout_sessions) ? day.workout_sessions : [];
    if (!sessions.length) {
      if (planWorkoutSummary) {
        planWorkoutSummary.hidden = false;
        planWorkoutSummary.innerHTML = `<span class="plan-macro-empty">Sin entrenos cargados.</span>`;
      }
      planWorkoutSessions.innerHTML = `<div class="plan-empty">Importa <code>plan_workout_template.csv</code> para ver tus sesiones planificadas.</div>`;
      return;
    }
    if (planWorkoutSummary) {
      planWorkoutSummary.hidden = true;
      planWorkoutSummary.textContent = "";
    }
    planWorkoutSessions.innerHTML = sessions
      .map((s) => {
        const exList = Array.isArray(s.exercises) ? s.exercises : [];
        const exHtml = exList.length
          ? exList
            .map((ex) => {
              const range =
                ex.target_reps_min != null && ex.target_reps_max != null
                  ? `${ex.target_reps_min}-${ex.target_reps_max}`
                  : (ex.target_reps_min != null ? `${ex.target_reps_min}` : "—");
              const sets = ex.target_sets != null ? `${ex.target_sets}x${range}` : `reps ${range}`;
              const weight = ex.target_weight_kg != null ? ` · ${ex.target_weight_kg}kg` : "";
              const rpe = ex.target_rpe != null ? ` · RPE ${ex.target_rpe}` : "";
              const intensity = ex.intensity_target ? ` · ${escapeHtml(String(ex.intensity_target))}` : "";
              const progressBits = [ex.progression_weight_rule, ex.progression_reps_rule]
                .filter((x) => String(x || "").trim())
                .map((x) => escapeHtml(String(x)))
                .join(" · ");
              return `
                <li>
                  <div><strong>${escapeHtml(String(ex.exercise_name || "Ejercicio"))}</strong>: ${sets}${weight}${rpe}${intensity}</div>
                  ${progressBits ? `<div class="plan-ex-note mono">Progresión: ${progressBits}</div>` : ""}
                </li>
              `;
            })
            .join("")
          : `<li class="mono">Sin ejercicios definidos para esta sesión.</li>`;

        const sessionMeta = [
          s.warmup ? `<div><strong>Warmup:</strong> ${escapeHtml(s.warmup)}</div>` : "",
          s.class_sessions ? `<div><strong>Clases:</strong> ${escapeHtml(s.class_sessions)}</div>` : "",
          s.cardio ? `<div><strong>Cardio:</strong> ${escapeHtml(s.cardio)}</div>` : "",
          s.mobility_cooldown ? `<div><strong>Cooldown:</strong> ${escapeHtml(s.mobility_cooldown)}</div>` : "",
          s.additional_exercises ? `<div><strong>Adicionales:</strong> ${escapeHtml(s.additional_exercises)}</div>` : "",
          s.notes ? `<div><strong>Notas:</strong> ${escapeHtml(s.notes)}</div>` : "",
        ]
          .filter(Boolean)
          .join("");

        const typeMeta = sessionTypeMeta(s.session_type);
        const planSessionId = String(s.plan_session_id || "").trim();
        const deleteSessionBtn = planSessionId
          ? `<button class="btn ghost danger plan-session-delete-btn" type="button" data-plan-delete-session="${escapeHtml(planSessionId)}">Eliminar sesión</button>`
          : "";
        return `
          <article class="plan-session">
            <div class="plan-session-head">
              <div class="plan-session-badges">
                <span class="pill">${escapeHtml(String(s.plan_session_id || "S"))}</span>
                <span class="pill ${typeMeta.cls}">${typeMeta.label}</span>
              </div>
              ${deleteSessionBtn}
            </div>
            <ul class="plan-ex-list">${exHtml}</ul>
            <div class="plan-session-meta">${sessionMeta || `<div class="mono">Sin notas adicionales.</div>`}</div>
          </article>
        `;
      })
      .join("");
  }

  function renderPlanDay(payload) {
    const day = payload && typeof payload === "object" ? payload : { log_date: isoToday() };
    currentPlanDay = day;
    const logDate = String(day.log_date || isoToday());
    if (planDayDate) planDayDate.value = logDate;

    const hasDietPlan = !!day?.coverage?.has_diet_plan;
    const hasWorkoutPlan = !!day?.coverage?.has_workout_plan;
    const dietLogged = !!day?.actual?.diet_logged;
    const workoutLogged = Number(day?.actual?.workout_sessions_logged || 0);

    if (planHubSub) {
      planHubSub.textContent =
        `Plan para ${humanDate(logDate)} · check-in registrado: ${dietLogged ? "sí" : "no"} · sesiones registradas: ${workoutLogged}.`;
    }

    if (planDietMacros) {
      if (hasDietPlan && day.diet) {
        const d = day.diet;
        const chips = [
          { label: "Calorías", value: `${fmt0(d.calories_target_kcal)} kcal` },
          { label: "Proteínas", value: fmtGrams(d.protein_target_g) },
          { label: "Carbs", value: fmtGrams(d.carbs_target_g) },
          { label: "Grasas", value: fmtGrams(d.fat_target_g) },
        ];
        planDietMacros.innerHTML = chips
          .map((chip) => (
            `<span class="plan-macro-chip">` +
            `<span class="plan-macro-chip-label">${escapeHtml(chip.label)}:</span> ` +
            `<span class="plan-macro-chip-value">${escapeHtml(chip.value)}</span>` +
            `</span>`
          ))
          .join("");
      } else {
        planDietMacros.innerHTML = `<span class="plan-macro-empty">Sin objetivos cargados.</span>`;
      }
    }
    renderPlanMeals(day.diet || null);
    renderPlanWorkoutSessions(day);

    const adherence = day?.adherence || {};
    const dietPill = planPillFromAdherenceScore(adherence.diet_score, hasDietPlan);
    const workoutPill = planPillFromAdherenceScore(adherence.workout_score, hasWorkoutPlan);
    setPlanPill(planDietActualPill, dietPill.label, dietPill.tone);
    setPlanPill(planWorkoutActualPill, workoutPill.label, workoutPill.tone);
    if (planDietScore) planDietScore.value = adherence.diet_score == null ? "" : String(adherence.diet_score);
    if (planWorkoutScore) planWorkoutScore.value = adherence.workout_score == null ? "" : String(adherence.workout_score);
    if (planAdherenceNotes) planAdherenceNotes.value = adherence.notes || "";

    renderPlanAdherenceHistory(day);
  }

  function dietPhotoCell(r) {
    if (r.photo_url) {
      const url = escapeHtml(r.photo_url);
      const date = escapeHtml(r.log_date || "");
      return `
        <button class="photo-link photo-pill" type="button" data-photo-url="${url}" data-photo-date="${date}">
          Ver foto
        </button>`;
    }
    return "";
  }

  function dietRow(r) {
    const dateRaw = String(r.log_date || "");
    const dateIso = escapeHtml(dateRaw);
    const dateDisplay = escapeHtml(humanDateDash(dateRaw));
    const alcohol = r.alcohol_units == null || r.alcohol_units === "" ? "0" : escapeHtml(String(r.alcohol_units));
    return `
      <tr class="data-row" data-kind="diet" data-log-date="${dateIso}" title="Click para editar">
        <td class="mono" data-label="Fecha">${dateDisplay}</td>
        <td data-label="Sueño">${displayFloat(r.sleep_hours, 1)}</td>
        <td data-label="Calidad">${asDisplay(r.sleep_quality)}</td>
        <td data-label="Pasos">${displayInt(r.steps)}</td>
        <td data-label="Peso">${displayFloat(r.weight_kg, 1)}</td>
        <td data-label="Cintura">${displayFloat(r.waist_cm, 1)}</td>
        <td data-label="Cadera">${displayFloat(r.hip_cm, 1)}</td>
        <td class="mono" data-label="WHR">${computeWHR(r)}</td>
        <td data-label="Foto">${dietPhotoCell(r)}</td>
        <td class="mono" data-label="Alcohol">${displayInt(alcohol)}</td>
      </tr>
    `;
  }

  function workoutRow(r) {
    const dateRaw = String(r.log_date || "");
    const dateIso = escapeHtml(dateRaw);
    const dateDisplay = escapeHtml(humanDateDash(dateRaw));
    const sessionId = escapeHtml(String(r.session_id || ""));
    return `
      <tr class="data-row" data-kind="workout" data-log-date="${dateIso}" data-session-id="${sessionId}" title="Click para editar">
        <td class="mono" data-label="Fecha">${dateDisplay}</td>
        <td data-label="Sesión">${pillSession(r.session_order)}</td>
        <td data-label="Hecho">${pillDone(r.session_done_yn)}</td>
        <td data-label="Tipo">${pillType(r.session_type)}</td>
        <td data-label="Clase / foco">${asDisplay(r.class_done)}</td>
        <td data-label="RPE">${asDisplay(r.rpe_session)}</td>
        <td data-label="Ejercicios">${workoutExercisesCell(r)}</td>
        <td data-label="Notas">${asDisplay(r.notes)}</td>
      </tr>
    `;
  }

  function renderDiet(rows) {
    currentDietRows = Array.isArray(rows) ? [...rows] : [];
    renderViewCounts();
    if (!dietTable) return;
    const tb = dietTable.querySelector("tbody");
    if (!tb) return;

    if (!currentDietRows.length) {
      tb.innerHTML = `<tr><td colspan="10" class="mono">Sin registros</td></tr>`;
      return;
    }
    tb.innerHTML = currentDietRows.map(dietRow).join("");
  }

  function renderWorkout(rows) {
    currentWorkoutRows = Array.isArray(rows) ? [...rows] : [];
    renderViewCounts();
    if (!workTable) return;
    const tb = workTable.querySelector("tbody");
    if (!tb) return;

    if (!currentWorkoutRows.length) {
      tb.innerHTML = `<tr><td colspan="8" class="mono">Sin registros</td></tr>`;
      return;
    }
    tb.innerHTML = currentWorkoutRows.map(workoutRow).join("");
  }

  function filterTable(tableNode, query) {
    if (!tableNode) return;
    const tb = tableNode.querySelector("tbody");
    if (!tb) return;

    const q = (query || "").trim().toLowerCase();
    const trs = tb.querySelectorAll("tr");
    trs.forEach((tr) => {
      const txt = `${tr.innerText || ""} ${tr.dataset.logDate || ""}`.toLowerCase();
      tr.style.display = txt.includes(q) ? "" : "none";
    });
  }

  async function fetchJSON(url) {
    const res = await fetch(url);
    const text = await res.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (_) {
      data = {};
    }
    if (res.status === 401) {
      const next = `${window.location.pathname}${window.location.search}`;
      window.location.href = `/login?next=${encodeURIComponent(next)}`;
      throw new Error("No autenticado");
    }
    if (!res.ok) {
      const msg = data.error || data.message || text || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  async function refreshState() {
    setSyncStatus("Sincronizando...", "warn");
    const dietLabel = $("dietLimitLabel");
    const workLabel = $("workLimitLabel");
    if (!isSummaryCustomMode()) {
      summaryWindowDays = parseLimitValue(summaryModeSelect?.value, summaryWindowDays);
      if (summaryModeSelect) summaryModeSelect.value = String(summaryWindowDays);
    }
    const qp = new URLSearchParams();
    qp.set("summary_days", String(summaryWindowDays));
    if (summaryRangeFrom && summaryRangeTo) {
      qp.set("date_from", summaryRangeFrom);
      qp.set("date_to", summaryRangeTo);
    }
    const q = qp.toString();
    const qSuffix = q ? `&${q}` : "";

    try {
      const [s1, s2] = await Promise.all([
        fetchJSON(`/api/state?limit=${dietLimit}${qSuffix}`),
        fetchJSON(`/api/state?limit=${workLimit}${qSuffix}`),
      ]);

      latestSummary = s1.summary || {};
      renderSummary(latestSummary);
      renderDiet(s1.diet || []);
      renderWorkout(s2.workout || []);
      currentPlanDay = s1.plan_today || currentPlanDay || { log_date: isoToday() };
      renderPlanDay(currentPlanDay);
      const selectedPlanDate = String(planDayDate?.value || "").trim();
      if (
        /^\d{4}-\d{2}-\d{2}$/.test(selectedPlanDate)
        && selectedPlanDate !== String(currentPlanDay?.log_date || "")
      ) {
        await fetchPlanDay(selectedPlanDate);
      }
      lightboxItems = normalizePhotoItems(s1.photos || [], s1.diet || []);
      renderPerformanceChart(chartMetric);

      if (dietLabel) dietLabel.textContent = String(dietLimit);
      if (workLabel) workLabel.textContent = String(workLimit);
      if (dietLimitSelect) dietLimitSelect.value = String(dietLimit);
      if (workLimitSelect) workLimitSelect.value = String(workLimit);
      setSyncStatus(syncOkStatus(s1.diet || [], s2.workout || []), "ok");
    } catch (err) {
      setSyncStatus("Error de sincronizacion", "bad");
      throw err;
    }
  }

  function openPhotoGallery() {
    if (!Array.isArray(lightboxItems) || !lightboxItems.length) {
      lightboxItems = normalizePhotoItems([], currentDietRows);
    }
    if (!Array.isArray(lightboxItems) || !lightboxItems.length) {
      showToast("Galería", "Aún no hay fotos guardadas.");
      return;
    }
    const first = lightboxItems[0];
    openLightbox(first.photo_url, first.label || `Foto ${first.log_date || ""}`.trim(), first.log_date || "");
  }

  function remember(form, key) {
    if (!form) return;
    const fd = new FormData(form);
    const obj = {};
    for (const [k, v] of fd.entries()) {
      if (k === "photo" || k === "entry_mode" || k === "session_id" || k === "exercises_json") continue;
      obj[k] = v;
    }
    try {
      localStorage.setItem(key, JSON.stringify(obj));
    } catch (_) {}
  }

  function restore(form, key) {
    if (!form) return;
    let raw = "";
    try {
      raw = localStorage.getItem(key) || "";
    } catch (_) {}
    if (!raw) return;

    try {
      const obj = JSON.parse(raw);
      for (const [k, v] of Object.entries(obj)) {
        setFormValue(form, k, v);
      }
    } catch (_) {}
  }

  // ----------------------------
  // Photo preview / lightbox
  // ----------------------------
  function updateExistingPhotoButton(url, caption, logDate = "") {
    if (!photoExistingWrap || !photoExistingBtn) return;
    if (url) {
      photoExistingWrap.hidden = false;
      photoExistingBtn.dataset.photoUrl = url;
      photoExistingBtn.dataset.photoCaption = caption || "Foto actual";
      if (logDate) photoExistingBtn.dataset.photoDate = logDate;
      else photoExistingBtn.removeAttribute("data-photo-date");
    } else {
      photoExistingWrap.hidden = true;
      photoExistingBtn.removeAttribute("data-photo-url");
      photoExistingBtn.removeAttribute("data-photo-caption");
      photoExistingBtn.removeAttribute("data-photo-date");
    }
    syncPhotoClearButton();
  }

  function currentExistingPhotoURL() {
    return String(photoExistingBtn?.dataset?.photoUrl || "").trim();
  }

  function hasPendingPhotoSelection() {
    return !!previewObjectURL || !!photoFile?.files?.length;
  }

  function syncPhotoClearButton() {
    if (!photoClear) return;
    const hasExisting = !!currentExistingPhotoURL();
    const hasPending = hasPendingPhotoSelection();
    const show = hasExisting || hasPending;
    photoClear.hidden = !show;
    if (!show) return;
    photoClear.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none"><path d="M18 6 6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      ${hasPending ? "Quitar selección" : "Quitar foto"}
    `;
  }

  function restoreExistingPhotoPreview() {
    const existingURL = currentExistingPhotoURL();
    if (!existingURL) return false;
    if (photoPreview) {
      photoPreview.src = existingURL;
      photoPreview.classList.add("show");
    }
    if (photoMeta) photoMeta.textContent = "Foto actual del registro";
    if (photoYN) photoYN.value = "Y";
    return true;
  }

  function clearPreview({ preservePhotoYN = false, clearFileInput = true } = {}) {
    if (previewObjectURL) {
      URL.revokeObjectURL(previewObjectURL);
      previewObjectURL = "";
    }
    if (clearFileInput && photoFile) photoFile.value = "";
    if (photoPreview) {
      photoPreview.removeAttribute("src");
      photoPreview.classList.remove("show");
    }
    if (photoMeta) photoMeta.textContent = "Sin archivo";
    if (!preservePhotoYN && photoYN) photoYN.value = "";
    syncPhotoClearButton();
  }

  function setPreviewFromFile(file) {
    if (!file) {
      clearPreview();
      return;
    }
    // Mantén el file input para que FormData realmente incluya el archivo.
    clearPreview({ preservePhotoYN: true, clearFileInput: false });
    previewObjectURL = URL.createObjectURL(file);
    if (photoPreview) {
      photoPreview.src = previewObjectURL;
      photoPreview.classList.add("show");
    }
    if (photoMeta) {
      photoMeta.textContent = `${file.name} · ${(file.size / (1024 * 1024)).toFixed(2)} MB`;
    }
    if (photoYN) photoYN.value = "Y";
    syncPhotoClearButton();
  }

  function listCompareCandidates(index) {
    if (!Array.isArray(lightboxItems) || !lightboxItems.length) return [];
    return lightboxItems.filter((item, i) => i !== index && item?.photo_url);
  }

  function pickDefaultCompareTarget(current, candidates) {
    if (!current || !Array.isArray(candidates) || !candidates.length) return null;
    const older = candidates.find((item) => String(item.log_date || "") < String(current.log_date || ""));
    return older || candidates[0] || null;
  }

  function syncCompareSelect(current, candidates) {
    if (!lightboxCompareSelect) return null;
    if (!Array.isArray(candidates) || !candidates.length) {
      lightboxCompareSelect.innerHTML = "";
      lightboxCompareSelect.disabled = true;
      return null;
    }

    const selectedCandidate =
      candidates.find((item) => String(item.log_date || "") === String(lightboxCompareTargetDate || "")) ||
      pickDefaultCompareTarget(current, candidates);
    lightboxCompareTargetDate = selectedCandidate?.log_date || "";

    lightboxCompareSelect.innerHTML = candidates
      .map((item) => {
        const date = String(item.log_date || "");
        const isSelected = date === lightboxCompareTargetDate ? " selected" : "";
        return `<option value="${escapeHtml(date)}"${isSelected}>${escapeHtml(humanDate(date))}</option>`;
      })
      .join("");
    lightboxCompareSelect.disabled = false;
    return selectedCandidate || null;
  }

  function renderLightboxCompare(index) {
    if (!lightboxCompareWrap || !lightboxCompareToggle) return;
    const current = lightboxItems[index];
    const candidates = listCompareCandidates(index);

    if (!current || !candidates.length) {
      lightboxCompareWrap.hidden = true;
      lightboxCompareOpen = false;
      if (lightboxShell) lightboxShell.classList.remove("compare-open");
      lightboxCompareToggle.hidden = true;
      lightboxCompareToggle.disabled = true;
      lightboxCompareToggle.textContent = "Comparar";
      if (lightboxCompareSelect) {
        lightboxCompareSelect.innerHTML = "";
        lightboxCompareSelect.disabled = true;
      }
      return;
    }

    lightboxCompareToggle.hidden = false;
    lightboxCompareToggle.disabled = false;
    lightboxCompareToggle.textContent = lightboxCompareOpen ? "Ocultar comparativa" : "Comparar";
    lightboxCompareWrap.hidden = !lightboxCompareOpen;
    if (!lightboxCompareOpen) {
      if (lightboxShell) lightboxShell.classList.remove("compare-open");
      return;
    }
    if (lightboxShell) lightboxShell.classList.add("compare-open");

    const target = syncCompareSelect(current, candidates);
    if (!target) return;

    if (compareBeforeImg) compareBeforeImg.src = target.photo_url;
    if (compareAfterImg) compareAfterImg.src = current.photo_url;
    if (compareBeforeLabel) compareBeforeLabel.textContent = `Antes · ${humanDate(target.log_date || "")}`;
    if (compareAfterLabel) compareAfterLabel.textContent = `Después · ${humanDate(current.log_date || "")}`;
    if (lightboxCompareLabel) {
      lightboxCompareLabel.textContent = `${humanDate(target.log_date || "")} vs ${humanDate(current.log_date || "")}`;
    }
    requestAnimationFrame(() => {
      lightboxCompareWrap?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  function renderLightboxStrip(index) {
    if (!lightboxThumbs) return;
    if (!Array.isArray(lightboxItems) || !lightboxItems.length) {
      lightboxThumbs.innerHTML = "";
      return;
    }
    const maxThumbs = 8;
    const start = Math.max(0, Math.min(index - 3, lightboxItems.length - maxThumbs));
    const slice = lightboxItems.slice(start, start + maxThumbs);
    lightboxThumbs.innerHTML = slice
      .map((item, i) => {
        const realIdx = start + i;
        const active = realIdx === index ? "active" : "";
        return `
          <button class="lightbox-thumb ${active}" type="button" data-lightbox-index="${realIdx}" aria-label="Foto ${escapeHtml(item.log_date)}">
            <img src="${escapeHtml(item.photo_url)}" alt="Miniatura ${escapeHtml(item.log_date)}"/>
          </button>
        `;
      })
      .join("");
  }

  function renderLightboxAt(index) {
    if (!photoLightbox || !lightboxImg || !Array.isArray(lightboxItems) || !lightboxItems.length) return;
    const nextIndex = Math.max(0, Math.min(index, lightboxItems.length - 1));
    lightboxIndex = nextIndex;
    const item = lightboxItems[nextIndex];
    const parsed = String(item.photo_url || "").split("?")[0].split("#")[0];
    const filename = parsed.split("/").pop() || "foto";
    const ext = filename.includes(".") ? filename.split(".").pop() : "";

    lightboxImg.src = item.photo_url;
    if (lightboxCaption) lightboxCaption.textContent = item.label || `Foto ${item.log_date}`;
    if (lightboxMetaTag) lightboxMetaTag.textContent = ext ? ext.toUpperCase() : "foto";
    if (lightboxMetaDetails) {
      const hasWeight = item.weight_kg != null && !Number.isNaN(Number(item.weight_kg));
      const hasWhr = item.whr != null && !Number.isNaN(Number(item.whr));
      const weightTxt = hasWeight ? `${Number(item.weight_kg).toFixed(1)} kg` : "—";
      const whrTxt = hasWhr ? fmt3(Number(item.whr)) : "—";
      const original = String(item.original_name || "").trim();
      const originTxt = original || filename;
      lightboxMetaDetails.textContent =
        `Fecha ${item.log_date ? humanDate(item.log_date) : "—"} · Peso ${weightTxt} · WHR ${whrTxt} · ${originTxt}`;
    }
    if (lightboxDownload) {
      lightboxDownload.href = item.photo_url;
      lightboxDownload.download = filename;
    }
    if (lightboxPrev) lightboxPrev.disabled = nextIndex >= lightboxItems.length - 1;
    if (lightboxNext) lightboxNext.disabled = nextIndex <= 0;
    if (lightboxCount) lightboxCount.textContent = `${nextIndex + 1} de ${lightboxItems.length}`;

    renderLightboxStrip(nextIndex);
    renderLightboxCompare(nextIndex);
  }

  function openLightbox(url, caption, dateHint) {
    if (!url || !photoLightbox || !lightboxImg) return;
    if (!Array.isArray(lightboxItems) || !lightboxItems.length) {
      lightboxItems = normalizePhotoItems([], currentDietRows);
    }
    const date = isoLike(dateHint);
    let idx = -1;
    if (date) idx = lightboxItems.findIndex((p) => p.log_date === date);
    if (idx < 0) idx = lightboxItems.findIndex((p) => String(p.photo_url) === String(url));
    if (idx < 0) {
      const parsed = String(url || "").split("?")[0].split("#")[0];
      const fallbackName = parsed.split("/").pop() || "";
      lightboxItems.unshift({
        log_date: date || "",
        photo_url: url,
        label: caption || (date ? `Foto ${date}` : "Vista previa"),
        original_name: fallbackName,
        weight_kg: null,
        whr: null,
      });
      idx = 0;
    }
    lightboxCompareOpen = false;
    lightboxCompareTargetDate = "";
    renderLightboxAt(idx);
    safeOpen(photoLightbox);
  }

  function openReplaceConfirm(payload, onConfirm) {
    if (!replaceConfirmModal) return;
    pendingReplaceAction = typeof onConfirm === "function" ? onConfirm : null;

    const dateLabel = payload?.log_date ? `Ya existe una foto para ${payload.log_date}.` : "Ya existe una foto para esa fecha.";
    if (replaceConfirmText) replaceConfirmText.textContent = dateLabel;

    const existingURL = payload?.existing_photo_url || "";
    if (replaceConfirmImg) {
      if (existingURL) {
        replaceConfirmImg.src = existingURL;
        replaceConfirmImg.classList.add("show");
      } else {
        replaceConfirmImg.removeAttribute("src");
        replaceConfirmImg.classList.remove("show");
      }
    }
    safeOpen(replaceConfirmModal);
  }

  // ----------------------------
  // POST helpers
  // ----------------------------
  async function postJSON(url, data) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const text = await res.text();
    let payload = {};
    try {
      payload = text ? JSON.parse(text) : {};
    } catch (_) {
      payload = {};
    }
    if (res.status === 401) {
      const next = `${window.location.pathname}${window.location.search}`;
      window.location.href = `/login?next=${encodeURIComponent(next)}`;
      throw new Error("No autenticado");
    }
    if (!res.ok) {
      const msg = payload.error || payload.message || text || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return payload;
  }

  async function postMultipart(url, form) {
    const fd = new FormData(form);
    const res = await fetch(url, { method: "POST", body: fd });
    const text = await res.text();
    let payload = {};
    try {
      payload = text ? JSON.parse(text) : {};
    } catch (_) {
      payload = {};
    }
    if (res.status === 401) {
      const next = `${window.location.pathname}${window.location.search}`;
      window.location.href = `/login?next=${encodeURIComponent(next)}`;
      return { ok: false, status: 401, payload, text };
    }
    return { ok: res.ok, status: res.status, payload, text };
  }

  async function deleteJSON(url) {
    const res = await fetch(url, { method: "DELETE" });
    const text = await res.text();
    let payload = {};
    try {
      payload = text ? JSON.parse(text) : {};
    } catch (_) {
      payload = {};
    }
    if (res.status === 401) {
      const next = `${window.location.pathname}${window.location.search}`;
      window.location.href = `/login?next=${encodeURIComponent(next)}`;
      throw new Error("No autenticado");
    }
    if (!res.ok) {
      const msg = payload.error || payload.message || text || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return payload;
  }

  function supplementActivePill(v) {
    const yn = String(v || "Y").toUpperCase() === "N" ? "N" : "Y";
    return yn === "Y" ? `<span class="pill good">Sí</span>` : `<span class="pill warn">No</span>`;
  }

  function supplementStatusPill(status, label) {
    const s = String(status || "").toLowerCase();
    if (s === "good") return `<span class="pill good">${escapeHtml(label || "OK")}</span>`;
    if (s === "warn") return `<span class="pill warn">${escapeHtml(label || "Parcial")}</span>`;
    if (s === "bad") return `<span class="pill bad">${escapeHtml(label || "Baja")}</span>`;
    return `<span class="pill">${escapeHtml(label || "—")}</span>`;
  }

  function renderSuppHistory(rows) {
    suppHistoryRows = Array.isArray(rows) ? [...rows] : [];
    if (suppLimitLabel) suppLimitLabel.textContent = String(suppLimit);
    if (!suppHistoryTable) return;
    const tb = suppHistoryTable.querySelector("tbody");
    if (!tb) return;

    if (!suppHistoryRows.length) {
      tb.innerHTML = `<tr><td colspan="7" class="mono">Sin registros</td></tr>`;
      if (suppCountMeta) suppCountMeta.textContent = "Sin registros en esta vista.";
      return;
    }

    if (suppCountMeta) {
      suppCountMeta.textContent = `${suppHistoryRows.length} registros cargados.`;
    }

    tb.innerHTML = suppHistoryRows
      .map((row) => {
        const date = String(row.log_date || "");
        const dateDisplay = humanDateDash(date);
        const target = Number(row.target_doses || 0);
        const taken = Number(row.taken_doses || 0);
        const adh = String(row.adherence_label || "—");
        const state = supplementStatusPill(row.status, row.status === "good" ? "Bien" : (row.status === "warn" ? "Parcial" : (row.status === "bad" ? "Baja" : "—")));
        return `
          <tr class="data-row" data-kind="supplement-day" data-log-date="${escapeHtml(date)}">
            <td class="mono">${escapeHtml(dateDisplay)}</td>
            <td class="mono">${target}</td>
            <td class="mono">${taken}</td>
            <td class="mono">${escapeHtml(adh)}</td>
            <td>${state}</td>
            <td class="supp-history-detail">${asDisplay(row.details)}</td>
            <td class="supp-history-notes">${asDisplay(row.notes)}</td>
          </tr>
        `;
      })
      .join("");
  }

  function resetSuppCatalogForm() {
    if (!suppCatalogForm) return;
    suppCatalogForm.reset();
    setFormValue(suppCatalogForm, "supplement_id", "");
    setFormValue(suppCatalogForm, "active_yn", "Y");
    setSuppCatalogAlert("");
    const saveBtn = $("suppSaveBtn");
    if (saveBtn) saveBtn.textContent = "Guardar suplemento";
    if (suppCancelEditBtn) suppCancelEditBtn.hidden = true;
  }

  function fillSuppCatalogForm(row) {
    if (!suppCatalogForm || !row) return;
    setFormValue(suppCatalogForm, "supplement_id", row.supplement_id);
    setFormValue(suppCatalogForm, "name", row.name || "");
    setFormValue(suppCatalogForm, "doses_per_day", row.doses_per_day);
    setFormValue(suppCatalogForm, "active_yn", row.active_yn || "Y");
    setFormValue(suppCatalogForm, "notes", row.notes || "");
    setSuppCatalogAlert("");
    const saveBtn = $("suppSaveBtn");
    if (saveBtn) saveBtn.textContent = "Actualizar suplemento";
    if (suppCancelEditBtn) suppCancelEditBtn.hidden = false;
  }

  function renderSuppCatalog(rows) {
    suppCatalogRows = Array.isArray(rows) ? [...rows] : [];
    if (!suppCatalogTable) return;
    const tb = suppCatalogTable.querySelector("tbody");
    if (!tb) return;

    if (!suppCatalogRows.length) {
      tb.innerHTML = `<tr><td colspan="5" class="mono">Sin suplementos configurados</td></tr>`;
      return;
    }

    tb.innerHTML = suppCatalogRows
      .map((row) => {
        const sid = escapeHtml(String(row.supplement_id || ""));
        return `
          <tr data-supplement-id="${sid}">
            <td>${asDisplay(row.name)}</td>
            <td class="mono">${asDisplay(row.doses_per_day)}</td>
            <td>${supplementActivePill(row.active_yn)}</td>
            <td>${asDisplay(row.notes)}</td>
            <td class="supp-actions-cell">
              <button class="btn ghost" type="button" data-supp-action="edit" data-supplement-id="${sid}">Editar</button>
              <button class="btn ghost danger" type="button" data-supp-action="delete" data-supplement-id="${sid}">Eliminar</button>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function currentSuppDate() {
    const value = String(suppDayDate?.value || "").trim();
    if (value && /^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
    return isoToday();
  }

  function renderSuppDay(payload) {
    suppDayRows = Array.isArray(payload?.entries) ? [...payload.entries] : [];
    if (suppDayDate && payload?.log_date) suppDayDate.value = String(payload.log_date);

    if (!suppDayTable) return;
    const tb = suppDayTable.querySelector("tbody");
    if (!tb) return;

    if (!suppDayRows.length) {
      const catalogCount = suppCatalogRows.length;
      const activeCount = suppCatalogRows.filter((r) => String(r?.active_yn || "Y").toUpperCase() === "Y").length;
      const emptyMsg = catalogCount > 0 && activeCount === 0
        ? "No hay suplementos activos para esa fecha. Abre Catálogo y marca \"Disponible\" en Sí."
        : "No hay suplementos configurados para esa fecha.";
      tb.innerHTML = `<tr><td colspan="4" class="mono">${escapeHtml(emptyMsg)}</td></tr>`;
      if (suppDayTotals) {
        suppDayTotals.textContent = catalogCount > 0
          ? `${activeCount} suplementos activos de ${catalogCount} configurados en catálogo.`
          : "Sin suplementos configurados.";
      }
      if (suppDayDeleteBtn) suppDayDeleteBtn.hidden = true;
      return;
    }

    tb.innerHTML = suppDayRows
      .map((row) => {
        const sid = escapeHtml(String(row.supplement_id || ""));
        const target = Number(row.doses_per_day || 0);
        const taken = Number(row.doses_taken || 0);
        const notes = escapeHtml(String(row.notes || ""));
        return `
          <tr data-supplement-id="${sid}">
            <td>${asDisplay(row.name)}</td>
            <td class="mono">${target}</td>
            <td>
              <input
                type="number"
                min="0"
                max="24"
                step="1"
                data-supp-field="doses_taken"
                value="${Number.isFinite(taken) ? taken : 0}"
              />
            </td>
            <td>
              <input
                type="text"
                data-supp-field="notes"
                value="${notes}"
                placeholder="opcional"
              />
            </td>
          </tr>
        `;
      })
      .join("");

    const totals = payload?.totals || {};
    const target = Number(totals.target_doses || 0);
    const taken = Number(totals.taken_doses || 0);
    const basePctRaw = target > 0 ? Math.min((taken / target), 1) * 100 : NaN;
    const basePct = Number.isFinite(basePctRaw) ? `${basePctRaw.toFixed(0)}%` : "—";
    const extra = Math.max(0, taken - target);
    if (suppDayTotals) {
      suppDayTotals.textContent = `Objetivo del dia: ${target} tomas · Realizadas: ${taken} · Adherencia base: ${basePct}${extra > 0 ? ` · Extra: +${extra}` : ""}`;
    }
    if (suppDayDeleteBtn) suppDayDeleteBtn.hidden = !payload?.has_logs;
  }

  async function refreshSuppCatalog() {
    const out = await fetchJSON("/api/supplements/config");
    renderSuppCatalog(out.supplements || []);
    return out.supplements || [];
  }

  async function refreshSuppHistory(limitValue = suppLimit) {
    suppLimit = parseLimitValue(limitValue, suppLimit);
    if (suppLimitSelect) suppLimitSelect.value = String(suppLimit);
    const out = await fetchJSON(`/api/supplements/history?limit=${encodeURIComponent(String(suppLimit))}`);
    renderSuppHistory(out.rows || []);
    if (suppSearch && suppSearch.value) filterTable(suppHistoryTable, suppSearch.value);
    return out.rows || [];
  }

  async function refreshSuppDay(logDate) {
    const date = (logDate && /^\d{4}-\d{2}-\d{2}$/.test(logDate)) ? logDate : currentSuppDate();
    const out = await fetchJSON(`/api/supplements/day?log_date=${encodeURIComponent(date)}`);
    renderSuppDay(out || {});
    return out;
  }

  async function openSupplementsView({ scroll = true } = {}) {
    setActiveView("supplements");
    await refreshSuppHistory(suppLimit);
    const section = document.querySelector(".app-view[data-view='supplements']");
    if (scroll) section?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function openSuppDayEditor(forceDate = "") {
    setActiveView("supplements");
    const date = /^\d{4}-\d{2}-\d{2}$/.test(String(forceDate || ""))
      ? String(forceDate)
      : (suppDayDate?.value || isoToday());
    if (suppDayDate) suppDayDate.value = date;
    await Promise.all([refreshSuppCatalog(), refreshSuppDay(date)]);
    safeOpen(suppDayModal);
  }

  async function openSuppCatalogEditor() {
    resetSuppCatalogForm();
    await refreshSuppCatalog();
    safeOpen(suppCatalogModal);
  }

  async function saveSuppCatalogFromForm() {
    if (!suppCatalogForm) return;
    const fd = new FormData(suppCatalogForm);
    const data = {};
    for (const [k, v] of fd.entries()) data[k] = v;
    const currentId = data.supplement_id ? Number(data.supplement_id) : null;
    const normalizedName = String(data.name || "").trim().replace(/\s+/g, " ").toLowerCase();
    if (normalizedName && !currentId) {
      const existing = suppCatalogRows.find((row) => {
        const rowName = String(row?.name || "").trim().replace(/\s+/g, " ").toLowerCase();
        return rowName === normalizedName;
      });
      if (existing) {
        fillSuppCatalogForm(existing);
        setSuppCatalogAlert("Ese suplemento ya existe. Te lo cargué para editar: ajusta los campos y pulsa \"Actualizar suplemento\".");
        return;
      }
    }
    const payload = {
      supplement_id: currentId,
      name: data.name,
      doses_per_day: data.doses_per_day,
      active_yn: data.active_yn,
      notes: data.notes,
    };
    const out = await postJSON("/api/supplements/config", payload);
    await refreshSuppCatalog();
    await refreshSuppDay(currentSuppDate());
    await refreshSuppHistory(suppLimit);
    const mode = out?.entry_mode === "edit" ? "actualizado" : "guardado";
    showToast("Suplemento", `${out?.supplement?.name || "Suplemento"} ${mode}.`);
    setSuppCatalogAlert("");
    resetSuppCatalogForm();
  }

  async function deleteSuppCatalog(supplementId) {
    const sid = Number(supplementId);
    if (!Number.isInteger(sid) || sid < 1) return;
    const row = suppCatalogRows.find((r) => Number(r.supplement_id) === sid);
    const name = row?.name || `ID ${sid}`;
    const ok = window.confirm(`Vas a eliminar "${name}" del catalogo. Esta accion no se puede deshacer.`);
    if (!ok) return;
    await deleteJSON(`/api/supplements/config/${encodeURIComponent(String(sid))}`);
    await refreshSuppCatalog();
    await refreshSuppDay(currentSuppDate());
    await refreshSuppHistory(suppLimit);
    showToast("Suplemento eliminado", name);
    if (String($("supplementId")?.value || "") === String(sid)) {
      resetSuppCatalogForm();
    }
  }

  function collectSuppDayEntries() {
    if (!suppDayTable) return [];
    const tb = suppDayTable.querySelector("tbody");
    if (!tb) return [];
    const rows = Array.from(tb.querySelectorAll("tr[data-supplement-id]"));
    const entries = [];
    rows.forEach((tr) => {
      const sid = Number(tr.dataset.supplementId || 0);
      if (!sid) return;
      const dosesNode = tr.querySelector("[data-supp-field='doses_taken']");
      const notesNode = tr.querySelector("[data-supp-field='notes']");
      const dosesRaw = String(dosesNode?.value || "").trim();
      const dosesTaken = dosesRaw === "" ? 0 : Number(dosesRaw);
      entries.push({
        supplement_id: sid,
        doses_taken: Number.isFinite(dosesTaken) ? Math.max(0, Math.round(dosesTaken)) : 0,
        notes: String(notesNode?.value || "").trim(),
      });
    });
    return entries;
  }

  async function saveSuppDayFromForm() {
    const logDate = currentSuppDate();
    const payload = {
      log_date: logDate,
      entries: collectSuppDayEntries(),
    };
    const out = await postJSON("/api/supplements/day", payload);
    renderSuppDay(out || {});
    await refreshSuppHistory(suppLimit);
    showToast("Suplementos guardados", `Fecha ${logDate}`);
    safeClose(suppDayModal);
  }

  async function deleteSuppDay(logDate) {
    const date = String(logDate || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return;
    const ok = window.confirm(`Vas a eliminar el registro de suplementos del ${humanDate(date)}.`);
    if (!ok) return;
    await deleteJSON(`/api/supplements/day/${encodeURIComponent(date)}`);
    await refreshSuppHistory(suppLimit);
    showToast("Suplementos", `Registro del ${humanDate(date)} eliminado.`);
    safeClose(suppDayModal);
  }

  function findDietByDate(logDate) {
    return currentDietRows.find((r) => String(r.log_date || "") === String(logDate || ""));
  }

  function findWorkoutBySessionId(sessionId) {
    return currentWorkoutRows.find((r) => String(r.session_id || "") === String(sessionId || ""));
  }

  function openDietForCreate(forceDate = "") {
    if (!dietModal || !dietForm) return;
    dietForm.reset();
    setDietFormAlert("");
    try {
      localStorage.removeItem("dietForm");
    } catch (_) {}
    const dateSeed = (/^\d{4}-\d{2}-\d{2}$/.test(String(forceDate || "")))
      ? String(forceDate)
      : ($("diet_date")?.value || isoToday());
    setFormValue(dietForm, "log_date", dateSeed);
    if (!$("diet_date")?.value && !forceDate) setFormValue(dietForm, "log_date", isoToday());
    if (dietEntryMode) dietEntryMode.value = "create";
    if (dietDeleteBtn) {
      dietDeleteBtn.hidden = true;
      dietDeleteBtn.removeAttribute("data-log-date");
    }

    clearPreview();
    updateExistingPhotoButton("", "");
    if (photoReplaceConfirm) photoReplaceConfirm.value = "";
    safeOpen(dietModal);
  }

  function openDietForEdit(row) {
    if (!dietModal || !dietForm || !row) return;
    dietForm.reset();
    setDietFormAlert("");
    setFormValue(dietForm, "log_date", row.log_date || isoToday());
    setFormValue(dietForm, "sleep_hours", row.sleep_hours);
    setFormValue(dietForm, "sleep_quality", row.sleep_quality);
    setFormValue(dietForm, "steps", row.steps);
    setFormValue(dietForm, "weight_kg", row.weight_kg);
    setFormValue(dietForm, "waist_cm", row.waist_cm);
    setFormValue(dietForm, "hip_cm", row.hip_cm);
    setFormValue(dietForm, "alcohol_units", row.alcohol_units);
    setFormValue(dietForm, "photo_yn", row.photo_yn || (row.photo_url ? "Y" : ""));
    if (photoReplaceConfirm) photoReplaceConfirm.value = "";
    if (dietEntryMode) dietEntryMode.value = "edit";
    if (dietDeleteBtn) {
      dietDeleteBtn.hidden = false;
      dietDeleteBtn.dataset.logDate = String(row.log_date || "");
    }

    clearPreview({ preservePhotoYN: true });
    if (row.photo_url && photoPreview) {
      photoPreview.src = row.photo_url;
      photoPreview.classList.add("show");
    } else if (photoPreview) {
      photoPreview.removeAttribute("src");
      photoPreview.classList.remove("show");
    }
    if (photoMeta) {
      photoMeta.textContent = row.photo_url ? "Foto actual del registro" : "Sin archivo";
    }
    updateExistingPhotoButton(row.photo_url || "", `Foto ${row.log_date || ""}`.trim(), row.log_date || "");
    safeOpen(dietModal);
  }

  function syncWorkoutClassFieldCopy(mode) {
    const currentMode = normalizeSessionType(mode || "clase");
    const classInput = workClassField?.querySelector('input[name="class_done"]');
    if (workClassLabel) {
      workClassLabel.textContent = currentMode === "pesas"
        ? "Foco de la sesión (opcional)"
        : "Clase / actividad";
    }
    if (classInput) {
      classInput.placeholder = currentMode === "pesas"
        ? "Pierna / empuje / tirón / full body..."
        : "Cross-fit + core / yoga / pilates...";
    }
  }

  function toggleWorkoutModeUI() {
    const mode = normalizeSessionType(workSessionType?.value || "clase");
    const showStrength = mode === "pesas";

    if (workClassField) workClassField.style.display = "";
    if (workStrengthBlock) workStrengthBlock.style.display = showStrength ? "" : "none";
    if (showStrength && workExerciseList && !workExerciseList.querySelector("[data-exercise-row]")) {
      addExerciseRow();
    }
    syncWorkoutClassFieldCopy(mode);
  }

  function syncWorkDoneToggleUI() {
    const value = String(workDoneSelect?.value || "").toUpperCase();
    workDoneButtons.forEach((btn) => {
      const active = String(btn?.dataset?.workDoneValue || "").toUpperCase() === value;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function clearExerciseRows() {
    if (!workExerciseList) return;
    workExerciseList.innerHTML = "";
  }

  function addExerciseRow(data = {}) {
    if (!workExerciseList || !workExerciseTemplate) return;
    const fragment = workExerciseTemplate.content.cloneNode(true);
    const row = fragment.querySelector("[data-exercise-row]");
    if (!row) return;

    const setVal = (field, value) => {
      const node = row.querySelector(`[data-ex-field="${field}"]`);
      if (node) node.value = value == null ? "" : String(value);
    };
    setVal("exercise_name", data.exercise_name || data.name || "");
    setVal("weight_kg", data.weight_kg);
    setVal("reps", data.reps);
    setVal("rpe", data.rpe);

    const removeBtn = row.querySelector("[data-remove-exercise]");
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        row.remove();
      });
    }
    workExerciseList.appendChild(fragment);
  }

  function collectExerciseRows() {
    if (!workExerciseList) return [];
    const rows = Array.from(workExerciseList.querySelectorAll("[data-exercise-row]"));
    const out = [];
    rows.forEach((row) => {
      const read = (field) => row.querySelector(`[data-ex-field="${field}"]`)?.value?.trim() || "";
      const ex = {
        exercise_name: read("exercise_name"),
        weight_kg: read("weight_kg"),
        reps: read("reps"),
        rpe: read("rpe"),
      };
      const hasValue = ex.exercise_name || ex.weight_kg || ex.reps || ex.rpe;
      if (hasValue) out.push(ex);
    });
    return out;
  }

  function syncWorkExercisesHiddenField() {
    if (!workExercisesJson) return;
    const mode = normalizeSessionType(workSessionType?.value || "clase");
    if (mode === "clase") {
      workExercisesJson.value = "[]";
      return;
    }
    workExercisesJson.value = JSON.stringify(collectExerciseRows());
  }

  function openWorkoutForCreate(forceDate = "") {
    if (!workoutModal || !workForm) return;
    workForm.reset();
    try {
      localStorage.removeItem("workForm");
    } catch (_) {}
    const dateSeed = (/^\d{4}-\d{2}-\d{2}$/.test(String(forceDate || "")))
      ? String(forceDate)
      : ($("work_date")?.value || isoToday());
    setFormValue(workForm, "log_date", dateSeed);
    if (!$("work_date")?.value && !forceDate) setFormValue(workForm, "log_date", isoToday());
    setFormValue(workForm, "session_type", "clase");
    if (workSessionId) workSessionId.value = "";
    if (workExercisesJson) workExercisesJson.value = "[]";
    clearExerciseRows();
    if (workEntryMode) workEntryMode.value = "create";
    if (workDeleteBtn) {
      workDeleteBtn.hidden = true;
      workDeleteBtn.removeAttribute("data-session-id");
    }
    toggleWorkoutModeUI();
    syncWorkDoneToggleUI();
    safeOpen(workoutModal);
  }

  function openWorkoutForEdit(row) {
    if (!workoutModal || !workForm || !row) return;
    workForm.reset();
    const sessionType = normalizeSessionType(row.session_type || "clase");
    setFormValue(workForm, "log_date", row.log_date || isoToday());
    setFormValue(workForm, "session_type", sessionType);
    setFormValue(workForm, "session_done_yn", row.session_done_yn);
    setFormValue(workForm, "class_done", row.class_done);
    setFormValue(workForm, "rpe_session", row.rpe_session);
    setFormValue(workForm, "notes", row.notes);
    if (workSessionId) workSessionId.value = String(row.session_id || "");
    clearExerciseRows();
    if (Array.isArray(row.exercises)) {
      row.exercises.forEach((ex) => addExerciseRow(ex));
    }
    if (workExercisesJson) {
      workExercisesJson.value = JSON.stringify(Array.isArray(row.exercises) ? row.exercises : []);
    }
    if (workEntryMode) workEntryMode.value = "edit";
    if (workDeleteBtn) {
      workDeleteBtn.hidden = false;
      workDeleteBtn.dataset.sessionId = String(row.session_id || "");
    }
    toggleWorkoutModeUI();
    syncWorkDoneToggleUI();
    safeOpen(workoutModal);
  }

  function openImportDietModal() {
    if (!importDietModal) return;
    if (importDietForm) importDietForm.reset();
    clearImportPreview();
    safeOpen(importDietModal);
  }

  function clearPlanImportSummary() {
    planImportDetailRows = [];
    if (planImportSummary) {
      planImportSummary.hidden = true;
      planImportSummary.textContent = "";
      planImportSummary.classList.remove("ok", "error");
    }
    if (planImportFeedback) planImportFeedback.hidden = true;
    if (planImportHuman) planImportHuman.innerHTML = "";
    if (planImportGroups) planImportGroups.innerHTML = "";
    if (planImportDetailBody) planImportDetailBody.innerHTML = "";
    if (planImportDetailWrap) planImportDetailWrap.hidden = true;
    if (planImportDownloadDetailBtn) planImportDownloadDetailBtn.hidden = true;
  }

  function renderPlanImportSummary(text, kind = "ok") {
    if (!planImportSummary) return;
    planImportSummary.hidden = false;
    planImportSummary.textContent = String(text || "");
    planImportSummary.classList.remove("ok", "error");
    planImportSummary.classList.add(kind === "error" ? "error" : "ok");
    planImportSummary.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function splitPlanImportReasons(reasonText) {
    return String(reasonText || "")
      .split(/[;|]/g)
      .map((chunk) => chunk.trim())
      .filter(Boolean);
  }

  function planImportIssueType(status, reasonText) {
    const statusTxt = String(status || "").trim().toLowerCase();
    const hasReason = !!String(reasonText || "").trim();
    if (statusTxt === "invalid") return "Error";
    if (statusTxt === "warning") return "Aviso";
    if (statusTxt === "imported" && hasReason) return "Aviso";
    return "";
  }

  function planImportActionHint(reasonText, issueType, rowData = {}) {
    const reason = String(reasonText || "").toLowerCase();
    const sessionType = String(rowData.session_type || "").toLowerCase();
    if (reason.includes("date invalida")) {
      return "Usa formato AAAA-MM-DD, por ejemplo 2026-03-02.";
    }
    if (reason.includes("session_type 'mixta'")) {
      return "Reemplaza mixta por clase o pesas.";
    }
    if (reason.includes("session_type debe ser")) {
      return "Escribe session_type exactamente como clase o pesas.";
    }
    if (reason.includes("name obligatorio")) {
      return "Completa exercise_*_name o deja vacío todo el bloque exercise_* de ese slot.";
    }
    if (
      reason.includes("sets invalido")
      || reason.includes("sets fuera de rango")
      || reason.includes("debe ser entero")
    ) {
      return "En exercise_*_sets usa enteros de 1 a 12 (sin rangos tipo 3-4).";
    }
    if (reason.includes("reps_min invalido") || reason.includes("reps_max invalido")) {
      return "En reps_min y reps_max usa enteros (no texto ni rangos en una sola celda).";
    }
    if (reason.includes("reps_min no puede ser mayor")) {
      return "Ajusta los valores para que reps_min sea menor o igual que reps_max.";
    }
    if (reason.includes("weight_kg invalido") || reason.includes("weight_kg fuera de rango")) {
      return "En weight_kg usa un número simple (ejemplo: 75.5).";
    }
    if (reason.includes("rpe invalido") || reason.includes("rpe fuera de rango")) {
      return "En rpe usa un número entre 1 y 10.";
    }
    if (reason.includes("duplicad")) {
      return "Elimina filas repetidas para la misma fecha/sesión antes de importar.";
    }
    if (reason.includes("se ignoraron") && (reason.includes("session_type clase") || sessionType === "clase")) {
      return "Para session_type=clase, deja vacías las columnas exercise_*.";
    }
    if (issueType === "Aviso") {
      return "La fila se importó, pero conviene ajustar ese dato para futuras ediciones.";
    }
    return "Corrige la fila usando la plantilla oficial y vuelve a importar.";
  }

  function normalizePlanImportCause(reasonText) {
    return String(reasonText || "")
      .replace(/^exercise_\d+\s*:\s*/i, "exercise_*: ")
      .trim();
  }

  function buildPlanImportDetailRows(results) {
    const rows = Array.isArray(results) ? results : [];
    const out = [];
    rows.forEach((item) => {
      const issueType = planImportIssueType(item?.status, item?.reason);
      if (!issueType) return;
      const rowData = item?.row && typeof item.row === "object" ? item.row : {};
      const lineNo = Number(item?.row_number);
      const reasons = splitPlanImportReasons(item?.reason);
      if (!reasons.length) reasons.push("Incidencia sin detalle.");
      reasons.forEach((reason) => {
        out.push(
          {
            line: Number.isFinite(lineNo) ? lineNo : "",
            log_date: String(rowData.log_date || ""),
            session_type: String(rowData.session_type || ""),
            issue_type: issueType,
            reason: String(reason),
            action: planImportActionHint(reason, issueType, rowData),
          }
        );
      });
    });
    return out;
  }

  function summarizePlanImportGroups(detailRows) {
    const grouped = new Map();
    detailRows.forEach((row) => {
      const cause = normalizePlanImportCause(row.reason);
      const key = `${row.issue_type}|${cause}`;
      if (!grouped.has(key)) {
        grouped.set(key, {
          issue_type: row.issue_type,
          cause,
          action: row.action,
          count: 0,
          lines: new Set(),
        });
      }
      const item = grouped.get(key);
      item.count += 1;
      if (row.line !== "") item.lines.add(String(row.line));
    });
    return Array.from(grouped.values()).sort((a, b) => {
      if (a.issue_type !== b.issue_type) return a.issue_type === "Error" ? -1 : 1;
      if (a.count !== b.count) return b.count - a.count;
      return a.cause.localeCompare(b.cause, "es");
    });
  }

  function csvCell(raw) {
    const text = String(raw ?? "");
    if (/[",\n]/.test(text)) {
      return `"${text.replace(/"/g, "\"\"")}"`;
    }
    return text;
  }

  function downloadPlanImportDetailCsv(label) {
    if (!planImportDetailRows.length) {
      showToast("Importación CSV", "No hay incidencias para descargar.");
      return;
    }
    const safeLabel = String(label || "plan").trim().toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const stamp = new Date().toISOString().replace(/[:T]/g, "-").slice(0, 16);
    const filename = `plan-import-diagnostico-${safeLabel || "plan"}-${stamp}.csv`;
    const header = ["linea", "fecha", "session_type", "tipo", "motivo", "accion_sugerida"];
    const lines = [header.map(csvCell).join(",")];
    planImportDetailRows.forEach((row) => {
      lines.push(
        [
          row.line,
          row.log_date,
          row.session_type,
          row.issue_type,
          row.reason,
          row.action,
        ]
          .map(csvCell)
          .join(",")
      );
    });

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 800);
  }

  function renderPlanImportFeedback(label, payload) {
    if (!planImportFeedback) return;
    const summary = payload?.summary || {};
    const total = Number(summary.total || 0);
    const imported = Number(summary.imported || 0);
    const invalid = Number(summary.invalid || 0);
    const warnedFromSummary = Number(summary.warned || 0);
    const warningRows = Array.isArray(payload?.results)
      ? payload.results.filter((item) => planImportIssueType(item?.status, item?.reason) === "Aviso").length
      : 0;
    const warned = warnedFromSummary > 0 ? warnedFromSummary : warningRows;

    const intro = `Se analizaron ${total} fila${total === 1 ? "" : "s"} para ${label}.`;
    const importLine = imported > 0
      ? `Se importaron ${imported} fila${imported === 1 ? "" : "s"}.`
      : "No se importó ninguna fila.";
    const incidents = invalid > 0 || warned > 0
      ? `Resultado: ${invalid} error${invalid === 1 ? "" : "es"} bloqueante${invalid === 1 ? "" : "s"} y ${warned} aviso${warned === 1 ? "" : "s"} no bloqueante${warned === 1 ? "" : "s"}.`
      : "Resultado: importación sin incidencias.";
    const closeHint = invalid > 0
      ? "Corrige primero los errores y vuelve a importar."
      : (warned > 0
        ? "Puedes continuar, pero conviene revisar los avisos."
        : "No necesitas hacer ajustes adicionales.");
    if (planImportHuman) {
      planImportHuman.innerHTML = [
        `<p>${escapeHtml(intro)}</p>`,
        `<p>${escapeHtml(importLine)}</p>`,
        `<p>${escapeHtml(incidents)}</p>`,
        `<p>${escapeHtml(closeHint)}</p>`,
      ].join("");
    }

    planImportDetailRows = buildPlanImportDetailRows(payload?.results);
    const grouped = summarizePlanImportGroups(planImportDetailRows);
    if (planImportGroups) {
      if (!grouped.length) {
        planImportGroups.innerHTML = `<div class="plan-empty">Sin incidencias por causa para este archivo.</div>`;
      } else {
        planImportGroups.innerHTML = grouped
          .map((item) => {
            const sampleRows = Array.from(item.lines).slice(0, 6).join(", ");
            const rowHint = sampleRows ? `Filas ejemplo: ${sampleRows}.` : "Sin fila de ejemplo.";
            return `
              <article class="plan-import-group-item ${item.issue_type === "Error" ? "is-error" : "is-warn"}">
                <div class="plan-import-group-head">
                  <span class="plan-import-group-pill">${escapeHtml(item.issue_type)}</span>
                  <strong>${escapeHtml(item.cause)}</strong>
                  <span class="mono">${escapeHtml(`${item.count} caso${item.count === 1 ? "" : "s"}`)}</span>
                </div>
                <div class="plan-import-group-meta mono">${escapeHtml(rowHint)}</div>
                <div class="plan-import-group-action">${escapeHtml(item.action)}</div>
              </article>
            `;
          })
          .join("");
      }
    }

    if (planImportDetailBody && planImportDetailWrap) {
      if (!planImportDetailRows.length) {
        planImportDetailBody.innerHTML = "";
        planImportDetailWrap.hidden = true;
      } else {
        planImportDetailBody.innerHTML = planImportDetailRows
          .map((row) => `
            <tr>
              <td class="mono">${escapeHtml(String(row.line || "—"))}</td>
              <td class="mono">${escapeHtml(row.log_date ? humanDateDash(row.log_date) : "—")}</td>
              <td>${escapeHtml(row.session_type || "—")}</td>
              <td>${escapeHtml(row.issue_type)}</td>
              <td>${escapeHtml(row.reason)}</td>
              <td>${escapeHtml(row.action)}</td>
            </tr>
          `)
          .join("");
        planImportDetailWrap.hidden = false;
      }
    }

    if (planImportDownloadDetailBtn) {
      planImportDownloadDetailBtn.hidden = planImportDetailRows.length === 0;
      planImportDownloadDetailBtn.dataset.detailLabel = String(label || "plan");
    }

    planImportFeedback.hidden = false;
  }

  function openPlanImportModal() {
    if (!planImportModal) return;
    if (planDietFile) planDietFile.value = "";
    if (planWorkoutFile) planWorkoutFile.value = "";
    if (planAiPromptText) planAiPromptText.value = PLAN_AI_PROMPT;
    clearPlanImportSummary();
    safeOpen(planImportModal);
  }

  function openPlanAiWorkflowModal() {
    if (!planAiWorkflowModal) return;
    if (planAiPromptText && !String(planAiPromptText.value || "").trim()) {
      planAiPromptText.value = PLAN_AI_PROMPT;
    }
    safeOpen(planAiWorkflowModal);
  }

  async function copyPlanAiPrompt() {
    const text = String(planAiPromptText?.value || PLAN_AI_PROMPT).trim();
    if (!text) {
      showToast("Prompt IA", "No hay texto para copiar.");
      return;
    }
    const copied = await copyTextToClipboard(text);
    if (copied) {
      showToast("Prompt IA", "Copiado. Pégalo en tu IA junto con los 5 archivos.");
    } else {
      showToast("Prompt IA", "No se pudo copiar automáticamente.");
    }
  }

  async function fetchPlanDay(logDate) {
    const d = (logDate && /^\d{4}-\d{2}-\d{2}$/.test(logDate)) ? logDate : isoToday();
    const adherenceDays = parsePlanAdherenceWindow(
      planAdherenceWindow?.value,
      planAdherenceWindowDays
    );
    planAdherenceWindowDays = adherenceDays;
    const out = await fetchJSON(
      `/api/plan/day?log_date=${encodeURIComponent(d)}&adherence_days=${encodeURIComponent(String(adherenceDays))}`
    );
    renderPlanDay(out || { log_date: d });
    return out;
  }

  async function savePlanAdherence() {
    const logDate = String(planDayDate?.value || currentPlanDay?.log_date || isoToday()).trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(logDate)) {
      showToast("Adherencia", "Fecha inválida para guardar puntuación.");
      return;
    }
    const payload = {
      log_date: logDate,
      diet_score: planDietScore?.value || "",
      workout_score: planWorkoutScore?.value || "",
      notes: planAdherenceNotes?.value || "",
    };
    await postJSON("/api/plan/adherence", payload);
    await fetchPlanDay(logDate);
    showToast("Adherencia", `Puntuación guardada para ${logDate}`);
  }

  function currentPlanLogDate() {
    const raw = String(planDayDate?.value || currentPlanDay?.log_date || "").trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
    return "";
  }

  function confirmPlanFlush(scopeLabel) {
    const first = window.confirm(`Vas a vaciar ${scopeLabel}. Esta acción no se puede deshacer.`);
    if (!first) return false;
    return window.confirm(`Confirmación final: eliminar definitivamente ${scopeLabel}.`);
  }

  async function deletePlanDietDay() {
    const logDate = currentPlanLogDate();
    if (!logDate) {
      showToast("Planes", "No se encontró una fecha válida del plan.");
      return;
    }
    const ok = window.confirm(`Vas a eliminar la dieta plan del ${humanDate(logDate)}.`);
    if (!ok) return;
    const out = await deleteJSON(`/api/plan/diet/${encodeURIComponent(logDate)}`);
    await fetchPlanDay(logDate);
    const deletedRows = Number(out?.deleted_rows || 0);
    showToast("Planes", `Dieta del día eliminada (${deletedRows} fila${deletedRows === 1 ? "" : "s"}).`);
  }

  async function flushPlanDiet() {
    if (!confirmPlanFlush("toda la dieta plan importada")) return;
    const out = await deleteJSON("/api/plan/diet");
    const logDate = currentPlanLogDate() || isoToday();
    await fetchPlanDay(logDate);
    const deletedRows = Number(out?.deleted_rows || 0);
    showToast("Planes", `Dieta plan vaciada (${deletedRows} fila${deletedRows === 1 ? "" : "s"} eliminadas).`);
  }

  async function deletePlanWorkoutSession(planSessionId) {
    const sessionId = String(planSessionId || "").trim();
    const logDate = currentPlanLogDate();
    if (!sessionId) {
      showToast("Planes", "No se encontró la sesión planificada a eliminar.");
      return;
    }
    if (!logDate) {
      showToast("Planes", "No se encontró una fecha válida del plan.");
      return;
    }
    const ok = window.confirm(
      `Vas a eliminar la sesión ${sessionId} del ${humanDate(logDate)}.`
    );
    if (!ok) return;
    const out = await deleteJSON(
      `/api/plan/workout/${encodeURIComponent(logDate)}/${encodeURIComponent(sessionId)}`
    );
    await fetchPlanDay(logDate);
    const deletedExercises = Number(out?.deleted_exercises || 0);
    showToast(
      "Planes",
      `Sesión ${sessionId} eliminada (${deletedExercises} ejercicio${deletedExercises === 1 ? "" : "s"}).`
    );
  }

  async function flushPlanWorkout() {
    if (!confirmPlanFlush("todo el entreno planificado importado")) return;
    const out = await deleteJSON("/api/plan/workout");
    const logDate = currentPlanLogDate() || isoToday();
    await fetchPlanDay(logDate);
    const deletedSessions = Number(out?.deleted_sessions || 0);
    showToast(
      "Planes",
      `Entreno planificado vaciado (${deletedSessions} sesión${deletedSessions === 1 ? "" : "es"} eliminadas).`
    );
  }

  async function importPlanCSV(endpoint, file, label) {
    clearPlanImportSummary();
    if (!file) {
      renderPlanImportSummary(`Selecciona un archivo CSV para ${label}.`, "error");
      return false;
    }
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("source_tag", "csv_template");

      const res = await fetch(endpoint, {
        method: "POST",
        body: fd,
      });
      const text = await res.text();
      let payload = {};
      try {
        payload = text ? JSON.parse(text) : {};
      } catch (_) {
        payload = {};
      }
      if (!res.ok) {
        const msg = payload.error || payload.message || text || `HTTP ${res.status}`;
        renderPlanImportSummary(`Error al importar ${label}: ${userErrorMessage(msg)}`, "error");
        return false;
      }
      const summary = payload?.summary || {};
      const warned = Number(summary.warned || 0);
      const line =
        `${label}: total ${summary.total || 0} · importadas ${summary.imported || 0} · inválidas ${summary.invalid || 0}` +
        (warned > 0 ? ` · avisos ${warned}` : "");
      const kind = Number(summary.invalid || 0) > 0 ? "error" : "ok";
      renderPlanImportSummary(line, kind);
      renderPlanImportFeedback(label, payload || {});
      await fetchPlanDay(String(planDayDate?.value || currentPlanDay?.log_date || isoToday()));
      return true;
    } catch (err) {
      renderPlanImportSummary(`Error al importar ${label}: ${userErrorMessage(err)}`, "error");
      return false;
    }
  }

  async function applySummaryRangeFromUI(source = "summary") {
    const from = String(source === "progress" ? (perfFrom?.value || "") : (summaryFrom?.value || "")).trim();
    const to = String(source === "progress" ? (perfTo?.value || "") : (summaryTo?.value || "")).trim();
    if (!from || !to) {
      showToast("Rango KPIs", "Selecciona ambas fechas (desde y hasta).");
      return;
    }
    if (from > to) {
      showToast("Rango KPIs", "La fecha inicial no puede ser mayor que la final.");
      return;
    }
    if (summaryModeSelect) summaryModeSelect.value = "custom";
    if (perfModeSelect) perfModeSelect.value = "custom";
    if (summaryFrom) summaryFrom.value = from;
    if (summaryTo) summaryTo.value = to;
    if (perfFrom) perfFrom.value = from;
    if (perfTo) perfTo.value = to;
    syncSummaryAnalysisUI();
    syncPerfAnalysisUI();
    summaryRangeFrom = from;
    summaryRangeTo = to;
    await refreshState();
    showToast("Rango aplicado", `${from} -> ${to}`);
  }

  async function applySummaryWindowFromUI(notify = true, source = "summary") {
    const raw = source === "progress" ? perfModeSelect?.value : summaryModeSelect?.value;
    if (String(raw || "") === "custom") return;
    summaryWindowDays = parseLimitValue(raw, summaryWindowDays);
    if (summaryModeSelect) summaryModeSelect.value = String(summaryWindowDays);
    if (perfModeSelect) perfModeSelect.value = String(summaryWindowDays);
    summaryRangeFrom = "";
    summaryRangeTo = "";
    if (summaryFrom) summaryFrom.value = "";
    if (summaryTo) summaryTo.value = "";
    if (perfFrom) perfFrom.value = "";
    if (perfTo) perfTo.value = "";
    syncSummaryAnalysisUI();
    syncPerfAnalysisUI();
    await refreshState();
    if (notify) {
      showToast("KPIs", `Ventana base aplicada: ultimos ${summaryWindowDays} dias.`);
    }
  }

  async function applySummaryFromUI() {
    if (isSummaryCustomMode()) {
      await applySummaryRangeFromUI();
      return;
    }
    await applySummaryWindowFromUI(true);
  }

  async function previewDietImport() {
    const file = importDietFile?.files?.[0];
    if (!file) {
      showToast("Importacion CSV", "Selecciona un archivo .csv antes de previsualizar.");
      return;
    }

    const fd = new FormData();
    fd.append("file", file);

    const res = await fetch("/api/diet/import/preview", {
      method: "POST",
      body: fd,
    });
    const text = await res.text();
    let payload = {};
    try {
      payload = text ? JSON.parse(text) : {};
    } catch (_) {
      payload = {};
    }
    if (!res.ok) {
      const msg = payload.error || payload.message || text || `HTTP ${res.status}`;
      throw new Error(userErrorMessage(msg));
    }
    renderImportPreview(payload);
  }

  async function applyDietImport() {
    const validRows = importPreviewRows
      .filter((r) => String(r?.status || "").toLowerCase() === "valid")
      .map((r) => ({ row_number: r.row_number, row: r.row }));

    if (!validRows.length) {
      showToast("Importacion CSV", "No hay filas validas para importar.");
      return;
    }

    const out = await postJSON("/api/diet/import/apply", { rows: validRows });
    renderImportSummary(out.summary || {});
    await refreshState();
    const imported = Number(out?.summary?.imported || 0);
    const conflicts = Number(out?.summary?.conflict || 0);
    const invalid = Number(out?.summary?.invalid || 0);
    showToast("Importacion completada", `Importadas: ${imported} · Conflictos: ${conflicts} · Invalidas: ${invalid}`);
  }

  function openBackupRestoreModal() {
    if (!backupRestoreModal) return;
    if (backupRestoreForm) backupRestoreForm.reset();
    safeOpen(backupRestoreModal);
  }

  async function submitBackupRestore() {
    const file = backupRestoreFile?.files?.[0];
    if (!file) {
      showToast("Restaurar backup", "Selecciona un archivo ZIP.");
      return;
    }
    const confirmed = !!backupRestoreConfirm?.checked;
    if (!confirmed) {
      showToast("Restaurar backup", "Marca la confirmacion para continuar.");
      return;
    }

    const fd = new FormData();
    fd.append("backup_file", file);
    fd.append("restore_confirm", "1");

    const res = await fetch("/backup/restore", {
      method: "POST",
      body: fd,
    });
    const text = await res.text();
    let payload = {};
    try {
      payload = text ? JSON.parse(text) : {};
    } catch (_) {
      payload = {};
    }

    if (!res.ok) {
      const msg = payload.error || payload.message || text || `HTTP ${res.status}`;
      throw new Error(userErrorMessage(msg));
    }

    safeClose(backupRestoreModal);
    await refreshState();
    const s = payload.summary || {};
    showToast(
      "Backup restaurado",
      `Dieta: ${s.diet_rows ?? "?"} · Rutina: ${s.workout_rows ?? "?"} · Fotos: ${s.upload_files ?? "?"}`
    );
  }

  async function submitDiet(confirmReplace) {
    if (!dietForm) return;
    setDietFormAlert("");
    if (photoReplaceConfirm) photoReplaceConfirm.value = confirmReplace ? "1" : "";
    remember(dietForm, "dietForm");

    const res = await postMultipart("/api/diet", dietForm);
    if (res.ok) {
      if (photoReplaceConfirm) photoReplaceConfirm.value = "";
      safeClose(replaceConfirmModal);
      safeClose(dietModal);
      await refreshState();
      const title = (dietEntryMode && dietEntryMode.value === "edit") ? "Check-in actualizado" : "Check-in guardado";
      showToast(title, `Fecha ${res.payload.log_date || isoToday()}`);
      return;
    }

    if (res.status === 409 && res.payload && res.payload.needs_confirm) {
      openReplaceConfirm(res.payload, async () => {
        safeClose(replaceConfirmModal);
        try {
          await submitDiet(true);
        } catch (err) {
          showToast("Error", String(err).slice(0, 180));
        }
      });
      return;
    }
    if (res.status === 409 && res.payload && res.payload.needs_edit) {
      setDietFormAlert(userErrorMessage(res.payload.message));
      return;
    }

    const msg = userErrorMessage(res.payload.error || res.payload.message || res.text || `HTTP ${res.status}`);
    setDietFormAlert(msg);
  }

  async function deleteDietFromModal() {
    const fromBtn = String(dietDeleteBtn?.dataset?.logDate || "").trim();
    const fromInput = String($("diet_date")?.value || "").trim();
    const logDate = fromBtn || fromInput;
    if (!logDate) {
      showToast("Eliminar check-in", "No se encontró la fecha del registro.");
      return;
    }
    const ok = window.confirm(
      `Vas a eliminar el check-in del ${logDate}. Esta acción no se puede deshacer.`
    );
    if (!ok) return;

    await deleteJSON(`/api/diet/${encodeURIComponent(logDate)}`);
    safeClose(dietModal);
    await refreshState();
    showToast("Check-in eliminado", `Fecha ${logDate}`);
  }

  function currentDietModalDate() {
    const fromBtn = String(dietDeleteBtn?.dataset?.logDate || "").trim();
    const fromInput = String($("diet_date")?.value || "").trim();
    return fromBtn || fromInput;
  }

  async function deleteDietPhotoFromModal() {
    const logDate = currentDietModalDate();
    if (!logDate) {
      showToast("Quitar foto", "No se encontró la fecha del check-in.");
      return;
    }
    const ok = window.confirm(
      `Vas a eliminar solo la foto del ${logDate}. El check-in se mantiene.`
    );
    if (!ok) return;

    await deleteJSON(`/api/diet/${encodeURIComponent(logDate)}/photo`);
    const row = findDietByDate(logDate);
    if (row) {
      row.photo_url = "";
      row.photo_yn = "";
    }
    if (photoYN) photoYN.value = "";
    clearPreview();
    updateExistingPhotoButton("", "");
    if (photoMeta) photoMeta.textContent = "Sin archivo";
    await refreshState();
    showToast("Foto eliminada", `Fecha ${logDate}`);
  }

  async function deleteWorkoutFromModal() {
    const sid = String(workDeleteBtn?.dataset?.sessionId || workSessionId?.value || "").trim();
    if (!sid) {
      showToast("Eliminar entreno", "No se encontró la sesión a eliminar.");
      return;
    }
    const row = findWorkoutBySessionId(sid);
    const label = row?.log_date ? `${row.log_date} (S${row.session_order || "?"})` : `ID ${sid}`;
    const ok = window.confirm(
      `Vas a eliminar la sesión ${label}. Esta acción no se puede deshacer.`
    );
    if (!ok) return;

    await deleteJSON(`/api/workout/${encodeURIComponent(sid)}`);
    safeClose(workoutModal);
    await refreshState();
    showToast("Entreno eliminado", `Sesión ${label}`);
  }

  // ----------------------------
  // UI bindings
  // ----------------------------
  if (fabMain && fabMenu) {
    fabMain.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isOpen = fabMain.classList.contains("is-open");
      setFabOpen(!isOpen);
    });

    fabMenu.addEventListener("click", (e) => {
      const trigger = e.target.closest(".fab-btn");
      if (trigger) closeFab();
    });

    document.addEventListener("click", (e) => {
      if (!fabMain.classList.contains("is-open")) return;
      const target = e.target;
      if (fabMain.contains(target) || fabMenu.contains(target)) return;
      closeFab();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeFab();
    });
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
      const trigger = e.target.closest(".btn");
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

  if (viewButtons.length) {
    document.addEventListener("click", (e) => {
      const trigger = e.target.closest("[data-view-target]");
      if (!trigger) return;
      const target = String(trigger.dataset.viewTarget || "").trim();
      if (!allowedView(target)) return;
      e.preventDefault();
      setActiveView(target);
      closeTopMenu();
      closeFab();
      if (target === "supplements") {
        void openSupplementsView().catch((err) => {
          showToast("Error", userErrorMessage(err));
        });
        return;
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    window.addEventListener("hashchange", () => {
      const next = allowedView(window.location.hash.replace(/^#/, ""));
      if (next) {
        setActiveView(next, { persist: true, syncHash: false });
        if (next === "supplements") {
          void openSupplementsView().catch((err) => {
            showToast("Error", userErrorMessage(err));
          });
        }
      }
    });
  }

  if (helpTipTriggers.length && helpTipPopover) {
    helpTipTriggers.forEach((trigger) => {
      trigger.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (activeHelpTipTrigger === trigger && !helpTipPopover.hidden) {
          closeHelpTip();
          return;
        }
        openHelpTip(trigger);
      });
      trigger.addEventListener("focus", () => openHelpTip(trigger));
      if (hoverCapableMql?.matches) {
        trigger.addEventListener("mouseenter", () => openHelpTip(trigger));
      }
    });
    helpTipPopover.addEventListener("click", (e) => {
      e.stopPropagation();
    });
    document.addEventListener("click", (e) => {
      if (helpTipPopover.hidden) return;
      const isTrigger = e.target.closest("[data-help-tip]");
      if (isTrigger) return;
      closeHelpTip();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeHelpTip();
    });
    window.addEventListener("resize", () => {
      if (activeHelpTipTrigger) positionHelpTip(activeHelpTipTrigger);
    });
    window.addEventListener("scroll", () => {
      if (activeHelpTipTrigger) positionHelpTip(activeHelpTipTrigger);
    }, { passive: true });
  }

  if (photoFile) {
    photoFile.addEventListener("change", (e) => {
      const f = e.target.files?.[0];
      setPreviewFromFile(f);
    });
  }
  if (photoClear) {
    photoClear.addEventListener("click", async () => {
      const hasExisting = !!currentExistingPhotoURL();
      const hasPendingUpload = !!previewObjectURL || !!photoFile?.files?.length;

      if (hasPendingUpload) {
        clearPreview({ preservePhotoYN: hasExisting });
        if (!restoreExistingPhotoPreview() && photoMeta) {
          photoMeta.textContent = "Sin archivo";
        }
        return;
      }

      if (hasExisting) {
        try {
          await deleteDietPhotoFromModal();
        } catch (err) {
          showToast("Error", userErrorMessage(err));
        }
        return;
      }

      clearPreview();
    });
  }

  on("photoExistingBtn", "click", (e) => {
    const btn = e.currentTarget;
    const url = btn?.dataset?.photoUrl || "";
    const caption = btn?.dataset?.photoCaption || "Foto actual";
    if (!url) return;
    openLightbox(url, caption, btn?.dataset?.photoDate || "");
  });

  on("btnDiet", "click", () => openDietForCreate());
  on("btnWorkout", "click", () => openWorkoutForCreate());
  on("btnSupplements", "click", async () => {
    try {
      await openSuppDayEditor(isoToday());
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("btnPlanHub", "click", () => openPlanImportModal());
  on("btnPlanHubImport", "click", () => openPlanImportModal());
  on("suppCatalogBtn", "click", async () => {
    try {
      await openSuppCatalogEditor();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("suppNewDayBtn", "click", async () => {
    try {
      await openSuppDayEditor(isoToday());
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("suppDayLoadBtn", "click", async () => {
    try {
      await refreshSuppDay(currentSuppDate());
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("suppDayDeleteBtn", "click", async () => {
    try {
      await deleteSuppDay(currentSuppDate());
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("suppDayCancel", "click", () => safeClose(suppDayModal));
  on("suppDayClose", "click", () => safeClose(suppDayModal));
  on("suppCatalogDone", "click", () => safeClose(suppCatalogModal));
  on("suppCatalogClose", "click", () => safeClose(suppCatalogModal));
  on("suppLimitSelect", "change", async (e) => {
    const next = parseLimitValue(e?.target?.value, suppLimit);
    if (next === suppLimit) return;
    suppLimit = next;
    try {
      await refreshSuppHistory(suppLimit);
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("suppSearch", "input", (e) => filterTable(suppHistoryTable, e.target.value));
  on("planDayLoadBtn", "click", async () => {
    try {
      await fetchPlanDay(String(planDayDate?.value || ""));
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("planAdherenceWindow", "change", async (e) => {
    const next = parsePlanAdherenceWindow(e?.target?.value, planAdherenceWindowDays);
    if (next === planAdherenceWindowDays && currentPlanDay) return;
    planAdherenceWindowDays = next;
    try {
      await fetchPlanDay(String(planDayDate?.value || currentPlanDay?.log_date || ""));
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("planDeleteDietDayBtn", "click", async () => {
    try {
      await deletePlanDietDay();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("planFlushDietBtn", "click", async () => {
    try {
      await flushPlanDiet();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("planFlushWorkoutBtn", "click", async () => {
    try {
      await flushPlanWorkout();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  if (planWorkoutSessions) {
    planWorkoutSessions.addEventListener("click", async (e) => {
      const trigger = e.target.closest("[data-plan-delete-session]");
      if (!trigger) return;
      const sessionId = String(trigger.dataset.planDeleteSession || "");
      try {
        await deletePlanWorkoutSession(sessionId);
      } catch (err) {
        showToast("Error", userErrorMessage(err));
      }
    });
  }
  on("planSaveAdherenceBtn", "click", async () => {
    try {
      await savePlanAdherence();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("fabDiet", "click", () => {
    closeFab();
    openDietForCreate();
  });
  on("fabWorkout", "click", () => {
    closeFab();
    openWorkoutForCreate();
  });
  on("fabSupplements", "click", async () => {
    closeFab();
    try {
      await openSupplementsView();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("btnImportDiet", "click", () => openImportDietModal());
  on("btnRestoreBackup", "click", () => openBackupRestoreModal());
  on("btnLogout", "click", async () => {
    try {
      await fetch("/logout", { method: "POST" });
    } catch (_) {}
    window.location.href = "/login";
  });
  on("summaryApplyBtn", "click", async () => {
    try {
      await applySummaryFromUI();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("summaryModeSelect", "change", async () => {
    syncSummaryAnalysisUI();
    if (isSummaryCustomMode()) {
      if (perfModeSelect) perfModeSelect.value = "custom";
      syncPerfAnalysisUI();
      return;
    }
    try {
      await applySummaryWindowFromUI(false, "summary");
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("perfApplyBtn", "click", async () => {
    try {
      await applySummaryRangeFromUI("progress");
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("perfModeSelect", "change", async () => {
    syncPerfAnalysisUI();
    if (isPerfCustomMode()) {
      if (summaryModeSelect) summaryModeSelect.value = "custom";
      syncSummaryAnalysisUI();
      return;
    }
    try {
      await applySummaryWindowFromUI(false, "progress");
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  if (perfMetricTabs) {
    perfMetricTabs.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-chart-metric]");
      if (!btn) return;
      renderPerformanceChart(String(btn.dataset.chartMetric || "weight_kg"));
    });
  }
  on("exportReportBtn", "click", () => {
    try {
      exportReportPNG();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("exportReportPdfBtn", "click", () => {
    try {
      exportReportPDF();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("copyReportBtn", "click", async () => {
    try {
      await copyReportSummary();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("shareReportBtn", "click", async () => {
    try {
      await shareReportQuick();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("viewAllPhotosBtn", "click", () => {
    openPhotoGallery();
  });
  on("btnReportBug", "click", () => openBugReportModal());

  on("dietClose", "click", () => safeClose(dietModal));
  on("dietCancel", "click", () => safeClose(dietModal));
  on("suppCancelEditBtn", "click", () => resetSuppCatalogForm());
  on("dietDeleteBtn", "click", async () => {
    try {
      await deleteDietFromModal();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("workClose", "click", () => safeClose(workoutModal));
  on("workCancel", "click", () => safeClose(workoutModal));
  on("workDeleteBtn", "click", async () => {
    try {
      await deleteWorkoutFromModal();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("importDietClose", "click", () => safeClose(importDietModal));
  on("planImportClose", "click", () => safeClose(planImportModal));
  on("planImportCancel", "click", () => safeClose(planImportModal));
  on("planAiWorkflowOpenBtn", "click", () => openPlanAiWorkflowModal());
  on("planAiWorkflowClose", "click", () => safeClose(planAiWorkflowModal));
  on("planAiWorkflowDoneBtn", "click", () => safeClose(planAiWorkflowModal));
  on("planAiPromptCopyBtn", "click", async () => {
    try {
      await copyPlanAiPrompt();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("backupRestoreClose", "click", () => safeClose(backupRestoreModal));
  on("backupRestoreCancel", "click", () => safeClose(backupRestoreModal));
  on("reportBugClose", "click", () => safeClose(reportBugModal));
  on("reportBugDoneBtn", "click", () => safeClose(reportBugModal));
  on("reportBugCopyBtn", "click", async () => {
    try {
      await copyBugReport();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });
  on("reportBugMailBtn", "click", () => openBugMail());

  on("lightboxClose", "click", () => safeClose(photoLightbox));
  on("lightboxPrev", "click", () => renderLightboxAt(lightboxIndex + 1));
  on("lightboxNext", "click", () => renderLightboxAt(lightboxIndex - 1));
  if (lightboxThumbs) {
    lightboxThumbs.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-lightbox-index]");
      if (!btn) return;
      renderLightboxAt(Number(btn.dataset.lightboxIndex || 0));
    });
  }
  on("lightboxCompareToggle", "click", () => {
    lightboxCompareOpen = !lightboxCompareOpen;
    renderLightboxCompare(lightboxIndex);
  });
  if (lightboxCompareSelect) {
    lightboxCompareSelect.addEventListener("change", (e) => {
      lightboxCompareTargetDate = String(e.target.value || "");
      renderLightboxCompare(lightboxIndex);
    });
  }
  on("replaceConfirmClose", "click", () => safeClose(replaceConfirmModal));
  on("replaceConfirmCancel", "click", () => safeClose(replaceConfirmModal));

  on("replaceConfirmOk", "click", async () => {
    if (!pendingReplaceAction) {
      safeClose(replaceConfirmModal);
      return;
    }
    const action = pendingReplaceAction;
    pendingReplaceAction = null;
    await action();
  });

  const managedDialogs = [
    dietModal,
    workoutModal,
    suppDayModal,
    suppCatalogModal,
    importDietModal,
    planImportModal,
    planAiWorkflowModal,
    backupRestoreModal,
    reportBugModal,
    photoLightbox,
    replaceConfirmModal,
  ];
  managedDialogs.forEach(setupBackdropClose);
  managedDialogs.forEach((dialog) => {
    if (!dialog) return;
    dialog.addEventListener("close", syncModalScrollLock);
  });
  syncModalScrollLock();

  if (replaceConfirmModal) {
    replaceConfirmModal.addEventListener("close", () => {
      pendingReplaceAction = null;
    });
  }
  if (photoLightbox) {
    photoLightbox.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") renderLightboxAt(lightboxIndex + 1);
      if (e.key === "ArrowRight") renderLightboxAt(lightboxIndex - 1);
    });
    photoLightbox.addEventListener("close", () => {
      if (lightboxImg) lightboxImg.removeAttribute("src");
      if (lightboxThumbs) lightboxThumbs.innerHTML = "";
      if (lightboxCount) lightboxCount.textContent = "0 de 0";
      if (lightboxDownload) {
        lightboxDownload.removeAttribute("href");
        lightboxDownload.removeAttribute("download");
      }
      if (lightboxMetaTag) lightboxMetaTag.textContent = "foto";
      if (lightboxCaption) lightboxCaption.textContent = "Vista previa";
      if (lightboxMetaDetails) lightboxMetaDetails.textContent = "Fecha — · Peso — · WHR —";
      if (lightboxCompareWrap) lightboxCompareWrap.hidden = true;
      if (lightboxCompareLabel) lightboxCompareLabel.textContent = "";
      if (lightboxCompareSelect) {
        lightboxCompareSelect.innerHTML = "";
        lightboxCompareSelect.disabled = true;
      }
      if (compareBeforeImg) compareBeforeImg.removeAttribute("src");
      if (compareAfterImg) compareAfterImg.removeAttribute("src");
      if (compareBeforeLabel) compareBeforeLabel.textContent = "Antes";
      if (compareAfterLabel) compareAfterLabel.textContent = "Después";
      if (lightboxCompareToggle) {
        lightboxCompareToggle.textContent = "Comparar";
        lightboxCompareToggle.disabled = false;
        lightboxCompareToggle.hidden = false;
      }
      lightboxIndex = -1;
      lightboxCompareOpen = false;
      lightboxCompareTargetDate = "";
      if (lightboxShell) lightboxShell.classList.remove("compare-open");
    });
  }
  if (importDietModal) {
    importDietModal.addEventListener("close", () => {
      if (importDietForm) importDietForm.reset();
      clearImportPreview();
    });
  }
  if (planImportModal) {
    planImportModal.addEventListener("close", () => {
      if (planDietFile) planDietFile.value = "";
      if (planWorkoutFile) planWorkoutFile.value = "";
      safeClose(planAiWorkflowModal);
      clearPlanImportSummary();
    });
  }
  if (backupRestoreModal) {
    backupRestoreModal.addEventListener("close", () => {
      if (backupRestoreForm) backupRestoreForm.reset();
    });
  }
  if (suppCatalogModal) {
    suppCatalogModal.addEventListener("close", () => {
      resetSuppCatalogForm();
    });
  }

  if (dietTable) {
    dietTable.addEventListener("click", (e) => {
      const photoBtn = e.target.closest("[data-photo-url]");
      if (photoBtn) {
        e.preventDefault();
        e.stopPropagation();
        const url = photoBtn.dataset.photoUrl || "";
        const date = photoBtn.dataset.photoDate || "";
        openLightbox(url, date ? `Foto ${date}` : "Foto", date);
        return;
      }

      const rowNode = e.target.closest("tr[data-kind='diet']");
      if (!rowNode) return;
      const row = findDietByDate(rowNode.dataset.logDate || "");
      if (row) openDietForEdit(row);
    });
  }

  if (suppCatalogTable) {
    suppCatalogTable.addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-supp-action]");
      if (!btn) return;
      const action = String(btn.dataset.suppAction || "");
      const sid = Number(btn.dataset.supplementId || 0);
      if (!sid) return;
      if (action === "edit") {
        const row = suppCatalogRows.find((r) => Number(r.supplement_id) === sid);
        if (row) fillSuppCatalogForm(row);
        return;
      }
      if (action === "delete") {
        try {
          await deleteSuppCatalog(sid);
        } catch (err) {
          showToast("Error", userErrorMessage(err));
        }
      }
    });
  }

  if (suppCatalogForm) {
    suppCatalogForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await saveSuppCatalogFromForm();
      } catch (err) {
        setSuppCatalogAlert(userErrorMessage(err));
      }
    });
  }

  if (suppDayForm) {
    suppDayForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await saveSuppDayFromForm();
      } catch (err) {
        showToast("Error", userErrorMessage(err));
      }
    });
  }

  if (suppHistoryTable) {
    suppHistoryTable.addEventListener("click", async (e) => {
      const rowNode = e.target.closest("tr[data-kind='supplement-day']");
      if (!rowNode) return;
      const logDate = String(rowNode.dataset.logDate || "").trim();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(logDate)) return;
      try {
        await openSuppDayEditor(logDate);
      } catch (err) {
        showToast("Error", userErrorMessage(err));
      }
    });
  }

  if (workTable) {
    workTable.addEventListener("click", (e) => {
      const rowNode = e.target.closest("tr[data-kind='workout']");
      if (!rowNode) return;
      const row = findWorkoutBySessionId(rowNode.dataset.sessionId || "");
      if (row) {
        // Defer modal open one frame to avoid click interception race with table row clicks.
        window.requestAnimationFrame(() => openWorkoutForEdit(row));
      }
    });
  }

  if (dietForm) {
    dietForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await submitDiet(false);
      } catch (err) {
        setDietFormAlert(userErrorMessage(err));
      }
    });
  }

  if (workSessionType) {
    workSessionType.addEventListener("change", () => {
      toggleWorkoutModeUI();
    });
  }

  if (workAddExerciseBtn) {
    workAddExerciseBtn.addEventListener("click", () => {
      addExerciseRow();
    });
  }

  if (workDoneSelect) {
    workDoneSelect.addEventListener("change", () => syncWorkDoneToggleUI());
  }
  if (workDoneButtons.length && workDoneSelect) {
    workDoneButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = String(btn?.dataset?.workDoneValue || "").toUpperCase();
        workDoneSelect.value = next === "Y" || next === "N" ? next : "";
        syncWorkDoneToggleUI();
      });
    });
  }

  if (workForm) {
    workForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      syncWorkExercisesHiddenField();
      const fd = new FormData(workForm);
      const data = {};
      for (const [k, v] of fd.entries()) data[k] = v;
      try {
        const out = await postJSON("/api/workout", data);
        safeClose(workoutModal);
        await refreshState();
        const title = (workEntryMode && workEntryMode.value === "edit") ? "Entreno actualizado" : "Entreno guardado";
        showToast(title, `Fecha ${out.log_date || isoToday()}`);
      } catch (err) {
        showToast("Error", userErrorMessage(err));
      }
    });
  }

  on("importPreviewBtn", "click", async () => {
    try {
      await previewDietImport();
      const summary = importDietSummary?.textContent || "Previsualizacion completada.";
      showToast("Preview CSV", summary);
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });

  on("importApplyBtn", "click", async () => {
    try {
      await applyDietImport();
    } catch (err) {
      showToast("Error", userErrorMessage(err));
    }
  });

  on("planImportDietBtn", "click", async () => {
    await importPlanCSV("/api/plan/import/diet", planDietFile?.files?.[0], "dieta");
  });

  on("planImportWorkoutBtn", "click", async () => {
    await importPlanCSV(
      "/api/plan/import/workout",
      planWorkoutFile?.files?.[0],
      "entreno planificado",
    );
  });
  on("planImportDownloadDetailBtn", "click", (e) => {
    const label = String(e?.currentTarget?.dataset?.detailLabel || "plan");
    downloadPlanImportDetailCsv(label);
  });

  if (backupRestoreForm) {
    backupRestoreForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await submitBackupRestore();
      } catch (err) {
        showToast("Error", userErrorMessage(err));
      }
    });
  }

  const dietSearch = on("dietSearch", "input", (e) => filterTable(dietTable, e.target.value));
  const workSearch = on("workSearch", "input", (e) => filterTable(workTable, e.target.value));

  on("dietLimitSelect", "change", async (e) => {
    const next = parseLimitValue(e?.target?.value, dietLimit);
    if (next === dietLimit) return;
    dietLimit = next;
    await refreshState();
    if (dietSearch && dietSearch.value) filterTable(dietTable, dietSearch.value);
  });

  on("workLimitSelect", "change", async (e) => {
    const next = parseLimitValue(e?.target?.value, workLimit);
    if (next === workLimit) return;
    workLimit = next;
    await refreshState();
    if (workSearch && workSearch.value) filterTable(workTable, workSearch.value);
  });

  // ----------------------------
  // Initial render
  // ----------------------------
  setActiveView(readInitialView(), { persist: false, syncHash: true });
  latestSummary = INITIAL_STATE.summary || {};
  summaryWindowDays = parseLimitValue(INITIAL_STATE.summary?.window_days, summaryWindowDays);
  if (summaryModeSelect) {
    summaryModeSelect.value = INITIAL_STATE.summary?.mode === "range"
      ? "custom"
      : String(summaryWindowDays);
  }
  if (perfModeSelect) {
    perfModeSelect.value = INITIAL_STATE.summary?.mode === "range"
      ? "custom"
      : String(summaryWindowDays);
  }
  syncSummaryAnalysisUI();
  syncPerfAnalysisUI();
  renderSummary(latestSummary);
  renderDiet(INITIAL_STATE.diet || []);
  renderWorkout(INITIAL_STATE.workout || []);
  if (planAdherenceWindow) planAdherenceWindow.value = String(planAdherenceWindowDays);
  renderPlanDay(INITIAL_STATE.plan_today || { log_date: isoToday() });
  lightboxItems = normalizePhotoItems(INITIAL_STATE.photos || [], INITIAL_STATE.diet || []);
  renderPerformanceChart(chartMetric);
  setSyncStatus(syncOkStatus(INITIAL_STATE.diet || [], INITIAL_STATE.workout || []), "ok");

  if (INITIAL_STATE.summary?.mode === "range") {
    summaryRangeFrom = String(INITIAL_STATE.summary?.date_from || "");
    summaryRangeTo = String(INITIAL_STATE.summary?.date_to || "");
    if (summaryFrom) summaryFrom.value = summaryRangeFrom;
    if (summaryTo) summaryTo.value = summaryRangeTo;
    if (perfFrom) perfFrom.value = summaryRangeFrom;
    if (perfTo) perfTo.value = summaryRangeTo;
  }

  const dietDate = $("diet_date");
  if (dietDate && !dietDate.value) dietDate.value = isoToday();

  const workDate = $("work_date");
  if (workDate && !workDate.value) workDate.value = isoToday();
  if (dietLimitSelect) dietLimitSelect.value = String(dietLimit);
  if (workLimitSelect) workLimitSelect.value = String(workLimit);
  if (summaryModeSelect && !isSummaryCustomMode()) summaryModeSelect.value = String(summaryWindowDays);
  if (perfModeSelect && !isPerfCustomMode()) perfModeSelect.value = String(summaryWindowDays);
  if (suppLimitSelect) suppLimitSelect.value = String(suppLimit);
  if (planDayDate && !planDayDate.value) planDayDate.value = String(currentPlanDay?.log_date || isoToday());
  toggleWorkoutModeUI();
  syncWorkDoneToggleUI();
})();
