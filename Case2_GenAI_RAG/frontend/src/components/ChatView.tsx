import { useEffect, useRef, useState } from "react";
import { ArrowUp, HeartPulse, Menu, Moon, PanelRight, PawPrint, ShieldPlus, Sun, UserPlus } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import type { Message } from "../types";

const SUGGESTIONS = [
  { icon: HeartPulse, title: "Health plan", text: "What does Prima Care plan M pay for room and board per day?" },
  { icon: ShieldPlus, title: "ประกันอุบัติเหตุ", text: "ประกันอุบัติเหตุ ทิพย TIP PA SENIOR แผน 1 เบี้ยเท่าไหร่" },
  { icon: PawPrint, title: "ประกันสัตว์เลี้ยง", text: "ประกันสัตว์เลี้ยง แผน XL เบี้ยปีละเท่าไหร่" },
  { icon: UserPlus, title: "Capture a lead", text: "I'm interested in travel insurance, can an agent call me?" },
];

interface Props {
  title: string;
  messages: Message[];
  busy: boolean;
  leadMode: boolean;
  theme: "dark" | "light";
  onSend: (text: string) => void;
  onToggleTheme: () => void;
  onToggleSidebar: () => void;
  onTogglePanel: () => void;
}

export function ChatView(p: Props) {
  const [text, setText] = useState("");
  const scroller = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [p.messages]);

  useEffect(() => {
    const t = input.current;
    if (!t) return;
    t.style.height = "auto";
    t.style.height = Math.min(t.scrollHeight, 180) + "px";
  }, [text]);

  const send = (value = text) => {
    const v = value.trim();
    if (!v || p.busy) return;
    p.onSend(v);
    setText("");
    input.current?.focus();
  };

  return (
    <main className="chat">
      <header className="topbar glass">
        <button className="icon only-mobile" aria-label="Show chats" onClick={p.onToggleSidebar}><Menu size={18} /></button>
        <h1 title={p.title}>{p.title}</h1>
        {p.leadMode && <span className="badge"><UserPlus size={13} /> Collecting contact details</span>}
        <button className="icon" aria-label="Toggle theme" onClick={p.onToggleTheme}>{p.theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}</button>
        <button className="icon only-narrow" aria-label="Show details" onClick={p.onTogglePanel}><PanelRight size={17} /></button>
      </header>

      <div className="messages" ref={scroller} aria-live="polite">
        {p.messages.length === 0 ? (
          <div className="hero">
            <div className="hero-orb" aria-hidden="true">IX</div>
            <h2>How can I help you <span className="grad">sell today?</span></h2>
            <p>Answers come only from the InsureX product documents, with sources. Say you're interested and I'll capture the customer's details. Every chat remembers its own conversation.</p>
            <div className="cards">
              {SUGGESTIONS.map(s => (
                <button key={s.text} className="s-card glass" onClick={() => send(s.text)}>
                  <s.icon size={18} /><b>{s.title}</b><span>{s.text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          p.messages.map(m => <MessageBubble key={m.id} msg={m} />)
        )}
      </div>

      <form className="composer glass" onSubmit={e => { e.preventDefault(); send(); }}>
        <textarea ref={input} rows={1} value={text} maxLength={2000}
                  placeholder="Ask about health, accident, savings, travel or pet insurance… (English or ภาษาไทย)"
                  onChange={e => setText(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                  aria-label="Message" />
        <button className="send" type="submit" disabled={p.busy || !text.trim()} aria-label="Send"><ArrowUp size={18} /></button>
      </form>
      <div className="foot-note">Runs locally with Ollama · answers cite the product documents · Enter to send, Shift+Enter for a new line</div>
    </main>
  );
}
