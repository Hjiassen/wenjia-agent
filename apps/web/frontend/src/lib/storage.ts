import type { ChatMessage, Conversation, FlowEvent } from "../types";

const activeSessionKey = "wenjia-agent-web-active-session";
const legacySessionKey = "wenjia-agent-web-session";
const conversationsKey = "wenjia-agent-web-conversations";
const clientIdKey = "wenjia-agent-web-client-id";
const runFlowViewportKeyPrefix = "wenjia-agent-web-run-flow-viewport:";

export interface StoredRunFlowViewport {
  x: number;
  y: number;
  scale: number;
}

export function nowIso(): string {
  return new Date().toISOString();
}

function fallbackUuid(): string {
  const cryptoApi = globalThis.crypto;
  if (typeof cryptoApi?.randomUUID === "function") {
    return cryptoApi.randomUUID();
  }

  if (typeof cryptoApi?.getRandomValues === "function") {
    const bytes = cryptoApi.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0"));
    return [
      hex.slice(0, 4).join(""),
      hex.slice(4, 6).join(""),
      hex.slice(6, 8).join(""),
      hex.slice(8, 10).join(""),
      hex.slice(10, 16).join(""),
    ].join("-");
  }

  const timePart = Date.now().toString(36);
  const randomPart = Math.random().toString(36).slice(2, 12);
  return `${timePart}-${randomPart}`;
}

export function createSessionId(): string {
  return `web:${fallbackUuid()}`;
}

export function getClientId(): string {
  const existing = localStorage.getItem(clientIdKey);
  if (existing) {
    return existing;
  }
  const created = `client:${fallbackUuid()}`;
  localStorage.setItem(clientIdKey, created);
  return created;
}

export function createConversation(id: string = createSessionId()): Conversation {
  const createdAt = nowIso();
  return { id, title: "新的对话", createdAt, updatedAt: createdAt, messages: [] };
}

function isFlowEvent(value: unknown): value is FlowEvent {
  return Boolean(
    value &&
      typeof value === "object" &&
      typeof (value as FlowEvent).type === "string",
  );
}

function legacyFlow(message: Record<string, unknown>): FlowEvent[] {
  const source = Array.isArray(message.flow)
    ? message.flow
    : Array.isArray(message.flowSteps)
      ? message.flowSteps
      : [];
  return source.filter(isFlowEvent);
}

function terminalFlowType(events: FlowEvent[]): FlowEvent["type"] | null {
  const terminal = [...events]
    .reverse()
    .find((event) => event.type === "done" || event.type === "error" || event.type === "interrupted");
  return terminal?.type ?? null;
}

function looksInterrupted(body: string): boolean {
  return /手动|中止|停止|取消|打断/.test(body);
}

function makeHistoryTerminalEvent(
  conversationId: string,
  messageIndex: number,
  type: "interrupted" | "error",
  message: ChatMessage,
): FlowEvent {
  return {
    id: `history:${conversationId}:${messageIndex}:${type}`,
    type,
    session_id: conversationId,
    timestamp: message.createdAt,
    success: false,
    source: "client",
    message: type === "interrupted" ? "推演已被手动中止。" : message.body || "请求失败。",
  };
}

function makeHistoryIncompleteEvent(
  conversationId: string,
  messageIndex: number,
  message: ChatMessage,
): FlowEvent {
  return {
    id: `history:${conversationId}:${messageIndex}:incomplete`,
    type: "interrupted",
    session_id: conversationId,
    timestamp: nowIso(),
    success: false,
    source: "client",
    message: message.body
      ? "页面离开时生成尚未完成，已保留离开前内容。"
      : "页面离开时生成尚未完成，未收到输出内容。",
  };
}

function normalizeSuggestions(value: unknown): ChatMessage["suggestions"] {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return value
    .map((item) => {
      if (
        item &&
        typeof item === "object" &&
        typeof (item as { prompt?: unknown }).prompt === "string"
      ) {
        return { prompt: (item as { prompt: string }).prompt.trim() };
      }
      return null;
    })
    .filter((item): item is NonNullable<ChatMessage["suggestions"]>[number] =>
      Boolean(item?.prompt),
    );
}

function normalizeMessage(
  conversationId: string,
  message: unknown,
  index: number,
): ChatMessage | null {
  if (!message || typeof message !== "object") {
    return null;
  }

  const raw = message as Record<string, unknown>;
  const role = raw.role === "user" || raw.role === "assistant" ? raw.role : null;
  if (!role) {
    return null;
  }

  const normalized: ChatMessage = {
    ...(raw as Partial<ChatMessage>),
    role,
    body: typeof raw.body === "string" ? raw.body : "",
    type: raw.type === "error" ? "error" : "",
    flow: legacyFlow(raw),
    createdAt: typeof raw.createdAt === "string" ? raw.createdAt : nowIso(),
    suggestions: normalizeSuggestions(raw.suggestions),
    suggestionsLoading: false,
    streaming: raw.streaming === true,
    streamingStatus: typeof raw.streamingStatus === "string" ? raw.streamingStatus : undefined,
    streamingError: raw.streamingError === true,
    incomplete: raw.incomplete === true,
  };

  if (normalized.role === "assistant" && normalized.streaming) {
    normalized.streaming = false;
    normalized.streamingStatus = undefined;
    normalized.streamingError = false;
    normalized.incomplete = true;
    if (!normalized.body.trim()) {
      normalized.body = "（页面离开时生成尚未完成，未收到输出内容。）";
      normalized.type = "error";
    }
    normalized.flow = [
      ...normalized.flow,
      makeHistoryIncompleteEvent(conversationId, index, normalized),
    ];
  }

  if (normalized.role === "assistant" && normalized.type === "error") {
    const terminal = terminalFlowType(normalized.flow);
    if (terminal !== "error" && terminal !== "interrupted") {
      const type = looksInterrupted(normalized.body) ? "interrupted" : "error";
      normalized.flow = [
        ...normalized.flow,
        makeHistoryTerminalEvent(conversationId, index, type, normalized),
      ];
    }
  }

  return normalized;
}

function messageForStorage(message: ChatMessage): ChatMessage {
  const stored = { ...message };
  delete stored.suggestionsLoading;
  return stored;
}

function conversationForStorage(conversation: Conversation): Conversation {
  return {
    ...conversation,
    messages: conversation.messages.map(messageForStorage),
  };
}

function normalizeConversation(value: unknown): Conversation | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const raw = value as Record<string, unknown>;
  if (typeof raw.id !== "string" || !raw.id) {
    return null;
  }

  const createdAt = typeof raw.createdAt === "string" ? raw.createdAt : nowIso();
  const messages = Array.isArray(raw.messages)
    ? raw.messages
        .map((message, index) => normalizeMessage(raw.id as string, message, index))
        .filter((message): message is ChatMessage => Boolean(message))
    : [];

  return {
    id: raw.id,
    title: typeof raw.title === "string" ? raw.title : "新的对话",
    createdAt,
    updatedAt: typeof raw.updatedAt === "string" ? raw.updatedAt : createdAt,
    messages,
  };
}

export function loadConversations(): Conversation[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(conversationsKey) || "[]");
    if (Array.isArray(parsed)) {
      return parsed
        .map(normalizeConversation)
        .filter((item): item is Conversation => Boolean(item));
    }
  } catch {
    // Ignore broken localStorage data and start fresh.
  }
  return [];
}

export function saveConversations(conversations: Conversation[]): void {
  localStorage.setItem(conversationsKey, JSON.stringify(conversations.map(conversationForStorage)));
}

export function loadActiveSessionId(): string | null {
  return (
    localStorage.getItem(activeSessionKey) || localStorage.getItem(legacySessionKey) || null
  );
}

export function saveActiveSessionId(id: string): void {
  localStorage.setItem(activeSessionKey, id);
  localStorage.setItem(legacySessionKey, id);
}

export function loadRunFlowViewport(sessionId: string): StoredRunFlowViewport | null {
  try {
    const parsed = JSON.parse(
      localStorage.getItem(`${runFlowViewportKeyPrefix}${sessionId}`) || "null",
    ) as Partial<StoredRunFlowViewport> | null;
    if (
      parsed &&
      Number.isFinite(parsed.x) &&
      Number.isFinite(parsed.y) &&
      Number.isFinite(parsed.scale)
    ) {
      return { x: parsed.x!, y: parsed.y!, scale: parsed.scale! };
    }
  } catch {
    // Ignore broken view state and start from the default canvas position.
  }
  return null;
}

export function saveRunFlowViewport(
  sessionId: string,
  viewport: StoredRunFlowViewport,
): void {
  try {
    localStorage.setItem(
      `${runFlowViewportKeyPrefix}${sessionId}`,
      JSON.stringify(viewport),
    );
  } catch {
    // Canvas persistence is best-effort and must never block closing the panel.
  }
}

export function conversationTitle(conversation: Conversation): string {
  if (conversation.title && conversation.title !== "新的对话") {
    return conversation.title;
  }
  const firstUser = conversation.messages.find((message) => message.role === "user");
  if (!firstUser) {
    return "新的对话";
  }
  const compact = firstUser.body.replace(/\s+/g, " ").trim();
  return compact.length > 24 ? `${compact.slice(0, 24)}...` : compact;
}

export function conversationPreview(conversation: Conversation): string {
  const last = conversation.messages.at(-1);
  if (!last) {
    return "还没有消息";
  }
  if (last.streaming) {
    return last.body.trim() || last.streamingStatus || "正在生成回答";
  }
  if (last.incomplete && !last.body.trim()) {
    return "生成未完成";
  }
  const compact = last.body.replace(/\s+/g, " ").trim();
  return compact.length > 36 ? `${compact.slice(0, 36)}...` : compact;
}

export function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function withMessage(
  conversation: Conversation,
  message: ChatMessage,
): Conversation {
  const messages = [...conversation.messages, message];
  return {
    ...conversation,
    messages,
    updatedAt: nowIso(),
    title: conversationTitle({ ...conversation, messages }),
  };
}
