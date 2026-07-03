import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bubble, Prompts, Sender, Welcome } from "@ant-design/x";
import type { BubbleProps } from "@ant-design/x";
import { Badge, Button, Skeleton, Tag } from "antd";
import {
  DownloadOutlined,
  IdcardOutlined,
  MenuOutlined,
  NodeIndexOutlined,
} from "@ant-design/icons";
import type { AttachedProfile, ChatMessage, FlowEvent, Profile } from "../types";
import { renderMarkdown } from "../lib/markdown";
import { RECOMMENDED_PROMPTS } from "../lib/prompts";
import { ProfilePanel } from "./ProfilePanel";

interface BubbleListRef {
  nativeElement: HTMLDivElement;
  scrollTo: (info: {
    offset?: number;
    key?: string | number;
    behavior?: ScrollBehavior;
    block?: ScrollLogicalPosition;
  }) => void;
}

interface PendingState {
  active: boolean;
  body: string;
  status: string;
  events: FlowEvent[];
  error: boolean;
}

interface ChatWindowProps {
  messages: ChatMessage[];
  pending: PendingState;
  draft: string;
  isSending: boolean;
  isMobile: boolean;
  flowTurnCount: number;
  sessionId: string;
  profiles: Profile[];
  selectedProfileIds: number[];
  canInstall: boolean;
  onDraftChange: (value: string) => void;
  onSelectedProfileIdsChange: (ids: number[]) => void;
  onProfilesChanged: () => void;
  onSubmit: (message: string, attachedProfiles: Profile[]) => void;
  onCancel: () => void;
  onOpenSider: () => void;
  onOpenFlow: () => void;
  onInstall: () => void | Promise<void>;
}

const MAX_LEN = 4000;
const LIVE_MESSAGE_KEY = "live";

const roles: Record<string, Partial<BubbleProps>> = {
  user: {
    placement: "end",
    variant: "filled",
  },
  assistant: {
    placement: "start",
    variant: "outlined",
  },
};

function markdownRender(content: string, className = "") {
  const classes = ["markdown-body", className].filter(Boolean).join(" ");
  return (
    <div
      className={classes}
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  );
}

function userMessageRender(content: string, attachedProfiles?: AttachedProfile[]) {
  return (
    <div className="user-message-with-context">
      <div className="user-message-text">{content}</div>
      {attachedProfiles && attachedProfiles.length > 0 && (
        <div className="bubble-profile-strip">
          {attachedProfiles.map((profile) => (
            <span key={profile.id} className="bubble-profile-chip">
              {profile.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function suggestionsLoadingRender() {
  return (
    <div className="message-suggestions is-loading">
      <div className="message-suggestions-title">你可以继续问</div>
      <div className="message-suggestions-loading-list">
        {[0, 1, 2].map((item) => (
          <Skeleton.Button key={item} active block size="small" />
        ))}
      </div>
    </div>
  );
}

function assistantMessageRender(
  content: string,
  message: ChatMessage,
  isMobile: boolean,
  onSuggestionClick: (prompt: string) => void,
) {
  const suggestions = message.suggestions ?? [];
  const showSuggestions = suggestions.length > 0;

  return (
    <div className="assistant-message-content">
      {markdownRender(content)}
      {message.suggestionsLoading ? suggestionsLoadingRender() : null}
      {!message.suggestionsLoading && showSuggestions ? (
        <Prompts
          className="message-suggestions"
          title="你可以继续问"
          wrap={!isMobile}
          vertical={isMobile}
          items={suggestions.map((suggestion) => ({
            key: suggestion.prompt,
            label: suggestion.prompt,
          }))}
          onItemClick={(info) => onSuggestionClick(String(info.data.key))}
        />
      ) : null}
    </div>
  );
}

function pendingAssistantRender(pending: PendingState) {
  const status = pending.status || "正在整理关键内容";
  const loadingBlock = (live = false) => (
    <div
      className={`assistant-waiting${pending.error ? " is-error" : ""}${
        live ? " is-live" : ""
      }`}
    >
      <div className="assistant-waiting-head">
        <span className="analysis-loader" aria-hidden="true">
          <span className="analysis-loader-core" />
        </span>
        <span className="assistant-waiting-copy">
          <span className="assistant-waiting-title">
            {pending.error ? "处理遇到问题" : "问甲正在推演"}
          </span>
          <span className="assistant-waiting-status">{status}</span>
        </span>
      </div>
      <span className="analysis-progress" aria-hidden="true">
        <span />
      </span>
    </div>
  );
  const hasContent = pending.body.trim().length > 0;
  if (hasContent) {
    return (
      <div className="assistant-message-content assistant-live-content" aria-live="polite">
        {loadingBlock(true)}
        {markdownRender(pending.body, pending.error ? "is-live-error" : "")}
      </div>
    );
  }

  return (
    <div aria-live="polite">
      {loadingBlock()}
    </div>
  );
}

function pendingFromStreamingMessage(message: ChatMessage): PendingState {
  return {
    active: true,
    body: message.body,
    status: message.streamingStatus || "正在整理关键内容",
    events: message.flow,
    error: Boolean(message.streamingError),
  };
}

function messageKey(index: number): string {
  return `message-${index}`;
}

function isScrollKey(key: string): boolean {
  return [
    "ArrowUp",
    "ArrowDown",
    "PageUp",
    "PageDown",
    "Home",
    "End",
    " ",
  ].includes(key);
}

export function ChatWindow({
  messages,
  pending,
  draft,
  isSending,
  isMobile,
  flowTurnCount,
  sessionId,
  profiles,
  selectedProfileIds,
  canInstall,
  onDraftChange,
  onSelectedProfileIdsChange,
  onProfilesChanged,
  onSubmit,
  onCancel,
  onOpenSider,
  onOpenFlow,
  onInstall,
}: ChatWindowProps) {
  const [profilePickerOpen, setProfilePickerOpen] = useState(false);
  const composerRef = useRef<HTMLDivElement | null>(null);
  const bubbleListRef = useRef<BubbleListRef | null>(null);
  const userScrollLockedRef = useRef(false);
  const pendingAutoScrolledUserRef = useRef<string | null>(null);
  const previousSessionRef = useRef(sessionId);
  const previousLastUserKeyRef = useRef<string | null>(null);
  const selectedProfiles = useMemo(() => {
    const selected = new Set(selectedProfileIds);
    return profiles.filter((profile) => selected.has(profile.id));
  }, [profiles, selectedProfileIds]);
  const profileButtonText =
    selectedProfiles.length === 0
      ? "档案"
      : selectedProfiles.length === 1
        ? selectedProfiles[0].name
        : `${selectedProfiles[0].name}等${selectedProfiles.length}人`;

  const handleSubmit = useCallback((value: string) => {
    const text = value.trim();
    if (!text || isSending) {
      return;
    }
    setProfilePickerOpen(false);
    onSubmit(text, selectedProfiles);
  }, [isSending, onSubmit, selectedProfiles]);

  const items = useMemo(() => {
    let hasStreamingMessage = false;
    const list = messages.map((message, index) => {
      const isAssistant = message.role === "assistant";
      const isError = message.type === "error";
      const item: BubbleProps & { key: string | number } = {
        key: messageKey(index),
        role: message.role,
        content: message.body || message.streamingStatus || "正在思考",
      };
      if (isAssistant && message.streaming) {
        hasStreamingMessage = true;
        item.messageRender = () => pendingAssistantRender(pendingFromStreamingMessage(message));
      } else if (isAssistant && !isError) {
        item.messageRender = (text: string) =>
          assistantMessageRender(text, message, isMobile, handleSubmit);
      }
      if (!isAssistant && message.profileContext?.length) {
        item.messageRender = (text: string) => userMessageRender(text, message.profileContext);
      }
      if (isError) {
        item.messageRender = (text: string) => <div className="bubble-error">{text}</div>;
      }
      return item;
    });

    const lastMessage = messages.at(-1);
    if (pending.active && !hasStreamingMessage && lastMessage?.role !== "assistant") {
      list.push({
        key: LIVE_MESSAGE_KEY,
        role: "assistant",
        content: pending.body || pending.status || "正在思考",
        loading: false,
        messageRender: () => pendingAssistantRender(pending),
      });
    }
    return list;
  }, [messages, pending, isMobile, handleSubmit]);

  const showWelcome = messages.length === 0 && !pending.active;
  const lastUserKey = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].role === "user") {
        return messageKey(index);
      }
    }
    return null;
  }, [messages]);

  const scrollLastUserToTop = useCallback(
    (key: string, behavior: ScrollBehavior = "auto") => {
      if (!bubbleListRef.current) {
        return;
      }
      bubbleListRef.current.scrollTo({ key, block: "start", behavior });
    },
    [],
  );

  const lockAutoScroll = useCallback(() => {
    userScrollLockedRef.current = true;
  }, []);

  useEffect(() => {
    if (!lastUserKey || showWelcome) {
      return;
    }

    const sessionChanged = previousSessionRef.current !== sessionId;
    const userChanged = previousLastUserKeyRef.current !== lastUserKey;
    if (!sessionChanged && !userChanged) {
      return;
    }

    previousSessionRef.current = sessionId;
    previousLastUserKeyRef.current = lastUserKey;
    userScrollLockedRef.current = false;
    pendingAutoScrolledUserRef.current = null;
    const frame = window.requestAnimationFrame(() => {
      if (!userScrollLockedRef.current) {
        scrollLastUserToTop(lastUserKey);
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [lastUserKey, scrollLastUserToTop, sessionId, showWelcome]);

  useEffect(() => {
    if (!pending.active) {
      pendingAutoScrolledUserRef.current = null;
      return;
    }
    if (
      !lastUserKey ||
      userScrollLockedRef.current ||
      pendingAutoScrolledUserRef.current === lastUserKey
    ) {
      return;
    }

    pendingAutoScrolledUserRef.current = lastUserKey;

    const frame = window.requestAnimationFrame(() => {
      if (!userScrollLockedRef.current) {
        scrollLastUserToTop(lastUserKey);
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [lastUserKey, pending.active, scrollLastUserToTop]);

  useEffect(() => {
    if (!profilePickerOpen) {
      return;
    }
    const closeOnOutside = (event: PointerEvent) => {
      if (!composerRef.current?.contains(event.target as Node)) {
        setProfilePickerOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setProfilePickerOpen(false);
      }
    };
    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [profilePickerOpen]);

  const removeSelectedProfile = (profileId: number) => {
    onSelectedProfileIdsChange(selectedProfileIds.filter((id) => id !== profileId));
  };

  const selectedFooter =
    selectedProfiles.length > 0 ? (
      <div className="composer-profile-footer">
        <span className="composer-profile-footer-label">已附加</span>
        <div className="composer-profile-tags">
          {selectedProfiles.map((profile) => (
            <Tag
              key={profile.id}
              closable
              className="composer-profile-tag"
              onClose={(event) => {
                event.preventDefault();
                removeSelectedProfile(profile.id);
              }}
            >
              {profile.name}
            </Tag>
          ))}
        </div>
      </div>
    ) : null;

  const profilePicker = (
    <ProfilePanel
      sessionId={sessionId}
      profiles={profiles}
      selectedProfileIds={selectedProfileIds}
      onSelectedProfileIdsChange={onSelectedProfileIdsChange}
      onChanged={onProfilesChanged}
    />
  );

  return (
    <div className="chat-window">
      <header className="chat-header">
        <div className="chat-header-left">
          {isMobile && (
            <Button
              type="text"
              aria-label="打开会话菜单"
              icon={<MenuOutlined />}
              onClick={onOpenSider}
            />
          )}
        </div>
        <span className="chat-header-title">命理推演</span>
        <div className="chat-header-actions">
          {canInstall ? (
            <Button
              type="text"
              icon={<DownloadOutlined />}
              aria-label="安装到桌面"
              title="安装到桌面"
              className="pwa-install-button"
              onClick={onInstall}
            >
              安装
            </Button>
          ) : null}
          <Badge dot={isSending} color="#0f766e" offset={[-2, 4]}>
            <Button
              icon={<NodeIndexOutlined />}
              onClick={onOpenFlow}
              disabled={flowTurnCount === 0 && !isSending}
            >
              运行流{flowTurnCount > 0 ? ` (${flowTurnCount})` : ""}
            </Button>
          </Badge>
        </div>
      </header>

      <div
        className="chat-scroll"
        onWheelCapture={lockAutoScroll}
        onTouchStartCapture={lockAutoScroll}
        onTouchMoveCapture={lockAutoScroll}
        onPointerDownCapture={lockAutoScroll}
      >
        <div className="chat-column">
          {showWelcome ? (
            <div className="chat-welcome">
              <Welcome
                variant="borderless"
                icon="🧭"
                title="问甲 · 命理 Agent"
                description="确定性排盘加多智能体分析。先补全出生信息，我会带你完成排盘、命格、关系与起名推演。"
              />
              <Prompts
                className="welcome-prompts"
                title="从这里开始"
                wrap={!isMobile}
                vertical={isMobile}
                items={RECOMMENDED_PROMPTS.map((prompt) => ({
                  key: prompt.prompt,
                  label: prompt.label,
                  description: prompt.description,
                }))}
                onItemClick={(info) => handleSubmit(String(info.data.key))}
              />
            </div>
          ) : (
            <Bubble.List
              ref={bubbleListRef}
              roles={roles}
              items={items}
              autoScroll={false}
              onWheel={lockAutoScroll}
              onTouchStart={lockAutoScroll}
              onPointerDown={lockAutoScroll}
              onKeyDown={(event) => {
                if (isScrollKey(event.key)) {
                  lockAutoScroll();
                }
              }}
            />
          )}
        </div>
      </div>

      <div className="chat-composer">
        <div className="chat-column composer-column" ref={composerRef}>
          <div
            className={`composer-profile-popover${profilePickerOpen ? " is-open" : ""}`}
            role="dialog"
            aria-label="人物档案"
            aria-hidden={!profilePickerOpen}
          >
            {profilePicker}
          </div>
          <Sender
            rootClassName="chat-sender"
            value={draft}
            loading={isSending}
            placeholder={isMobile ? "输入你的问题" : "输入你的问题；Enter 发送，Shift + Enter 换行"}
            prefix={
              <Button
                type="text"
                title="选择人物档案"
                aria-label="选择人物档案"
                aria-expanded={profilePickerOpen}
                icon={<IdcardOutlined />}
                className={`composer-profile-button${
                  selectedProfiles.length > 0 ? " is-active" : ""
                }`}
                onClick={() => setProfilePickerOpen((open) => !open)}
              >
                <span className="composer-profile-button-text">{profileButtonText}</span>
              </Button>
            }
            footer={selectedFooter}
            onChange={(value) => onDraftChange(value.slice(0, MAX_LEN))}
            onSubmit={handleSubmit}
            onCancel={onCancel}
          />
        </div>
      </div>
    </div>
  );
}
