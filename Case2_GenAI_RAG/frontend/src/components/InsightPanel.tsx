import { useState } from "react";
import { Archive, Briefcase, Check, Database, FileText, Phone, RefreshCw, Sparkles, User, Wallet, Workflow } from "lucide-react";
import { docName } from "../markdown";
import { STEPS, stepLabel } from "../steps";
import type { Health, Lead, LeadField } from "../types";

const FIELDS: { key: LeadField; label: string; icon: typeof User }[] = [
  { key: "name", label: "Name", icon: User },
  { key: "occupation", label: "Occupation", icon: Briefcase },
  { key: "monthly_income", label: "Income / month", icon: Wallet },
  { key: "phone", label: "Phone", icon: Phone },
];

interface Props {
  steps: string[];
  busy: boolean;
  seconds: number | null;
  mode: string;
  lead: Partial<Record<LeadField, string | number>>;
  missing: LeadField[];
  leadId: number | null;
  summary: string;
  messageCount: number;
  leads: Lead[];
  currentSession: string;
  health: Health | null;
  onRefreshLeads: () => void;
}

function Ring({ value }: { value: number }) {
  const r = 22, c = 2 * Math.PI * r;
  return (
    <svg className="ring" viewBox="0 0 56 56" aria-label={`${Math.round(value * 100)}% complete`}>
      <circle cx="28" cy="28" r={r} className="ring-bg" />
      <circle cx="28" cy="28" r={r} className="ring-fg" strokeDasharray={c} strokeDashoffset={c * (1 - value)} />
      <text x="28" y="32" textAnchor="middle">{Math.round(value * 4)}/4</text>
    </svg>
  );
}

export function InsightPanel(p: Props) {
  const [showSummary, setShowSummary] = useState(true);
  const filled = FIELDS.filter(f => p.lead[f.key] != null && p.lead[f.key] !== "").length;
  const active = p.mode === "lead_collection";

  return (
    <aside className="panel">
      <section className="card glass">
        <h3><Workflow size={15} /> Agent pipeline <span className="hint">LangGraph, this turn</span></h3>
        {p.steps.length === 0 ? (
          <p className="muted">Send a message to watch the graph run node by node.</p>
        ) : (
          <ol className="timeline">
            {p.steps.map((node, i) => {
              const S = STEPS[node];
              const Icon = S?.icon ?? Sparkles;
              const isActive = p.busy && i === p.steps.length - 1;
              const loop = node === "rewrite_query" || (node === "retrieve" && p.steps.slice(0, i).includes("retrieve"));
              return (
                <li key={i} className={`t-step g-${S?.group ?? "route"} ${isActive ? "active" : "done"} ${loop ? "loop" : ""}`}>
                  <span className="t-dot"><Icon size={12} /></span>
                  <span className="t-label">{stepLabel(node)}{loop && <em> · retry loop</em>}</span>
                  <code>{node}</code>
                </li>
              );
            })}
          </ol>
        )}
        {p.seconds != null && !p.busy && <div className="muted small">Finished in {p.seconds.toFixed(1)} s</div>}
      </section>

      <section className="card glass">
        <h3><Archive size={15} /> Session memory</h3>
        <div className="mem-stats">
          <div><b>{p.messageCount}</b><span>messages remembered</span></div>
          <div><b>{p.summary ? "On" : "Off"}</b><span>running summary</span></div>
        </div>
        {p.summary ? (
          <>
            <button className="link" onClick={() => setShowSummary(s => !s)}>{showSummary ? "Hide" : "Show"} summary of older messages</button>
            {showSummary && <pre className="summary">{p.summary}</pre>}
          </>
        ) : (
          <p className="muted small">Every chat keeps its own history in the SQLite checkpointer. After 12+ messages, older ones are folded into a summary so long chats are still remembered.</p>
        )}
      </section>

      <section className={`card glass ${active ? "lead-active" : ""}`}>
        <h3><User size={15} /> Lead capture</h3>
        <div className="lead-head">
          <Ring value={filled / 4} />
          <p className="small">
            {p.leadId ? <>Saved as <b>lead #{p.leadId}</b> via the MCP tool.</>
              : active ? <>Collecting details: <b>{p.missing.length}</b> still needed.</>
              : "Say you're interested in a product to start."}
          </p>
        </div>
        <ul className="fields">
          {FIELDS.map(({ key, label, icon: Icon }) => {
            const v = p.lead[key];
            const ok = v != null && v !== "";
            const shown = ok ? (key === "monthly_income" ? `${Number(v).toLocaleString()} THB` : String(v)) : "–";
            return (
              <li key={key} className={ok ? "ok" : active && p.missing.includes(key) ? "need" : ""}>
                <Icon size={13} /><span className="f-label">{label}</span><span className="f-val">{shown}</span>
                {ok && <Check size={13} className="f-check" />}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="card glass">
        <h3><Database size={15} /> Saved leads <span className="hint">via MCP</span>
          <button className="icon" aria-label="Refresh leads" onClick={p.onRefreshLeads}><RefreshCw size={13} /></button></h3>
        {p.leads.length === 0 ? <p className="muted small">No leads yet.</p> : (
          <ul className="leads">
            {p.leads.map(l => (
              <li key={l.lead_id} className={l.session_id === p.currentSession ? "mine" : ""}>
                <b>#{l.lead_id} {l.name}</b>
                <span>{l.interested_product ?? "–"} · {l.occupation} · {l.monthly_income.toLocaleString()} THB · {l.phone}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card glass">
        <h3><FileText size={15} /> Knowledge base</h3>
        <ul className="docs">
          {p.health?.documents.map(d => <li key={d.file}><span>{docName(d.file)}</span><span className="muted">{d.chunks} chunks</span></li>)}
        </ul>
      </section>
    </aside>
  );
}
