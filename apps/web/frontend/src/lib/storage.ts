import type { ChatMessage, Conversation } from "../types";

const activeSessionKey = "wenjia-agent-web-active-session";
const legacySessionKey = "wenjia-agent-web-session";
const conversationsKey = "wenjia-agent-web-conversations";

export function nowIso(): string {
  return new Date().toISOString();
}

export function createSessionId(): string {
  return `web:${crypto.randomUUID()}`;
}

export function createConversation(id: string = createSessionId()): Conversation {
  const createdAt = nowIso();
  return { id, title: "新的对话", createdAt, updatedAt: createdAt, messages: [] };
}

export function loadConversations(): Conversation[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(conversationsKey) || "[]");
    if (Array.isArray(parsed)) {
      return parsed.filter((item) => item && item.id) as Conversation[];
    }
  } catch {
    // Ignore broken localStorage data and start fresh.
  }
  return [];
}

export function saveConversations(conversations: Conversation[]): void {
  localStorage.setItem(conversationsKey, JSON.stringify(conversations));
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
