import { expect, test, type Locator, type Page } from "@playwright/test";

// This suite exercises existing demo data without creating or modifying reports,
// assignments, weather, recommendations, notifications, or administrative records.
// Authentication records ordinary sign-in audit entries on the real backend.
const roles = ["Authority", "Citizen", "Worker", "Admin"] as const;
type Role = (typeof roles)[number];
const viewports = [
  { width: 1440, height: 1000 },
  { width: 1280, height: 900 },
  { width: 768, height: 1024 },
  { width: 390, height: 844 },
];
const routes: Record<Role, string[]> = {
  Authority: ["/", "/incidents", "/risk", "/agents", "/notifications"],
  Citizen: ["/", "/incidents", "/notifications"],
  Worker: ["/", "/incidents", "/notifications"],
  Admin: ["/admin", "/", "/incidents", "/risk", "/agents", "/notifications"],
};
const headings: Record<string, string> = {
  "/risk": "Disaster intelligence",
  "/agents": "Agent activity",
  "/admin": "Administration",
  "/notifications": "Notifications",
};
const evidenceDirectory = "docs/redesign/qa";
const reference = "CS-DEMO-0004";
const photograph = {
  name: "unsaved-redesign-preview.png",
  mimeType: "image/png",
  buffer: Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  ),
};

function observeHealth(page: Page) {
  const pageErrors: string[] = [];
  const apiErrors: string[] = [];
  const localConsoleErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname.startsWith("/api/") && response.status() >= 400)
      apiErrors.push(`${response.request().method()} ${url.pathname}: ${response.status()}`);
  });
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const source = message.location().url;
    // External map tiles/fonts are network dependencies, not local app scripts.
    // Runtime exceptions are independently captured by the pageerror listener.
    if (/https?:\/\/(127\.0\.0\.1|localhost):5173\/(src|api)\//.test(source))
      localConsoleErrors.push(message.text());
  });
  return () => {
    expect(pageErrors, "The rendered app must not throw browser exceptions").toEqual([]);
    expect(apiErrors, "Read-only role views must load authorized real API data").toEqual([]);
    expect(localConsoleErrors, "Local app scripts must not log console errors").toEqual([]);
  };
}

async function signIn(page: Page, role: Role) {
  await page.goto("/");
  await expect(page).toHaveTitle(/CivicShield/);
  const account = page.getByRole("button", { name: role, exact: true });
  await expect(account).toBeVisible();
  await account.click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  // Closed mobile navigation is intentionally inert and absent from the accessibility tree.
  await expect(page.locator('button[aria-label="Sign out"]').first()).toBeAttached();
}

async function assertHealthyLayout(page: Page, width: number) {
  await expect(page.locator("main")).toBeVisible();
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.locator(".loading")).toHaveCount(0);
  await expect.poll(async () => (await page.locator("main").innerText()).trim().length).toBeGreaterThan(50);
  expect(
    await page.evaluate(() => ({
      content: document.documentElement.scrollWidth,
      viewport: document.documentElement.clientWidth,
    })),
  ).toEqual(expect.objectContaining({ viewport: width }));
  const dimensions = await page.evaluate(() => ({
    content: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  if (dimensions.content > dimensions.viewport + 1) {
    console.log("Overflow diagnostics", await page.evaluate(() => Array.from(document.querySelectorAll("body *")).map((element) => {
      const rect = element.getBoundingClientRect(), style = getComputedStyle(element);
      return { element: element.tagName, class: element.className?.toString().slice(0, 70), right: Math.round(rect.right), width: Math.round(rect.width), minWidth: style.minWidth, overflow: style.overflowX, position: style.position };
    }).filter((item) => item.right > innerWidth + 1 && item.width > 1 && item.position !== "fixed").slice(0, 18)));
  }
  expect(dimensions.content, "Horizontal scrolling belongs inside tables, never the whole page").toBeLessThanOrEqual(dimensions.viewport + 1);
  const headingBox = await page.getByRole("heading", { level: 1 }).boundingBox();
  expect(headingBox).not.toBeNull();
  expect(headingBox!.x).toBeGreaterThanOrEqual(-1);
  expect(headingBox!.x + headingBox!.width).toBeLessThanOrEqual(width + 1);
  expect(await page.locator("body").innerText()).toMatch(/synthetic|simulation|demonstration/i);
}

async function assertRoleNavigation(page: Page, role: Role, width: number) {
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  const opener = page.getByRole("button", { name: "Open navigation", exact: true });
  const compact = await opener.isVisible();
  if (width === 390) expect(compact, "A narrow screen needs a usable navigation control").toBe(true);
  if (compact) {
    await expect(navigation).not.toBeInViewport();
    await opener.focus();
    await opener.press("Enter");
    await expect(navigation).toBeInViewport();
  } else {
    await expect(navigation).toBeInViewport();
  }
  await expect(navigation.getByRole("link", { name: "Overview", exact: true })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Administration", exact: true })).toHaveCount(role === "Admin" ? 1 : 0);
  await expect(navigation.getByRole("link", { name: "Disaster intelligence", exact: true })).toHaveCount(role === "Admin" || role === "Authority" ? 1 : 0);
  if (compact) {
    await page.getByRole("button", { name: "Close navigation", exact: true }).first().click();
    await expect(navigation).not.toBeInViewport();
  }
}

for (const role of roles) {
  for (const viewport of viewports) {
    test(`${role.toLowerCase()} workspace is healthy at ${viewport.width}px`, async ({ page }) => {
      test.setTimeout(90_000);
      await page.setViewportSize(viewport);
      const assertHealth = observeHealth(page);
      await signIn(page, role);
      for (const [index, route] of routes[role].entries()) {
        if (route !== "/") await page.goto(route);
        else if (index > 0) await page.goto("/");
        await expect(page).toHaveURL(new RegExp(`${route === "/" ? "/" : route}$`));
        if (headings[route])
          await expect(page.getByRole("heading", { level: 1 })).toHaveText(headings[route]);
        await assertHealthyLayout(page, viewport.width);
        if (index === 0) {
          await assertRoleNavigation(page, role, viewport.width);
          await page.screenshot({
            path: `${evidenceDirectory}/${role.toLowerCase()}-${viewport.width}.png`,
            fullPage: false,
          });
        }
      }
      assertHealth();
    });
  }
}

test("390px citizen reporting keeps photo and numeric location controls usable and closes by keyboard", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const assertHealth = observeHealth(page);
  await signIn(page, "Citizen");
  const newReport = page.getByRole("button", { name: "New report", exact: true });
  await newReport.click();
  const dialog = page.getByRole("dialog", { name: "Report a civic hazard", exact: true });
  await expect(dialog).toBeVisible();
  for (const label of ["Report title", "Location name", "Description", "Latitude", "Longitude", "Hazard photograph"])
    await expect(dialog.getByLabel(label, { exact: true })).toBeVisible();
  await expect(dialog.getByLabel("Camera photograph", { exact: true })).toHaveAttribute("capture", "environment");
  const cameraChooser = page.waitForEvent("filechooser");
  await dialog.getByRole("button", { name: "Take photo", exact: true }).click();
  await (await cameraChooser).setFiles(photograph);
  await expect(dialog.getByAltText("Selected hazard preview")).toBeVisible();
  const latitude = dialog.getByLabel("Latitude", { exact: true });
  await latitude.fill("");
  await expect(latitude).toHaveValue("");
  expect(await latitude.evaluate((input) => (input as HTMLInputElement).validity.valueMissing)).toBe(true);
  await latitude.fill("31.510122");
  await dialog.getByLabel("Longitude", { exact: true }).fill("74.350441");
  await expect(dialog.getByLabel("Latitude", { exact: true })).toHaveValue("31.510122");
  await expect(dialog.getByLabel("Longitude", { exact: true })).toHaveValue("74.350441");
  await dialog.getByLabel("Hazard photograph", { exact: true }).setInputFiles(photograph);
  const preview = dialog.getByAltText("Selected hazard preview");
  await expect(preview).toBeVisible();
  const originalPreview = await preview.getAttribute("src");
  await expect.poll(() => preview.evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  await dialog.getByLabel("Hazard photograph", { exact: true }).setInputFiles({
    name: "oversized-rejected-photo.png",
    mimeType: "image/png",
    buffer: Buffer.alloc(8 * 1024 * 1024 + 1),
  });
  await expect(page.getByText("Images must be smaller than 8 MB.", { exact: true })).toBeVisible();
  await expect(preview).toBeVisible();
  await expect(preview).toHaveAttribute("src", originalPreview!);
  await expect.poll(() => preview.evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  await dialog.getByRole("button", { name: "Remove selected photograph", exact: true }).click();
  await expect(dialog.getByAltText("Selected hazard preview")).toHaveCount(0);
  await dialog.getByLabel("Hazard photograph", { exact: true }).setInputFiles({ ...photograph, name: "replacement-unsaved-preview.png" });
  await expect(dialog.getByAltText("Selected hazard preview")).toBeVisible();
  const width = await dialog.evaluate((node) => ({ content: node.scrollWidth, visible: node.clientWidth }));
  expect(width.content).toBeLessThanOrEqual(width.visible + 1);
  const box = await dialog.boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  await page.screenshot({ path: `${evidenceDirectory}/citizen-report-390.png`, fullPage: false });
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(newReport).toBeFocused();
  assertHealth();
});

test("operational map layers reflect real incidents and risk estimates and can be toggled independently", async ({ page, request }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const assertHealth = observeHealth(page);
  await signIn(page, "Authority");
  await assertHealthyLayout(page, 1440);
  const token = await page.evaluate(() => localStorage.getItem("civicshield.session.v1"));
  const headers = { Authorization: `Bearer ${token}` };
  const incidentResponse = await request.get("/api/incidents", { headers });
  const riskResponse = await request.get("/api/risk", { headers });
  expect(incidentResponse.ok()).toBeTruthy();
  expect(riskResponse.ok()).toBeTruthy();
  const incidents = await incidentResponse.json();
  const risks = await riskResponse.json();
  const markers = page.getByRole("button", { name: /^Select incident / });
  const zones = page.locator(".leaflet-overlay-pane path.civic-risk-zone");
  const incidentLayer = page.getByRole("checkbox", { name: "Incident layer", exact: true });
  const riskLayer = page.getByRole("checkbox", { name: "Flood-risk layer", exact: true });
  await expect(incidentLayer).toBeChecked();
  await expect(riskLayer).toBeChecked();
  await expect(markers).toHaveCount(incidents.filter((incident: any) => incident.latitude && incident.longitude).length);
  await expect(zones).toHaveCount(risks.length);
  await incidentLayer.uncheck();
  await expect(markers).toHaveCount(0);
  await expect(zones).toHaveCount(risks.length);
  await riskLayer.uncheck();
  await expect(zones).toHaveCount(0);
  await incidentLayer.check();
  await expect(markers).toHaveCount(incidents.filter((incident: any) => incident.latitude && incident.longitude).length);
  await expect(zones).toHaveCount(0);
  await riskLayer.focus();
  await riskLayer.press("Space");
  await expect(riskLayer).toBeChecked();
  await expect(zones).toHaveCount(risks.length);
  await page.screenshot({ path: `${evidenceDirectory}/map-layers-1440.png`, fullPage: false });
  assertHealth();
});

test("keyboard incident selection connects its marker to context and the existing detail workflow", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const assertHealth = observeHealth(page);
  await signIn(page, "Authority");
  const marker = page.getByRole("button", { name: `Select incident ${reference}`, exact: true });
  await expect(marker).toBeVisible();
  await marker.focus();
  await expect(marker).toBeFocused();
  await marker.press("Enter");
  const context = page.getByRole("region", { name: "Selected incident", exact: true });
  await expect(context).toBeVisible();
  await expect(context.getByText(reference, { exact: true })).toBeVisible();
  await expect(marker).toHaveAttribute("aria-pressed", "true");
  const openDetails = context.getByRole("button", { name: "Open incident details", exact: true });
  await expect(openDetails).toBeEnabled();
  await page.screenshot({ path: `${evidenceDirectory}/map-selected-incident-1440.png`, fullPage: false });
  await openDetails.focus();
  await openDetails.press("Enter");
  const dialog = page.getByRole("dialog").first();
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: reference, exact: true })).toBeVisible();
  for (const tab of ["Overview", "Response", "Evidence", "Activity"])
    await expect(dialog.getByRole("tab", { name: new RegExp(`^${tab}`) })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(openDetails).toBeFocused();
  assertHealth();
});

async function markerPosition(marker: Locator, map: Locator) {
  const [point, frame] = await Promise.all([marker.boundingBox(), map.boundingBox()]);
  if (!point || !frame) throw new Error("The map and incident marker must be rendered.");
  return { x: point.x + point.width / 2 - frame.x, y: point.y + point.height / 2 - frame.y };
}
function displacement(a: { x: number; y: number }, b: { x: number; y: number }) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

test("Focus Lahore restores the operational view after an actual map zoom", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const assertHealth = observeHealth(page);
  await signIn(page, "Authority");
  const map = page.locator(".leaflet-container").first();
  const marker = page.getByRole("button", { name: `Select incident ${reference}`, exact: true });
  const focus = page.getByRole("button", { name: "Focus Lahore", exact: true });
  await expect(marker).toBeVisible();
  await expect(page.getByRole("button", { name: /^Inspect risk zone / }).first()).toBeVisible();
  await focus.click();
  await expect(map.locator(".leaflet-pan-anim")).toHaveCount(0);
  const initial = await markerPosition(marker, map);
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  await expect.poll(async () => displacement(initial, await markerPosition(marker, map))).toBeGreaterThan(3);
  await focus.click();
  await expect.poll(async () => displacement(initial, await markerPosition(marker, map))).toBeLessThan(2);
  await expect(focus).toBeFocused();
  await page.screenshot({ path: `${evidenceDirectory}/map-focus-lahore-1440.png`, fullPage: false });
  assertHealth();
});

test("keyboard risk-zone inspection opens calculated factors and preserved history", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const assertHealth = observeHealth(page);
  await signIn(page, "Authority");
  await page.goto("/risk");
  await assertHealthyLayout(page, 1440);
  const zone = page.getByRole("button", { name: /^Inspect risk zone / }).first();
  await expect(zone).toBeVisible();
  const zoneName = (await zone.getAttribute("aria-label"))!.replace(/^Inspect risk zone /, "");
  await zone.focus();
  await expect(zone).toBeFocused();
  await zone.press("Enter");
  const dialog = page.getByRole("dialog", { name: zoneName, exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Contributing factors", exact: true })).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Input provenance & limitations", exact: true })).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Assessment history", exact: true })).toBeVisible();
  await expect(dialog.locator(".history-list")).toBeVisible();
  expect(await dialog.locator(".history-list > div").count()).toBeGreaterThan(0);
  const factorText = await dialog.getByRole("heading", { name: "Contributing factors", exact: true }).locator("..").innerText();
  expect(factorText.trim().length).toBeGreaterThan("Contributing factors".length);
  await page.screenshot({ path: `${evidenceDirectory}/risk-zone-keyboard-1440.png`, fullPage: false });
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(zone).toBeFocused();
  assertHealth();
});
