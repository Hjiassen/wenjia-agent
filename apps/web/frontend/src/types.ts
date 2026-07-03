// Mirrors the SSE event contract emitted by app/runtime/stream_runner.py.
export type FlowEventType =
  | "run_start"
  | "agent_start"
  | "thinking"
  | "handoff"
  | "tool_start"
  | "tool_done"
  | "input_guardrail"
  | "generating"
  | "answer_delta"
  | "answer_reset"
  | "fallback"
  | "revise"
  | "verify"
  | "done"
  | "interrupted"
  | "error";

export interface FlowEvent {
  type: FlowEventType;
  id?: string;
  session_id?: string;
  timestamp?: string;
  message?: string;
  agent?: string;
  agent_label?: string;
  from_agent?: string;
  to_agent?: string;
  from_agent_label?: string;
  to_agent_label?: string;
  tool?: string;
  tool_call_id?: string;
  display_name?: string;
  success?: boolean;
  blocked?: boolean;
  code?: string;
  category?: string;
  duration?: number;
  content?: string;
  delta?: string;
  source?: "server" | "client";
}

export type StageStatus = "pending" | "active" | "success" | "failed";

export interface ToolItem {
  id: string;
  label: string;
  status: StageStatus;
  duration?: number;
  note?: string;
}

export type StageKind =
  | "start"
  | "agent"
  | "guardrail"
  | "revise"
  | "verify"
  | "done"
  | "interrupted"
  | "error";

export interface FlowStage {
  id: string;
  kind: StageKind;
  label: string;
  status: StageStatus;
  thinkingSteps: string[];
  viaHandoff?: string;
  tools: ToolItem[];
  startedAt?: string;
  endedAt?: string;
}

export interface PipelineStats {
  durationSec: number | null;
  toolCount: number;
  toolFailures: number;
  agentCount: number;
  reviseCount: number;
  verifyPassed: boolean | null;
}

export interface StepRow {
  id: string;
  time: string;
  text: string;
  kind: FlowEventType;
  status: StageStatus | "";
  duration?: number;
}

export type MessageRole = "user" | "assistant";

export interface SuggestedQuestion {
  prompt: string;
}

export interface ChatMessage {
  role: MessageRole;
  body: string;
  type?: "" | "error";
  flow: FlowEvent[];
  createdAt: string;
  profileContext?: AttachedProfile[];
  suggestions?: SuggestedQuestion[];
  suggestionsLoading?: boolean;
  streaming?: boolean;
  streamingStatus?: string;
  streamingError?: boolean;
  incomplete?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface Profile {
  id: number;
  name: string;
  relationship_type: string;
  gender: string | null;
  birth?: {
    year: number | null;
    month: number | null;
    day: number | null;
    hour: number | null;
    minute: number | null;
    calendar_type: string | null;
    is_leap_month: boolean | null;
    province: string | null;
    city: string | null;
    longitude: string | null;
  };
  pillars: { year: string | null; month: string | null; day: string | null; hour: string | null };
  five_elements: Record<string, number> | null;
}

export interface AttachedProfile {
  id: number;
  name: string;
  relationship_type: string;
}

export interface ProfilePayload {
  client_id?: string | null;
  name: string;
  relationship_type: string;
  gender?: string | null;
  birth_year?: number | null;
  birth_month?: number | null;
  birth_day?: number | null;
  birth_hour?: number | null;
  birth_minute?: number | null;
  calendar_type?: string | null;
  is_leap_month?: boolean | null;
  province?: string | null;
  city?: string | null;
  longitude?: string | null;
}

export interface LongTermMemory {
  id: number;
  user_id?: string;
  kind: string;
  key: string;
  title: string;
  content: string;
  payload?: unknown;
  source_session_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}
