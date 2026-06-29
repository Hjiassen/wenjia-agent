import type { FlowStage } from "../types";

const STATUS_TEXT: Record<FlowStage["status"], string> = {
  pending: "等待",
  active: "进行中",
  success: "完成",
  failed: "失败",
};

function durationText(value?: number): string {
  return typeof value === "number" ? `${value.toFixed(2)}s` : "";
}

export function StageCard({ stage }: { stage: FlowStage }) {
  return (
    <article className={`stage-card kind-${stage.kind} status-${stage.status}`}>
      <header className="stage-card-head">
        <span className="stage-dot" aria-hidden />
        <h3 className="stage-title">{stage.label}</h3>
        <span className="stage-status">{STATUS_TEXT[stage.status]}</span>
      </header>

      {stage.viaHandoff ? (
        <p className="stage-handoff">← 由{stage.viaHandoff}移交</p>
      ) : null}

      {stage.thinking ? <p className="stage-thinking">{stage.thinking}</p> : null}

      {stage.tools.length ? (
        <ul className="stage-tools">
          {stage.tools.map((tool) => (
            <li key={tool.id} className={`tool-chip tool-${tool.status}`}>
              <span className="tool-mark" aria-hidden>
                {tool.status === "success" ? "✓" : tool.status === "failed" ? "✗" : "…"}
              </span>
              <span className="tool-label">{tool.label}</span>
              {tool.duration !== undefined ? (
                <span className="tool-duration">{durationText(tool.duration)}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}
