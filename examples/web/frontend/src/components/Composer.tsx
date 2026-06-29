import { useState } from "react";

interface ComposerProps {
  disabled: boolean;
  value: string;
  onChange: (value: string) => void;
  onSubmit: (message: string) => void;
}

export function Composer({ disabled, value, onChange, onSubmit }: ComposerProps) {
  const [composing, setComposing] = useState(false);

  const submit = () => {
    const message = value.trim();
    if (message) {
      onSubmit(message);
    }
  };

  return (
    <form
      className="composer"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <label className="sr-only" htmlFor="messageInput">
        消息
      </label>
      <textarea
        id="messageInput"
        rows={3}
        maxLength={4000}
        placeholder="输入问题，按 Enter 发送"
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onCompositionStart={() => setComposing(true)}
        onCompositionEnd={() => setComposing(false)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey && !composing) {
            event.preventDefault();
            submit();
          }
        }}
      />
      <button type="submit" disabled={disabled}>
        {disabled ? "推演中" : "发送"}
      </button>
    </form>
  );
}
