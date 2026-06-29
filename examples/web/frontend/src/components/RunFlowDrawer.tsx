import type { FlowEvent } from "../types";
import { FlowPipeline } from "./FlowPipeline";

export interface RunFlowTurn {
  id: string;
  prompt: string;
  events: FlowEvent[];
  live?: boolean;
  error?: boolean;
}

interface RunFlowDrawerProps {
  open: boolean;
  turns: RunFlowTurn[];
  onClose: () => void;
}

function snippet(text: string): string {
  const compact = text.replace(/\s+/g, " ").trim();
  return compact.length > 40 ? `${compact.slice(0, 40)}…` : compact || "（无提问）";
}

export function RunFlowDrawer({ open, turns, onClose }: RunFlowDrawerProps) {
  return (
    <div className={`runflow-root ${open ? "is-open" : ""}`} aria-hidden={!open}>
      <div className="runflow-overlay" onClick={onClose} />
      <aside className="runflow-drawer" role="dialog" aria-label="运行流" aria-modal="true">
        <header className="runflow-head">
          <div>
            <p className="eyebrow">推演过程</p>
            <h2>运行流 · 共 {turns.length} 轮</h2>
          </div>
          <button type="button" className="runflow-close" onClick={onClose} aria-label="关闭">
            ✕
          </button>
        </header>

        <div className="runflow-body">
          {turns.length ? (
            turns.map((turn, index) => (
              <section
                key={turn.id}
                className={`runflow-turn ${turn.live ? "is-live" : ""} ${
                  turn.error ? "is-error" : ""
                }`.trim()}
              >
                <h3 className="runflow-turn-title">
                  <span className="runflow-turn-index">第 {index + 1} 轮</span>
                  <span className="runflow-turn-prompt">{snippet(turn.prompt)}</span>
                  {turn.live ? <span className="runflow-live-dot" aria-hidden /> : null}
                </h3>
                <FlowPipeline events={turn.events} defaultOpen />
              </section>
            ))
          ) : (
            <p className="runflow-empty">还没有推演记录，发起一次提问后这里会出现完整运行流。</p>
          )}
        </div>
      </aside>
    </div>
  );
}
