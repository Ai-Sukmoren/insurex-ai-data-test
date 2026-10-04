export type Role = "user" | "assistant";

export interface TurnResult {
  session_id: string;
  user: string;
  reply: string;
  path: string[];
  seconds: number;
  mode: "qa" | "lead_collection";
  lead: Partial<Record<LeadField, string | number>>;
  missing: LeadField[];
  lead_id: number | null;
  error: string | null;
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  path?: string[];
  seconds?: number;
  streaming?: boolean;
  activeStep?: string;
  leadId?: number | null;
  error?: boolean;
}

export interface SessionMeta {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  turns: number;
}

export interface SessionState {
  session_id: string;
  messages: { role: Role; content: string }[];
  mode: "qa" | "lead_collection";
  lead: Partial<Record<LeadField, string | number>>;
  missing: LeadField[];
  lead_id: number | null;
  summary: string;
}

export type LeadField = "name" | "occupation" | "monthly_income" | "phone";

export interface Lead {
  lead_id: number;
  name: string;
  occupation: string;
  monthly_income: number;
  phone: string;
  interested_product: string | null;
  session_id: string;
  created_at: string;
}

export interface Health {
  ok: boolean;
  chat_model: string;
  embed_model: string;
  documents: { file: string; chunks: number }[];
}
