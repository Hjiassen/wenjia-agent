const sessionKey = "wenjia-agent-web-session";

const messages = document.querySelector("#messages");
const chatForm = document.querySelector("#chatForm");
const messageInput = document.querySelector("#messageInput");
const sendButton = document.querySelector("#sendButton");
const sessionIdLabel = document.querySelector("#sessionId");
const newSessionButton = document.querySelector("#newSessionButton");
const statusDot = document.querySelector("#statusDot");
const statusText = document.querySelector("#statusText");
const promptButtons = document.querySelectorAll("[data-prompt]");

let sessionId = localStorage.getItem(sessionKey) || createSessionId();
let isSending = false;

function createSessionId() {
  const value = `web:${crypto.randomUUID()}`;
  localStorage.setItem(sessionKey, value);
  return value;
}

function updateSessionLabel() {
  sessionIdLabel.textContent = sessionId;
}

function appendMessage(role, body, type = "") {
  const article = document.createElement("article");
  article.className = `message ${role} ${type}`.trim();

  const roleNode = document.createElement("div");
  roleNode.className = "message-role";
  roleNode.textContent = role === "user" ? "You" : "Agent";

  const bodyNode = document.createElement("div");
  bodyNode.className = "message-body";
  bodyNode.textContent = body;

  article.append(roleNode, bodyNode);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function setSending(value) {
  isSending = value;
  sendButton.disabled = value;
  sendButton.textContent = value ? "Sending" : "Send";
}

async function sendMessage(message) {
  if (!message || isSending) {
    return;
  }

  appendMessage("user", message);
  messageInput.value = "";
  setSending(true);
  const pending = appendMessage("assistant", "Thinking...");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Agent request failed.");
    }

    sessionId = payload.session_id;
    localStorage.setItem(sessionKey, sessionId);
    updateSessionLabel();
    pending.querySelector(".message-body").textContent = payload.output;
  } catch (error) {
    pending.classList.add("error");
    pending.querySelector(".message-body").textContent = error.message;
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
    statusText.textContent = "Ready";
  } catch {
    statusDot.className = "status-dot error";
    statusText.textContent = "Unavailable";
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
  sessionId = createSessionId();
  updateSessionLabel();
  appendMessage("assistant", "Started a new session.");
});

promptButtons.forEach((button) => {
  button.addEventListener("click", () => {
    messageInput.value = button.dataset.prompt || "";
    messageInput.focus();
  });
});

updateSessionLabel();
checkHealth();
