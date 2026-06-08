import { test, expect } from "@playwright/test";

/**
 * @spec.given the app is deployed
 * @spec.when  the home page is requested
 * @spec.then  it renders without errors
 * @spec.us    US-001-sample-story
 */
test("home_page_renders", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/sample/);
});
