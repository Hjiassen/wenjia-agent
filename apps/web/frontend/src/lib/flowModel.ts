import type { FlowEvent, FlowStage, PipelineStats, StageStatus, StepRow, ToolItem } from "../types";

// Reduce a flat list of SSE flow events into an ordered list of pipeline
// "stage cards". Recomputed from scratch on every new event — the arrays are
// small, so this stays simple and avoids stateful mutation bugs.

function newStage(
  id: string,
  kind: FlowStage["kind"],
  label: string,
  status: StageStatus,
): FlowStage {
  return { id, kind, label, status, tools: [], thinkingSteps: [] };
}

function fallbackName(event: FlowEvent): string {
  return (
    event.display_name ||
    event.agent_label ||
    event.agent ||
    "处理中"
  );
}

function eventAgentLabel(event: FlowEvent): string | undefined {
  return event.agent_label || event.agent;
}

export function buildPipeline(events: FlowEvent[]): FlowStage[] {
  const stages: FlowStage[] = [];
  let current: FlowStage | null = null;
  let pendingHandoff: string | undefined;
  let agentSeq = 0;
  let markerSeq = 0;

  const touch = (stage: FlowStage, event: FlowEvent) => {
    if (!stage.startedAt) stage.startedAt = event.timestamp;
    if (event.timestamp) stage.endedAt = event.timestamp;
  };

  const finishCurrentAgent = (event: FlowEvent, expectedAgent?: string) => {
    if (!current || current.kind !== "agent") return;
    if (expectedAgent && current.label !== expectedAgent) return;
    current.status = current.tools.some((t) => t.status === "failed") ? "failed" : "success";
    touch(current, event);
    current = null;
  };

  const ensureAgentStage = (event: FlowEvent): FlowStage => {
    if (current && current.kind === "agent") {
      const agentLabel = eventAgentLabel(event);
      if (!agentLabel || current.label === agentLabel) {
        return current;
      }
      finishCurrentAgent(event, current.label);
    }
    agentSeq += 1;
    const stage = newStage(
      `agent-${agentSeq}`,
      "agent",
      event.agent_label || event.agent || "智能体",
      "active",
    );
    if (pendingHandoff) {
      stage.viaHandoff = pendingHandoff;
      pendingHandoff = undefined;
    }
    stages.push(stage);
    current = stage;
    return stage;
  };

  const marker = (
    kind: FlowStage["kind"],
    label: string,
    status: StageStatus,
    event: FlowEvent,
  ) => {
    markerSeq += 1;
    const stage = newStage(`${kind}-${markerSeq}`, kind, label, status);
    stage.startedAt = event.timestamp;
    stage.endedAt = event.timestamp;
    stages.push(stage);
    current = null;
  };

  for (const event of events) {
    switch (event.type) {
      case "run_start": {
        const stage = newStage("start", "start", event.message || "开始处理请求", "success");
        stage.startedAt = event.timestamp;
        stage.endedAt = event.timestamp;
        stages.push(stage);
        break;
      }
      case "agent_start": {
        finishCurrentAgent(event, current?.label);
        agentSeq += 1;
        const stage = newStage(
          `agent-${agentSeq}`,
          "agent",
          event.agent_label || event.agent || "智能体",
          "active",
        );
        if (pendingHandoff) {
          stage.viaHandoff = pendingHandoff;
          pendingHandoff = undefined;
        }
        touch(stage, event);
        stages.push(stage);
        current = stage;
        break;
      }
      case "thinking": {
        const stage = ensureAgentStage(event);
        const step = event.message || "正在判断下一步";
        // The thinking line is a fixed per-agent template, so repeated LLM
        // calls in one stage emit the same text; keep only distinct steps.
        if (!stage.thinkingSteps.includes(step)) {
          stage.thinkingSteps.push(step);
        }
        stage.status = "active";
        touch(stage, event);
        break;
      }
      case "handoff": {
        const fromAgent = event.from_agent_label || event.from_agent;
        pendingHandoff = fromAgent;
        finishCurrentAgent(event, current?.label);
        break;
      }
      case "tool_start": {
        const stage = ensureAgentStage(event);
        const tool: ToolItem = {
          id: event.tool_call_id || event.tool || `tool-${stage.tools.length}`,
          label: fallbackName(event),
          status: "active",
        };
        stage.tools.push(tool);
        touch(stage, event);
        break;
      }
      case "tool_done": {
        const stage = ensureAgentStage(event);
        const id = event.tool_call_id || event.tool;
        const tool =
          stage.tools.find((item) => item.id === id) ??
          stage.tools.find((item) => item.status === "active");
        if (tool) {
          tool.status = event.success === false ? "failed" : "success";
          tool.duration = event.duration;
          tool.note = event.message;
        }
        touch(stage, event);
        break;
      }
      case "generating": {
        finishCurrentAgent(event, eventAgentLabel(event));
        break;
      }
      case "revise": {
        if (current) {
          current.status = "failed";
        }
        marker("revise", event.message || "修订重试", "active", event);
        break;
      }
      case "verify": {
        finishCurrentAgent(event);
        const ok = event.success !== false;
        marker("verify", event.message || "结果校验", ok ? "success" : "failed", event);
        break;
      }
      case "done": {
        finishCurrentAgent(event);
        marker("done", event.message || "推演完成", "success", event);
        break;
      }
      case "interrupted": {
        if (current) {
          current.status = "failed";
        }
        marker("interrupted", event.message || "推演已中止", "failed", event);
        break;
      }
      case "error": {
        if (current) {
          current.status = "failed";
        }
        marker("error", event.message || "请求失败", "failed", event);
        break;
      }
    }
  }

  return stages;
}

export function pipelineStats(events: FlowEvent[]): PipelineStats {
  const times = events.map((e) => e.timestamp).filter(Boolean) as string[];
  const durationSec =
    times.length >= 2
      ? (new Date(times[times.length - 1]).getTime() - new Date(times[0]).getTime()) / 1000
      : null;
  const toolDone = events.filter((e) => e.type === "tool_done");
  const verify = [...events].reverse().find((e) => e.type === "verify");
  return {
    durationSec,
    toolCount: toolDone.length,
    toolFailures: toolDone.filter((e) => e.success === false).length,
    agentCount: events.filter((e) => e.type === "agent_start").length,
    reviseCount: events.filter((e) => e.type === "revise").length,
    verifyPassed: verify ? verify.success !== false : null,
  };
}

export function pipelineSummary(events: FlowEvent[]): string {
  if (!events.length) {
    return "等待开始";
  }
  const stats = pipelineStats(events);
  const parts = [`${stats.toolCount} 个工具`];
  if (stats.durationSec && stats.durationSec > 0) {
    parts.push(`${stats.durationSec.toFixed(2)}s`);
  }
  if (stats.reviseCount > 0) {
    parts.push(`修订 ${stats.reviseCount} 次`);
  }
  return parts.join(" · ");
}

export function formatClock(iso?: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export function stageElapsed(stage: FlowStage): number | null {
  if (!stage.startedAt || !stage.endedAt) return null;
  const ms = new Date(stage.endedAt).getTime() - new Date(stage.startedAt).getTime();
  return Number.isNaN(ms) ? null : ms / 1000;
}

const STEP_STATUS: Partial<Record<FlowEvent["type"], StageStatus>> = {
  tool_done: "success",
  done: "success",
  verify: "success",
  generating: "success",
  interrupted: "failed",
  error: "failed",
  revise: "active",
};

// Flatten events into a chronological, human-readable step log (明细 view).
export function stepRows(events: FlowEvent[]): StepRow[] {
  return events.map((event, index) => {
    let status: StageStatus | "" = STEP_STATUS[event.type] ?? "";
    if ((event.type === "tool_done" || event.type === "verify") && event.success === false) {
      status = "failed";
    }
    return {
      id: `${event.id || event.type}-${index}`,
      time: formatClock(event.timestamp),
      text: event.message || fallbackName(event),
      kind: event.type,
      status,
      duration: event.duration,
    };
  });
}
