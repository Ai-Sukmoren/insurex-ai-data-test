import { Fragment, type ReactNode } from "react";
import { FileText } from "lucide-react";

/** Friendly document name: "InsureX_Health_Insurance.pdf" -> "InsureX Health Insurance". */
export const docName = (file: string) => file.replace(/^\d+_/, "").replace(/\.pdf$/i, "").replace(/_/g, " ");

const CITE = /\[([^[\]]+?\.pdf),\s*p\.(\d+)\]/gi;
const BOLD = /\*\*(.+?)\*\*/g;

/** Inline formatting built as React elements (never innerHTML), so model output cannot inject markup. */
function inline(text: string, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  const tokens: { index: number; length: number; node: ReactNode }[] = [];
  for (const m of text.matchAll(CITE)) {
    tokens.push({
      index: m.index!, length: m[0].length,
      node: <span className="cite" title={`${m[1]}, page ${m[2]}`}><FileText size={11} />{docName(m[1])} · p.{m[2]}</span>,
    });
  }
  for (const m of text.matchAll(BOLD)) {
    if (!tokens.some(t => m.index! >= t.index && m.index! < t.index + t.length))
      tokens.push({ index: m.index!, length: m[0].length, node: <b>{m[1]}</b> });
  }
  tokens.sort((a, b) => a.index - b.index).forEach((t, i) => {
    if (t.index > last) out.push(text.slice(last, t.index));
    out.push(<Fragment key={`${key}-${i}`}>{t.node}</Fragment>);
    last = t.index + t.length;
  });
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let list: { kind: "ul" | "ol"; items: ReactNode[] } | null = null;
  const flush = () => {
    if (!list) return;
    const L = list.kind;
    blocks.push(<L key={`l${blocks.length}`}>{list.items}</L>);
    list = null;
  };
  text.split("\n").forEach((raw, i) => {
    const line = raw.trim();
    const bullet = line.match(/^(?:[-*•]|(\d+)[.)])\s+(.*)/);
    if (bullet) {
      const kind = bullet[1] ? "ol" : "ul";
      if (!list || list.kind !== kind) { flush(); list = { kind, items: [] }; }
      list.items.push(<li key={i}>{inline(bullet[2], `li${i}`)}</li>);
      return;
    }
    flush();
    if (line) blocks.push(<p key={i}>{inline(line, `p${i}`)}</p>);
  });
  flush();
  return <>{blocks}</>;
}
