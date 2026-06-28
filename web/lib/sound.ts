// Plays the "trade ready" chime (bundled under public/sounds).
export function playReady(enabled: boolean, volume = 0.5) {
  if (!enabled || typeof window === "undefined") return;
  try {
    const audio = new Audio("/sounds/soft_chime.wav");
    audio.volume = Math.max(0, Math.min(1, volume));
    void audio.play().catch(() => {});
  } catch {
    /* ignore */
  }
}
