/**
 * Background music for a scheduler run and its celebration (ux9, item 4).
 *
 * The clip is the third movement (Minuet) of Mozart's Eine kleine Nachtmusik, K. 525,
 * a 75 second excerpt in public/audio. Its source and licence are in
 * public/audio/mozart-minuet-k525-excerpt.txt. Playback starts from the Run click,
 * because browsers allow sound only after a user action, and stops when the
 * celebration ends or the run fails. Every call is safe without audio: a blocked
 * or missing file leaves the fireworks and captions working.
 */
export const RUN_MUSIC_SRC = "/audio/mozart-minuet-k525-excerpt.mp3";

let audio: HTMLAudioElement | null = null;
let muted = false;

function element(): HTMLAudioElement | null {
  if (typeof Audio === "undefined") return null;
  if (!audio) {
    audio = new Audio(RUN_MUSIC_SRC);
    audio.loop = true;
    audio.preload = "auto";
    audio.volume = 0.6;
  }
  return audio;
}

/** Starts the music. Call it synchronously from the Run click. */
export function startRunMusic(): void {
  try {
    const a = element();
    if (!a) return;
    a.muted = muted;
    a.currentTime = 0;
    const playing = a.play();
    if (playing) playing.catch(() => { /* Blocked or unavailable: the run still shows its fireworks. */ });
  } catch {
    /* No audio support: nothing to play. */
  }
}

/** Stops the music when the celebration ends, or the run fails, or the page closes. */
export function stopRunMusic(): void {
  try {
    audio?.pause();
  } catch {
    /* Nothing playing. */
  }
}

export function isRunMusicMuted(): boolean {
  return muted;
}

/** Mute keeps the music going silently, so unmuting picks it up where it is. */
export function setRunMusicMuted(next: boolean): void {
  muted = next;
  try {
    if (audio) audio.muted = next;
  } catch {
    /* No audio support. */
  }
}
