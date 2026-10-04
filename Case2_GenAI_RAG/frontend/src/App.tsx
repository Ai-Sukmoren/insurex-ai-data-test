import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2, Trash2 } from "lucide-react";
import { api, streamChat } from "./api";
import { ChatView } from "./components/ChatView";
import { InsightPanel } from "./components/InsightPanel";
import { Sidebar } from "./components/Sidebar";
import type { Health, Lead, LeadField, Message, SessionMeta } from "./types";

const newId = () => "web-" + Math.random().toString(36).slice(2, 10);
const uid = () => Math.random().toString(36).slice(2);
const store = {
  get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};

interface Toast { id: string; text: string; kind: "ok" | "del" }

export default function App() {
  const [theme, setTheme] = useState<"dark" | "light">(() =>
    (store.get("insurex.theme") as "dark" | "light") ?? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"));
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [current, setCurrent] = useState<string>(() => new URLSearchParams(location.search).get("session") ?? store.get("insurex.current") ?? newId());
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const [seconds, setSeconds] = useState<number | null>(null);
  const [mode, setMode] = useState("qa");
  const [lead, setLead] = useState<Partial<Record<LeadField, string | number>>>({});
  const [missing, setMissing] = useState<LeadField[]>([]);
  const [leadId, setLeadId] = useState<number | null>(null);
  const [summary, setSummary] = useState("");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [ui, setUi] = useState({ sidebar: false, panel: false });
  const loadToken = useRef(0);

  useEffect(() => { document.documentElement.dataset.theme = theme; store.set("insurex.theme", theme); }, [theme]);
  useEffect(() => { store.set("insurex.current", current); }, [current]);

  const toast = (text: string, kind: Toast["kind"] = "ok") => {
    const t = { id: uid(), text, kind };
    setToasts(ts => [...ts, t]);
    setTimeout(() => setToasts(ts => ts.filter(x => x.id !== t.id)), 3200);
  };
  const refreshSessions = useCallback(() => api.sessions().then(setSessions).catch(() => {}), []);
  const refreshLeads = useCallback(() => api.leads().then(setLeads).catch(() => {}), []);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    refreshSessions();
    refreshLeads();
  }, [refreshSessions, refreshLeads]);

  // load the selected session's memory from the server
  useEffect(() => {
    const token = ++loadToken.current;
    setMessages([]); setSteps([]); setSeconds(null);
    api.session(current).then(st => {
      if (token !== loadToken.current) return;
      setMessages(st.messages.map(m => ({ id: uid(), role: m.role, content: m.content })));
      setMode(st.mode); setLead(st.lead); setMissing(st.missing); setLeadId(st.lead_id); setSummary(st.summary);
    }).catch(() => { setMode("qa"); setLead({}); setMissing([]); setLeadId(null); setSummary(""); });
  }, [current]);

  const isDraft = !sessions.some(s => s.session_id === current);
  const title = sessions.find(s => s.session_id === current)?.title ?? "New chat";

  const select = (id: string) => { if (!busy) { setCurrent(id); setUi({ sidebar: false, panel: false }); } };
  const startNew = () => { if (!busy) { setCurrent(newId()); setUi({ sidebar: false, panel: false }); } };

  const rename = async (id: string, t: string) => {
    await api.rename(id, t).catch(() => {});
    refreshSessions();
  };

  const remove = async (id: string) => {
    await api.remove(id).catch(() => {});
    const rest = sessions.filter(s => s.session_id !== id);
    setSessions(rest);
    if (id === current) setCurrent(rest[0]?.session_id ?? newId());
    toast("Chat and its memory deleted", "del");
  };

  const send = async (text: string) => {
    const session = current;
    const botId = uid();
    setBusy(true); setSteps([]); setSeconds(null);
    setMessages(ms => [...ms, { id: uid(), role: "user", content: text }, { id: botId, role: "assistant", content: "", streaming: true }]);
    const patch = (fn: (m: Message) => Message) => setMessages(ms => ms.map(m => (m.id === botId ? fn(m) : m)));
    try {
      await streamChat(session, text, {
        onStep: node => { setSteps(s => [...s, node]); patch(m => ({ ...m, activeStep: node })); },
        onToken: t => patch(m => ({ ...m, content: m.content + t })),
        onFinal: r => {
          patch(m => ({ ...m, content: r.reply, streaming: false, path: r.path, seconds: r.seconds, leadId: r.lead_id, error: !!r.error }));
          setSeconds(r.seconds); setMode(r.mode); setLead(r.lead); setMissing(r.missing);
          if (r.lead_id) { setLeadId(r.lead_id); toast(`Lead #${r.lead_id} saved via MCP`); refreshLeads(); }
          else if (r.mode === "lead_collection") setLeadId(null);
        },
      });
      api.session(session).then(st => setSummary(st.summary)).catch(() => {});
    } catch (e) {
      patch(m => ({ ...m, streaming: false, error: true, content: `Could not reach the assistant (${(e as Error).message}). Check that the server and Ollama are running.` }));
    } finally {
      setBusy(false);
      refreshSessions();
    }
  };

  const userMessages = messages.filter(m => !m.streaming).length;

  return (
    <div className={`app ${ui.sidebar ? "show-sidebar" : ""} ${ui.panel ? "show-panel" : ""}`}>
      <div className="aurora" aria-hidden="true"><i /><i /><i /></div>
      <Sidebar sessions={sessions} current={current} draftId={isDraft ? current : null} health={health}
               onSelect={select} onNew={startNew} onRename={rename} onDelete={remove} />
      <ChatView title={title} messages={messages} busy={busy} leadMode={mode === "lead_collection"} theme={theme}
                onSend={send} onToggleTheme={() => setTheme(t => (t === "dark" ? "light" : "dark"))}
                onToggleSidebar={() => setUi(u => ({ ...u, sidebar: !u.sidebar }))}
                onTogglePanel={() => setUi(u => ({ ...u, panel: !u.panel }))} />
      <InsightPanel steps={steps} busy={busy} seconds={seconds} mode={mode} lead={lead} missing={missing} leadId={leadId}
                    summary={summary} messageCount={userMessages} leads={leads} currentSession={current} health={health}
                    onRefreshLeads={refreshLeads} />
      {(ui.sidebar || ui.panel) && <div className="scrim" onClick={() => setUi({ sidebar: false, panel: false })} />}
      <div className="toasts" role="status">
        {toasts.map(t => (
          <div key={t.id} className={`toast ${t.kind}`}>{t.kind === "ok" ? <CheckCircle2 size={16} /> : <Trash2 size={16} />}{t.text}</div>
        ))}
      </div>
    </div>
  );
}
