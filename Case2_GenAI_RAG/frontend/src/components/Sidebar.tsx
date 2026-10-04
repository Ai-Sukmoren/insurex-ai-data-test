import { useState } from "react";
import { Check, MessageSquare, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import type { Health, SessionMeta } from "../types";

interface Props {
  sessions: SessionMeta[];
  current: string;
  draftId: string | null;
  health: Health | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}

function relative(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  return new Date(iso).toLocaleDateString();
}

export function Sidebar({ sessions, current, draftId, health, onSelect, onNew, onRename, onDelete }: Props) {
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [confirming, setConfirming] = useState<string | null>(null);

  const shown = sessions.filter(s => s.title.toLowerCase().includes(query.toLowerCase()));
  const saveTitle = (id: string) => {
    if (title.trim()) onRename(id, title.trim());
    setEditing(null);
  };

  return (
    <aside className="sidebar glass">
      <div className="brand">
        <div className="logo">IX</div>
        <div>
          <b>InsureX</b>
          <span>Sales Assistant</span>
        </div>
      </div>

      <button className="btn-new" onClick={onNew}><Plus size={16} /> New chat</button>

      <label className="search">
        <Search size={14} />
        <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search chats" aria-label="Search chats" />
      </label>

      <div className="side-label">Chats <span>{sessions.length}</span></div>
      <ul className="sessions">
        {draftId && (
          <li className="session active draft">
            <MessageSquare size={15} />
            <div className="s-text"><span className="s-title">New chat</span><span className="s-meta">not started</span></div>
          </li>
        )}
        {shown.map(s => (
          <li key={s.session_id} className={`session ${s.session_id === current ? "active" : ""}`}>
            {confirming === s.session_id ? (
              <div className="confirm">
                <span>Delete this chat and its memory?</span>
                <div>
                  <button className="danger" onClick={() => { onDelete(s.session_id); setConfirming(null); }}>Delete</button>
                  <button onClick={() => setConfirming(null)}>Cancel</button>
                </div>
              </div>
            ) : editing === s.session_id ? (
              <div className="rename">
                <input autoFocus value={title} maxLength={80} onChange={e => setTitle(e.target.value)}
                       onKeyDown={e => { if (e.key === "Enter") saveTitle(s.session_id); if (e.key === "Escape") setEditing(null); }} />
                <button aria-label="Save name" onClick={() => saveTitle(s.session_id)}><Check size={14} /></button>
                <button aria-label="Cancel" onClick={() => setEditing(null)}><X size={14} /></button>
              </div>
            ) : (
              <>
                <button className="s-main" onClick={() => onSelect(s.session_id)}>
                  <MessageSquare size={15} />
                  <div className="s-text">
                    <span className="s-title">{s.title}</span>
                    <span className="s-meta">{relative(s.updated_at)} · {s.turns} message{s.turns === 1 ? "" : "s"}</span>
                  </div>
                </button>
                <div className="s-actions">
                  <button aria-label="Rename chat" title="Rename" onClick={() => { setEditing(s.session_id); setTitle(s.title); }}><Pencil size={13} /></button>
                  <button aria-label="Delete chat" title="Delete" className="del" onClick={() => setConfirming(s.session_id)}><Trash2 size={13} /></button>
                </div>
              </>
            )}
          </li>
        ))}
        {!shown.length && !draftId && <li className="s-empty">{query ? "No matching chats" : "No chats yet"}</li>}
      </ul>

      <div className="side-foot">
        <span className={`dot ${health ? "ok" : ""}`} />
        {health ? <>Local models <b>{health.chat_model}</b> + <b>{health.embed_model}</b></> : "Connecting to server…"}
      </div>
    </aside>
  );
}
