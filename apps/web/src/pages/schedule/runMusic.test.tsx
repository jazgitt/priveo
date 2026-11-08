import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Fireworks } from "./RunFireworks";
import { isRunMusicMuted, RUN_MUSIC_SRC, setRunMusicMuted, startRunMusic, stopRunMusic } from "./runMusic";

/** A stand-in for HTMLAudioElement that records what the page asked of it. */
class FakeAudio {
  static made: FakeAudio[] = [];
  src: string;
  loop = false;
  muted = false;
  volume = 1;
  preload = "";
  currentTime = 5;
  play = vi.fn(() => Promise.resolve());
  pause = vi.fn();
  constructor(src: string) { this.src = src; FakeAudio.made.push(this); }
}

describe("run music", () => {
  beforeEach(() => {
    // The module keeps one element for the page, so the first test's instance is the one the later tests check.
    vi.stubGlobal("Audio", FakeAudio);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    setRunMusicMuted(false);
  });

  it("starts the Mozart excerpt from the start, looping, and stops it", () => {
    startRunMusic();
    const a = FakeAudio.made[0];
    expect(a.src).toBe(RUN_MUSIC_SRC);
    expect(a.loop).toBe(true);
    expect(a.currentTime).toBe(0);
    expect(a.play).toHaveBeenCalledTimes(1);
    stopRunMusic();
    expect(a.pause).toHaveBeenCalled();
  });

  it("mute is kept across runs and applied to the element", () => {
    startRunMusic();
    setRunMusicMuted(true);
    expect(isRunMusicMuted()).toBe(true);
    expect(FakeAudio.made[0].muted).toBe(true);
    startRunMusic();
    expect(FakeAudio.made[0].muted).toBe(true);
    setRunMusicMuted(false);
    expect(FakeAudio.made[0].muted).toBe(false);
  });

  it("a blocked play does not throw", async () => {
    vi.stubGlobal("Audio", class extends FakeAudio {
      constructor(src: string) { super(src); this.play = vi.fn(() => Promise.reject(new Error("blocked"))); }
    });
    expect(() => startRunMusic()).not.toThrow();
    await Promise.resolve();
  });

  it("the overlay shows a Mute control that toggles the music, and only it takes clicks", () => {
    const onToggle = vi.fn();
    render(<Fireworks mode="running" muted={false} onToggleMute={onToggle} />);
    fireEvent.click(screen.getByRole("button", { name: "Mute music" }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("the overlay has no Mute control without a toggle", () => {
    render(<Fireworks mode="celebrate" message="Done" />);
    expect(screen.queryByRole("button", { name: /mute/i })).toBeNull();
  });
});

describe("the run music file", () => {
  // The portal is served under its base path, so a root URL is a 404 and nothing plays (owner, 8-Nov-26).
  it("is a file in public/, reached from the base path", () => {
    expect(RUN_MUSIC_SRC.startsWith(import.meta.env.BASE_URL)).toBe(true);
    const rel = RUN_MUSIC_SRC.slice(import.meta.env.BASE_URL.length);
    expect(existsSync(resolve(process.cwd(), "public", rel))).toBe(true); // the web tests run from apps/web
  });
});
