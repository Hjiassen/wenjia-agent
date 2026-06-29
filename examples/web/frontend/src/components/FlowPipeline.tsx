import { useMemo, useState } from "react";
import type { FlowEvent } from "../types";
import { buildPipeline, pipelineSummary } from "../lib/flowModel";
import { StageCard } from "./StageCard";

interface FlowPipelineProps {
  events: FlowEvent[];
  // Live pipelines stay open and auto-expanded; saved ones start collapsed.
  live?: boolean;
  // Force an expanded, non-collapsible view (used inside the run-flow drawer).
  defaultOpen?: boolean;
}

export function FlowPipeline({ events, live = false, defaultOpen = false }: FlowPipelineProps) {
  const stages = useMemo(() => buildPipeline(events), [events]);
  const hasError = stages.some((stage) => stage.status === "failed");
  const [open, setOpen] = useState(live || defaultOpen || hasError);

  if (!stages.length) {
    return null;
  }

  const expanded = live || defaultOpen || open;
  const collapsible = !live && !defaultOpen;

  return (
    <section className={`flow-pipeline ${live ? "is-live" : ""}`}>
      <button
        type="button"
        className="flow-pipeline-summary"
        onClick={() => collapsible && setOpen((value) => !value)}
        aria-expanded={expanded}
        disabled={!collapsible}
      >
        <span>推演流程 · {pipelineSummary(events)}</span>
        {collapsible ? <span className="flow-caret">{expanded ? "收起" : "展开"}</span> : null}
      </button>

      {expanded ? (
        <div className="flow-track" role="list">
          {stages.map((stage, index) => (
            <div className="flow-track-item" role="listitem" key={stage.id}>
              {index > 0 ? <span className="flow-arrow" aria-hidden>→</span> : null}
              <StageCard stage={stage} />
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
