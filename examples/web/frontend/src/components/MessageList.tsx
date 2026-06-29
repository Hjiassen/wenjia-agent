import { useEffect, useRef } from "react";
import type { ChatMessage, FlowEvent } from "../types";
import { renderMarkdown } from "../lib/markdown";
import { FlowPipeline } from "./FlowPipeline";

const WELCOME =
  "你好，我是问甲 Agent。你可以先提交完整出生信息，也可以直接选择左侧推荐问题开始。涉及个人命盘、流年、关系或起名时，我会先确认出生信息是否完整。";

interface PendingState {
  active: boolean;
  body: string;
  events: FlowEvent[];
  error: boolean;
}

interface MessageListProps {
  messages: ChatMessage[];
  pending: PendingState;
}

function AssistantBody({ body }: { body: string }) {
  return (
    <div
      className="message-body markdown-body"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(body) }}
    />
  );
}

export function MessageList({ messages, pending }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, pending]);

  return (
    <div className="messages" aria-live="polite">
      <article className="message assistant">
        <div className="message-role">问甲</div>
        <AssistantBody body={WELCOME} />
      </article>

      {messages.map((message, index) => (
        <article key={index} className={`message ${message.role} ${message.type || ""}`.trim()}>
          <div className="message-role">{message.role === "user" ? "你" : "问甲"}</div>
          {message.role === "assistant" ? (
            <>
              {message.flow.length ? <FlowPipeline events={message.flow} /> : null}
              <AssistantBody body={message.body} />
            </>
          ) : (
            <div className="message-body">{message.body}</div>
          )}
        </article>
      ))}

      {pending.active ? (
        <article className={`message assistant ${pending.error ? "error" : ""}`.trim()}>
          <div className="message-role">问甲</div>
          <FlowPipeline events={pending.events} live />
          {pending.error ? (
            <div className="message-body">{pending.body}</div>
          ) : (
            <AssistantBody body={pending.body} />
          )}
        </article>
      ) : null}

      <div ref={endRef} />
    </div>
  );
}
