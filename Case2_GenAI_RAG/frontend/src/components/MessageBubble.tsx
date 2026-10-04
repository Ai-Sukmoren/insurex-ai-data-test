import { useState } from "react";
import { BadgeCheck, ChevronDown, Timer } from "lucide-react";
import { Markdown } from "../markdown";
import { STEPS, stepLabel } from "../steps";
import type { Message } from "../types";

export function MessageBubble({ msg }: { msg: Message }) {
  const [open, setOpen] = useState(false);

  if (msg.role === "user") {
    return (
      <div className="msg user">
        <div className="bubble">{msg.content}</div>
      </div>
    );
  }

  const thinking = msg.streaming && !msg.content;
  return (
    <div className={`msg assistant ${msg.error ? "error" : ""}`}>
      <div className={`orb ${msg.streaming ? "live" : ""}`} aria-hidden="true">IX</div>
      <div className="bubble">
        {thinking ? (
          <div className="thinking">
            <span className="wave"><i /><i /><i /></span>
            {msg.activeStep ? stepLabel(msg.activeStep) : "Thinking"}…
          </div>
        ) : (
          <div className={`md ${msg.streaming ? "typing" : ""}`}><Markdown text={msg.content} /></div>
        )}

        {msg.leadId ? <div className="saved"><BadgeCheck size={14} /> Lead #{msg.leadId} saved to SQLite via MCP</div> : null}

        {!msg.streaming && msg.path && msg.path.length > 0 && (
          <div className="trace">
            <button className="trace-toggle" onClick={() => setOpen(o => !o)} aria-expanded={open}>
              <Timer size={12} /> {msg.seconds?.toFixed(1)} s · {msg.path.length} steps
              <ChevronDown size={12} className={open ? "rot" : ""} />
            </button>
            {open && (
              <div className="trace-steps">
                {msg.path.map((node, i) => {
                  const S = STEPS[node];
                  const Icon = S?.icon;
                  return (
                    <span key={i} className={`pill g-${S?.group ?? "route"}`} title={stepLabel(node)}>
                      {Icon && <Icon size={11} />}{node}
                    </span>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
