import type { Conversation } from "../types";
import { conversationPreview, conversationTitle, formatTime } from "../lib/storage";

const FLOW_GUIDE = ["理解问题", "检查出生信息", "路由专门 Agent", "调用确定性工具", "整理回答"];

type HealthStatus = "checking" | "ready" | "error";

interface SidebarProps {
  sessionId: string;
  conversations: Conversation[];
  health: HealthStatus;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
  onClearHistory: () => void;
}

const HEALTH_TEXT: Record<HealthStatus, string> = {
  checking: "检测中",
  ready: "已连接",
  error: "不可用",
};

export function Sidebar({
  sessionId,
  conversations,
  health,
  onNewSession,
  onSelectSession,
  onClearHistory,
}: SidebarProps) {
  const sorted = [...conversations].sort(
    (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
  );

  return (
    <aside className="sidebar" aria-label="演示控制区">
      <header className="brand">
        <img src="/static/wenjia-mark.svg" alt="" className="brand-mark" />
        <div>
          <h1>问甲 Agent</h1>
          <p>八字智能体开源演示</p>
        </div>
      </header>

      <section className="panel session-panel">
        <div className="panel-heading">
          <h2>当前会话</h2>
          <button className="small-button" type="button" onClick={onNewSession}>
            新建
          </button>
        </div>
        <p className="session-id">{sessionId.replace("web:", "")}</p>
      </section>

      <section className="panel history-panel">
        <div className="panel-heading">
          <h2>历史记录</h2>
          <button className="text-button" type="button" onClick={onClearHistory}>
            清空
          </button>
        </div>
        <div className="history-list">
          {sorted.length ? (
            sorted.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                className={
                  conversation.id === sessionId ? "history-item active" : "history-item"
                }
                onClick={() => onSelectSession(conversation.id)}
              >
                <span className="history-title">{conversationTitle(conversation)}</span>
                <span className="history-meta">
                  {formatTime(conversation.updatedAt)} · {conversation.messages.length} 条
                </span>
                <span className="history-preview">{conversationPreview(conversation)}</span>
              </button>
            ))
          ) : (
            <p className="history-empty">暂无历史记录</p>
          )}
        </div>
      </section>

      <section className="panel flow-guide">
        <h2>推演流程</h2>
        <ol>
          {FLOW_GUIDE.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </section>

      <section className="panel status-panel">
        <h2>状态</h2>
        <p>
          <span className={`status-dot ${health === "checking" ? "" : health}`} />
          <span>{HEALTH_TEXT[health]}</span>
        </p>
      </section>
    </aside>
  );
}
