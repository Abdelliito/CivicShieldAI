import { afterEach, describe, expect, it, vi } from "vitest";
import { api, date, relative, session, upload } from "./api";
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
describe("API boundary", () => {
  it("attaches the current bearer token and serializes real server responses", async () => {
    session.set("session-token");
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 12 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    expect(await api("/incidents/12")).toEqual({ id: 12 });
    const headers = fetcher.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer session-token");
    expect(fetcher.mock.calls[0][0]).toBe("/api/incidents/12");
  });
  it("surfaces backend validation text to the form", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: "Only the reporting citizen can edit this report.",
          }),
          { status: 403 },
        ),
      ),
    );
    await expect(api("/reports/2", { method: "PATCH" })).rejects.toThrow(
      "Only the reporting citizen can edit this report.",
    );
  });
  it("clears an expired session and notifies the auth provider", async () => {
    session.set("expired-token");
    const listener = vi.fn();
    window.addEventListener("civicshield:unauthorized", listener);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Expired token" }), {
          status: 401,
        }),
      ),
    );
    await expect(api("/auth/me")).rejects.toThrow("Expired token");
    expect(session.get()).toBeNull();
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener("civicshield:unauthorized", listener);
  });
  it("does not log out an existing session for an invalid login attempt", async () => {
    session.set("existing-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Invalid credentials" }), {
          status: 401,
        }),
      ),
    );
    await expect(api("/auth/login", { method: "POST" })).rejects.toThrow(
      "Invalid credentials",
    );
    expect(session.get()).toBe("existing-token");
  });
  it("does not let a stale unauthorized response clear a replacement session", async () => {
    session.set("old-session-token");
    let resolveResponse!: (response: Response) => void;
    const pendingResponse = new Promise<Response>((resolve) => {
      resolveResponse = resolve;
    });
    const fetcher = vi.fn().mockReturnValue(pendingResponse);
    const listener = vi.fn();
    window.addEventListener("civicshield:unauthorized", listener);
    vi.stubGlobal("fetch", fetcher);
    const request = api("/incidents");
    session.set("replacement-session-token");
    resolveResponse(
      new Response(JSON.stringify({ detail: "Old session expired" }), {
        status: 401,
      }),
    );
    await expect(request).rejects.toThrow("Old session expired");
    expect(session.get()).toBe("replacement-session-token");
    expect(listener).not.toHaveBeenCalled();
    const headers = fetcher.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer old-session-token");
    window.removeEventListener("civicshield:unauthorized", listener);
  });
  it("forwards cancellation and ignores an aborted request's late unauthorized response", async () => {
    session.set("current-session-token");
    const controller = new AbortController();
    let resolveResponse!: (response: Response) => void;
    const fetcher = vi.fn().mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveResponse = resolve;
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    const request = api("/incidents", { signal: controller.signal });
    controller.abort();
    resolveResponse(
      new Response(JSON.stringify({ detail: "Cancelled request" }), {
        status: 401,
      }),
    );
    await expect(request).rejects.toThrow("Cancelled request");
    expect(fetcher.mock.calls[0][1].signal).toBe(controller.signal);
    expect(session.get()).toBe("current-session-token");
  });
  it("rejects oversize evidence before making a network request", async () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    const file = new File([new Uint8Array(8 * 1024 * 1024 + 1)], "hazard.png", {
      type: "image/png",
    });
    await expect(upload(file)).rejects.toThrow("8 MB");
    expect(fetcher).not.toHaveBeenCalled();
  });
});
describe("persisted timestamps", () => {
  it("handles both explicit UTC offsets and naive backend UTC dates", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-16T17:00:00Z"));
    expect(relative("2026-10-16T16:30:00+00:00")).toBe("30m ago");
    expect(relative("2026-10-16T16:30:00")).toBe("30m ago");
    expect(relative("2026-10-16T16:30:00Z")).toBe("30m ago");
    expect(date("2026-10-16T16:30:00+00:00")).not.toContain("Invalid");
  });
});
