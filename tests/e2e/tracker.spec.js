const fs = require("fs");
const path = require("path");
const { test, expect } = require("@playwright/test");

const DIET_DATE = "2099-01-11";
const WORK_DATE = "2099-01-12";
const IMPORT_EXISTING_DATE = "2099-02-10";
const IMPORT_NEW_DATE = "2099-02-11";
const RANGE_FROM = "2099-03-01";
const RANGE_TO = "2099-03-20";
const BACKUP_BASE_DATE = "2099-04-01";
const BACKUP_TEMP_DATE = "2099-04-02";
const PLAN_DAY_ONE = "2099-05-01";
const PLAN_DAY_TWO = "2099-05-02";
const PHOTO_FIXTURE = path.resolve(__dirname, "../fixtures/photo.png");

async function goView(page, viewName) {
  await page.click(`.view-nav [data-view-target='${viewName}']`);
  await expect(page.locator(`.app-view[data-view='${viewName}']`).first()).toBeVisible();
}

async function openFabAction(page, selector) {
  const desktopMap = {
    "#fabDiet": "#btnDiet",
    "#fabWorkout": "#btnWorkout",
    "#fabSupplements": "#btnSupplements",
  };
  const desktopBtn = desktopMap[selector];
  if (desktopBtn && await page.locator(desktopBtn).isVisible()) {
    await page.click(desktopBtn);
    return;
  }
  const menu = page.locator("#fabMenu");
  if (await menu.isHidden()) {
    await page.click("#fabMain");
    await expect(menu).toBeVisible();
  }
  await page.click(selector);
}

async function clickAndAcceptDialogs(page, selector) {
  const handler = (dialog) => {
    dialog.accept().catch(() => {});
  };
  page.on("dialog", handler);
  try {
    await page.click(selector);
    await page.waitForTimeout(120);
  } finally {
    page.off("dialog", handler);
  }
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Gym Tracker");
  await goView(page, "home");
});

test("topbar permanece visible en scroll largo", async ({ page }) => {
  const topbar = page.locator("body.page-index .topbar").first();
  await expect(topbar).toBeVisible();

  await page.evaluate(() => {
    const shell = document.querySelector(".wrap.app-shell");
    if (!shell) return;
    const filler = document.createElement("div");
    filler.id = "qa-sticky-filler";
    filler.style.height = "4200px";
    shell.appendChild(filler);
    window.scrollTo(0, 0);
  });

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(120);
  const box = await topbar.boundingBox();
  expect(box).toBeTruthy();
  expect(box.y).toBeGreaterThanOrEqual(-1);
  expect(box.y).toBeLessThanOrEqual(1.5);
});

test("check-in con foto, edicion y lightbox", async ({ page, request }) => {
  const toast = page.locator("#toast");
  const dietModal = page.locator("#dietModal");

  await openFabAction(page, "#fabDiet");
  await expect(dietModal).toHaveAttribute("open", "");

  await page.fill("#dietForm input[name='log_date']", DIET_DATE);
  await page.fill("#dietForm input[name='sleep_hours']", "7.4");
  await page.fill("#dietForm input[name='steps']", "9500");
  await page.fill("#dietForm input[name='weight_kg']", "70.2");
  await page.fill("#dietForm input[name='waist_cm']", "78.2");
  await page.fill("#dietForm input[name='hip_cm']", "97.5");

  await page.click("#dietForm button[type='submit']");
  await expect(dietModal).not.toHaveAttribute("open", "");
  await expect(toast).toContainText("Check-in guardado");
  await expect(toast).toHaveClass(/show/);
  await expect(toast).not.toHaveClass(/show/, { timeout: 5000 });

  const row = page.locator(
    `#dietTable tbody tr[data-kind='diet'][data-log-date='${DIET_DATE}']`
  );
  await goView(page, "checkin");
  await expect(row).toBeVisible();
  await expect(row).toContainText("9.500");
  await expect(row.locator("td[data-label='Foto'] button[data-photo-url]")).toHaveCount(0);

  await row.click();
  await expect(dietModal).toHaveAttribute("open", "");
  await page.fill("#dietForm input[name='steps']", "12345");
  await page.click("#dietForm button[type='submit']");
  await expect(dietModal).not.toHaveAttribute("open", "");
  await expect(toast).toContainText("Check-in actualizado");
  await expect(toast).toHaveClass(/show/);

  const updatedRow = page.locator(
    `#dietTable tbody tr[data-kind='diet'][data-log-date='${DIET_DATE}']`
  );
  await expect(updatedRow).toContainText("12.345");

  // Upload por UI: debe persistir foto real (regresión de input file vacío).
  await updatedRow.click();
  await expect(dietModal).toHaveAttribute("open", "");
  await page.setInputFiles("#photoFile", PHOTO_FIXTURE);
  await page.click("#dietForm button[type='submit']");
  await expect(dietModal).not.toHaveAttribute("open", "");
  await expect(toast).toContainText("Check-in actualizado");

  await expect(
    page.locator(`#dietTable tbody tr[data-kind='diet'][data-log-date='${DIET_DATE}'] button[data-photo-url]`)
  ).toBeVisible();

  // Seed adicional para comparación en lightbox.
  const olderPhotoRes = await request.post("/api/diet", {
    multipart: {
      log_date: "2099-01-10",
      sleep_hours: "7.0",
      steps: "12000",
      weight_kg: "70.6",
      waist_cm: "78.8",
      hip_cm: "97.8",
      photo: {
        name: "photo-old.png",
        mimeType: "image/png",
        buffer: fs.readFileSync(PHOTO_FIXTURE),
      },
    },
  });
  expect(olderPhotoRes.ok()).toBeTruthy();

  await page.reload();
  await goView(page, "checkin");
  const rowWithPhoto = page.locator(
    `#dietTable tbody tr[data-kind='diet'][data-log-date='${DIET_DATE}']`
  );
  await expect(rowWithPhoto).toBeVisible();

  const photoBtn = rowWithPhoto.locator("button[data-photo-url]");
  await expect(photoBtn).toBeVisible();
  await photoBtn.click();
  await expect(page.locator("#photoLightbox")).toHaveAttribute("open", "");
  await expect(page.locator("#lightboxImg")).toHaveAttribute("src", /uploads/);
  await expect(page.locator("#lightboxCount")).toContainText("de");
  await expect(page.locator("#lightboxPrev")).toBeEnabled();
  await expect(page.locator("#lightboxCompareToggle")).toBeEnabled();
  await page.click("#lightboxCompareToggle");
  const compareWrap = page.locator("#lightboxCompareWrap");
  await expect(compareWrap).toBeVisible();
  const compareBox = await compareWrap.boundingBox();
  expect(compareBox).toBeTruthy();
  expect(compareBox.height).toBeGreaterThan(120);
  await page.click("#lightboxClose");
  await expect(page.locator("#photoLightbox")).not.toHaveAttribute("open", "");

  await rowWithPhoto.click();
  await expect(dietModal).toHaveAttribute("open", "");
  page.once("dialog", (dialog) => dialog.accept());
  await page.click("#photoClear");
  await expect(toast).toContainText("Foto eliminada");
  await expect(rowWithPhoto.locator("button[data-photo-url]")).toHaveCount(0);
  await page.click("#dietCancel");
  await expect(dietModal).not.toHaveAttribute("open", "");

  await rowWithPhoto.click();
  await expect(dietModal).toHaveAttribute("open", "");
  await expect(page.locator("#dietDeleteBtn")).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page.click("#dietDeleteBtn");
  await expect(dietModal).not.toHaveAttribute("open", "");
  await expect(page.locator("#toast")).toContainText("Check-in eliminado");
  await expect(
    page.locator(`#dietTable tbody tr[data-kind='diet'][data-log-date='${DIET_DATE}']`)
  ).toHaveCount(0);
});

test("check-in create abre limpio y no arrastra valores previos", async ({ page }) => {
  const date = "2099-01-13";

  await openFabAction(page, "#fabDiet");
  await expect(page.locator("#dietModal")).toHaveAttribute("open", "");
  await page.fill("#dietForm input[name='log_date']", date);
  await page.fill("#dietForm input[name='sleep_hours']", "7.9");
  await page.fill("#dietForm input[name='steps']", "12345");
  await page.fill("#dietForm input[name='weight_kg']", "71.4");
  await page.fill("#dietForm input[name='waist_cm']", "79.3");
  await page.fill("#dietForm input[name='hip_cm']", "98.1");
  await page.click("#dietForm button[type='submit']");
  await expect(page.locator("#toast")).toContainText("Check-in guardado");

  await openFabAction(page, "#fabDiet");
  await expect(page.locator("#dietModal")).toHaveAttribute("open", "");
  await expect(page.locator("#dietForm input[name='log_date']")).not.toHaveValue(date);
  await expect(page.locator("#dietForm input[name='sleep_hours']")).toHaveValue("");
  await expect(page.locator("#dietForm input[name='steps']")).toHaveValue("");
  await expect(page.locator("#dietForm input[name='weight_kg']")).toHaveValue("");
  await expect(page.locator("#dietForm input[name='waist_cm']")).toHaveValue("");
  await expect(page.locator("#dietForm input[name='hip_cm']")).toHaveValue("");
  await expect(page.locator("#dietEntryMode")).toHaveValue("create");
  await expect(page.locator("#dietDeleteBtn")).toBeHidden();
});

test("entreno, filtro y toggle de limite", async ({ page }) => {
  await openFabAction(page, "#fabWorkout");
  await expect(page.locator("#workoutModal")).toHaveAttribute("open", "");

  await page.fill("#workForm input[name='log_date']", WORK_DATE);
  await page.selectOption("#workForm select[name='session_type']", "pesas");
  await page.selectOption("#workForm select[name='session_done_yn']", "Y");
  await page.fill("#workForm input[name='rpe_session']", "7");
  const firstExercise = page.locator("#workExerciseList [data-exercise-row]").first();
  await expect(firstExercise).toBeVisible();
  await firstExercise.locator("[data-ex-field='exercise_name']").fill("Hip Thrust");
  await firstExercise.locator("[data-ex-field='weight_kg']").fill("120");
  await firstExercise.locator("[data-ex-field='reps']").fill("6");
  await firstExercise.locator("[data-ex-field='rpe']").fill("8");
  await page.click("#workAddExerciseBtn");
  const secondExercise = page.locator("#workExerciseList [data-exercise-row]").nth(1);
  await expect(secondExercise).toBeVisible();
  await secondExercise.locator("[data-ex-field='exercise_name']").fill("Sentadilla");
  await secondExercise.locator("[data-ex-field='weight_kg']").fill("80");
  await secondExercise.locator("[data-ex-field='reps']").fill("8");
  await secondExercise.locator("[data-ex-field='rpe']").fill("7");
  await page.fill("#workForm textarea[name='notes']", "Notas QA, con coma");

  await page.click("#workForm button[type='submit']");
  await expect(page.locator("#toast")).toContainText("Entreno guardado");

  const row = page.locator(
    `#workTable tbody tr[data-kind='workout'][data-log-date='${WORK_DATE}']`
  );
  await goView(page, "workouts");
  await expect(row).toBeVisible();
  await expect(row).toContainText("Pesas");
  await expect(row).toContainText("Hip Thrust");

  await page.fill("#workSearch", "Hip Thrust");
  await expect(row).toBeVisible();

  await page.fill("#workSearch", "NO_EXISTE_EN_TABLA");
  await expect(row).toBeHidden();

  await page.fill("#workSearch", "");
  await page.selectOption("#workLimitSelect", "30");
  await expect(page.locator("#workLimitSelect")).toHaveValue("30");

  await row.click();
  await expect(page.locator("#workoutModal")).toHaveAttribute("open", "");
  await expect(page.locator("#workDeleteBtn")).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page.click("#workDeleteBtn");
  await expect(page.locator("#workoutModal")).not.toHaveAttribute("open", "");
  await expect(page.locator("#toast")).toContainText("Entreno eliminado");
  await expect(
    page.locator(`#workTable tbody tr[data-kind='workout'][data-log-date='${WORK_DATE}']`)
  ).toHaveCount(0);
});

test("pesas sin ejercicios no persiste ejercicios por defecto", async ({ page, request }) => {
  const date = "2099-01-14";

  await openFabAction(page, "#fabWorkout");
  await expect(page.locator("#workoutModal")).toHaveAttribute("open", "");
  await page.fill("#workForm input[name='log_date']", date);
  await page.selectOption("#workForm select[name='session_type']", "pesas");
  await expect(page.locator("#workExerciseList [data-exercise-row]")).toHaveCount(1);
  await page.click("#workExerciseList [data-remove-exercise]");
  await expect(page.locator("#workExerciseList [data-exercise-row]")).toHaveCount(0);
  await page.click("#workForm button[type='submit']");
  await expect(page.locator("#toast")).toContainText("Entreno guardado");

  await goView(page, "workouts");
  const row = page.locator(`#workTable tbody tr[data-kind='workout'][data-log-date='${date}']`);
  await expect(row).toBeVisible();
  await expect(row).not.toContainText("Hip Thrust");
  await expect(row).not.toContainText("Sentadilla");

  const apiState = await request.get("/api/state?limit=15");
  expect(apiState.ok()).toBeTruthy();
  const payload = await apiState.json();
  const apiRow = (payload.workout || []).find((item) => item.log_date === date);
  expect(apiRow).toBeTruthy();
  expect(apiRow.session_type).toBe("pesas");
  expect(Array.isArray(apiRow.exercises)).toBeTruthy();
  expect(apiRow.exercises).toHaveLength(0);
});

test("suplementos: catalogo editable y registro diario", async ({ page, request }) => {
  const toast = page.locator("#toast");
  const supplementsView = page.locator(".app-view[data-view='supplements']");
  const catalogModal = page.locator("#suppCatalogModal");
  const dayModal = page.locator("#suppDayModal");
  const uniqueSeed = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const suffix = uniqueSeed.slice(-8);
  const melName = `Melatonina QA ${suffix}`;
  const wheyName = `Whey QA ${suffix}`;
  const month = String((Number(uniqueSeed.slice(-4, -2)) % 12) + 1).padStart(2, "0");
  const day = String((Number(uniqueSeed.slice(-2)) % 28) + 1).padStart(2, "0");
  const suppDate = `2099-${month}-${day}`;

  await goView(page, "supplements");
  await expect(supplementsView).toBeVisible();

  await page.click("#btnSupplements");
  await expect(dayModal).toHaveAttribute("open", "");
  await page.click("#suppCatalogBtn");
  await expect(catalogModal).toHaveAttribute("open", "");

  await page.fill("#supplementName", melName);
  await page.fill("#supplementDosesPerDay", "1");
  await page.fill("#supplementNotes", "Antes de dormir");
  await page.click("#suppSaveBtn");
  await expect(toast).toContainText("Suplemento");

  await page.fill("#supplementName", wheyName);
  await page.fill("#supplementDosesPerDay", "2");
  await page.click("#suppSaveBtn");
  await expect(toast).toContainText("Suplemento");

  const wheyRow = page.locator("#suppCatalogTable tbody tr", { hasText: wheyName });
  await expect(wheyRow).toBeVisible();
  await wheyRow.locator("button[data-supp-action='edit']").click();
  await page.fill("#supplementDosesPerDay", "3");
  await page.click("#suppSaveBtn");
  await expect(wheyRow).toContainText("3");

  await page.click("#suppCatalogDone");
  await expect(catalogModal).not.toHaveAttribute("open", "");
  await page.fill("#suppDayDate", suppDate);
  await Promise.all([
    page.waitForResponse(
      (res) =>
        res.url().includes(`/api/supplements/day?log_date=${encodeURIComponent(suppDate)}`) &&
        res.status() === 200
    ),
    page.click("#suppDayLoadBtn"),
  ]);

  const melRow = page.locator("#suppDayTable tbody tr", { hasText: melName });
  const wheyDayRow = page.locator("#suppDayTable tbody tr", { hasText: wheyName });
  await expect(melRow).toBeVisible();
  await expect(wheyDayRow).toBeVisible();

  await melRow.locator("input[data-supp-field='doses_taken']").fill("1");
  await wheyDayRow.locator("input[data-supp-field='doses_taken']").fill("3");
  await melRow.locator("input[data-supp-field='notes']").fill("OK");
  await wheyDayRow.locator("input[data-supp-field='notes']").fill("Post entreno");
  await Promise.all([
    page.waitForResponse(
      (res) =>
        res.url().includes("/api/supplements/day") &&
        res.request().method() === "POST" &&
        res.status() === 200
    ),
    page.click("#suppSaveDayBtn"),
  ]);
  await expect(toast).toContainText("Suplementos guardados");
  await expect(dayModal).not.toHaveAttribute("open", "");

  const historyRow = page.locator(
    `#suppHistoryTable tbody tr[data-kind='supplement-day'][data-log-date='${suppDate}']`,
    { hasText: melName }
  );
  await expect(historyRow).toBeVisible();
  await expect(historyRow).toContainText(melName);
  await expect(historyRow).toContainText(wheyName);

  await Promise.all([
    page.waitForResponse(
      (res) =>
        res.url().includes(`/api/supplements/day?log_date=${encodeURIComponent(suppDate)}`) &&
        res.status() === 200
    ),
    historyRow.click(),
  ]);
  await expect(dayModal).toHaveAttribute("open", "");
  await expect(page.locator("#suppDayDate")).toHaveValue(suppDate);
  const melRowReload = page.locator("#suppDayTable tbody tr", { hasText: melName });
  const wheyRowReload = page.locator("#suppDayTable tbody tr", { hasText: wheyName });
  await expect(melRowReload).toHaveCount(1);
  await expect(wheyRowReload).toHaveCount(1);

  const dayCheck = await request.get(`/api/supplements/day?log_date=${encodeURIComponent(suppDate)}`);
  expect(dayCheck.ok()).toBeTruthy();
  const dayPayload = await dayCheck.json();
  const dayByName = Object.fromEntries((dayPayload.entries || []).map((item) => [item.name, item]));
  expect(dayByName[melName]).toBeTruthy();
  expect(dayByName[wheyName]).toBeTruthy();

  page.once("dialog", (dialog) => dialog.accept());
  await page.click("#suppDayDeleteBtn");
  await expect(dayModal).not.toHaveAttribute("open", "");
  await expect(toast).toContainText("eliminado");
  await expect(page.locator("#suppHistoryTable tbody tr[data-kind='supplement-day']", { hasText: melName })).toHaveCount(0);
});

test("importacion CSV dieta con preview y conflictos por fecha", async ({ page, request }) => {
  const existing = await request.post("/api/diet", {
    data: {
      log_date: IMPORT_EXISTING_DATE,
      sleep_hours: 7.0,
      steps: 5000,
      weight_kg: 70.0,
      waist_cm: 78.0,
      hip_cm: 98.0,
    },
  });
  expect(existing.ok()).toBeTruthy();

  const csvText = [
    "log_date,sleep_hours,steps,weight_kg,waist_cm,hip_cm,creatine_yn,alcohol_units",
    `${IMPORT_EXISTING_DATE},7.4,9999,69.9,77.0,96.0,Y,1`,
    `${IMPORT_NEW_DATE},7.2,9100,69.5,76.8,95.8,N,0`,
    "bad-date,7.1,9000,70.1,78.0,97.0,Y,0",
  ].join("\n");

  await goView(page, "checkin");
  await page.click("#btnImportDiet");
  await expect(page.locator("#importDietModal")).toHaveAttribute("open", "");
  await page.setInputFiles("#importDietFile", {
    name: "diet-import.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csvText, "utf-8"),
  });

  await page.click("#importPreviewBtn");
  await expect(page.locator("#importDietSummary")).toContainText("validas: 1");
  await expect(page.locator("#importDietSummary")).toContainText("conflictos: 1");
  await expect(page.locator("#importDietSummary")).toContainText("invalidas: 1");

  const previewTable = page.locator("#importPreviewTable");
  await expect(previewTable).toContainText(IMPORT_NEW_DATE);
  await expect(previewTable).toContainText("Conflicto");
  await expect(previewTable).toContainText("Invalida");

  await page.click("#importApplyBtn");
  await expect(page.locator("#toast")).toContainText("Importacion completada");
  await page.click("#importDietClose");
  await expect(page.locator("#importDietModal")).not.toHaveAttribute("open", "");

  const importedRow = page.locator(
    `#dietTable tbody tr[data-kind='diet'][data-log-date='${IMPORT_NEW_DATE}']`
  );
  await goView(page, "checkin");
  await expect(importedRow).toBeVisible();
  await expect(importedRow).toContainText("9.100");

  const existingRow = page.locator(
    `#dietTable tbody tr[data-kind='diet'][data-log-date='${IMPORT_EXISTING_DATE}']`
  );
  await expect(existingRow).toContainText("5.000");
  await expect(existingRow).not.toContainText("9.999");
});

test("planes permite borrar por fecha/sesion y vaciar dieta-entreno completos", async ({ page, request }) => {
  const dietCsv = [
    "date,calories_target_kcal,protein_target_g,carbs_target_g,fat_target_g,breakfast,snack_1,lunch,snack_2,dinner,notes",
    `${PLAN_DAY_ONE},2200,150,220,80,Huevos,Fruta,Pollo,Yogur,Pescado,Dia 1`,
    `${PLAN_DAY_TWO},2300,150,260,70,Avena,Fruta,Carne,Queso,Tortilla,Dia 2`,
  ].join("\n");
  const workoutCsv = [
    "log_date,session_type,warmup,class_sessions,cardio,mobility_cooldown,additional_exercises,notes,exercise_1_name,exercise_1_sets,exercise_1_reps_min,exercise_1_reps_max,exercise_1_weight_kg,exercise_1_rpe,exercise_1_intensity_target,exercise_1_progression_weight_rule,exercise_1_progression_reps_rule",
    `${PLAN_DAY_ONE},pesas,Bici 10,,Caminata,Movilidad,Pallof,AM,Hip Thrust,4,5,8,120,8,RPE 7-8,+2.5kg,+1 rep`,
    `${PLAN_DAY_ONE},clase,,Pilates,,,Bandas,PM,,,,,,,`,
    `${PLAN_DAY_TWO},pesas,Bici 5,,Caminata,Movilidad,,Noche,Sentadilla,4,6,8,90,7.5,RPE 7-8,+2kg,+1 rep`,
  ].join("\n");

  const importDiet = await request.post("/api/plan/import/diet", {
    multipart: {
      file: {
        name: "plan_diet.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(dietCsv, "utf-8"),
      },
      source_tag: "e2e",
    },
  });
  expect(importDiet.ok()).toBeTruthy();

  const importWorkout = await request.post("/api/plan/import/workout", {
    multipart: {
      file: {
        name: "plan_workout.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(workoutCsv, "utf-8"),
      },
      source_tag: "e2e",
    },
  });
  expect(importWorkout.ok()).toBeTruthy();

  await page.reload();
  await goView(page, "plans");
  await expect(page.locator("#planHubTitle")).toHaveText("Planes");
  await expect(page.locator("label[for='planAdherenceWindow']")).toHaveText("Período");
  await expect(page.locator("#planOpenDietBtn")).toHaveCount(0);
  await expect(page.locator("#planOpenWorkoutBtn")).toHaveCount(0);
  await page.fill("#planDayDate", PLAN_DAY_ONE);
  await page.click("#planDayLoadBtn");
  await expect(page.locator("#planDietMeals")).toContainText("Huevos");
  await expect(page.locator("#planWorkoutSessions .plan-session")).toHaveCount(2);
  await expect(page.locator("#planDietMacros")).toContainText("Proteínas:");
  await expect(page.locator("#planDietMacros")).toContainText("Carbs:");
  await expect(page.locator("#planDietMacros")).toContainText("Grasas:");
  await expect(page.locator("#planDietMacros")).toContainText("150 g");

  await page.click("#btnPlanHubImport");
  await expect(page.locator("#planImportModal")).toHaveAttribute("open", "");
  await expect(page.locator("a[href='/export/template/plan-csv-ai-instructions-diet.md']")).toHaveCount(1);
  await expect(page.locator("a[href='/export/template/plan-csv-ai-instructions-workout.md']")).toHaveCount(1);
  await page.click("#planImportCancel");
  await expect(page.locator("#planImportModal")).not.toHaveAttribute("open", "");

  await page.selectOption("#planDietScore", "1");
  await page.selectOption("#planWorkoutScore", "0.5");
  await page.click("#planSaveAdherenceBtn");
  await expect(page.locator("#toast")).toContainText("Puntuación guardada");
  await expect(page.locator("#planDietActualPill")).toContainText("Cumplida");
  await expect(page.locator("#planWorkoutActualPill")).toContainText("Parcial");
  await expect(page.locator("#planAdherencePeriod")).toContainText("Resumen del período");
  await expect(page.locator("#planAdherenceHistoryList")).toContainText("Media diaria combinada");

  await clickAndAcceptDialogs(page, "#planDeleteDietDayBtn");
  await expect(page.locator("#toast")).toContainText("Dieta del día eliminada");
  await expect(page.locator("#planDietActualPill")).toContainText("Sin plan");

  await clickAndAcceptDialogs(page, "[data-plan-delete-session='S01']");
  await expect(page.locator("#toast")).toContainText("Sesión S01 eliminada");
  await expect(page.locator("#planWorkoutSessions .plan-session")).toHaveCount(1);
  await expect(page.locator("#planWorkoutSessions")).toContainText("S02");

  await clickAndAcceptDialogs(page, "#planFlushWorkoutBtn");
  await expect(page.locator("#toast")).toContainText("Entreno planificado vaciado");
  await expect(page.locator("#planWorkoutActualPill")).toContainText("Sin plan");

  await page.fill("#planDayDate", PLAN_DAY_TWO);
  await page.click("#planDayLoadBtn");
  await expect(page.locator("#planDietMeals")).toContainText("Avena");
  await clickAndAcceptDialogs(page, "#planFlushDietBtn");
  await expect(page.locator("#toast")).toContainText("Dieta plan vaciada");
  await expect(page.locator("#planDietActualPill")).toContainText("Sin plan");
});

test("kpis por rango libre y tendencia corporal", async ({ page, request }) => {
  const previousRows = [
    { log_date: "2099-02-10", sleep_hours: 6.5, steps: 8000, weight_kg: 71.0, waist_cm: 81.0, hip_cm: 100.0 },
    { log_date: "2099-02-15", sleep_hours: 6.8, steps: 8500, weight_kg: 71.0, waist_cm: 81.2, hip_cm: 100.0 },
    { log_date: "2099-02-20", sleep_hours: 6.7, steps: 8200, weight_kg: 71.0, waist_cm: 81.1, hip_cm: 100.0 },
  ];
  for (const row of previousRows) {
    const res = await request.post("/api/diet", { data: row });
    expect(res.ok()).toBeTruthy();
  }

  const seedRows = [
    { log_date: "2099-03-01", sleep_hours: 7.0, steps: 10000, weight_kg: 70.0, waist_cm: 80.0, hip_cm: 100.0 },
    { log_date: "2099-03-10", sleep_hours: 7.0, steps: 9000, weight_kg: 69.0, waist_cm: 79.0, hip_cm: 100.0 },
    { log_date: "2099-03-20", sleep_hours: 7.0, steps: 11000, weight_kg: 68.0, waist_cm: 78.0, hip_cm: 100.0 },
  ];
  for (const row of seedRows) {
    const res = await request.post("/api/diet", { data: row });
    expect(res.ok()).toBeTruthy();
  }

  await page.selectOption("#summaryModeSelect", "custom");
  await page.fill("#summaryFrom", RANGE_FROM);
  await page.fill("#summaryTo", RANGE_TO);
  await page.click("#summaryApplyBtn");

  await expect(page.locator("#summaryCaption")).toContainText("de un total de 20");
  await expect(page.locator("#summaryCaption")).toContainText(/d[ií]as con datos/i);
  await expect(page.locator("#kpiWeightTitle")).toContainText("PESO");
  await expect(page.locator("#kWeight")).toContainText("69,0 kg");
  await expect(page.locator("#kWeightDelta")).toContainText("Mejor:");
  await expect(page.locator("#kWeightDelta")).toContainText("kg");
  await expect(page.locator("#kWeightDelta")).toContainText("Del: 09-02-2099");
  await expect(page.locator("#kWeightDelta")).toContainText("Al: 28-02-2099");
  await expect(page.locator("#kSleepDelta")).toContainText(/Mejor|Igual|Peor/);
  await expect(page.locator("#kStepsDelta")).toContainText(/Mejor|Igual|Peor/);
  await expect(page.locator("#kWHRDelta")).toContainText(/Mejor|Igual|Peor/);
  await goView(page, "progress");
  await expect(page.locator("#perfChart .chart-line")).toBeVisible();
  await expect(page.locator("#perfChart .chart-area")).toBeVisible();
  await expect(page.locator("#perfChart .chart-y")).toHaveCount(2);
  await expect(page.locator("#viewAllPhotosBtn")).toBeVisible();
  await expect(page.locator("#exportReportPdfBtn")).toBeVisible();
  await expect(page.locator("#shareReportBtn")).toBeHidden();
  await expect(page.locator("#exportReportBtn")).toBeHidden();
  await expect(page.locator("#copyReportBtn")).toBeHidden();
  await expect(page.locator("#syncStatus")).toContainText("Última sincronización:");
  await expect(page.locator("#trendText")).toContainText(/buena señal|bajan/i);
  await expect(page.locator("#trendDelta")).toContainText(/Cambios en el per/i);
  await expect(page.locator("#trendDelta")).toContainText(/Peso:\s*-2,0 kg/i);

  await goView(page, "home");
  await page.selectOption("#summaryModeSelect", "30");
  await expect(page.locator("#summaryCaption")).toContainText("de un total de 30");
  await expect(page.locator("#kWeightPeriod")).toContainText("Del:");
  await expect(page.locator("#kWeightPeriod")).toContainText("Al:");
  await page.selectOption("#summaryModeSelect", "7");
  await expect(page.locator("#summaryCaption")).toContainText("de un total de 7");
  await expect(page.locator("#kWeightPeriod")).toContainText("Del:");
  await expect(page.locator("#kWeightPeriod")).toContainText("Al:");
});

test("backup export y restauracion desde GUI", async ({ page, request }) => {
  const baseSeed = await request.post("/api/diet", {
    data: {
      log_date: BACKUP_BASE_DATE,
      sleep_hours: 7.1,
      steps: 9000,
      weight_kg: 70.0,
      waist_cm: 79.0,
      hip_cm: 99.0,
    },
  });
  expect(baseSeed.ok()).toBeTruthy();

  const backupRes = await request.get("/backup/export");
  expect(backupRes.ok()).toBeTruthy();
  const backupBuffer = Buffer.from(await backupRes.body());

  const tempSeed = await request.post("/api/diet", {
    data: {
      log_date: BACKUP_TEMP_DATE,
      sleep_hours: 8.5,
      steps: 12000,
      weight_kg: 69.0,
      waist_cm: 77.0,
      hip_cm: 98.0,
    },
  });
  expect(tempSeed.ok()).toBeTruthy();

  await page.reload();
  await goView(page, "checkin");
  await expect(
    page.locator(`#dietTable tbody tr[data-kind='diet'][data-log-date='${BACKUP_TEMP_DATE}']`)
  ).toBeVisible();

  await goView(page, "data");
  await expect(page.locator("#dataHubTitle")).toContainText("Backups");
  await expect(page.locator(".app-view[data-view='data'] #btnImportDiet")).toHaveCount(0);
  await expect(page.locator(".app-view[data-view='data'] a[href='/export/diet.csv']")).toHaveCount(0);
  await expect(page.locator(".app-view[data-view='data'] a[href='/export/workout.csv']")).toHaveCount(0);
  await expect(page.locator(".app-view[data-view='data'] a[href='/export/supplements.csv']")).toHaveCount(0);
  await page.click("#btnRestoreBackup");
  await expect(page.locator("#backupRestoreModal")).toHaveAttribute("open", "");
  await page.setInputFiles("#backupRestoreFile", {
    name: "tracker-backup.zip",
    mimeType: "application/zip",
    buffer: backupBuffer,
  });
  await page.check("#backupRestoreConfirm");
  await page.click("#backupRestoreSubmit");

  await expect(page.locator("#toast")).toContainText("Backup restaurado");
  await goView(page, "checkin");
  await expect(
    page.locator(`#dietTable tbody tr[data-kind='diet'][data-log-date='${BACKUP_BASE_DATE}']`)
  ).toBeVisible();
  await expect(
    page.locator(`#dietTable tbody tr[data-kind='diet'][data-log-date='${BACKUP_TEMP_DATE}']`)
  ).toHaveCount(0);
});

test("entreno permite varias sesiones el mismo dia y edicion por sesion", async ({ page }) => {
  const date = "2099-01-20";

  await openFabAction(page, "#fabWorkout");
  await expect(page.locator("#workClassLabel")).toHaveText("Clase / actividad");
  await page.selectOption("#workForm select[name='session_type']", "pesas");
  await expect(page.locator("#workClassLabel")).toHaveText("Foco de la sesión (opcional)");
  await page.selectOption("#workForm select[name='session_type']", "clase");
  await page.fill("#workForm input[name='log_date']", date);
  await page.selectOption("#workForm select[name='session_done_yn']", "Y");
  await page.fill("#workForm input[name='class_done']", "BASE AM");
  await page.click("#workForm button[type='submit']");
  await expect(page.locator("#toast")).toContainText("Entreno guardado");

  await openFabAction(page, "#fabWorkout");
  await expect(page.locator("#workForm input[name='class_done']")).toHaveValue("");
  await page.fill("#workForm input[name='log_date']", date);
  await page.selectOption("#workForm select[name='session_type']", "clase");
  await page.selectOption("#workForm select[name='session_done_yn']", "N");
  await page.fill("#workForm input[name='class_done']", "PM RECOVERY");
  await page.click("#workForm button[type='submit']");
  await expect(page.locator("#toast")).toContainText("Entreno guardado");

  const rows = page.locator(`#workTable tbody tr[data-kind='workout'][data-log-date='${date}']`);
  await goView(page, "workouts");
  await expect(rows).toHaveCount(2);
  const baseRow = rows.filter({ hasText: "BASE AM" }).first();
  const pmRow = rows.filter({ hasText: "PM RECOVERY" }).first();
  await expect(baseRow).toBeVisible();
  await expect(pmRow).toBeVisible();

  await baseRow.click();
  await page.fill("#workForm input[name='class_done']", "EDITADO");
  await page.click("#workForm button[type='submit']");
  await expect(page.locator("#toast")).toContainText("Entreno actualizado");
  await expect(page.locator(`#workTable tbody tr[data-kind='workout'][data-log-date='${date}']`).filter({ hasText: "EDITADO" })).toHaveCount(1);
  await expect(page.locator(`#workTable tbody tr[data-kind='workout'][data-log-date='${date}']`).filter({ hasText: "PM RECOVERY" })).toHaveCount(1);

  const editedRow = page
    .locator(`#workTable tbody tr[data-kind='workout'][data-log-date='${date}']`)
    .filter({ hasText: "EDITADO" })
    .first();
  await editedRow.click();
  await page.click("#workForm .done-btn.clear");
  await page.click("#workForm button[type='submit']");
  await expect(page.locator("#toast")).toContainText("Entreno actualizado");
  await expect(editedRow.locator("td[data-label='Hecho']")).toContainText("—");
});

test("galeria fotos, filtros por ventana y reportar bug", async ({ page, request }) => {
  const galleryDate = "2099-06-01";
  const seedPhoto = await request.post("/api/diet", {
    multipart: {
      log_date: galleryDate,
      sleep_hours: "7.0",
      steps: "10000",
      weight_kg: "70.0",
      waist_cm: "78.0",
      hip_cm: "97.0",
      photo: {
        name: "gallery-photo.png",
        mimeType: "image/png",
        buffer: fs.readFileSync(PHOTO_FIXTURE),
      },
    },
  });
  expect(seedPhoto.ok()).toBeTruthy();

  await page.reload();

  await goView(page, "checkin");
  await page.selectOption("#dietLimitSelect", "90");
  await expect(page.locator("#dietLimitSelect")).toHaveValue("90");
  await expect(page.locator(".footer-view-actions [data-footer-view='checkin']")).toBeVisible();
  await expect(page.locator(".footer-view-actions [data-footer-view='workouts']")).toBeHidden();

  await goView(page, "workouts");
  await page.selectOption("#workLimitSelect", "90");
  await expect(page.locator("#workLimitSelect")).toHaveValue("90");
  await expect(page.locator(".footer-view-actions [data-footer-view='workouts']")).toBeVisible();

  await goView(page, "progress");
  await page.click("#viewAllPhotosBtn");
  await expect(page.locator("#photoLightbox")).toHaveAttribute("open", "");
  await page.click("#lightboxClose");
  await expect(page.locator("#photoLightbox")).not.toHaveAttribute("open", "");

  await goView(page, "data");
  await expect(page.locator(".footer-view-actions [data-footer-view='checkin']")).toBeHidden();
  await expect(page.locator(".footer-view-actions [data-footer-view='workouts']")).toBeHidden();
  await expect(page.locator(".footer-view-actions [data-footer-view='supplements']")).toBeHidden();
  await page.click("#btnReportBug");
  await expect(page.locator("#reportBugModal")).toHaveAttribute("open", "");
  await expect(page.locator("#reportBugText")).toHaveValue(/Gym Tracker - Reporte de bug/);
  await page.click("#reportBugDoneBtn");
  await expect(page.locator("#reportBugModal")).not.toHaveAttribute("open", "");
});
