// Mirrors the SSE event contract emitted by app/runtime/stream_runner.py.
export type FlowEventType =
  | "run_start"
  | "agent_start"
  | "thinking"
  | "handoff"
  | "tool_start"
  | "tool_done"
  | "generating"
  | "revise"
  | "verify"
  | "done"
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
  duration?: number;
  content?: string;
}

export type StageStatus = "pending" | "active" | "success" | "failed";

export interface ToolItem {
  id: string;
  label: string;
  status: StageStatus;
  duration?: number;
}

export type StageKind = "start" | "agent" | "revise" | "verify" | "done" | "error";

export interface FlowStage {
  id: string;
  kind: StageKind;
  label: string;
  status: StageStatus;
  thinking?: string;
  viaHandoff?: string;
  tools: ToolItem[];
}

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  role: MessageRole;
  body: string;
  type?: "" | "error";
  flow: FlowEvent[];
  createdAt: string;
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
  pillars: { year: string | null; month: string | null; day: string | null; hour: string | null };
  five_elements: Record<string, number> | null;
}
