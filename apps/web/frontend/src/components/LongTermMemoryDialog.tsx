import { useCallback, useEffect, useState } from "react";
import { App as AntdApp, Button, Empty, Modal, Popconfirm, Spin, Tag } from "antd";
import { DeleteOutlined, ReloadOutlined } from "@ant-design/icons";
import type { LongTermMemory } from "../types";
import { getClientId } from "../lib/storage";

const MEMORY_KIND_LABELS: Record<string, string> = {
  profile: "人物档案",
  note: "记录",
};

interface LongTermMemoryDialogProps {
  open: boolean;
  onClose: () => void;
}

function formatMemoryTime(value?: string | null): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function LongTermMemoryDialog({ open, onClose }: LongTermMemoryDialogProps) {
  const { message } = AntdApp.useApp();
  const [memories, setMemories] = useState<LongTermMemory[]>([]);
  const [loading, setLoading] = useState(false);
  const [deletingMemoryId, setDeletingMemoryId] = useState<number | null>(null);

  const loadMemories = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/memories?client_id=${encodeURIComponent(getClientId())}`,
      );
      if (!response.ok) {
        throw new Error("长期记忆加载失败");
      }
      const payload = await response.json().catch(() => null);
      setMemories(Array.isArray(payload?.memories) ? payload.memories : []);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "长期记忆加载失败");
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    if (open) {
      void loadMemories();
    }
  }, [loadMemories, open]);

  const handleDeleteMemory = async (memoryId: number) => {
    setDeletingMemoryId(memoryId);
    try {
      const response = await fetch(
        `/api/memories/${memoryId}?client_id=${encodeURIComponent(getClientId())}`,
        { method: "DELETE" },
      );
      if (!response.ok) {
        throw new Error("长期记忆删除失败");
      }
      setMemories((current) => current.filter((item) => item.id !== memoryId));
      message.success("长期记忆已删除");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "长期记忆删除失败");
    } finally {
      setDeletingMemoryId(null);
    }
  };

  return (
    <Modal
      title="长期记忆"
      open={open}
      width={640}
      className="profile-modal memory-modal"
      onCancel={onClose}
      footer={[
        <Button
          key="refresh"
          icon={<ReloadOutlined />}
          loading={loading}
          onClick={() => void loadMemories()}
        >
          刷新
        </Button>,
        <Button key="close" type="primary" onClick={onClose}>
          关闭
        </Button>,
      ]}
    >
      <div className="memory-modal-body">
        {loading ? (
          <div className="memory-list-state">
            <Spin size="small" />
            <span>加载中</span>
          </div>
        ) : memories.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无长期记忆"
            className="profile-empty memory-empty"
          />
        ) : (
          <div className="memory-list">
            {memories.map((memory) => {
              const timeText = formatMemoryTime(memory.updated_at || memory.created_at);
              return (
                <article key={memory.id} className="memory-item">
                  <div className="memory-item-main">
                    <div className="memory-item-title">
                      <span>{memory.title}</span>
                      <Tag className="memory-kind-tag">
                        {MEMORY_KIND_LABELS[memory.kind] ?? memory.kind}
                      </Tag>
                    </div>
                    <p>{memory.content}</p>
                    {timeText ? <time>{timeText}</time> : null}
                  </div>
                  <Popconfirm
                    title="删除这条长期记忆？"
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => handleDeleteMemory(memory.id)}
                  >
                    <Button
                      danger
                      type="text"
                      size="small"
                      icon={<DeleteOutlined />}
                      loading={deletingMemoryId === memory.id}
                      aria-label={`删除${memory.title}`}
                      className="memory-delete"
                    />
                  </Popconfirm>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </Modal>
  );
}
