import assert from "node:assert/strict";
import test from "node:test";

import { normalizeFinalOutput } from "../src/lib/streamText.ts";

test("collapses an answer repeated in full at stream completion", () => {
  const answer = "先给结论，再说明确定性依据，并补充具体行动建议和文化娱乐边界提醒。";

  assert.equal(normalizeFinalOutput(answer + answer, answer + answer), answer);
});

test("does not collapse a short repeated expression", () => {
  assert.equal(normalizeFinalOutput("哈哈", "哈哈"), "哈哈");
});

test("keeps a legitimate suffix added during finalization", () => {
  const streamed = "先给结论，再说明依据。";
  const finalOutput = `${streamed}\n\n> 仅作文化娱乐与个人参考。`;

  assert.equal(normalizeFinalOutput(finalOutput, streamed), finalOutput);
});
