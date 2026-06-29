import { useMemo } from "react";
import type { FlowEvent, FlowStage } from "../types";
import { buildPipeline } from "../lib/flowModel";
import { StageCard } from "./StageCard";

export interface RunFlowTurn {
  id: string;
  prompt: string;
  events: FlowEvent[];
  live?: boolean;
  error?: boolean;
}

interface RunFlowModalProps {
  open: boolean;
  turns: RunFlowTurn[];
  onClose: () => void;
}

type FlowItem =
  | { kind: "turn"; id: string; index: number; prompt: string; live?: boolean; error?: boolean }
  | { kind: "stage"; id: string; stage: FlowStage };

function snippet(text: string): string {
  const compact = text.replace(/\s+/g, " ").trim();
  return compact.length > 24 ? `${compact.slice(0, 24)}…` : compact || "（无提问）";
}

// Flatten every turn into one continuous chain: a turn marker followed by its
// stage cards, so multi-turn flows read head-to-tail and wrap automatically.
function flatten(turns: RunFlowTurn[]): FlowItem[] {
  const items: FlowItem[] = [];
  turns.forEach((turn, index) => {
    items.push({
      kind: "turn",
      id: turn.id,
      index: index + 1,
      prompt: turn.prompt,
      live: turn.live,
      error: turn.error,
    });
    buildPipeline(turn.events).forEach((stage) => {
      items.push({ kind: "stage", id: `${turn.id}-${stage.id}`, stage });
    });
  });
  return items;
}

export function RunFlowModal({ open, turns, onClose }: RunFlowModalProps) {
  const items = useMemo(() => flatten(turns), [turns]);

  return (
    <div className={`runflow-root ${open ? "is-open" : ""}`} aria-hidden={!open}>
      <div className="runflow-overlay" onClick={onClose} />
      <div className="runflow-modal" role="dialog" aria-label="运行流" aria-modal="true">
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
          {items.length ? (
            <div className="runflow-flow">
              {items.map((item, index) => (
                <div className="runflow-node" key={item.id}>
                  {index > 0 ? <span className="runflow-connector" aria-hidden>→</span> : null}
                  {item.kind === "turn" ? (
                    <div
                      className={`runflow-turn-chip ${item.live ? "is-live" : ""} ${
                        item.error ? "is-error" : ""
                      }`.trim()}
                    >
                      <span className="runflow-turn-index">第 {item.index} 轮</span>
                      <span className="runflow-turn-prompt">{snippet(item.prompt)}</span>
                      {item.live ? <span className="runflow-live-dot" aria-hidden /> : null}
                    </div>
                  ) : (
                    <StageCard stage={item.stage} />
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="runflow-empty">还没有推演记录，发起一次提问后这里会出现完整运行流。</p>
          )}
        </div>
      </div>
    </div>
  );
}
