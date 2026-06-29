import { useCallback, useRef, useState } from "react";
import type { FlowEvent } from "../types";

export interface StreamResult {
  finalOutput: string;
  events: FlowEvent[];
  sessionId: string;
}

interface StreamCallbacks {
  onEvent: (event: FlowEvent) => void;
  onSessionId?: (sessionId: string) => void;
}

function parseSseChunk(chunk: string): FlowEvent | null {
  const data = chunk
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim())
    .join("\n");
  if (!data) {
    return null;
  }
  try {
    return JSON.parse(data) as FlowEvent;
  } catch {
    return null;
  }
}

export function useChatStream() {
  const [isSending, setIsSending] = useState(false);
  const sendingRef = useRef(false);

  const send = useCallback(
    async (
      message: string,
      sessionId: string,
      callbacks: StreamCallbacks,
    ): Promise<StreamResult> => {
      if (sendingRef.current) {
        throw new Error("已有推演正在进行。");
      }
      sendingRef.current = true;
      setIsSending(true);

      const events: FlowEvent[] = [];
      let resolvedSession = sessionId;

      try {
        const response = await fetch("/api/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, session_id: sessionId }),
        });

        if (!response.ok || !response.body) {
          const payload = await response.json().catch(() => null);
          throw new Error(payload?.detail || "Agent 请求失败。");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalOutput = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }
          buffer += decoder.decode(value, { stream: true });
          const chunks = buffer.split("\n\n");
          buffer = chunks.pop() || "";
          for (const chunk of chunks) {
            const event = parseSseChunk(chunk);
            if (!event) {
              continue;
            }
            if (event.session_id && event.session_id !== resolvedSession) {
              resolvedSession = event.session_id;
              callbacks.onSessionId?.(resolvedSession);
            }
            events.push(event);
            callbacks.onEvent(event);

            if (event.type === "done") {
              if (event.success === false) {
                throw new Error(event.message || "Agent 请求失败。");
              }
              finalOutput = event.content || "";
            } else if (event.type === "error") {
              throw new Error(event.message || "Agent 请求失败。");
            }
          }
        }

        if (!finalOutput) {
          throw new Error("Agent 未返回最终内容。");
        }
        return { finalOutput, events, sessionId: resolvedSession };
      } finally {
        sendingRef.current = false;
        setIsSending(false);
      }
    },
    [],
  );

  return { send, isSending };
}
