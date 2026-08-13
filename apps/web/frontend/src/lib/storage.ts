import type { ConversationSummary } from "../types";

const runFlowViewportKeyPrefix = "wenjia-agent-web-run-flow-viewport:";
let storageNamespace = "auth-pending";

export function setStorageNamespace(namespace: string): void {
  storageNamespace = namespace.trim() || "auth-pending";
}

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


export function loadRunFlowViewport(sessionId: string): StoredRunFlowViewport | null {
  try {
    const parsed = JSON.parse(
      localStorage.getItem(`${runFlowViewportKeyPrefix}${storageNamespace}:${sessionId}`) || "null",
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
      `${runFlowViewportKeyPrefix}${storageNamespace}:${sessionId}`,
      JSON.stringify(viewport),
    );
  } catch {
    // Canvas persistence is best-effort and must never block closing the panel.
  }
}

export function conversationTitle(conversation: ConversationSummary): string {
  if (conversation.title && conversation.title !== "新的对话") {
    return conversation.title;
  }
  return "新的对话";
}
