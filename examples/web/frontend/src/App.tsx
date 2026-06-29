import { useCallback, useEffect, useMemo, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { MessageList } from "./components/MessageList";
import { Composer } from "./components/Composer";
import { useChatStream } from "./hooks/useChatStream";
import type { ChatMessage, Conversation, FlowEvent } from "./types";
import {
  createConversation,
  loadActiveSessionId,
  loadConversations,
  nowIso,
  saveActiveSessionId,
  saveConversations,
  withMessage,
} from "./lib/storage";

type HealthStatus = "checking" | "ready" | "error";

interface PendingState {
  active: boolean;
  body: string;
  events: FlowEvent[];
  error: boolean;
}

const IDLE_PENDING: PendingState = { active: false, body: "", events: [], error: false };

function initialState(): { conversations: Conversation[]; sessionId: string } {
  const conversations = loadConversations();
  const stored = loadActiveSessionId();

  if (stored && conversations.some((conversation) => conversation.id === stored)) {
    return { conversations, sessionId: stored };
  }
  const conversation = createConversation(stored ?? undefined);
  return { conversations: [conversation, ...conversations], sessionId: conversation.id };
}

export default function App() {
  const [{ conversations, sessionId }, setState] = useState(initialState);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<PendingState>(IDLE_PENDING);
  const [health, setHealth] = useState<HealthStatus>("checking");
  const { send, isSending } = useChatStream();

  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  useEffect(() => {
    saveActiveSessionId(sessionId);
  }, [sessionId]);

  useEffect(() => {
    let cancelled = false;
    fetch("/health")
      .then((response) => {
        if (!response.ok) throw new Error("offline");
        if (!cancelled) setHealth("ready");
      })
      .catch(() => {
        if (!cancelled) setHealth("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const currentMessages = useMemo<ChatMessage[]>(() => {
    return conversations.find((item) => item.id === sessionId)?.messages ?? [];
  }, [conversations, sessionId]);

  const appendMessage = useCallback(
    (targetId: string, message: ChatMessage) => {
      setState((prev) => {
        const exists = prev.conversations.some((item) => item.id === targetId);
        const base = exists
          ? prev.conversations
          : [createConversation(targetId), ...prev.conversations];
        const updated = base.map((item) =>
          item.id === targetId ? withMessage(item, message) : item,
        );
        const target = updated.find((item) => item.id === targetId)!;
        const reordered = [target, ...updated.filter((item) => item.id !== targetId)].slice(0, 30);
        return { conversations: reordered, sessionId: prev.sessionId };
      });
    },
    [],
  );

  const handleSubmit = useCallback(
    async (message: string) => {
      if (isSending) {
        return;
      }
      const activeSession = sessionId;
      appendMessage(activeSession, {
        role: "user",
        body: message,
        flow: [],
        createdAt: nowIso(),
      });
      setDraft("");
      setPending({ active: true, body: "正在连接推演流程...", events: [], error: false });

      try {
        const result = await send(message, activeSession, {
          onEvent: (event) =>
            setPending((prev) => ({
              ...prev,
              events: [...prev.events, event],
              body: event.type === "done" ? prev.body : event.message || prev.body,
            })),
          onSessionId: (id) => setState((prev) => ({ ...prev, sessionId: id })),
        });
        appendMessage(result.sessionId, {
          role: "assistant",
          body: result.finalOutput,
          flow: result.events,
          createdAt: nowIso(),
        });
      } catch (error) {
        const text = error instanceof Error ? error.message : "请求失败，请稍后再试。";
        appendMessage(activeSession, {
          role: "assistant",
          body: text,
          type: "error",
          flow: [],
          createdAt: nowIso(),
        });
      } finally {
        setPending(IDLE_PENDING);
      }
    },
    [appendMessage, isSending, send, sessionId],
  );

  const handleNewSession = useCallback(() => {
    const conversation = createConversation();
    setState((prev) => ({
      conversations: [conversation, ...prev.conversations],
      sessionId: conversation.id,
    }));
  }, []);

  const handleSelectSession = useCallback(
    (id: string) => {
      if (isSending) return;
      setState((prev) => ({ ...prev, sessionId: id }));
    },
    [isSending],
  );

  const handleClearHistory = useCallback(() => {
    if (!confirm("确定清空本浏览器中的历史对话吗？")) {
      return;
    }
    const conversation = createConversation();
    setState({ conversations: [conversation], sessionId: conversation.id });
  }, []);

  return (
    <main className="app-shell">
      <Sidebar
        sessionId={sessionId}
        conversations={conversations}
        health={health}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        onClearHistory={handleClearHistory}
        onPickPrompt={(prompt) => setDraft(prompt)}
      />

      <section className="chat-panel" aria-label="Agent 对话">
        <header className="chat-header">
          <div>
            <p className="eyebrow">Agent 工作台</p>
            <h2>命盘、分析、起名与推演过程</h2>
          </div>
          <a href="/docs" target="_blank" rel="noreferrer">
            接口文档
          </a>
        </header>

        <MessageList messages={currentMessages} pending={pending} />

        <Composer
          disabled={isSending}
          value={draft}
          onChange={setDraft}
          onSubmit={handleSubmit}
        />
      </section>
    </main>
  );
}
