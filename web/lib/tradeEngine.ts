// Orchestrates the trade flow in the browser. Port of berichan/trade_manager.py:
// post each set to chat, whisper the code (via /api/whisper), wait for the queue
// + "Initializing trade" confirmations, alert the user, wait for "Trade Done",
// then cooldown. Runs entirely client-side on the qasync-equivalent event loop
// (the browser tab) using the WebSocket IRC client.

import { TwitchChat } from "./twitchChat";
import { TWITCH_MAX_CHAT_LENGTH, chatMessage } from "./teamParser";
import type { Pokemon } from "./types";

export type LogLevel = "info" | "success" | "warn" | "error";

export interface TradeCallbacks {
  log: (msg: string, level?: LogLevel) => void;
  status: (s: string) => void;
  pokemonStart: (index: number, total: number, mon: Pokemon) => void;
  queueJoined: (id: string, position: string) => void;
  tradeReady: (pokemonName: string, code: string) => void;
  pokemonDone: (index: number, total: number) => void;
  cooldown: (remaining: number, total: number) => void;
  complete: (total: number) => void;
}

export interface RunOpts {
  token: string;
  login: string;
  channel: string;
  botUsername: string;
  tradeCode: string;
  gameCommand: string;
  lineDelay: number;
  whisperDelay: number;
  queueTimeout: number;
  tradeTimeout: number;
  cooldown: number;
}

export class TradeEngine {
  private chat = new TwitchChat();
  private cancelled = false;
  private login = "";
  private doneResolve: (() => void) | null = null;
  private queueResolve: ((v: { id: string; pos: string } | null) => void) | null = null;
  private tradeResolve: ((name: string | null) => void) | null = null;

  constructor(private cb: TradeCallbacks) {}

  confirmDone() {
    this.doneResolve?.();
    this.doneResolve = null;
  }

  stop() {
    this.cancelled = true;
    this.cb.log("Stopping…", "warn");
    // Unblock any pending waits so run() can exit.
    this.queueResolve?.(null);
    this.tradeResolve?.(null);
    this.doneResolve?.();
    this.queueResolve = this.tradeResolve = this.doneResolve = null;
    this.chat.close();
  }

  private sleep(ms: number) {
    return new Promise<void>((r) => setTimeout(r, ms));
  }

  async run(team: Pokemon[], o: RunOpts) {
    this.cancelled = false;
    this.login = o.login.toLowerCase();
    this.chat.onMessage((_s, _c, text) => this.onMessage(text));

    this.cb.status("Connecting to Twitch…");
    await this.chat.connect(o.token, o.login, o.channel);
    this.cb.log(`Connected to #${o.channel} as ${o.login}.`, "success");

    const total = team.length;
    for (let i = 0; i < total; i++) {
      if (this.cancelled) break;
      const mon = team[i];
      this.cb.pokemonStart(i + 1, total, mon);
      await this.tradeOne(mon, o);
      if (this.cancelled) break;
      this.cb.pokemonDone(i + 1, total);
      if (i < total - 1) await this.doCooldown(o.cooldown);
    }

    this.chat.close();
    if (!this.cancelled) this.cb.complete(total);
  }

  private async tradeOne(mon: Pokemon, o: RunOpts) {
    const message = `${o.gameCommand} ${chatMessage(mon)}`;
    if (message.length > TWITCH_MAX_CHAT_LENGTH) {
      this.cb.log(`[skip] ${mon.species}: set is ${message.length} chars (Twitch limit ${TWITCH_MAX_CHAT_LENGTH}).`, "error");
      return;
    }

    this.cb.status(`Posting ${mon.species}…`);
    this.cb.log(`Posting ${mon.species} to chat…`);
    this.chat.sendChat(message);
    await this.sleep(o.lineDelay * 1000);
    await this.sleep(o.whisperDelay * 1000);
    if (this.cancelled) return;

    this.cb.status("Whispering trade code…");
    try {
      const res = await fetch("/api/whisper", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ toLogin: o.botUsername, message: o.tradeCode }),
      });
      if (res.ok) {
        this.cb.log(`Whispered trade code to @${o.botUsername}.`, "success");
      } else {
        const d = await res.json().catch(() => ({}));
        this.cb.log(`[whisper] failed: ${d.error ?? res.status}${d.detail ? ` — ${d.detail}` : ""}`, "error");
      }
    } catch (e) {
      this.cb.log(`[whisper] error: ${e instanceof Error ? e.message : e}`, "error");
    }
    if (this.cancelled) return;

    this.cb.status("Waiting for queue confirmation…");
    const q = await this.waitQueue(o.queueTimeout * 1000);
    if (this.cancelled) return;
    if (q) this.cb.queueJoined(q.id, q.pos);
    else this.cb.log("[timeout] No queue confirmation in 30s. Waiting for the trade anyway…", "warn");

    this.cb.status("Waiting for the trade to start…");
    const name = await this.waitTrade(o.tradeTimeout * 1000);
    if (this.cancelled) return;
    if (!name) {
      this.cb.log(`[timeout] Trade never started after ${o.tradeTimeout}s. Skipping.`, "error");
      return;
    }

    this.cb.tradeReady(name, o.tradeCode);
    await this.waitDone();
  }

  private waitDone() {
    return new Promise<void>((resolve) => { this.doneResolve = resolve; });
  }
  private waitQueue(timeout: number) {
    return new Promise<{ id: string; pos: string } | null>((resolve) => {
      const t = setTimeout(() => { this.queueResolve = null; resolve(null); }, timeout);
      this.queueResolve = (v) => { clearTimeout(t); this.queueResolve = null; resolve(v); };
    });
  }
  private waitTrade(timeout: number) {
    return new Promise<string | null>((resolve) => {
      const t = setTimeout(() => { this.tradeResolve = null; resolve(null); }, timeout);
      this.tradeResolve = (name) => { clearTimeout(t); this.tradeResolve = null; resolve(name); };
    });
  }

  private onMessage(text: string) {
    const lower = text.toLowerCase();
    const user = this.login;
    if (this.queueResolve && lower.includes(user) && lower.includes("added to the linktrade queue")) {
      const id = /unique id[:\s]+(\d+)/i.exec(text)?.[1] ?? "?";
      const pos = /current position[:\s]+(\d+)/i.exec(text)?.[1] ?? "?";
      this.queueResolve({ id, pos });
    }
    if (this.tradeResolve && lower.includes(user) && lower.includes("initializing trade")) {
      const name = /initializing trade\s*\(([^)]+)\)/i.exec(text)?.[1] ?? "?";
      this.tradeResolve(name);
    }
  }

  private async doCooldown(total: number) {
    this.cb.status("Cooldown before next Pokémon…");
    let remaining = total;
    while (remaining > 0 && !this.cancelled) {
      this.cb.cooldown(remaining, total);
      const step = Math.min(1, remaining);
      await this.sleep(step * 1000);
      remaining -= step;
    }
    this.cb.cooldown(0, total);
  }
}
