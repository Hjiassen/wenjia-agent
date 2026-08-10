import { useState } from "react";
import { App as AntdApp, Button, Form, Input, Modal, Segmented } from "antd";
import { LockOutlined, UserOutlined } from "@ant-design/icons";
import type { AuthUser } from "../types";

interface AuthDialogProps {
  open: boolean;
  onClose: () => void;
  onAuthenticated: (user: AuthUser) => void;
  required?: boolean;
}

export function AuthDialog({ open, onClose, onAuthenticated, required = false }: AuthDialogProps) {
  const { message } = AntdApp.useApp();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm<{ username: string; password: string; confirm_password?: string }>();

  const submit = async (values: { username: string; password: string; confirm_password?: string }) => {
    setLoading(true);
    try {
      const credentials = mode === "register"
        ? { username: values.username, password: values.password, confirm_password: values.confirm_password }
        : { username: values.username, password: values.password };
      const response = await fetch(`/api/auth/${mode === "login" ? "login" : "register"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(credentials),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail || "认证失败");
      onAuthenticated(payload.user as AuthUser);
      message.success(mode === "login" ? "登录成功" : "注册成功");
      onClose();
      form.resetFields();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "认证失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      title={null}
      width={420}
      destroyOnHidden
      centered
      closable={!required}
      maskClosable={!required}
      keyboard={!required}
      rootClassName="auth-modal-root"
      wrapClassName="auth-modal-wrap"
      className="auth-modal"
    >
      <header className="auth-dialog-head">
        <div className="auth-dialog-brand" aria-label="问甲">
          <span className="auth-dialog-mark">问</span>
          <span>问甲</span>
        </div>
        <h2>{mode === "login" ? "欢迎回来" : "创建你的账号"}</h2>
        <p>{mode === "login" ? "登录后继续上次的推演" : "注册后即可进入问甲工作台"}</p>
      </header>
      <Segmented
        block
        value={mode}
        options={[{ label: "登录", value: "login" }, { label: "注册", value: "register" }]}
        onChange={(value) => {
          setMode(value as "login" | "register");
          form.resetFields(["password", "confirm_password"]);
        }}
        className="auth-mode-switch"
      />
      <Form form={form} layout="vertical" onFinish={submit} className="auth-form" requiredMark={false}>
        <Form.Item name="username" label="用户名" rules={[{ required: true, min: 3, message: "请输入至少 3 个字符" }]}>
          <Input prefix={<UserOutlined />} autoComplete="username" maxLength={32} placeholder="输入用户名" size="large" />
        </Form.Item>
        <Form.Item
          name="password"
          label="密码"
          rules={[{ required: true, min: 8, message: "请输入至少 8 个字符" }]}
        >
          <Input.Password prefix={<LockOutlined />} autoComplete={mode === "login" ? "current-password" : "new-password"} maxLength={128} placeholder="至少 8 个字符" size="large" />
        </Form.Item>
        {mode === "register" && (
          <Form.Item
            name="confirm_password"
            label="确认密码"
            dependencies={["password"]}
            rules={[
              { required: true, message: "请再次输入密码" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("password") === value) return Promise.resolve();
                  return Promise.reject(new Error("两次输入的密码不一致"));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} autoComplete="new-password" maxLength={128} placeholder="再次输入密码" size="large" />
          </Form.Item>
        )}
        <Button type="primary" htmlType="submit" block loading={loading} size="large" className="auth-submit">
          {mode === "login" ? "登录" : "注册并登录"}
        </Button>
      </Form>
    </Modal>
  );
}
