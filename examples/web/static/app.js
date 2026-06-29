const activeSessionKey = "wenjia-agent-web-active-session";
const legacySessionKey = "wenjia-agent-web-session";
const conversationsKey = "wenjia-agent-web-conversations";

const welcomeText =
  "你好，我是文甲 Agent。你可以先提交完整出生信息，也可以直接选择左侧推荐问题开始。涉及个人命盘、流年、关系或起名时，我会先确认出生信息是否完整。";

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

function appendMessage(role, body, type = "") {
  const article = document.createElement("article");
  article.className = `message ${role} ${type}`.trim();

  const roleNode = document.createElement("div");
  roleNode.className = "message-role";
  roleNode.textContent = role === "user" ? "你" : "文甲";

  const bodyNode = document.createElement("div");
  bodyNode.className = "message-body";
  bodyNode.textContent = body;

  article.append(roleNode, bodyNode);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function renderMessages() {
  messages.replaceChildren();
  const conversation = getCurrentConversation();

  appendMessage("assistant", welcomeText);
  conversation.messages.forEach((message) => {
    appendMessage(message.role, message.body, message.type || "");
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

function saveMessage(role, body, type = "") {
  const conversation = getCurrentConversation();
  conversation.messages.push({
    role,
    body,
    type,
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
  const pending = appendMessage("assistant", "正在思考...");

  try {
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

    pending.querySelector(".message-body").textContent = payload.output;
    saveMessage("assistant", payload.output);
  } catch (error) {
    const text = error.message || "请求失败，请稍后再试。";
    pending.classList.add("error");
    pending.querySelector(".message-body").textContent = text;
    saveMessage("assistant", text, "error");
  } finally {
    setSending(false);
    messageInput.focus();
  }
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
