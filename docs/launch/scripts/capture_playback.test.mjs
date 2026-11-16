import assert from "node:assert/strict";
import test from "node:test";
import { tutorialIsPlaying } from "./capture_playback.mjs";

test("accepts tutorial playback and rejects search results or stopped video", (t) => {
  let video = { currentTime: 1, paused: false };
  globalThis.location = { pathname: "/watch" };
  globalThis.document = { querySelector: () => video };
  t.after(() => {
    delete globalThis.location;
    delete globalThis.document;
  });

  assert.equal(tutorialIsPlaying(), true);
  location.pathname = "/results";
  assert.equal(tutorialIsPlaying(), false);
  location.pathname = "/watch";
  video.paused = true;
  assert.equal(tutorialIsPlaying(), false);
  video.paused = false;
  video.currentTime = 0;
  assert.equal(tutorialIsPlaying(), false);
  video = null;
  assert.equal(tutorialIsPlaying(), false);
});
