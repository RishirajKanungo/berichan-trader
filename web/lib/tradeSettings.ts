// Trade settings persisted in localStorage (mirrors the desktop Config timing +
// channel/bot/code fields).

export interface TradeSettings {
  channel: string;
  botUsername: string;
  tradeCode: string;
  gameCommand: string;
  lineDelay: number;     // seconds after posting the set
  whisperDelay: number;  // seconds before whispering the code
  queueTimeout: number;  // seconds to wait for queue confirmation
  tradeTimeout: number;  // seconds to wait for "Initializing trade"
  cooldown: number;      // seconds between Pokémon
  sound: boolean;
}

const KEY = "berichan.tradeSettings";

export const DEFAULT_SETTINGS: TradeSettings = {
  channel: "berichandev",
  botUsername: "BerichanBot",
  tradeCode: "",
  gameCommand: "!tradeSV",
  lineDelay: 0.6,
  whisperDelay: 2.0,
  queueTimeout: 30,
  tradeTimeout: 600,
  cooldown: 90,
  sound: true,
};

export function loadSettings(): TradeSettings {
  if (typeof window === "undefined") return { ...DEFAULT_SETTINGS };
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const saved = { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
    if (saved.cooldown === 120) saved.cooldown = 90; // migrate the old default
    return saved;
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export function saveSettings(s: TradeSettings): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(s));
}
