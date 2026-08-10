import { useCallback, useEffect, useState } from "react";
import { App as AntdApp, Button, Empty, Form, Input, Modal, Popconfirm, Select, Spin, Tag } from "antd";
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import type { LongTermMemory } from "../types";

const MEMORY_KIND_LABELS: Record<string, string> = {
  preference: "偏好",
  goal: "目标",
  context: "背景",
  correction: "纠正",
  note: "记录",
};
const KIND_OPTIONS = Object.entries(MEMORY_KIND_LABELS).map(([value, label]) => ({ value, label }));
interface Props { open: boolean; onClose: () => void; }
interface MemoryForm { kind: string; key: string; title: string; content: string; }

function formatMemoryTime(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function LongTermMemoryDialog({ open, onClose }: Props) {
  const { message } = AntdApp.useApp();
  const [memories, setMemories] = useState<LongTermMemory[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<LongTermMemory | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form] = Form.useForm<MemoryForm>();

  const loadMemories = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/memories", { credentials: "include" });
      if (!response.ok) throw new Error("长期记忆加载失败");
      const payload = await response.json().catch(() => null);
      setMemories(Array.isArray(payload?.memories) ? payload.memories : []);
    } catch (error) { message.error(error instanceof Error ? error.message : "长期记忆加载失败"); }
    finally { setLoading(false); }
  }, [message]);

  useEffect(() => { if (open) void loadMemories(); }, [loadMemories, open]);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ kind: "note" }); setFormOpen(true); };
  const openEdit = (memory: LongTermMemory) => { setEditing(memory); form.setFieldsValue({ kind: memory.kind, key: memory.key, title: memory.title, content: memory.content }); setFormOpen(true); };

  const saveMemory = async (values: MemoryForm) => {
    setSaving(true);
    try {
      const response = await fetch(`/api/memories${editing ? `/${editing.id}` : ""}`, {
        method: editing ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify(values),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail || "长期记忆保存失败");
      setFormOpen(false); message.success("长期记忆已保存"); void loadMemories();
    } catch (error) { message.error(error instanceof Error ? error.message : "长期记忆保存失败"); }
    finally { setSaving(false); }
  };

  const deleteMemory = async (id: number) => {
    try {
      const response = await fetch(`/api/memories/${id}`, { method: "DELETE", credentials: "include" });
      if (!response.ok) throw new Error("长期记忆删除失败");
      setMemories((items) => items.filter((item) => item.id !== id)); message.success("长期记忆已删除");
    } catch (error) { message.error(error instanceof Error ? error.message : "长期记忆删除失败"); }
  };

  return <>
    <Modal title="长期记忆" open={open} width={680} className="profile-modal memory-modal" onCancel={onClose}
      footer={[<Button key="refresh" icon={<ReloadOutlined />} loading={loading} onClick={() => void loadMemories()}>刷新</Button>, <Button key="close" type="primary" onClick={onClose}>关闭</Button>]}>
      <div className="memory-modal-body">
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ marginBottom: 12 }}>新增记忆</Button>
        {loading ? <div className="memory-list-state"><Spin size="small" /><span>加载中</span></div> : memories.length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无长期记忆" className="profile-empty memory-empty" /> : <div className="memory-list">
          {memories.map((memory) => <article key={memory.id} className="memory-item"><div className="memory-item-main"><div className="memory-item-title"><span>{memory.title}</span><Tag className="memory-kind-tag">{MEMORY_KIND_LABELS[memory.kind] ?? memory.kind}</Tag></div><p>{memory.content}</p>{formatMemoryTime(memory.updated_at || memory.created_at) ? <time>{formatMemoryTime(memory.updated_at || memory.created_at)}</time> : null}</div><div><Button type="text" size="small" icon={<EditOutlined />} aria-label={`编辑${memory.title}`} onClick={() => openEdit(memory)} /><Popconfirm title="删除这条长期记忆？" okText="删除" cancelText="取消" okButtonProps={{ danger: true }} onConfirm={() => void deleteMemory(memory.id)}><Button danger type="text" size="small" icon={<DeleteOutlined />} aria-label={`删除${memory.title}`} /></Popconfirm></div></article>)}
        </div>}
      </div>
    </Modal>
    <Modal title={editing ? "编辑长期记忆" : "新增长期记忆"} open={formOpen} onCancel={() => setFormOpen(false)} okText="保存" cancelText="取消" confirmLoading={saving} onOk={() => form.submit()} destroyOnClose>
      <Form form={form} layout="vertical" onFinish={saveMemory}><Form.Item name="kind" label="类型" rules={[{ required: true }]}><Select options={KIND_OPTIONS} /></Form.Item><Form.Item name="key" label="标识" rules={[{ required: true, message: "请输入标识" }]}><Input maxLength={160} /></Form.Item><Form.Item name="title" label="标题" rules={[{ required: true, message: "请输入标题" }]}><Input maxLength={120} /></Form.Item><Form.Item name="content" label="内容" rules={[{ required: true, message: "请输入内容" }]}><Input.TextArea rows={4} maxLength={4000} /></Form.Item></Form>
    </Modal>
  </>;
}
