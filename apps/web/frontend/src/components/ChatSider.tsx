import { Conversations } from "@ant-design/x";
import { Badge, Button, Tooltip, Typography } from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import type { Conversation } from "../types";
import { conversationTitle } from "../lib/storage";

type HealthStatus = "checking" | "ready" | "error";

interface ChatSiderProps {
  sessionId: string;
  conversations: Conversation[];
  health: HealthStatus;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
  onClearHistory: () => void;
}

const HEALTH_META: Record<HealthStatus, { status: "processing" | "success" | "error"; text: string }> = {
  checking: { status: "processing", text: "连接中" },
  ready: { status: "success", text: "就绪" },
  error: { status: "error", text: "后端离线" },
};

export function ChatSider({
  sessionId,
  conversations,
  health,
  onNewSession,
  onSelectSession,
  onClearHistory,
}: ChatSiderProps) {
  const items = conversations.map((conversation) => ({
    key: conversation.id,
    label: conversationTitle(conversation),
    timestamp: new Date(conversation.updatedAt).getTime(),
  }));

  const meta = HEALTH_META[health];

  return (
    <div className="chat-sider">
      <div className="sider-brand">
        <span className="sider-logo">问甲</span>
        <Typography.Text type="secondary" className="sider-tagline">
          命理 Agent 工作台
        </Typography.Text>
      </div>

      <div className="sider-actions">
        <Button type="primary" icon={<PlusOutlined />} block onClick={onNewSession}>
          新的对话
        </Button>
      </div>

      <div className="sider-section sider-conversations">
        <Conversations
          items={items}
          activeKey={sessionId}
          onActiveChange={onSelectSession}
        />
      </div>

      <div className="sider-footer">
        <Badge status={meta.status} text={meta.text} />
        <Tooltip title="清空本浏览器历史对话">
          <Button size="small" type="text" icon={<DeleteOutlined />} onClick={onClearHistory}>
            清空
          </Button>
        </Tooltip>
      </div>
    </div>
  );
}
