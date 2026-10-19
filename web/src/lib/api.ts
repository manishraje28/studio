export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const DEV_LOGIN = process.env.NEXT_PUBLIC_DEV_LOGIN === "true";

const TOKEN_KEY = "studio.token";

export type ProjectStatus =
  | "briefed" | "researching" | "strategy" | "design" | "awaiting_approval"
  | "building" | "qa" | "preview" | "live" | "failed";

export type Project = {
  id: string;
  business_name: string;
  business_type: string;
  city: string | null;
  website_url: string | null;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
};

export type AgentEvent = {
  id: number;
  agent: string;
  kind: "status" | "progress" | "artifact" | "error" | string;
  message: string;
  data: Record<string, unknown>;
  created_at: string;
};

export type Artifact = {
  id: string;
  kind: string;
  version: number;
  agent: string;
  content: Record<string, unknown>;
  created_at: string;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// Session storage: the token disappears when the tab closes. Fine for dev sign-in;
// Supabase Auth will manage real sessions in step 8.
export const auth = {
  get: () => (typeof window === "undefined" ? null : sessionStorage.getItem(TOKEN_KEY)),
  set: (t: string) => sessionStorage.setItem(TOKEN_KEY, t),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = auth.get();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    if (res.status === 401) auth.clear();
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  devLogin: (email: string) =>
    request<{ access_token: string }>("/dev/token", { method: "POST", body: JSON.stringify({ email }) }),
  projects: () => request<Project[]>("/projects"),
  project: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (brief: {
    business_name: string;
    business_type: string;
    city?: string;
    website_url?: string;
    answers: Record<string, string>;
  }) => request<Project>("/projects", { method: "POST", body: JSON.stringify(brief) }),
  artifacts: (id: string) => request<Artifact[]>(`/projects/${id}/artifacts`),
};

/**
 * Follow the live event stream for a project. EventSource cannot send an Authorization
 * header, so this reads the SSE response with fetch and parses it by hand.
 * Reconnects with the last seen id if the connection drops. Returns a stop function.
 */
export function streamEvents(projectId: string, onEvent: (e: AgentEvent) => void): () => void {
  const controller = new AbortController();
  let lastId = 0;

  const run = async () => {
    while (!controller.signal.aborted) {
      try {
        const res = await fetch(`${API_URL}/projects/${projectId}/events/stream?after=${lastId}`, {
          headers: { Authorization: `Bearer ${auth.get() ?? ""}`, Accept: "text/event-stream" },
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new ApiError(res.status, "stream failed");
        const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
        let buffer = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += value.replace(/\r\n/g, "\n");
          let cut;
          while ((cut = buffer.indexOf("\n\n")) >= 0) {
            const block = buffer.slice(0, cut);
            buffer = buffer.slice(cut + 2);
            const data = block
              .split("\n")
              .filter((l) => l.startsWith("data:"))
              .map((l) => l.slice(5).trimStart())
              .join("\n");
            if (!data) continue; // keep-alive pings
            const event = JSON.parse(data) as AgentEvent;
            lastId = Math.max(lastId, event.id);
            onEvent(event);
          }
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        if (err instanceof ApiError && (err.status === 401 || err.status === 404)) return;
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
  };
  run();
  return () => controller.abort();
}
