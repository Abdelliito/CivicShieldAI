import { test, expect, Page, APIRequestContext } from "@playwright/test";
const password = "CivicDemo!2026";
const photo = {
  name: "synthetic-test-evidence.png",
  mimeType: "image/png",
  buffer: Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  ),
};

async function login(page: Page, role: string) {
  await page.goto("/");
  await expect(
    page
      .getByRole("button", { name: /sign out/i })
      .or(page.getByRole("button", { name: "Sign in", exact: true })),
  ).toBeVisible();
  if (await page.getByRole("button", { name: /sign out/i }).count())
    await page.getByRole("button", { name: /sign out/i }).click();
  await page.getByRole("button", { name: role, exact: true }).click();
  await expect(page.getByRole("button", { name: /sign out/i })).toBeVisible();
}
async function auth(request: APIRequestContext, role = "authority") {
  const res = await request.post("/api/auth/login", {
    data: { email: `${role}@civicshield.demo`, password },
  });
  expect(res.ok()).toBeTruthy();
  const data = await res.json();
  return { Authorization: `Bearer ${data.access_token}` };
}
async function searchOpen(page: Page, title: string) {
  await page.goto("/incidents");
  await page.getByLabel("Search incidents").fill(title);
  const row = page.getByRole("row").filter({ hasText: title }).first();
  await expect(row).toBeVisible();
  await row.getByRole("button").first().click();
  await expect(page.getByRole("dialog").first()).toBeVisible();
}
test("citizen → authority → worker evidence → authority verification → citizen notification", async ({
  page,
  request,
}) => {
  // This real database journey crosses four roles and several upload/review cycles.
  test.setTimeout(180_000);
  const title = `E2E blocked drainage ${Date.now()}`;
  page.on("dialog", (dialog) => dialog.accept());
  await login(page, "Citizen");
  await page.getByRole("button", { name: "New report", exact: true }).click();
  await page.getByLabel("Report title (optional)", { exact: true }).fill(title);
  await page
    .getByLabel("Location name (optional)", { exact: true })
    .fill("MM Alam Road, Gulberg");
  await page
    .getByLabel("Description (optional)", { exact: true })
    .fill(
      "Blocked drain full of garbage is causing water accumulation at a busy pedestrian crossing. Synthetic automated test.",
    );
  await page.getByLabel("Hazard photograph").setInputFiles(photo);
  await expect(page.getByAltText("Selected hazard preview")).toBeVisible();
  await page
    .getByRole("button", { name: "Remove selected photograph" })
    .click();
  await expect(page.getByAltText("Selected hazard preview")).toHaveCount(0);
  await page.getByLabel("Hazard photograph").setInputFiles(photo);
  await page.getByText("Enter coordinates manually", { exact: true }).click();
  await page.getByLabel("Latitude", { exact: true }).fill("31.5114");
  await page.getByLabel("Longitude", { exact: true }).fill("74.3506");
  const createResponse = page.waitForResponse(
    (r) => r.url().endsWith("/api/reports") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Submit report", exact: true })
    .click();
  const created = await (await createResponse).json();
  expect(created.reference).toBeTruthy();
  await expect(
    page.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit report", exact: true }).click();
  await page
    .getByLabel("Description (optional)", { exact: true })
    .fill(
      "Blocked drain full of garbage is causing water accumulation at a busy pedestrian crossing. Edited and persisted synthetic automated test.",
    );
  const savedReport = page.waitForResponse((r) => r.url().endsWith(`/api/reports/${created.id}`) && r.request().method() === "PATCH");
  await page.getByRole("button", { name: "Save report", exact: true }).click();
  expect((await savedReport).ok()).toBe(true);
  await expect(page.getByRole("dialog", { name: "Edit your report", exact: true })).toHaveCount(0);
  await expect(
    page.getByText(/Edited and persisted synthetic automated test/).first(),
  ).toBeVisible();
  await page.reload();
  await searchOpen(page, title);
  await expect(
    page.getByText(/Edited and persisted synthetic automated test/).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog", exact: true }).click();
  await login(page, "Authority");
  await searchOpen(page, title);
  await page.getByRole("tab", { name: "Response", exact: true }).click();
  const teams = await (
    await request.get("/api/teams", { headers: await auth(request) })
  ).json();
  const workerTeam = teams.find((t: any) => t.name.includes("Drainage"));
  await page
    .getByLabel("Assign / reassign team", { exact: true })
    .selectOption(String(workerTeam.id));
  await page
    .getByLabel("Assignment instructions")
    .fill("Inspect the blockage and clear drainage. Synthetic work order.");
  await page.getByRole("button", { name: "Assign team", exact: true }).click();
  await expect(
    page.getByText("Response team assigned", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Incident note")
    .fill("Authority reviewed report and requested photographic evidence.");
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  await expect(
    page.getByText(
      "Authority reviewed report and requested photographic evidence.",
      { exact: true },
    ),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Request additional evidence", exact: true })
    .click();
  await page.getByRole("button", { name: "Close dialog", exact: true }).click();
  await login(page, "Citizen");
  await searchOpen(page, title);
  await page.getByRole("tab", { name: /Evidence/ }).click();
  await page
    .getByLabel("Additional photograph", { exact: true })
    .setInputFiles(photo);
  await page
    .getByRole("button", { name: "Upload evidence", exact: true })
    .click();
  await expect(page.locator(".evidence img")).toHaveCount(2);
  await page.getByRole("tab", { name: "Response", exact: true }).click();
  await page
    .getByLabel("Incident note")
    .fill("Additional photograph supplied in response to authority request.");
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  await expect(
    page.getByText(
      "Additional photograph supplied in response to authority request.",
      { exact: true },
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog", exact: true }).click();
  await login(page, "Worker");
  await searchOpen(page, title);
  await page.getByRole("tab", { name: "Response", exact: true }).click();
  await page
    .getByRole("button", { name: "Accept assignment", exact: true })
    .click();
  await page.getByRole("button", { name: "Start work", exact: true }).click();
  await page
    .getByLabel("Completion evidence", { exact: true })
    .setInputFiles(photo);
  await page
    .getByLabel("Completion notes (optional)", { exact: true })
    .fill(
      "Synthetic test: obstruction removed, drainage flow checked, photograph attached.",
    );
  await page
    .getByRole("button", { name: "Submit completion", exact: true })
    .click();
  await expect(
    page.getByText("Completion submitted for authority verification", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog", exact: true }).click();
  await login(page, "Authority");
  await searchOpen(page, title);
  await page.getByRole("tab", { name: /Evidence/ }).click();
  await expect(
    page.getByText("Completion evidence", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".evidence img")).toHaveCount(3);
  await page.getByRole("tab", { name: "Response", exact: true }).click();
  await page.getByLabel("New status", { exact: true }).selectOption("Closed");
  await page
    .getByLabel("Status update reason")
    .fill("Evidence reviewed and completion verified in synthetic test.");
  await page
    .getByRole("button", { name: "Update status", exact: true })
    .click();
  await expect(
    page
      .locator(".incident-detail .badge")
      .filter({ hasText: /^Closed/ })
      .first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog", exact: true }).click();
  await login(page, "Citizen");
  await searchOpen(page, title);
  await expect(
    page
      .locator(".incident-detail .badge")
      .filter({ hasText: /^Closed/ })
      .first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog", exact: true }).click();
  await page.goto("/notifications");
  await expect(page.getByText(/closed/i).first()).toBeVisible();
});

test("citizen withdrawal is reversible and report photos/location survive reload", async ({
  page,
}) => {
  page.on("dialog", (dialog) => dialog.accept());
  await login(page, "Citizen");
  const title = `E2E open manhole ${Date.now()}`;
  await page.getByRole("button", { name: "New report", exact: true }).click();
  await page.getByLabel("Report title (optional)", { exact: true }).fill(title);
  await page
    .getByLabel("Location name (optional)", { exact: true })
    .fill("Jail Road school entrance");
  await page
    .getByLabel("Description (optional)", { exact: true })
    .fill(
      "Open manhole beside a school. Children and pedestrians are exposed to a deep hole. Synthetic test.",
    );
  await page.context().grantPermissions(["geolocation"]);
  await page.context().setGeolocation({ latitude: 31.535, longitude: 74.331 });
  await page.getByRole("button", { name: "Use GPS", exact: true }).click();
  await page.getByText("Enter coordinates manually", { exact: true }).click();
  await expect(page.getByLabel("Latitude", { exact: true })).toHaveValue(
    "31.535",
  );
  await page
    .locator(".dialog-content .leaflet-container")
    .click({ position: { x: 150, y: 100 } });
  await page.getByLabel("Hazard photograph").setInputFiles(photo);
  await page
    .getByRole("button", { name: "Submit report", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Withdraw report", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Restore report", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Restore report", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Withdraw report", exact: true }),
  ).toBeVisible();
  await page.reload();
  await searchOpen(page, title);
  await page.getByRole("tab", { name: /Evidence/ }).click();
  await expect(page.locator(".evidence img")).toHaveCount(1);
  await page.getByRole("button", { name: "Edit report", exact: true }).click();
  await page
    .getByRole("button", {
      name: "Remove synthetic-test-evidence.png",
      exact: true,
    })
    .click();
  await expect(
    page.locator(".dialog-content").last().locator(".evidence"),
  ).toHaveCount(0);
  await page.getByLabel("Hazard photograph").setInputFiles(photo);
  await page.getByRole("button", { name: "Save report", exact: true }).click();
  await expect(page.locator(".evidence img")).toHaveCount(1);
});

test("incident category, severity, location and date filters use persisted data", async ({
  page,
  request,
}) => {
  const citizen = await auth(request, "citizen");
  const title = `E2E filter open manhole ${Date.now()}`;
  await request.post("/api/reports", {
    headers: citizen,
    data: {
      title,
      description:
        "An open manhole beside the school entrance exposes children to a deep uncovered hole. Synthetic filter test.",
      latitude: 31.5114,
      longitude: 74.3506,
      location_name: "Synthetic Gulberg school",
    },
  });
  await login(page, "Authority");
  await page.goto("/incidents");
  await page.getByLabel("Search incidents").fill(title);
  await expect(page.getByRole("row").filter({ hasText: title })).toBeVisible();
  await page.getByLabel("Status filter").selectOption("Pending Review");
  await page.getByLabel("Category filter").selectOption("Open manholes");
  await page.getByLabel("Severity filter").selectOption("High");
  await page.getByLabel("Zone filter").selectOption({ label: "Gulberg" });
  await page.getByLabel("Reported from date").fill("2000-01-01");
  await page.getByLabel("Reported to date").fill("2099-12-31");
  await expect(page.getByRole("row").filter({ hasText: title })).toBeVisible();
  await page.getByLabel("Severity filter").selectOption("Low");
  await expect(
    page.getByText("No incidents match your filters", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Clear filters", exact: true })
    .click();
  await expect(page.getByRole("row").filter({ hasText: title })).toBeVisible();
});

test("registration, login errors, expired sessions and notification read state", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Email address", { exact: true })
    .fill("citizen@civicshield.demo");
  await page.getByLabel("Password", { exact: true }).fill("incorrect-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page
    .getByRole("button", { name: "Create an account", exact: true })
    .click();
  await page
    .getByLabel("Full name", { exact: true })
    .fill("Synthetic Browser Citizen");
  await page
    .getByLabel("Email address", { exact: true })
    .fill(`browser.${Date.now()}@civicshield.demo`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("SyntheticBrowser!2026");
  await page
    .getByRole("button", { name: "Create citizen account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your neighbourhood, made safer", exact: true }),
  ).toBeVisible();
  await page.goto("/admin");
  await expect(page).toHaveURL("http://127.0.0.1:5173/");
  await page.evaluate(() =>
    localStorage.setItem("civicshield.session.v1", "expired.invalid.token"),
  );
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Welcome back", exact: true }),
  ).toBeVisible();
  await login(page, "Citizen");
  await page.goto("/notifications");
  await page
    .getByRole("button", { name: "Mark read", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Mark unread", exact: true }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Mark unread", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Mark read", exact: true }).first(),
  ).toBeVisible();
});

for (const resource of ["department", "team", "zone", "user"])
  test(`admin ${resource} CRUD persists and availability can be restored`, async ({
    page,
  }) => {
    page.on("dialog", (dialog) => dialog.accept());
    await login(page, "Admin");
    await page.goto("/admin");
    const tab = (
      {
        department: "Departments",
        team: "Teams",
        zone: "Zones",
        user: "Users",
      } as any
    )[resource];
    await page.getByRole("button", { name: tab, exact: true }).click();
    const name = `E2E ${resource} ${Date.now()}`;
    await page
      .getByRole("button", { name: `New ${resource}`, exact: true })
      .click();
    await page.getByLabel("Name", { exact: true }).fill(name);
    if (resource === "department")
      await page
        .getByLabel("Description", { exact: true })
        .fill("Synthetic administrative test record.");
    if (resource === "team")
      await page
        .getByLabel("Department", { exact: true })
        .selectOption({ label: "Water & Sanitation" });
    if (resource === "zone") {
      await page.getByLabel("Latitude", { exact: true }).fill("31.5");
      await page.getByLabel("Longitude", { exact: true }).fill("74.3");
    }
    if (resource === "user") {
      await page
        .getByLabel("Email address", { exact: true })
        .fill(`test.${Date.now()}@civicshield.demo`);
      await page
        .getByLabel("Password", { exact: true })
        .fill("SyntheticTest!2026");
    }
    await page
      .getByRole("button", { name: `Save ${resource}`, exact: true })
      .click();
    const row = page.getByRole("row").filter({ hasText: name });
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Edit", exact: true }).click();
    await page.getByLabel("Name", { exact: true }).fill(name + " edited");
    await page
      .getByRole("button", { name: `Save ${resource}`, exact: true })
      .click();
    await page.reload();
    await page.getByRole("button", { name: tab, exact: true }).click();
    const edited = page.getByRole("row").filter({ hasText: name + " edited" });
    await expect(edited).toBeVisible();
    await edited
      .getByRole("button", { name: "Deactivate", exact: true })
      .click();
    await expect(edited.getByText("Inactive", { exact: true })).toBeVisible();
    await edited
      .getByRole("button", { name: "Reactivate", exact: true })
      .click();
    await expect(edited.getByText("Active", { exact: true })).toBeVisible();
    await edited
      .getByRole("button", { name: "Deactivate", exact: true })
      .click();
  });

test("weather independently changes persisted risk, missing input is explicit, and agent reviews work", async ({
  page,
  request,
}) => {
  await login(page, "Authority");
  await page.goto("/risk");
  await page.getByLabel("Weather scenario").selectOption("clear");
  await page
    .getByRole("button", { name: "Refresh weather & risk", exact: true })
    .click();
  await expect(
    page.getByText("Risk assessments recalculated", { exact: true }),
  ).toBeVisible();
  const headers = await auth(request);
  const clear = await (await request.get("/api/risk", { headers })).json();
  await page.getByLabel("Weather scenario").selectOption("heavy_rain");
  await page
    .getByRole("button", { name: "Refresh weather & risk", exact: true })
    .click();
  await expect
    .poll(async () => {
      const heavy = await (await request.get("/api/risk", { headers })).json();
      return heavy[0].score > clear[0].score;
    })
    .toBeTruthy();
  await page
    .getByRole("button", { name: "Inspect Gulberg", exact: true })
    .click();
  await expect(
    page.getByText("Input provenance & limitations", { exact: true }),
  ).toBeVisible();
  await expect(
    page
      .locator(".dialog-content")
      .getByText(/SYNTHETIC DEMONSTRATION/)
      .first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog", exact: true }).click();
  await page.getByLabel("Weather scenario").selectOption("missing");
  await page
    .getByRole("button", { name: "Refresh weather & risk", exact: true })
    .click();
  await expect(
    page.getByText("Insufficient Data", { exact: true }).first(),
  ).toBeVisible();
  await page.goto("/agents");
  for (const decision of ["Approve", "Reject", "Override decision"]) {
    await page
      .getByRole("button", { name: decision, exact: true })
      .first()
      .click();
    await page
      .getByLabel("Decision reason")
      .fill(`Synthetic test: ${decision} after human review.`);
    await page
      .getByRole("button", { name: "Confirm decision", exact: true })
      .click();
    await expect(
      page.getByText("Recommendation reviewed", { exact: true }).first(),
    ).toBeVisible();
  }
  await page.getByRole("tab", { name: /Execution log/ }).click();
  await expect(
    page.getByText("Civic Intelligence Agent", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("Disaster Risk Agent", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("Response Coordinator Agent", { exact: true }).first(),
  ).toBeVisible();
});

test("duplicate review, classification, notes, reassignment and archive controls persist", async ({
  page,
  request,
}) => {
  page.on("dialog", (dialog) => dialog.accept());
  const citizen = await auth(request, "citizen"),
    authority = await auth(request);
  const name = `E2E duplicate drain ${Date.now()}`;
  const base = {
    title: name,
    description:
      "Blocked drainage inlet with accumulated rubbish and standing water at the market entrance. Synthetic duplicate test.",
    latitude: 31.512,
    longitude: 74.351,
    location_name: "Synthetic market entrance, Gulberg",
  };
  const first = await (
    await request.post("/api/reports", { headers: citizen, data: base })
  ).json();
  const second = await (
    await request.post("/api/reports", {
      headers: citizen,
      data: { ...base, title: name + " second" },
    })
  ).json();
  await login(page, "Authority");
  await searchOpen(page, name + " second");
  await page.getByLabel("Related incident").selectOption(String(first.id));
  await page
    .getByRole("button", { name: "Confirm merge", exact: true })
    .click();
  await expect(page.getByText(/Consolidated with/)).toBeVisible();
  await page.getByRole("button", { name: "Separate", exact: true }).click();
  await expect(page.getByText(/Consolidated with/)).toHaveCount(0);
  await page.getByRole("button", { name: "Reject match", exact: true }).click();
  await page
    .getByRole("button", { name: "Review classification", exact: true })
    .click();
  await page.getByLabel("Severity", { exact: true }).selectOption("High");
  await page
    .getByLabel("Justification")
    .fill("Crowded market pedestrian exposure requires high priority review.");
  await page
    .getByRole("button", { name: "Save classification", exact: true })
    .click();
  await page.getByRole("tab", { name: "Response", exact: true }).click();
  await page.getByLabel("Incident note").fill("Synthetic first note");
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  const note = page
    .locator(".note")
    .filter({ hasText: "Synthetic first note" });
  await note.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Incident note").fill("Synthetic edited note");
  await page.getByRole("button", { name: "Save note", exact: true }).click();
  await page
    .locator(".note")
    .filter({ hasText: "Synthetic edited note" })
    .getByRole("button", { name: "Delete", exact: true })
    .click();
  await expect(
    page.getByText("Synthetic edited note", { exact: true }),
  ).toHaveCount(0);
  const teams = await (
    await request.get("/api/teams", { headers: authority })
  ).json();
  for (const team of teams.filter((t: any) => t.active).slice(0, 2)) {
    await page
      .getByLabel("Assign / reassign team", { exact: true })
      .selectOption(String(team.id));
    await page
      .getByRole("button", { name: "Assign team", exact: true })
      .click();
    await expect(
      page.getByLabel("Assign / reassign team", { exact: true }),
    ).toHaveValue("");
  }
  await page
    .getByRole("button", { name: "Cancel assignment", exact: true })
    .last()
    .click();
  await page.getByLabel("New status", { exact: true }).selectOption("Rejected");
  await page
    .getByLabel("Status update reason")
    .fill("Synthetic duplicate test concluded; archive the preserved record.");
  await page
    .getByRole("button", { name: "Update status", exact: true })
    .click();
  await expect(
    page
      .locator(".incident-detail .badge")
      .filter({ hasText: /^Not accepted$/ })
      .first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Archive incident", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Restore incident", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Restore incident", exact: true })
    .click();
  const detail = await (
    await request.get(`/api/incidents/${second.id}`, { headers: authority })
  ).json();
  expect(detail.archived).toBe(false);
  expect(detail.severity).toBe("High");
  expect(detail.duplicate_of).toBeNull();
  await page.reload();
  await searchOpen(page, name + " second");
  await expect(
    page
      .locator(".incident-detail .badge")
      .filter({ hasText: /^High$/ })
      .first(),
  ).toBeVisible();
});

test("desktop/mobile render and API failures produce visible feedback", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await login(page, "Authority");
  await page.setViewportSize({ width: 1536, height: 1024 });
  await expect(
    page.getByRole("heading", { name: "Reports & response", exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: ".runtime/desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({ path: ".runtime/mobile.png", fullPage: true });
  await page.route("**/api/incidents**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: '{"detail":"Synthetic network failure for verification"}',
    }),
  );
  await page.goto("/incidents");
  await expect(
    page.getByText("Synthetic network failure for verification", {
      exact: true,
    }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
