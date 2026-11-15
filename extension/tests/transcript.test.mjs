import test from "node:test";
import assert from "node:assert/strict";
import { parseTranscript } from "../transcript.mjs";

test("preserves customer and salesperson directions", () => {
  assert.deepEqual(parseTranscript("Customer: What is your price?\nSalesperson: Which model do you need?"), [
    { direction: "inbound", body: "What is your price?" },
    { direction: "outbound", body: "Which model do you need?" },
  ]);
});

test("keeps multiline messages with their speaker", () => {
  assert.deepEqual(parseTranscript("Customer: Hello\nI need a quote\nSalesperson: Sure\nI can help."), [
    { direction: "inbound", body: "Hello\nI need a quote" },
    { direction: "outbound", body: "Sure\nI can help." },
  ]);
});

test("treats unlabelled pasted context as customer input", () => {
  assert.deepEqual(parseTranscript("Can you send a catalogue?"), [
    { direction: "inbound", body: "Can you send a catalogue?" },
  ]);
});

test("ignores empty input and empty labelled entries", () => {
  assert.deepEqual(parseTranscript("  "), []);
  assert.deepEqual(parseTranscript("Customer:  \nSalesperson: Hi"), [
    { direction: "outbound", body: "Hi" },
  ]);
});
