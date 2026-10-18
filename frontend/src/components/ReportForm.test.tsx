import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api, upload } from "../lib/api";
import { ReportForm } from "./ReportForm";

vi.mock("./Map", () => ({ CivicMap: ({ picker }: any) => <button type="button" onClick={() => picker.onPick(31.52, 74.35)}>Select problem on map</button> }));
vi.mock("../lib/api", async (importOriginal) => ({ ...await importOriginal<typeof import("../lib/api")>(), api: vi.fn(), upload: vi.fn() }));
const mockApi = vi.mocked(api), mockUpload = vi.mocked(upload);
function show() {
  const saved = vi.fn(), closed = vi.fn();
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}><ReportForm open onClose={closed} onSaved={saved} /></QueryClientProvider>);
  return { saved, closed };
}
const photo = () => new File(["valid test photograph supplied by mock upload"], "drain.jpg", { type: "image/jpeg" });
beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(navigator, "geolocation", { configurable: true, value: { getCurrentPosition: vi.fn((_success, error) => error({ code: 1 })) } });
  URL.createObjectURL = vi.fn(() => "blob:preview"); URL.revokeObjectURL = vi.fn();
  mockUpload.mockResolvedValue({ id: 42, url: "/api/uploads/42/file", filename: "drain.jpg" });
});
describe("photo-first reporting safeguards", () => {
  it("does not submit the Lahore map default when location permission is denied", async () => {
    show();
    await userEvent.type(screen.getByRole("textbox", { name: "Description (optional)" }), "Drain blocked by leaves");
    await userEvent.click(screen.getByRole("button", { name: "Submit report" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Choose the problem’s location");
    expect(mockApi).not.toHaveBeenCalled();
  });
  it("keeps description optional and reuses the analyzed photo when sending a corrected category", async () => {
    mockApi.mockImplementation(async (path) => path === "/uploads/42/analyze" ? { attachment_id: 42, detection_succeeded: true, analysis: { image_analyzed: true, status: "success", category: "Blocked drainage", detected_title: "Blocked drain", summary: "Leaves obstruct a drain.", can_submit: true } } : { id: 73 });
    const { saved } = show();
    await userEvent.upload(screen.getByLabelText("Hazard photograph"), photo());
    expect(await screen.findByText("Photo checked — review the suggestion below")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Description (optional)" })).not.toBeRequired();
    expect(screen.getByRole("textbox", { name: "Report title (optional)" })).toHaveValue("Blocked drain");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Issue category" }), "Sewer overflow");
    await userEvent.click(screen.getByRole("button", { name: "Select problem on map" }));
    await userEvent.click(screen.getByRole("button", { name: "Submit report" }));
    await waitFor(() => expect(saved).toHaveBeenCalledWith(73));
    expect(mockUpload).toHaveBeenCalledTimes(1);
    const submission = mockApi.mock.calls.find(([path]) => path === "/reports");
    expect(JSON.parse(String(submission?.[1]?.body))).toMatchObject({ description: "", category: "Sewer overflow", attachment_ids: [42], latitude: 31.52, longitude: 74.35 });
  });
  it("never calls unavailable image analysis a successful detection, but allows human review", async () => {
    mockApi.mockImplementation(async (path) => path === "/uploads/42/analyze" ? { attachment_id: 42, detection_succeeded: false, analysis: { image_analyzed: false, status: "unconfigured", category: "Potholes", summary: "Image service is not configured.", can_submit: true } } : { id: 74 });
    show();
    await userEvent.upload(screen.getByLabelText("Hazard photograph"), photo());
    expect(await screen.findByText("Photo detection is unavailable")).toBeVisible();
    expect(screen.queryByText("Photo checked — review the suggestion below")).not.toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Issue category" })).toHaveValue("");
    await userEvent.click(screen.getByRole("button", { name: "Select problem on map" }));
    await userEvent.click(screen.getByRole("button", { name: "Submit report" }));
    await waitFor(() => expect(mockApi.mock.calls.some(([path]) => path === "/reports")).toBe(true));
  });
  it("blocks sending while a provider is still checking the uploaded image", async () => {
    let finish!: (value: any) => void;
    mockApi.mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    show();
    await userEvent.upload(screen.getByLabelText("Hazard photograph"), photo());
    expect(await screen.findByText("Checking the photograph…")).toBeVisible();
    expect(screen.getByRole("button", { name: "Submit report" })).toBeDisabled();
    finish({ attachment_id: 42, detection_succeeded: false, analysis: { image_analyzed: false, status: "failed", can_submit: true } });
    expect(await screen.findByText("Photo detection is unavailable")).toBeVisible();
    expect(screen.getByRole("button", { name: "Submit report" })).toBeEnabled();
  });
  it("does not accept a fabricated success flag without confirmed image analysis", async () => {
    mockApi.mockResolvedValue({ attachment_id: 42, detection_succeeded: true, analysis: { status: "success", image_analyzed: false, category: "Potholes" } });
    show();
    await userEvent.upload(screen.getByLabelText("Hazard photograph"), photo());
    expect(await screen.findByText("Photo detection is unavailable")).toBeVisible();
    expect(screen.getByRole("combobox", { name: "Issue category" })).toHaveValue("");
  });
});
