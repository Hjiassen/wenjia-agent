import assert from "node:assert/strict";
import test from "node:test";

import { shouldRefreshConversationOnResume } from "../src/lib/conversationRecovery.ts";

test("refreshes an idle conversation when the page resumes", () => {
  assert.equal(shouldRefreshConversationOnResume("visible", false), true);
});

test("does not replace an active stream while the page resumes", () => {
  assert.equal(shouldRefreshConversationOnResume("visible", true), false);
  assert.equal(shouldRefreshConversationOnResume("hidden", false), false);
});
