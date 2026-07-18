import type { FlowEvent } from "../types";

const PROFILE_WRITING_TOOLS = new Set(["build_bazi_context_tool", "save_profile_tool"]);

export function shouldRefreshProfiles(event: FlowEvent): boolean {
  return Boolean(
    event.type === "tool_done" &&
      event.success !== false &&
      event.tool &&
      PROFILE_WRITING_TOOLS.has(event.tool),
  );
}
