import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
const KEY = "civicshield.session.v1";
export const session = {
  get: () => localStorage.getItem(KEY),
  set: (token: string) => localStorage.setItem(KEY, token),
  clear: () => localStorage.removeItem(KEY),
};
export async function api<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const requestToken = session.get();
  const headers = new Headers(options.headers);
  if (requestToken) headers.set("Authorization", `Bearer ${requestToken}`);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`/api${path}`, { ...options, headers });
  if (!response.ok) {
    if (
      response.status === 401 &&
      path !== "/auth/login" &&
      requestToken &&
      session.get() === requestToken &&
      !options.signal?.aborted
    ) {
      session.clear();
      window.dispatchEvent(new Event("civicshield:unauthorized"));
    }
    const error = await response
      .json()
      .catch(() => ({ detail: "The server could not complete this request." }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
export const json = (body: unknown) => JSON.stringify(body);
export function useApi<T = any>(path: string, enabled = true) {
  return useQuery<T>({
    queryKey: [path],
    queryFn: ({ signal }) => api<T>(path, { signal }),
    enabled,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
export function useAction<T = any>(
  action: (variables: T) => Promise<any>,
  message = "Changes saved",
) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: action,
    onSuccess: () => {
      void client.invalidateQueries();
      if (message) toast.success(message);
    },
    onError: (error: Error) => toast.error(error.message),
  });
}
export async function upload(file: File, incidentId?: number, kind = "report") {
  if (file.size > 8 * 1024 * 1024)
    throw new Error("Photographs must be smaller than 8 MB.");
  if (!file.type.startsWith("image/"))
    throw new Error("Please choose a photograph.");
  const data = new FormData();
  data.append("file", file);
  data.append("kind", kind);
  if (incidentId) data.append("incident_id", String(incidentId));
  return api<{ id: number; url: string; filename: string }>("/uploads", {
    method: "POST",
    body: data,
  });
}
export async function attachmentBlob(id: number) {
  const response = await fetch(`/api/uploads/${id}/file`, {
    headers: { Authorization: `Bearer ${session.get()}` },
  });
  if (!response.ok) throw new Error("Unable to load evidence");
  return URL.createObjectURL(await response.blob());
}
export function date(value?: string) {
  return value
    ? new Date(
        value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value)
          ? value
          : `${value}Z`,
      ).toLocaleString("en-GB", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
}
export function relative(value: string) {
  const minutes = Math.max(
    0,
    Math.floor(
      (Date.now() -
        new Date(
          value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value)
            ? value
            : `${value}Z`,
        ).getTime()) /
        60000,
    ),
  );
  return minutes < 60
    ? `${minutes}m ago`
    : minutes < 1440
      ? `${Math.floor(minutes / 60)}h ago`
      : `${Math.floor(minutes / 1440)}d ago`;
}
