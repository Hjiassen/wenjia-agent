import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Layout, App as AntdApp, Button, Drawer, Grid, Tooltip } from "antd";
import { MenuUnfoldOutlined, PlusOutlined } from "@ant-design/icons";
import { ChatSider } from "./components/ChatSider";
import { ChatWindow } from "./components/ChatWindow";
import { RunFlowPanel, type RunFlowTurn } from "./components/RunFlowPanel";
import { StreamFlowError, useChatStream } from "./hooks/useChatStream";
import { usePwaInstall, type PwaInstallTarget } from "./hooks/usePwaInstall";
import {
  isPwaUpdateAvailable,
  PWA_UPDATE_AVAILABLE_EVENT,
  reloadForPwaUpdate,
} from "./lib/serviceWorker";
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
let mobileInstallSuggestionShownThisLoad = false;
const KEYBOARD_OPEN_THRESHOLD = 80;
const SUGGESTION_TIMEOUT_MS = 20_000;

function installGuideFor(target: PwaInstallTarget): {
  title: string;
  steps: string[];
  note: string;
} {
  switch (target) {
    case "inAppBrowser":
      return {
        title: "先用系统浏览器打开",
        steps: ["点击右上角菜单", "选择在浏览器打开", "打开后再点顶部安装"],
        note: "微信、QQ、抖音等内置浏览器通常不能直接安装 PWA。",
      };
    case "ios":
      return {
        title: "添加到主屏幕",
        steps: ["点击浏览器底部分享按钮", "选择添加到主屏幕", "确认名称后点击添加"],
        note: "iPhone 和 iPad 不会弹出自动安装框，需要从分享菜单添加。",
      };
    case "android":
      return {
        title: "安装到手机桌面",
        steps: ["点击浏览器右上角菜单", "选择安装应用或添加到主屏幕", "确认安装"],
        note: "Chrome、Edge、三星浏览器一般会在菜单里提供安装入口。",
      };
    case "mobile":
      return {
        title: "添加到手机桌面",
        steps: ["打开浏览器菜单或分享菜单", "选择添加到主屏幕", "确认添加"],
        note: "不同手机浏览器入口名称会略有差异。",
      };
    case "native":
    case "desktop":
      return {
        title: "安装问甲",
        steps: ["打开浏览器地址栏或菜单", "选择安装应用", "确认安装"],
        note: "如果没有安装入口，请确认当前页面使用 HTTPS 打开。",
      };
  }
}

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
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), SUGGESTION_TIMEOUT_MS);
  try {
    const response = await fetch("/api/chat/suggestions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
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
  } catch {
    return [];
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function initialState(): { conversations: Conversation[]; sessionId: string } {
  const conversations = loadConversations();
  const stored = loadActiveSessionId();

  if (stored && conversations.some((conversation) => conversation.id === stored)) {
    return { conversations, sessionId: stored };
  }
  return { conversations, sessionId: stored ?? createSessionId() };
}

function previousUserPrompt(messages: ChatMessage[], assistantIndex: number): string {
  for (let index = assistantIndex - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role === "user") {
      return message.body;
    }
  }
  return "";
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
  const { canInstall, installTarget, promptInstall } = usePwaInstall();
  const { modal } = AntdApp.useApp();
  const installActionRef = useRef<() => Promise<void> | void>(() => undefined);
  const suggestionRequestsRef = useRef<Set<string>>(new Set());
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
    const root = document.documentElement;
    if (!isMobile) {
      root.style.removeProperty("--layout-viewport-height");
      root.style.removeProperty("--visual-viewport-height");
      root.style.removeProperty("--keyboard-inset");
      root.removeAttribute("data-keyboard-open");
      return;
    }

    const viewport = window.visualViewport;
    let frameId = 0;
    let layoutHeight = Math.max(
      window.innerHeight,
      root.clientHeight,
      viewport ? viewport.height + viewport.offsetTop : 0,
    );

    const syncViewport = () => {
      frameId = 0;
      const visualHeight = viewport?.height ?? window.innerHeight;
      const visualTop = viewport?.offsetTop ?? 0;
      const visibleBottom = visualTop + visualHeight;
      const currentLayoutHeight = Math.max(window.innerHeight, root.clientHeight, visibleBottom);
      const estimatedKeyboardInset = Math.max(0, layoutHeight - visibleBottom);

      if (estimatedKeyboardInset <= KEYBOARD_OPEN_THRESHOLD) {
        layoutHeight = currentLayoutHeight;
      }

      const keyboardInset = Math.max(0, layoutHeight - visibleBottom);
      const keyboardOpen = keyboardInset > KEYBOARD_OPEN_THRESHOLD;

      root.style.setProperty("--layout-viewport-height", `${layoutHeight}px`);
      root.style.setProperty("--visual-viewport-height", `${visualHeight}px`);
      root.style.setProperty("--keyboard-inset", `${keyboardOpen ? keyboardInset : 0}px`);
      if (keyboardOpen) {
        root.setAttribute("data-keyboard-open", "true");
      } else {
        root.removeAttribute("data-keyboard-open");
      }
    };

    const scheduleSync = () => {
      if (frameId) {
        window.cancelAnimationFrame(frameId);
      }
      frameId = window.requestAnimationFrame(syncViewport);
    };

    const resetAndSync = () => {
      layoutHeight = Math.max(window.innerHeight, root.clientHeight);
      scheduleSync();
    };

    scheduleSync();
    window.addEventListener("resize", scheduleSync);
    window.addEventListener("orientationchange", resetAndSync);
    viewport?.addEventListener("resize", scheduleSync);
    viewport?.addEventListener("scroll", scheduleSync);

    return () => {
      if (frameId) {
        window.cancelAnimationFrame(frameId);
      }
      window.removeEventListener("resize", scheduleSync);
      window.removeEventListener("orientationchange", resetAndSync);
      viewport?.removeEventListener("resize", scheduleSync);
      viewport?.removeEventListener("scroll", scheduleSync);
      root.style.removeProperty("--layout-viewport-height");
      root.style.removeProperty("--visual-viewport-height");
      root.style.removeProperty("--keyboard-inset");
      root.removeAttribute("data-keyboard-open");
    };
  }, [isMobile]);

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

  useEffect(() => {
    let shown = false;
    const handleUpdateAvailable = () => {
      if (shown) {
        return;
      }
      shown = true;
      modal.confirm({
        title: "发现新版本",
        okText: "立即刷新",
        cancelText: "稍后",
        width: 360,
        content: (
          <div className="pwa-update-notice">
            <p>已发布新的界面和功能，本地安装的 App 需要刷新后才会切换到最新版。</p>
            <p>刷新只会重新加载页面，不会清除本机保存的对话记录。</p>
          </div>
        ),
        onOk: () => void reloadForPwaUpdate(),
      });
    };

    window.addEventListener(PWA_UPDATE_AVAILABLE_EVENT, handleUpdateAvailable);
    if (isPwaUpdateAvailable()) {
      handleUpdateAvailable();
    }
    return () => {
      window.removeEventListener(PWA_UPDATE_AVAILABLE_EVENT, handleUpdateAvailable);
    };
  }, [modal]);

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

  useEffect(() => {
    const conversation = conversations.find((item) => item.id === sessionId);
    if (!conversation) {
      return;
    }

    for (let index = conversation.messages.length - 1; index >= 0; index -= 1) {
      const message = conversation.messages[index];
      if (message.role !== "assistant") {
        continue;
      }
      if (
        message.type === "error" ||
        !message.body.trim() ||
        Array.isArray(message.suggestions) ||
        message.suggestionsLoading
      ) {
        return;
      }

      const userMessage = previousUserPrompt(conversation.messages, index);
      if (!userMessage) {
        return;
      }

      const requestKey = `${conversation.id}:${message.createdAt}`;
      if (suggestionRequestsRef.current.has(requestKey)) {
        return;
      }

      suggestionRequestsRef.current.add(requestKey);
      updateMessage(conversation.id, message.createdAt, { suggestionsLoading: true });
      void fetchSuggestedQuestions(conversation.id, userMessage, message.body)
        .then((suggestions) =>
          updateMessage(conversation.id, message.createdAt, {
            suggestions,
            suggestionsLoading: false,
          }),
        )
        .finally(() => {
          suggestionRequestsRef.current.delete(requestKey);
        });
      return;
    }
  }, [conversations, sessionId, updateMessage]);

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

  const showInstallGuide = useCallback((target: PwaInstallTarget) => {
    const guide = installGuideFor(target);
    modal.info({
      title: guide.title,
      okText: "知道了",
      width: 360,
      content: (
        <div className="pwa-install-guide">
          <ol>
            {guide.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <p>{guide.note}</p>
        </div>
      ),
    });
  }, [modal]);

  const handleInstall = useCallback(async () => {
    const result = await promptInstall();
    if (result !== "unavailable") {
      return;
    }

    showInstallGuide(installTarget);
  }, [installTarget, promptInstall, showInstallGuide]);

  useEffect(() => {
    installActionRef.current = handleInstall;
  }, [handleInstall]);

  useEffect(() => {
    if (!isMobile || !canInstall || mobileInstallSuggestionShownThisLoad) {
      return;
    }

    mobileInstallSuggestionShownThisLoad = true;
    const timer = window.setTimeout(() => {
      const nativeInstall = installTarget === "native";
      modal.confirm({
        title: "建议安装到手机桌面",
        okText: nativeInstall ? "立即安装" : "查看安装方法",
        cancelText: "先继续使用",
        width: 360,
        content: (
          <div className="pwa-install-suggestion">
            <p>这样使用会更接近一个独立 App：</p>
            <ul>
              <li>下次可以从桌面直接打开，不用再找浏览器标签页。</li>
              <li>手机浏览器地址栏占用更少，聊天和运行流视野更完整。</li>
              <li>刷新或切回页面时体验更稳定，也更适合长期对话。</li>
            </ul>
            <p>已经安装到桌面后，这个提示就不会再出现。</p>
          </div>
        ),
        onOk: () => installActionRef.current(),
      });
    }, 700);

    return () => window.clearTimeout(timer);
  }, [canInstall, installTarget, isMobile, modal]);

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
          canInstall={canInstall}
          onDraftChange={setDraft}
          onSelectedProfileIdsChange={setSelectedProfileIds}
          onProfilesChanged={() => loadProfiles(sessionId)}
          onSubmit={handleSubmit}
          onCancel={cancel}
          onOpenSider={() => setDrawerOpen(true)}
          onOpenFlow={() => setFlowOpen(true)}
          onInstall={handleInstall}
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
