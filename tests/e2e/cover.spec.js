const { test, expect } = require("@playwright/test");

test.describe("cover page", () => {
  test("renders key messages and highlight blocks", async ({ page }) => {
    await page.goto("/portada");

    await expect(page.locator("h1")).toContainText("My health, my database");
    await expect(page.locator(".hero-kicker")).toContainText("Absolute Data Sovereignty");
    await expect(page.locator(".command-title")).toContainText("Data Sovereignty Command Center");
    await expect(page.locator(".command-grid")).toContainText("LOCAL_HOST");
    await expect(page.locator(".viz-card h3")).toContainText("Vibrant Teal Gradients");
  });

  test("primary buttons navigate correctly", async ({ page }) => {
    await page.goto("/portada");
    await page.click("#coverEnterBtn");
    await expect(page).toHaveURL(/\/(#home)?$/);
    await expect(page.locator("h1")).toContainText("Gym Tracker");

    await page.goto("/portada");
    await page.click("#coverLoginBtn");
    // If local auth is disabled, /login redirects to "/" and still works.
    await expect(page).toHaveURL(/\/(#home)?$/);
  });

  test("mobile layout has no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/portada");

    await expect(page.locator(".cover-layout")).toBeVisible();
    await expect(page.locator(".cover-actions")).toBeVisible();

    const overflow = await page.evaluate(() => {
      const d = document.documentElement;
      return d.scrollWidth - d.clientWidth;
    });
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
