import assert from "node:assert/strict";
import test from "node:test";

import { shouldRefreshProfiles } from "../src/lib/profileEvents.ts";
import {
  loadRunFlowViewport,
  saveRunFlowViewport,
} from "../src/lib/storage.ts";

class MemoryStorage {
  private values = new Map<string, string>();

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }
}

Object.defineProperty(globalThis, "localStorage", {
  value: new MemoryStorage(),
  configurable: true,
});

test("refreshes profiles after a successful profile-writing tool", () => {
  assert.equal(
    shouldRefreshProfiles({ type: "tool_done", tool: "build_bazi_context_tool", success: true }),
    true,
  );
  assert.equal(
    shouldRefreshProfiles({ type: "tool_done", tool: "save_profile_tool", success: true }),
    true,
  );
  assert.equal(
    shouldRefreshProfiles({ type: "tool_done", tool: "save_profile_tool", success: false }),
    false,
  );
  assert.equal(shouldRefreshProfiles({ type: "thinking" }), false);
});

test("stores run-flow position per session", () => {
  saveRunFlowViewport("web:one", { x: -120, y: 48, scale: 0.8 });
  saveRunFlowViewport("web:two", { x: 30, y: -64, scale: 1.2 });

  assert.deepEqual(loadRunFlowViewport("web:one"), { x: -120, y: 48, scale: 0.8 });
  assert.deepEqual(loadRunFlowViewport("web:two"), { x: 30, y: -64, scale: 1.2 });
});
