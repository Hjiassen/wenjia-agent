import { useCallback, useEffect, useMemo, useState } from "react";
import { Layout, App as AntdApp, Button, Drawer, Grid, Tooltip } from "antd";
import { MenuUnfoldOutlined, PlusOutlined } from "@ant-design/icons";
import { ChatSider } from "./components/ChatSider";
import { ChatWindow } from "./components/ChatWindow";
import { RunFlowPanel, type RunFlowTurn } from "./components/RunFlowPanel";
import { StreamFlowError, useChatStream } from "./hooks/useChatStream";
import type { ChatMessage, Conversation, FlowEvent, Profile, SuggestedQuestion } from "./types";
import { buildProfilePrompt, toAttachedProfile } from "./lib/profileText";
import {
  createConversation,
  createSessionId,
  conversationTitle,
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
  status: string;
  events: FlowEvent[];
  error: boolean;
}

const IDLE_PENDING: PendingState = { active: false, body: "", status: "", events: [], error: false };

function pendingStatusForEvent(event: FlowEvent): string {
  switch (event.type) {
    case "run_start":
      return "正在准备推演";
    case "agent_start":
    case "thinking":
    case "handoff":
      return "正在理解问题";
    case "tool_start":
    case "tool_done":
      return event.success === false ? "正在调整计算结果" : "正在计算关键数据";
    case "input_guardrail":
      return event.blocked ? "输入需要调整" : "正在确认输入";
    case "generating":
    case "answer_delta":
    case "answer_reset":
      return "正在整理回答";
    case "revise":
    case "fallback":
      return "正在优化回答";
    case "verify":
      return event.success === false ? "正在优化回答" : "正在校验结果";
    case "interrupted":
      return "已中止";
    case "error":
      return "请求失败";
    case "done":
      return "推演完成";
  }
}

async function fetchSuggestedQuestions(
  sessionId: string,
  userMessage: string,
  assistantMessage: string,
): Promise<SuggestedQuestion[]> {
  const response = await fetch("/api/chat/suggestions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      user_message: userMessage,
      assistant_message: assistantMessage,
    }),
  });
  if (!response.ok) {
    return [];
  }

  const payload = await response.json().catch(() => null);
  if (!payload || !Array.isArray(payload.suggestions)) {
    return [];
  }

  const rawSuggestions: unknown[] = payload.suggestions;
  return rawSuggestions
    .map((item) => {
      if (typeof item === "string") {
        return { prompt: item.trim() };
      }
      if (
        item &&
        typeof item === "object" &&
        typeof (item as SuggestedQuestion).prompt === "string"
      ) {
        return { prompt: (item as SuggestedQuestion).prompt.trim() };
      }
      return { prompt: "" };
    })
    .filter((item) => item.prompt)
    .slice(0, 3);
}

function initialState(): { conversations: Conversation[]; sessionId: string } {
  const conversations = loadConversations();
  const stored = loadActiveSessionId();

  if (stored && conversations.some((conversation) => conversation.id === stored)) {
    return { conversations, sessionId: stored };
  }
  return { conversations, sessionId: stored ?? createSessionId() };
}

export default function App() {
  const [{ conversations, sessionId }, setState] = useState(initialState);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<PendingState>(IDLE_PENDING);
  const [health, setHealth] = useState<HealthStatus>("checking");
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfileIds, setSelectedProfileIds] = useState<number[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [siderCollapsed, setSiderCollapsed] = useState(false);
  const [flowOpen, setFlowOpen] = useState(false);
  const { send, cancel, isSending } = useChatStream();
  const { modal } = AntdApp.useApp();
  const screens = Grid.useBreakpoint();
  // `md` is unset until the first measurement; treat only an explicit false as mobile.
  const isMobile = screens.md === false;

  const loadProfiles = useCallback(async (id: string) => {
    try {
      const response = await fetch(`/api/profiles/${encodeURIComponent(id)}`);
      if (!response.ok) return;
      const payload = await response.json();
      setProfiles(Array.isArray(payload.profiles) ? payload.profiles : []);
    } catch {
      // Profiles are a non-critical panel; ignore transient fetch errors.
    }
  }, []);

  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  useEffect(() => {
    saveActiveSessionId(sessionId);
  }, [sessionId]);

  useEffect(() => {
    loadProfiles(sessionId);
  }, [sessionId, loadProfiles]);

  useEffect(() => {
    setSelectedProfileIds([]);
  }, [sessionId]);

  useEffect(() => {
    const validIds = new Set(profiles.map((profile) => profile.id));
    setSelectedProfileIds((ids) => ids.filter((id) => validIds.has(id)));
  }, [profiles]);

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

  // One run-flow turn per assistant reply, labelled by the user prompt that
  // triggered it; the in-progress reply is appended as a live turn.
  const runFlowTurns = useMemo<RunFlowTurn[]>(() => {
    const turns: RunFlowTurn[] = [];
    let lastPrompt = "";
    currentMessages.forEach((message, index) => {
      if (message.role === "user") {
        lastPrompt = message.body;
        return;
      }
      if (message.flow.length > 0) {
        turns.push({
          id: `turn-${index}`,
          prompt: lastPrompt,
          events: message.flow,
          error: message.type === "error",
        });
      }
    });
    if (pending.active) {
      turns.push({ id: "turn-live", prompt: lastPrompt, events: pending.events, live: true });
    }
    return turns;
  }, [currentMessages, pending]);

  const appendMessage = useCallback((targetId: string, message: ChatMessage) => {
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
  }, []);

  const updateMessage = useCallback(
    (targetId: string, messageCreatedAt: string, patch: Partial<ChatMessage>) => {
      setState((prev) => ({
        ...prev,
        conversations: prev.conversations.map((conversation) =>
          conversation.id === targetId
            ? {
                ...conversation,
                messages: conversation.messages.map((message) =>
                  message.createdAt === messageCreatedAt
                    ? { ...message, ...patch }
                    : message,
                ),
              }
            : conversation,
        ),
      }));
    },
    [],
  );

  const handleSubmit = useCallback(
    async (message: string, attachedProfiles: Profile[] = []) => {
      if (isSending) {
        return;
      }
      const activeSession = sessionId;
      const agentMessage = buildProfilePrompt(message, attachedProfiles);
      appendMessage(activeSession, {
        role: "user",
        body: message,
        flow: [],
        createdAt: nowIso(),
        profileContext: attachedProfiles.map(toAttachedProfile),
      });
      setDraft("");
      setPending({ active: true, body: "", status: "已发送，正在连接", events: [], error: false });

      try {
        const result = await send(agentMessage, activeSession, {
          onEvent: (event) =>
            setPending((prev) => ({
              ...prev,
              events: [...prev.events, event],
              status: pendingStatusForEvent(event),
              error:
                prev.error ||
                event.type === "error" ||
                event.type === "interrupted" ||
                (event.success === false && !event.blocked),
            })),
          onAnswerDelta: (_delta, text) =>
            setPending((prev) => ({
              ...prev,
              body: text,
              status: "正在生成回答",
            })),
          onAnswerReplace: (text) =>
            setPending((prev) => ({
              ...prev,
              body: text,
              status: "正在生成回答",
            })),
          onSessionId: (id) => setState((prev) => ({ ...prev, sessionId: id })),
        });
        if (result.aborted) {
          if (result.events.length) {
            appendMessage(result.sessionId, {
              role: "assistant",
              body: "（推演已被手动中止）",
              type: "error",
              flow: result.events,
              createdAt: nowIso(),
            });
          }
          return;
        }
        const assistantCreatedAt = nowIso();
        appendMessage(result.sessionId, {
          role: "assistant",
          body: result.finalOutput,
          flow: result.events,
          createdAt: assistantCreatedAt,
          suggestionsLoading: true,
        });
        void fetchSuggestedQuestions(result.sessionId, message, result.finalOutput)
          .then((suggestions) =>
            updateMessage(result.sessionId, assistantCreatedAt, {
              suggestions,
              suggestionsLoading: false,
            }),
          )
          .catch(() =>
            updateMessage(result.sessionId, assistantCreatedAt, {
              suggestions: [],
              suggestionsLoading: false,
            }),
          );
        loadProfiles(result.sessionId);
      } catch (error) {
        const text = error instanceof Error ? error.message : "请求失败，请稍后再试。";
        const streamFlow = error instanceof StreamFlowError ? error.events : [];
        const streamSession = error instanceof StreamFlowError ? error.sessionId : activeSession;
        appendMessage(streamSession, {
          role: "assistant",
          body: text,
          type: "error",
          flow: streamFlow,
          createdAt: nowIso(),
        });
        if (streamSession !== activeSession) {
          setState((prev) => ({ ...prev, sessionId: streamSession }));
        }
      } finally {
        setPending(IDLE_PENDING);
      }
    },
    [appendMessage, updateMessage, isSending, send, sessionId, loadProfiles],
  );

  const handleNewSession = useCallback(() => {
    if (isSending) return;
    setState((prev) => ({ conversations: prev.conversations, sessionId: createSessionId() }));
    setDraft("");
    setPending(IDLE_PENDING);
    setDrawerOpen(false);
  }, [isSending]);

  const handleSelectSession = useCallback(
    (id: string) => {
      if (isSending) return;
      setState((prev) => ({ ...prev, sessionId: id }));
      setDrawerOpen(false);
    },
    [isSending],
  );

  const handleDeleteSession = useCallback(
    (id: string) => {
      if (isSending) return;
      const target = conversations.find((conversation) => conversation.id === id);
      if (!target) return;

      modal.confirm({
        title: "删除对话",
        content: `确定删除「${conversationTitle(target)}」吗？此操作只会清除本浏览器中的对话缓存。`,
        okText: "删除",
        okButtonProps: { danger: true },
        cancelText: "取消",
        onOk: () => {
          setState((prev) => {
            const targetIndex = prev.conversations.findIndex(
              (conversation) => conversation.id === id,
            );
            if (targetIndex < 0) {
              return prev;
            }

            const remaining = prev.conversations.filter((conversation) => conversation.id !== id);
            const nextConversation =
              remaining[targetIndex] ?? remaining[targetIndex - 1] ?? remaining[0];
            const nextSessionId =
              prev.sessionId === id ? nextConversation?.id ?? createSessionId() : prev.sessionId;

            return { conversations: remaining, sessionId: nextSessionId };
          });

          if (sessionId === id) {
            setDraft("");
            setPending(IDLE_PENDING);
            setFlowOpen(false);
          }
        },
      });
    },
    [conversations, isSending, modal, sessionId],
  );

  const handleClearHistory = useCallback(() => {
    modal.confirm({
      title: "清空历史对话",
      content: "确定清空本浏览器中的历史对话吗？此操作不可撤销。",
      okText: "清空",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: () => {
        setState({ conversations: [], sessionId: createSessionId() });
        setDraft("");
        setPending(IDLE_PENDING);
      },
    });
  }, [modal]);

  const sider = (
    <ChatSider
      sessionId={sessionId}
      conversations={conversations}
      health={health}
      onNewSession={handleNewSession}
      onSelectSession={handleSelectSession}
      onDeleteSession={handleDeleteSession}
      onClearHistory={handleClearHistory}
      onCollapse={!isMobile ? () => setSiderCollapsed(true) : undefined}
    />
  );

  return (
    <Layout className="app-shell" hasSider={!isMobile}>
      {isMobile ? (
        <Drawer
          placement="left"
          width={288}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          styles={{ body: { padding: 0 } }}
          className="app-drawer"
        >
          {sider}
        </Drawer>
      ) : (
        <Layout.Sider
          width={siderCollapsed ? 58 : 288}
          className={`app-sider ${siderCollapsed ? "app-sider-collapsed" : ""}`.trim()}
          theme="light"
        >
          {siderCollapsed ? (
            <div className="sider-rail">
              <Tooltip title="展开历史" placement="right">
                <Button
                  type="text"
                  aria-label="展开历史"
                  icon={<MenuUnfoldOutlined />}
                  onClick={() => setSiderCollapsed(false)}
                />
              </Tooltip>
              <Tooltip title="新的对话" placement="right">
                <Button
                  type="text"
                  aria-label="新的对话"
                  icon={<PlusOutlined />}
                  disabled={isSending}
                  onClick={handleNewSession}
                />
              </Tooltip>
            </div>
          ) : (
            sider
          )}
        </Layout.Sider>
      )}

      <Layout.Content className="app-content">
        <ChatWindow
          messages={currentMessages}
          pending={pending}
          draft={draft}
          isSending={isSending}
          isMobile={isMobile}
          flowTurnCount={runFlowTurns.length}
          sessionId={sessionId}
          profiles={profiles}
          selectedProfileIds={selectedProfileIds}
          onDraftChange={setDraft}
          onSelectedProfileIdsChange={setSelectedProfileIds}
          onProfilesChanged={() => loadProfiles(sessionId)}
          onSubmit={handleSubmit}
          onCancel={cancel}
          onOpenSider={() => setDrawerOpen(true)}
          onOpenFlow={() => setFlowOpen(true)}
        />

        <RunFlowPanel
          open={flowOpen}
          turns={runFlowTurns}
          onClose={() => setFlowOpen(false)}
        />
      </Layout.Content>
    </Layout>
  );
}
