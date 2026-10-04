/* InsureX Sales Assistant - web client. Streams agent steps over SSE, keeps a session list in localStorage. */
"use strict";

const STEP_LABELS = {
  classify: "Understanding the message", contextualize: "Resolving the follow-up from memory",
  retrieve: "Searching the documents (FAISS)", grade: "Checking the passages are relevant",
  rewrite_query: "Rephrasing the search and retrying", generate: "Writing the answer",
  not_found: "Not in the documents: safe fallback", extract_lead: "Reading the customer's details",
  ask_missing: "Asking for missing details", save_lead: "Saving the lead via the MCP tool",
  exit_lead: "Leaving lead collection", smalltalk: "Replying", recall: "Recalling this session's memory",
};
const LEAD_FIELDS = [["name", "Name"], ["occupation", "Occupation"], ["monthly_income", "Income / month"], ["phone", "Phone"]];
const STORE_KEY = "insurex.sessions";

const $ = id => document.getElementById(id);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

class SessionStore {
  constructor() {
    try { this.items = JSON.parse(localStorage.getItem(STORE_KEY)) || []; } catch { this.items = []; }
  }
  save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(this.items)); } catch { /* private mode */ } }
  create() {
    const id = "web-" + Math.random().toString(36).slice(2, 10);
    this.items.unshift({id, title: "New chat", updated: Date.now()});
    this.save();
    return id;
  }
  touch(id, firstMessage) {
    const s = this.items.find(x => x.id === id);
    if (!s) return;
    if (s.title === "New chat" && firstMessage) s.title = firstMessage.slice(0, 48);
    s.updated = Date.now();
    this.items.sort((a, b) => b.updated - a.updated);
    this.save();
  }
}

/** Escape first, then apply a tiny markdown subset and turn [file.pdf, p.N] into source chips. */
function renderMarkdown(text) {
  const esc = s => s.replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const docName = f => f.replace(/^\d+_/, "").replace(/\.pdf$/i, "").replace(/_/g, " ");
  const inline = s => esc(s)
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/\[([^\[\]]+?\.pdf),\s*p\.(\d+)\]/gi, (_, f, p) => `<span class="cite" title="${f}, page ${p}">${docName(f)} · p.${p}</span>`);
  const out = [];
  let list = null;
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    const bullet = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)/);
    if (bullet) {
      const kind = /^\d/.test(line) ? "ol" : "ul";
      if (!list || list.kind !== kind) { list && out.push(`</${list.kind}>`); list = {kind}; out.push(`<${kind}>`); }
      out.push(`<li>${inline(bullet[1])}</li>`);
      continue;
    }
    if (list) { out.push(`</${list.kind}>`); list = null; }
    if (line) out.push(`<p>${inline(line)}</p>`);
  }
  if (list) out.push(`</${list.kind}>`);
  return out.join("");
}

class ChatApp {
  constructor() {
    this.store = new SessionStore();
    this.current = null;
    this.busy = false;
    this.bind();
    this.loadHealth();
    this.loadLeads();
    const fromUrl = new URLSearchParams(location.search).get("session");
    if (fromUrl && /^[A-Za-z0-9_-]{1,64}$/.test(fromUrl) && !this.store.items.some(s => s.id === fromUrl)) {
      this.store.items.unshift({id: fromUrl, title: fromUrl, updated: Date.now()});
      this.store.save();
    }
    this.open(fromUrl || this.store.items[0]?.id || this.store.create());
  }

  bind() {
    $("composer").addEventListener("submit", e => { e.preventDefault(); this.send(); });
    $("input").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this.send(); } });
    $("input").addEventListener("input", () => this.autosize());
    $("newChat").addEventListener("click", () => { this.open(this.store.create()); this.closeOverlays(); });
    $("refreshLeads").addEventListener("click", () => this.loadLeads());
    $("menuBtn").addEventListener("click", () => this.toggle("show-sidebar"));
    $("panelBtn").addEventListener("click", () => this.toggle("show-panel"));
    $("scrim").addEventListener("click", () => this.closeOverlays());
    document.querySelectorAll(".suggestions .chip").forEach(c => c.addEventListener("click", () => { $("input").value = c.textContent; this.send(); }));
  }

  toggle(cls) { $("app").classList.toggle(cls); $("scrim").hidden = !["show-sidebar", "show-panel"].some(c => $("app").classList.contains(c)); }
  closeOverlays() { $("app").classList.remove("show-sidebar", "show-panel"); $("scrim").hidden = true; }
  autosize() { const t = $("input"); t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 160) + "px"; }

  /* ---------------------------------------------------------------- sessions */
  renderSessions() {
    const ul = $("sessions");
    ul.replaceChildren();
    this.store.items.forEach(s => {
      const li = el("li"), b = el("button");
      b.type = "button";
      b.setAttribute("aria-current", String(s.id === this.current));
      b.append(el("span", "s-title", s.title), el("span", "s-meta", `${s.id} · ${new Date(s.updated).toLocaleString([], {dateStyle: "short", timeStyle: "short"})}`));
      b.addEventListener("click", () => { this.open(s.id); this.closeOverlays(); });
      li.append(b);
      ul.append(li);
    });
  }

  async open(id) {
    this.current = id;
    const meta = this.store.items.find(s => s.id === id);
    $("sessionTitle").textContent = meta?.title || "New chat";
    $("sessionId").textContent = `session: ${id}`;
    this.renderSessions();
    $("messages").replaceChildren($("empty"));
    $("empty").hidden = false;
    $("steps").replaceChildren(el("li", "muted", "Send a message to see how the agent works."));
    $("turnMeta").textContent = "";
    try {
      const res = await fetch(`/api/sessions/${encodeURIComponent(id)}`);
      if (!res.ok) throw new Error(res.statusText);
      const state = await res.json();
      if (this.current !== id) return;
      state.messages.forEach(m => this.addMessage(m.role, m.content));
      this.renderLead(state.mode, state.lead, state.missing, state.lead_id);
    } catch (e) {
      this.renderLead("qa", {}, [], null);
    }
  }

  /* ---------------------------------------------------------------- messages */
  addMessage(role, content, extra = {}) {
    $("empty").hidden = true;
    const row = el("div", `msg ${role}${extra.error ? " error" : ""}`);
    const bubble = el("div", "bubble");
    if (role === "user") {
      bubble.textContent = content;
      row.append(bubble);
    } else {
      bubble.innerHTML = renderMarkdown(content);
      row.append(el("div", "avatar", "IX"), bubble);
    }
    $("messages").append(row);
    this.scroll();
    return bubble;
  }

  scroll() { const m = $("messages"); m.scrollTop = m.scrollHeight; }

  thinkingBubble() {
    $("empty").hidden = true;
    const row = el("div", "msg assistant"), bubble = el("div", "bubble");
    const t = el("div", "thinking"), label = el("span", null, "Thinking…");
    t.append(el("span", "spinner"), label);
    bubble.append(t);
    row.append(el("div", "avatar", "IX"), bubble);
    $("messages").append(row);
    this.scroll();
    return {row, bubble, label};
  }

  /* ---------------------------------------------------------------- send + stream */
  async send() {
    const text = $("input").value.trim();
    if (!text || this.busy) return;
    const session = this.current;
    this.busy = true;
    $("send").disabled = true;
    $("input").value = "";
    this.autosize();
    this.addMessage("user", text);
    this.store.touch(session, text);
    $("sessionTitle").textContent = this.store.items.find(s => s.id === session)?.title || "Chat";
    this.renderSessions();
    $("steps").replaceChildren();
    $("turnMeta").textContent = "";
    const pending = this.thinkingBubble();
    const seen = [];

    try {
      const res = await fetch("/api/chat/stream", {method: "POST", headers: {"Content-Type": "application/json"},
                                                    body: JSON.stringify({session_id: session, message: text})});
      if (!res.ok || !res.body) throw new Error(`Server error ${res.status}`);
      const reader = res.body.getReader(), decoder = new TextDecoder();
      let buffer = "", final = null;
      while (true) {
        const {value, done} = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, {stream: true});
        let cut;
        while ((cut = buffer.indexOf("\n\n")) >= 0) {
          const block = buffer.slice(0, cut);
          buffer = buffer.slice(cut + 2);
          const type = (block.match(/^event: (.*)$/m) || [])[1];
          const data = JSON.parse((block.match(/^data: (.*)$/m) || [])[1] || "{}");
          if (type === "step") {
            seen.push(data.node);
            this.addStep(data.node, seen);
            pending.label.textContent = (STEP_LABELS[data.node] || data.node) + "…";
          } else if (type === "final") {
            final = data;
          }
        }
      }
      if (!final) throw new Error("The stream ended without an answer");
      this.finish(pending, final, session);
    } catch (e) {
      pending.row.classList.add("error");
      pending.bubble.textContent = `Could not reach the assistant (${e.message}). Check that the server and Ollama are running.`;
    } finally {
      this.busy = false;
      $("send").disabled = false;
      $("input").focus();
    }
  }

  finish(pending, r, session) {
    pending.bubble.innerHTML = renderMarkdown(r.reply);
    if (r.error) pending.row.classList.add("error");
    if (r.lead_id) pending.bubble.append(el("div", "saved", `Lead #${r.lead_id} saved to SQLite via MCP`));
    pending.bubble.append(el("div", "meta", `${r.seconds.toFixed(1)} s · ${r.path.length} steps`));
    $("turnMeta").textContent = `${r.seconds.toFixed(1)} s · mode: ${r.mode}`;
    if (session === this.current) this.renderLead(r.mode, r.lead, r.missing, r.lead_id);
    if (r.lead_id) this.loadLeads();
    this.scroll();
  }

  addStep(node, seen) {
    const li = el("li", "done");
    const isLoop = node === "retrieve" && seen.filter(n => n === "retrieve").length > 1 || node === "rewrite_query";
    if (isLoop) li.className = "loop";
    li.append(el("span", "n", String(seen.length)), el("span", null, STEP_LABELS[node] || node), el("code", null, node));
    $("steps").append(li);
  }

  /* ---------------------------------------------------------------- side panel */
  renderLead(mode, lead = {}, missing = [], savedId) {
    const active = mode === "lead_collection";
    $("modeBadge").hidden = !active;
    const ul = $("leadFields");
    ul.replaceChildren();
    LEAD_FIELDS.forEach(([key, label]) => {
      const value = lead[key];
      const filled = value != null && value !== "";
      const li = el("li", filled ? "filled" : (active && missing.includes(key) ? "needed" : ""));
      const shown = key === "monthly_income" && filled ? `${Number(value).toLocaleString()} THB` : (filled ? String(value) : "–");
      li.append(el("span", "state", filled ? "✓" : ""), el("span", "label", label), el("span", "value", shown));
      ul.append(li);
    });
    $("leadNote").textContent = savedId ? `Saved as lead #${savedId}.`
      : active ? `Collecting details: ${missing.length} field(s) still needed.`
      : "Say you're interested in a product to start lead collection.";
  }

  async loadLeads() {
    const box = $("leads");
    try {
      const res = await fetch("/api/leads?limit=20");
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      box.replaceChildren();
      if (!data.leads.length) { box.append(el("p", "muted", "No leads yet.")); return; }
      data.leads.forEach(l => {
        const row = el("div", "lead-row" + (l.session_id === this.current ? " mine" : ""));
        row.append(el("b", null, `#${l.lead_id} ${l.name}`), el("br"),
                   document.createTextNode(`${l.interested_product || "–"} · ${l.occupation} · ${Number(l.monthly_income).toLocaleString()} THB · ${l.phone}`));
        box.append(row);
      });
    } catch (e) {
      box.replaceChildren(el("p", "muted", "Could not load leads."));
    }
  }

  async loadHealth() {
    try {
      const h = await (await fetch("/api/health")).json();
      const foot = $("modelInfo");
      foot.replaceChildren(el("span", "dot ok"), document.createTextNode("Local models: "), el("b", null, h.chat_model),
                           document.createTextNode(" + "), el("b", null, h.embed_model));
      const ul = $("docs");
      ul.replaceChildren();
      h.documents.forEach(d => { const li = el("li"); li.append(el("span", null, d.file.replace(/\.pdf$/i, "")), el("span", "muted", `${d.chunks} chunks`)); ul.append(li); });
    } catch (e) {
      $("modelInfo").replaceChildren(el("span", "dot"), document.createTextNode("Server not reachable"));
    }
  }
}

new ChatApp();
