import type { Health, Lead, SessionMeta, SessionState, TurnResult } from "./types";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetch("/api/health").then(r => json<Health>(r)),
  sessions: () => fetch("/api/sessions").then(r => json<{ sessions: SessionMeta[] }>(r)).then(d => d.sessions),
  session: (id: string) => fetch(`/api/sessions/${encodeURIComponent(id)}`).then(r => json<SessionState>(r)),
  rename: (id: string, title: string) =>
    fetch(`/api/sessions/${encodeURIComponent(id)}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }),
    }).then(r => json<{ ok: boolean }>(r)),
  remove: (id: string) =>
    fetch(`/api/sessions/${encodeURIComponent(id)}`, { method: "DELETE" }).then(r => json<{ ok: boolean }>(r)),
  leads: () => fetch("/api/leads?limit=20").then(r => json<{ count: number; leads: Lead[] }>(r)).then(d => d.leads),
};

export interface StreamHandlers {
  onStep: (node: string) => void;
  onToken: (text: string) => void;
  onFinal: (result: TurnResult) => void;
}

/** POST a message and consume the server-sent-event stream (step / token / final events). */
export async function streamChat(sessionId: string, message: string, h: StreamHandlers): Promise<void> {
  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok || !res.body) throw new Error(`Server error ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let gotFinal = false;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut: number;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const type = block.match(/^event: (.*)$/m)?.[1];
      const data = JSON.parse(block.match(/^data: (.*)$/m)?.[1] ?? "{}");
      if (type === "step") h.onStep(data.node);
      else if (type === "token") h.onToken(data.text);
      else if (type === "final") { gotFinal = true; h.onFinal(data as TurnResult); }
    }
  }
  if (!gotFinal) throw new Error("The stream ended without an answer");
}
