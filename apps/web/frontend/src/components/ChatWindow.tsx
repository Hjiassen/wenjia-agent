import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bubble, Prompts, Sender, Welcome } from "@ant-design/x";
import type { BubbleProps } from "@ant-design/x";
import { Avatar, Badge, Button, Skeleton, Tag } from "antd";
import {
  IdcardOutlined,
  MenuOutlined,
  NodeIndexOutlined,
  RobotOutlined,
  UserOutlined,
} from "@ant-design/icons";
import type { AttachedProfile, ChatMessage, FlowEvent, Profile } from "../types";
import { renderMarkdown } from "../lib/markdown";
import { RECOMMENDED_PROMPTS } from "../lib/prompts";
import { ProfilePanel } from "./ProfilePanel";

interface PendingState {
  active: boolean;
  body: string;
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
  onDraftChange: (value: string) => void;
  onSelectedProfileIdsChange: (ids: number[]) => void;
  onProfilesChanged: () => void;
  onSubmit: (message: string, attachedProfiles: Profile[]) => void;
  onCancel: () => void;
  onOpenSider: () => void;
  onOpenFlow: () => void;
}

const MAX_LEN = 4000;

const roles: Record<string, Partial<BubbleProps>> = {
  user: {
    placement: "end",
    variant: "filled",
    avatar: <Avatar icon={<UserOutlined />} style={{ background: "#0f766e" }} />,
  },
  assistant: {
    placement: "start",
    variant: "outlined",
    avatar: <Avatar icon={<RobotOutlined />} style={{ background: "#115e59" }} />,
  },
};

function markdownRender(content: string) {
  return (
    <div
      className="markdown-body"
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
  onDraftChange,
  onSelectedProfileIdsChange,
  onProfilesChanged,
  onSubmit,
  onCancel,
  onOpenSider,
  onOpenFlow,
}: ChatWindowProps) {
  const [profilePickerOpen, setProfilePickerOpen] = useState(false);
  const composerRef = useRef<HTMLDivElement | null>(null);
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
    const list = messages.map((message, index) => {
      const isAssistant = message.role === "assistant";
      const isError = message.type === "error";
      const item: BubbleProps & { key: string | number } = {
        key: index,
        role: message.role,
        content: message.body,
      };
      if (isAssistant && !isError) {
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

    if (pending.active) {
      list.push({
        key: "live",
        role: "assistant",
        content: pending.body || "正在推演…",
        loading: pending.events.length === 0,
      });
    }
    return list;
  }, [messages, pending, isMobile, handleSubmit]);

  const showWelcome = messages.length === 0 && !pending.active;

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

      <div className="chat-scroll">
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
            <Bubble.List roles={roles} items={items} autoScroll />
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
                className={`composer-profile-button${selectedProfiles.length > 0 ? " is-active" : ""}`}
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
