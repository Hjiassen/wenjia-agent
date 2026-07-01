import { useCallback, useEffect, useMemo, useState } from "react";
import { Layout, App as AntdApp, Drawer, Grid } from "antd";
import { ChatSider } from "./components/ChatSider";
import { ChatWindow } from "./components/ChatWindow";
import { RunFlowPanel, type RunFlowTurn } from "./components/RunFlowPanel";
import { useChatStream } from "./hooks/useChatStream";
import type { ChatMessage, Conversation, FlowEvent, Profile } from "./types";
import { buildProfilePrompt, toAttachedProfile } from "./lib/profileText";
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
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfileIds, setSelectedProfileIds] = useState<number[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
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
      setPending({ active: true, body: "正在连接推演流程…", events: [], error: false });

      try {
        const result = await send(agentMessage, activeSession, {
          onEvent: (event) =>
            setPending((prev) => ({
              ...prev,
              events: [...prev.events, event],
              body: event.type === "done" ? prev.body : event.message || prev.body,
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
        appendMessage(result.sessionId, {
          role: "assistant",
          body: result.finalOutput,
          flow: result.events,
          createdAt: nowIso(),
        });
        loadProfiles(result.sessionId);
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
    [appendMessage, isSending, send, sessionId, loadProfiles],
  );

  const handleNewSession = useCallback(() => {
    const conversation = createConversation();
    setState((prev) => ({
      conversations: [conversation, ...prev.conversations],
      sessionId: conversation.id,
    }));
    setDrawerOpen(false);
  }, []);

  const handleSelectSession = useCallback(
    (id: string) => {
      if (isSending) return;
      setState((prev) => ({ ...prev, sessionId: id }));
      setDrawerOpen(false);
    },
    [isSending],
  );

  const handleClearHistory = useCallback(() => {
    modal.confirm({
      title: "清空历史对话",
      content: "确定清空本浏览器中的历史对话吗？此操作不可撤销。",
      okText: "清空",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: () => {
        const conversation = createConversation();
        setState({ conversations: [conversation], sessionId: conversation.id });
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
      onClearHistory={handleClearHistory}
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
        <Layout.Sider width={288} className="app-sider" theme="light">
          {sider}
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
      </Layout.Content>

      <RunFlowPanel
        open={flowOpen}
        turns={runFlowTurns}
        onClose={() => setFlowOpen(false)}
      />
    </Layout>
  );
}
