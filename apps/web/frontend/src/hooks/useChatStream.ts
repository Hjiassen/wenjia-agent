import { useCallback, useRef, useState } from "react";
import type { FlowEvent } from "../types";
import { getClientId } from "../lib/storage";
import { normalizeFinalOutput } from "../lib/streamText";

export interface StreamResult {
  finalOutput: string;
  events: FlowEvent[];
  sessionId: string;
  aborted?: boolean;
}

interface StreamCallbacks {
  onEvent: (event: FlowEvent) => void;
  onAnswerDelta?: (delta: string, text: string) => void;
  onAnswerReplace?: (text: string) => void;
  onSessionId?: (sessionId: string) => void;
}

export class StreamFlowError extends Error {
  events: FlowEvent[];
  sessionId: string;

  constructor(message: string, events: FlowEvent[], sessionId: string) {
    super(message);
    this.name = "StreamFlowError";
    Object.setPrototypeOf(this, StreamFlowError.prototype);
    this.events = events;
    this.sessionId = sessionId;
  }
}

function makeClientEvent(
  type: "interrupted" | "error",
  sessionId: string,
  message: string,
): FlowEvent {
  return {
    id: `client:${sessionId}:${Date.now()}`,
    type,
    session_id: sessionId,
    timestamp: new Date().toISOString(),
    success: false,
    source: "client",
    message,
  };
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

const ANSWER_FRAME_MS = 32;
const ANSWER_FRAME_WIDTH = 24;

function displayWidth(char: string): number {
  return char.charCodeAt(0) > 127 ? 2 : 1;
}

function takeDisplayChunk(text: string): [string, string] {
  let width = 0;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    width += displayWidth(char);
    if (char === "\n" || width >= ANSWER_FRAME_WIDTH) {
      return [text.slice(0, index + 1), text.slice(index + 1)];
    }
  }
  return [text, ""];
}

export function useChatStream() {
  const [isSending, setIsSending] = useState(false);
  const sendingRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  // Abort the in-flight stream (wired to the Sender cancel button).
  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

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
      const controller = new AbortController();
      abortRef.current = controller;

      const events: FlowEvent[] = [];
      let resolvedSession = sessionId;
      let stopAnswerAnimation: (() => void) | null = null;

      const pushClientEvent = (event: FlowEvent) => {
        events.push(event);
        callbacks.onEvent(event);
      };

      try {
        const response = await fetch("/api/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, session_id: sessionId, client_id: getClientId() }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          const payload = await response.json().catch(() => null);
          throw new Error(payload?.detail || "Agent 请求失败。");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalOutput = "";
        let streamedOutput = "";
        let displayedOutput = "";
        let queuedOutput = "";
        let answerFinalized = false;
        let flushTimer: ReturnType<typeof setTimeout> | null = null;
        let flushResolvers: Array<() => void> = [];

        const resolveFlushWaiters = () => {
          if (queuedOutput || flushTimer) {
            return;
          }
          const resolvers = flushResolvers;
          flushResolvers = [];
          resolvers.forEach((resolve) => resolve());
        };

        const scheduleFlush = () => {
          if (flushTimer) {
            return;
          }
          flushTimer = setTimeout(() => {
            flushTimer = null;
            if (!queuedOutput) {
              resolveFlushWaiters();
              return;
            }

            const [chunk, rest] = takeDisplayChunk(queuedOutput);
            queuedOutput = rest;
            displayedOutput += chunk;
            callbacks.onAnswerDelta?.(chunk, displayedOutput);

            if (queuedOutput) {
              scheduleFlush();
            } else {
              resolveFlushWaiters();
            }
          }, ANSWER_FRAME_MS);
        };

        const enqueueAnswer = (delta: string) => {
          streamedOutput += delta;
          queuedOutput += delta;
          scheduleFlush();
        };

        const resetAnswer = () => {
          if (flushTimer) {
            clearTimeout(flushTimer);
            flushTimer = null;
          }
          streamedOutput = "";
          displayedOutput = "";
          queuedOutput = "";
          callbacks.onAnswerReplace?.("");
          resolveFlushWaiters();
        };

        const finalizeAnswer = (text: string) => {
          if (flushTimer) {
            clearTimeout(flushTimer);
            flushTimer = null;
          }
          queuedOutput = "";
          streamedOutput = text;
          displayedOutput = text;
          answerFinalized = true;
          callbacks.onAnswerReplace?.(text);
          resolveFlushWaiters();
        };

        const waitForAnswerQueue = async () => {
          if (!queuedOutput && !flushTimer) {
            return;
          }
          await new Promise<void>((resolve) => {
            flushResolvers.push(resolve);
          });
        };

        stopAnswerAnimation = () => {
          if (flushTimer) {
            clearTimeout(flushTimer);
            flushTimer = null;
          }
          queuedOutput = "";
          resolveFlushWaiters();
        };

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

            if (event.type === "answer_delta") {
              const delta = event.delta || event.content || "";
              if (delta && !answerFinalized) {
                enqueueAnswer(delta);
              }
              continue;
            }

            if (event.type === "answer_reset") {
              if (!answerFinalized) {
                resetAnswer();
              }
              continue;
            }

            events.push(event);
            callbacks.onEvent(event);

            if (event.type === "done") {
              if (event.success === false) {
                throw new StreamFlowError(event.message || "Agent 请求失败。", events, resolvedSession);
              }
              finalOutput = normalizeFinalOutput(
                event.content || streamedOutput,
                streamedOutput,
              );
              if (finalOutput) {
                finalizeAnswer(finalOutput);
              }
            } else if (event.type === "error") {
              throw new StreamFlowError(event.message || "Agent 请求失败。", events, resolvedSession);
            }
          }
        }

        if (!finalOutput) {
          throw new Error("Agent 未返回最终内容。");
        }
        await waitForAnswerQueue();
        return { finalOutput, events, sessionId: resolvedSession };
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          pushClientEvent(
            makeClientEvent("interrupted", resolvedSession, "推演已被手动中止。"),
          );
          return { finalOutput: "", events, sessionId: resolvedSession, aborted: true };
        }
        if (error instanceof StreamFlowError) {
          throw error;
        }
        const text = error instanceof Error ? error.message : "请求失败，请稍后再试。";
        pushClientEvent(makeClientEvent("error", resolvedSession, text));
        throw new StreamFlowError(text, events, resolvedSession);
      } finally {
        stopAnswerAnimation?.();
        sendingRef.current = false;
        setIsSending(false);
        abortRef.current = null;
      }
    },
    [],
  );

  return { send, cancel, isSending };
}
