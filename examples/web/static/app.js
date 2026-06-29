const activeSessionKey = "wenjia-agent-web-active-session";
const legacySessionKey = "wenjia-agent-web-session";
const conversationsKey = "wenjia-agent-web-conversations";

const welcomeText =
  "你好，我是问甲 Agent。你可以先提交完整出生信息，也可以直接选择左侧推荐问题开始。涉及个人命盘、流年、关系或起名时，我会先确认出生信息是否完整。";

const messages = document.querySelector("#messages");
const chatForm = document.querySelector("#chatForm");
const messageInput = document.querySelector("#messageInput");
const sendButton = document.querySelector("#sendButton");
const sessionIdLabel = document.querySelector("#sessionId");
const newSessionButton = document.querySelector("#newSessionButton");
const clearHistoryButton = document.querySelector("#clearHistoryButton");
const historyList = document.querySelector("#historyList");
const statusDot = document.querySelector("#statusDot");
const statusText = document.querySelector("#statusText");
const promptButtons = document.querySelectorAll("[data-prompt]");

let conversations = loadConversations();
let sessionId = loadActiveSessionId();
let isSending = false;

function nowIso() {
  return new Date().toISOString();
}

function createSessionId() {
  return `web:${crypto.randomUUID()}`;
}

function loadConversations() {
  try {
    const parsed = JSON.parse(localStorage.getItem(conversationsKey) || "[]");
    if (Array.isArray(parsed)) {
      return parsed.filter((item) => item && item.id);
    }
  } catch {
    // Ignore broken localStorage data and start fresh.
  }
  return [];
}

function saveConversations() {
  localStorage.setItem(conversationsKey, JSON.stringify(conversations));
}

function loadActiveSessionId() {
  const stored = localStorage.getItem(activeSessionKey) || localStorage.getItem(legacySessionKey);
  if (stored && conversations.some((conversation) => conversation.id === stored)) {
    return stored;
  }

  if (stored) {
    const conversation = createConversation(stored);
    conversations.unshift(conversation);
    saveConversations();
    return conversation.id;
  }

  const conversation = createConversation();
  conversations.unshift(conversation);
  saveConversations();
  return conversation.id;
}

function createConversation(id = createSessionId()) {
  const createdAt = nowIso();
  return {
    id,
    title: "新的对话",
    createdAt,
    updatedAt: createdAt,
    messages: [],
  };
}

function getCurrentConversation() {
  let conversation = conversations.find((item) => item.id === sessionId);
  if (!conversation) {
    conversation = createConversation(sessionId);
    conversations.unshift(conversation);
    saveConversations();
  }
  return conversation;
}

function setActiveSession(id) {
  sessionId = id;
  localStorage.setItem(activeSessionKey, sessionId);
  localStorage.setItem(legacySessionKey, sessionId);
  updateSessionLabel();
  renderMessages();
  renderHistory();
}

function getConversationTitle(conversation) {
  if (conversation.title && conversation.title !== "新的对话") {
    return conversation.title;
  }

  const firstUserMessage = conversation.messages.find((message) => message.role === "user");
  if (!firstUserMessage) {
    return "新的对话";
  }

  const compact = firstUserMessage.body.replace(/\s+/g, " ").trim();
  return compact.length > 24 ? `${compact.slice(0, 24)}...` : compact;
}

function getConversationPreview(conversation) {
  const lastMessage = conversation.messages.at(-1);
  if (!lastMessage) {
    return "还没有消息";
  }
  const compact = lastMessage.body.replace(/\s+/g, " ").trim();
  return compact.length > 36 ? `${compact.slice(0, 36)}...` : compact;
}

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function updateSessionLabel() {
  sessionIdLabel.textContent = sessionId.replace("web:", "");
}

function appendMessage(role, body, type = "", flowSteps = []) {
  const article = document.createElement("article");
  article.className = `message ${role} ${type}`.trim();

  const roleNode = document.createElement("div");
  roleNode.className = "message-role";
  roleNode.textContent = role === "user" ? "你" : "问甲";

  const bodyNode = document.createElement("div");
  bodyNode.className = "message-body";
  bodyNode.textContent = body;

  article.append(roleNode);
  if (role === "assistant") {
    updateMessageFlow(article, flowSteps);
  }
  article.append(bodyNode);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function getFlowStepText(step) {
  const name = step.display_name || step.agent_label || step.tool || step.agent || "Agent";
  if (step.type === "run_start") {
    return step.message || "开始处理请求";
  }
  if (step.type === "agent_start") {
    return step.message || `${name}开始处理`;
  }
  if (step.type === "thinking") {
    return step.message || `${name}正在思考下一步`;
  }
  if (step.type === "handoff") {
    return step.message || "正在切换专门 Agent";
  }
  if (step.type === "tool_start") {
    return step.message || `正在执行${name}`;
  }
  if (step.type === "tool_done") {
    const duration = typeof step.duration === "number" ? ` · ${step.duration.toFixed(2)}s` : "";
    return `${step.message || `${name}${step.success === false ? "失败" : "完成"}`}${duration}`;
  }
  if (step.type === "generating") {
    return step.message || "正在整理最终回答";
  }
  if (step.type === "done") {
    return step.message || "推演完成";
  }
  if (step.type === "error") {
    return step.message || "请求失败";
  }
  return step.message || "处理中";
}

function getFlowSummary(steps) {
  if (!steps.length) {
    return "等待开始";
  }
  const toolDoneSteps = steps.filter((step) => step.type === "tool_done");
  const totalDuration = toolDoneSteps.reduce(
    (sum, step) => sum + (typeof step.duration === "number" ? step.duration : 0),
    0,
  );
  const lastStep = steps.at(-1);
  const toolText = `${toolDoneSteps.length} 个工具`;
  const durationText = totalDuration > 0 ? ` · ${totalDuration.toFixed(2)}s` : "";
  return `${toolText}${durationText} · ${getFlowStepText(lastStep)}`;
}

function createFlowBlock(steps) {
  const details = document.createElement("details");
  details.className = "flow-block";
  details.open = steps.some((step) => step.type === "error");

  const summary = document.createElement("summary");
  summary.textContent = `推演过程 · ${getFlowSummary(steps)}`;
  details.append(summary);

  const list = document.createElement("ol");
  list.className = "flow-steps";
  steps.forEach((step) => {
    const item = document.createElement("li");
    item.className = `flow-step ${step.type} ${step.success === false ? "failed" : ""}`.trim();

    const dot = document.createElement("span");
    dot.className = "flow-dot";

    const text = document.createElement("span");
    text.className = "flow-text";
    text.textContent = getFlowStepText(step);

    item.append(dot, text);
    list.append(item);
  });

  details.append(list);
  return details;
}

function updateMessageFlow(article, flowSteps) {
  const existing = article.querySelector(".flow-block");
  if (existing) {
    existing.remove();
  }
  if (!flowSteps || !flowSteps.length) {
    return;
  }
  const bodyNode = article.querySelector(".message-body");
  const flowBlock = createFlowBlock(flowSteps);
  if (bodyNode) {
    article.insertBefore(flowBlock, bodyNode);
  } else {
    article.append(flowBlock);
  }
}

function renderMessages() {
  messages.replaceChildren();
  const conversation = getCurrentConversation();

  appendMessage("assistant", welcomeText);
  conversation.messages.forEach((message) => {
    appendMessage(message.role, message.body, message.type || "", message.flowSteps || []);
  });
}

function renderHistory() {
  const sorted = [...conversations].sort(
    (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
  );

  historyList.replaceChildren();
  if (!sorted.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = "暂无历史记录";
    historyList.append(empty);
    return;
  }

  sorted.forEach((conversation) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = conversation.id === sessionId ? "history-item active" : "history-item";
    button.dataset.sessionId = conversation.id;

    const title = document.createElement("span");
    title.className = "history-title";
    title.textContent = getConversationTitle(conversation);

    const meta = document.createElement("span");
    meta.className = "history-meta";
    meta.textContent = `${formatTime(conversation.updatedAt)} · ${conversation.messages.length} 条`;

    const preview = document.createElement("span");
    preview.className = "history-preview";
    preview.textContent = getConversationPreview(conversation);

    button.append(title, meta, preview);
    historyList.append(button);
  });
}

function touchConversation(conversation) {
  conversation.updatedAt = nowIso();
  conversation.title = getConversationTitle(conversation);
  conversations = [
    conversation,
    ...conversations.filter((item) => item.id !== conversation.id),
  ].slice(0, 30);
  saveConversations();
  renderHistory();
}

function saveMessage(role, body, type = "", flowSteps = []) {
  const conversation = getCurrentConversation();
  conversation.messages.push({
    role,
    body,
    type,
    flowSteps,
    createdAt: nowIso(),
  });
  touchConversation(conversation);
}

function setSending(value) {
  isSending = value;
  sendButton.disabled = value;
  sendButton.textContent = value ? "推演中" : "发送";
}

async function sendMessage(message) {
  if (!message || isSending) {
    return;
  }

  appendMessage("user", message);
  saveMessage("user", message);
  messageInput.value = "";
  setSending(true);
  const pending = appendMessage("assistant", "正在连接推演流程...");
  const flowSteps = [];

  try {
    const finalOutput = await streamMessage(message, flowSteps, pending);
    pending.querySelector(".message-body").textContent = finalOutput;
    saveMessage("assistant", finalOutput, "", flowSteps);
  } catch (error) {
    const text = error.message || "请求失败，请稍后再试。";
    pending.classList.add("error");
    pending.querySelector(".message-body").textContent = text;
    saveMessage("assistant", text, "error", flowSteps);
  } finally {
    setSending(false);
    messageInput.focus();
  }
}

async function streamMessage(message, flowSteps, pending) {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || "Agent 请求失败。");
  }

  if (!response.body) {
    return sendJsonMessage(message);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalOutput = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const event = parseSseChunk(chunk);
      if (!event) {
        continue;
      }
      if (event.session_id && event.session_id !== sessionId) {
        setActiveSession(event.session_id);
      }
      flowSteps.push(event);
      updateMessageFlow(pending, flowSteps);

      if (event.type === "done") {
        if (event.success === false) {
          throw new Error(event.message || "Agent 请求失败。");
        }
        finalOutput = event.content || "";
        continue;
      }
      if (event.type === "error") {
        throw new Error(event.message || "Agent 请求失败。");
      }

      pending.querySelector(".message-body").textContent = getFlowStepText(event);
    }
  }

  if (!finalOutput) {
    throw new Error("Agent 未返回最终内容。");
  }

  return finalOutput;
}

function parseSseChunk(chunk) {
  const data = chunk
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim())
    .join("\n");

  if (!data) {
    return null;
  }

  return JSON.parse(data);
}

async function sendJsonMessage(message) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Agent 请求失败。");
  }

  if (payload.session_id !== sessionId) {
    setActiveSession(payload.session_id);
  }

  return payload.output;
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error("offline");
    }
    statusDot.className = "status-dot ready";
    statusText.textContent = "已连接";
  } catch {
    statusDot.className = "status-dot error";
    statusText.textContent = "不可用";
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(messageInput.value.trim());
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

newSessionButton.addEventListener("click", () => {
  const conversation = createConversation();
  conversations.unshift(conversation);
  saveConversations();
  setActiveSession(conversation.id);
  messageInput.focus();
});

clearHistoryButton.addEventListener("click", () => {
  if (!confirm("确定清空本浏览器中的历史对话吗？")) {
    return;
  }
  conversations = [createConversation()];
  saveConversations();
  setActiveSession(conversations[0].id);
});

historyList.addEventListener("click", (event) => {
  const item = event.target.closest("[data-session-id]");
  if (!item || isSending) {
    return;
  }
  setActiveSession(item.dataset.sessionId);
  messageInput.focus();
});

promptButtons.forEach((button) => {
  button.addEventListener("click", () => {
    messageInput.value = button.dataset.prompt || "";
    messageInput.focus();
  });
});

setActiveSession(sessionId);
checkHealth();
