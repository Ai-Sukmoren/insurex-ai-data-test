import {
  Archive, Ban, Brain, ClipboardList, History, LogOut, type LucideIcon, MessageSquare, PenLine, RotateCw, Save, Search,
  ShieldCheck, Smile, UserPlus,
} from "lucide-react";

export type StepGroup = "route" | "rag" | "lead" | "memory";

export const STEPS: Record<string, { label: string; icon: LucideIcon; group: StepGroup }> = {
  classify: { label: "Understanding the message", icon: Brain, group: "route" },
  contextualize: { label: "Resolving the follow-up from memory", icon: History, group: "rag" },
  retrieve: { label: "Searching the documents (FAISS)", icon: Search, group: "rag" },
  grade: { label: "Checking the passages are relevant", icon: ShieldCheck, group: "rag" },
  rewrite_query: { label: "Rephrasing the search and retrying", icon: RotateCw, group: "rag" },
  generate: { label: "Writing the answer", icon: PenLine, group: "rag" },
  not_found: { label: "Not in the documents: safe fallback", icon: Ban, group: "rag" },
  extract_lead: { label: "Reading the customer's details", icon: UserPlus, group: "lead" },
  ask_missing: { label: "Asking for missing details", icon: ClipboardList, group: "lead" },
  save_lead: { label: "Saving the lead via the MCP tool", icon: Save, group: "lead" },
  exit_lead: { label: "Leaving lead collection", icon: LogOut, group: "lead" },
  smalltalk: { label: "Replying", icon: Smile, group: "route" },
  recall: { label: "Recalling this session's memory", icon: MessageSquare, group: "memory" },
  update_memory: { label: "Updating session memory", icon: Archive, group: "memory" },
};

export const stepLabel = (node: string) => STEPS[node]?.label ?? node;
