import type { FlowEvent, FlowStage, StageStatus, ToolItem } from "../types";

// Reduce a flat list of SSE flow events into an ordered list of pipeline
// "stage cards". Recomputed from scratch on every new event — the arrays are
// small, so this stays simple and avoids stateful mutation bugs.

function newStage(
  id: string,
  kind: FlowStage["kind"],
  label: string,
  status: StageStatus,
): FlowStage {
  return { id, kind, label, status, tools: [] };
}

function fallbackName(event: FlowEvent): string {
  return (
    event.display_name ||
    event.agent_label ||
    event.tool ||
    event.agent ||
    "处理中"
  );
}

export function buildPipeline(events: FlowEvent[]): FlowStage[] {
  const stages: FlowStage[] = [];
  let current: FlowStage | null = null;
  let pendingHandoff: string | undefined;
  let agentSeq = 0;
  let markerSeq = 0;

  const ensureAgentStage = (event: FlowEvent): FlowStage => {
    if (current && current.kind === "agent") {
      return current;
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

  for (const event of events) {
    switch (event.type) {
      case "run_start": {
        const stage = newStage("start", "start", event.message || "开始处理请求", "success");
        stages.push(stage);
        break;
      }
      case "agent_start": {
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
        break;
      }
      case "thinking": {
        const stage = ensureAgentStage(event);
        stage.thinking = event.message || "正在判断下一步";
        stage.status = "active";
        break;
      }
      case "handoff": {
        pendingHandoff = event.from_agent_label || event.from_agent;
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
        }
        break;
      }
      case "generating": {
        if (current) {
          current.status = current.tools.some((t) => t.status === "failed")
            ? "failed"
            : "success";
        }
        break;
      }
      case "revise": {
        if (current) {
          current.status = "failed";
        }
        markerSeq += 1;
        stages.push(
          newStage(`revise-${markerSeq}`, "revise", event.message || "修订重试", "active"),
        );
        current = null;
        break;
      }
      case "verify": {
        const ok = event.success !== false;
        markerSeq += 1;
        stages.push(
          newStage(
            `verify-${markerSeq}`,
            "verify",
            event.message || "结果校验",
            ok ? "success" : "failed",
          ),
        );
        current = null;
        break;
      }
      case "done": {
        if (current) {
          current.status = current.tools.some((t) => t.status === "failed")
            ? "failed"
            : "success";
        }
        stages.push(newStage("done", "done", event.message || "推演完成", "success"));
        current = null;
        break;
      }
      case "error": {
        if (current) {
          current.status = "failed";
        }
        stages.push(newStage("error", "error", event.message || "请求失败", "failed"));
        current = null;
        break;
      }
    }
  }

  return stages;
}

export function pipelineSummary(events: FlowEvent[]): string {
  const toolDone = events.filter((event) => event.type === "tool_done");
  const total = toolDone.reduce(
    (sum, event) => sum + (typeof event.duration === "number" ? event.duration : 0),
    0,
  );
  if (!events.length) {
    return "等待开始";
  }
  const toolText = `${toolDone.length} 个工具`;
  const durationText = total > 0 ? ` · ${total.toFixed(2)}s` : "";
  return `${toolText}${durationText}`;
}
