"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { signIn } from "next-auth/react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/auth";
import { useTeam } from "@/components/team";
import { allMoveNames, getSpecies } from "@/lib/data";
import { GAMES } from "@/lib/games";
import { syncLines } from "@/lib/teamParser";
import { canLearnInGame, gameKey, loadLegality, speciesInGame, teamIssues } from "@/lib/legality";
import { playReady } from "@/lib/sound";
import { displayName } from "@/lib/teamParser";
import { TradeEngine, type LogLevel } from "@/lib/tradeEngine";
import { DEFAULT_SETTINGS, loadSettings, saveSettings, type TradeSettings } from "@/lib/tradeSettings";

const LOG_COLOR: Record<LogLevel, string> = {
  info: "var(--muted)", success: "#2ecc71", warn: "#f1c40f", error: "#e74c3c",
};

export default function TradePage() {
  const { authEnabled, signedIn, user, accessToken } = useAuth();
  const { team, setTeam } = useTeam();
  const engineRef = useRef<TradeEngine | null>(null);

  const [settings, setSettings] = useState<TradeSettings>(() => loadSettings());
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("Idle");
  const [logLines, setLogLines] = useState<{ msg: string; level: LogLevel }[]>([]);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [readyForTrade, setReadyForTrade] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const update = (patch: Partial<TradeSettings>) => {
    setSettings((s) => { const next = { ...s, ...patch }; saveSettings(next); return next; });
  };
  const log = (msg: string, level: LogLevel = "info") => setLogLines((p) => [...p, { msg, level }]);

  // Pre-flight legality: flag moves the team can't actually learn (these won't
  // legalize when traded). Recomputed when the team changes / data loads.
  const [, forceLegality] = useState(0);
  useEffect(() => { loadLegality().then(() => forceLegality((n) => n + 1)); }, []);
  const gkey = gameKey(settings.gameCommand);
  const issues = useMemo(() => teamIssues(team, gkey), [team, gkey]);
  const gameValidated = gkey !== null; // SwSh / Legends Arceus aren't in the dataset yet
  const currentGameLabel = GAMES.find((g) => g.command === settings.gameCommand)?.label ?? "the game";

  // Legal replacement moves for a species in the selected game (excludes ones it
  // already has), so the user can fix an illegal move right on this page.
  const legalOptionsFor = (speciesName: string, current: string[]): string[] => {
    if (!gkey) return [];
    return allMoveNames().filter((n) => canLearnInGame(speciesName, n, gkey) && !current.includes(n));
  };

  const replaceMove = (monIndex: number, slot: number, newMove: string) => {
    setTeam((prev) =>
      prev.map((m, i) => {
        if (i !== monIndex) return m;
        const moves = [...m.moves];
        if (newMove) moves[slot] = newMove;
        else moves.splice(slot, 1);
        return syncLines({ ...m, moves });
      }),
    );
  };

  const removeMon = (monIndex: number) => setTeam((prev) => prev.filter((_, i) => i !== monIndex));

  const canTrade = useMemo(
    () => authEnabled && signedIn && !!accessToken && !!user?.login,
    [authEnabled, signedIn, accessToken, user],
  );

  const start = () => {
    if (!settings.tradeCode.trim()) { setStatus("Enter your trade code first."); return; }
    if (!team.length) { setStatus("No team — build or load one first."); return; }
    if (!accessToken || !user?.login) { setStatus("Sign in with Twitch first."); return; }

    const engine = new TradeEngine({
      log,
      status: setStatus,
      pokemonStart: (i, total, mon) => { setProgress({ done: i - 1, total }); log(`[${i}/${total}] ${displayName(mon)}`); },
      queueJoined: (id, pos) => log(`Queue joined — ID ${id}, position ${pos}`, "success"),
      tradeReady: (name, code) => { setReadyForTrade(true); playReady(settings.sound); log(`TRADE READY: ${name} — code ${code} on your Switch, then click “Trade Done”.`, "warn"); },
      pokemonDone: (i, total) => { setProgress({ done: i, total }); setReadyForTrade(false); log("Trade confirmed.", "success"); },
      cooldown: (rem) => { if (rem > 0) setStatus(`Cooldown: ${Math.round(rem)}s…`); },
      complete: (total) => { log(`All ${total} Pokémon submitted!`, "success"); setStatus("Done 🎉"); },
    });
    engineRef.current = engine;
    setRunning(true);
    setReadyForTrade(false);
    setLogLines([]);
    log(`Starting ${team.length} Pokémon → #${settings.channel} (${settings.gameCommand})`);
    engine
      .run(team, {
        token: accessToken,
        login: user.login,
        channel: settings.channel,
        botUsername: settings.botUsername,
        tradeCode: settings.tradeCode,
        gameCommand: settings.gameCommand,
        lineDelay: settings.lineDelay,
        whisperDelay: settings.whisperDelay,
        queueTimeout: settings.queueTimeout,
        tradeTimeout: settings.tradeTimeout,
        cooldown: settings.cooldown,
      })
      .catch((e) => { log(`[error] ${e instanceof Error ? e.message : e}`, "error"); setStatus("Error."); })
      .finally(() => { setRunning(false); setReadyForTrade(false); });
  };

  const stop = () => { engineRef.current?.stop(); setRunning(false); };
  const tradeDone = () => { engineRef.current?.confirmDone(); setReadyForTrade(false); };

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-1 text-2xl font-bold">Trade</h1>
        <p className="muted mb-4 text-sm">Auto-post your team to Berichan&apos;s chat and trade into your game.</p>

        {!canTrade ? (
          <div className="card p-8 text-center">
            {!authEnabled ? (
              <p className="muted">Sign-in isn&apos;t configured on this deployment yet.</p>
            ) : (
              <>
                <p className="mb-3">Sign in with Twitch to trade (this grants chat + whisper permissions).</p>
                <button className="btn btn-primary" onClick={() => signIn("twitch")}>Sign in with Twitch</button>
                <p className="muted mt-3 text-xs">Already signed in? You may need to sign out and back in once to grant the new trade permissions.</p>
              </>
            )}
          </div>
        ) : (
          <>
            {/* Settings */}
            <div className="card mb-4 space-y-3 p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Game">
                  <select className="input" value={settings.gameCommand} onChange={(e) => update({ gameCommand: e.target.value })} disabled={running}>
                    {GAMES.map((g) => <option key={g.command} value={g.command}>{g.label} ({g.command})</option>)}
                  </select>
                </Field>
                <Field label="Trade code (your Switch Link Trade code)">
                  <input className="input" value={settings.tradeCode} onChange={(e) => update({ tradeCode: e.target.value })} placeholder="e.g. 12345678" disabled={running} />
                </Field>
                <Field label="Channel"><input className="input" value={settings.channel} onChange={(e) => update({ channel: e.target.value })} disabled={running} /></Field>
                <Field label="Bot username"><input className="input" value={settings.botUsername} onChange={(e) => update({ botUsername: e.target.value })} disabled={running} /></Field>
              </div>

              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={settings.sound} onChange={(e) => update({ sound: e.target.checked })} style={{ accentColor: "var(--accent)" }} /> Play a sound when a trade is ready
              </label>

              <button className="muted text-xs underline" onClick={() => setShowAdvanced((v) => !v)}>
                {showAdvanced ? "Hide" : "Show"} timing settings
              </button>
              {showAdvanced && (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Field label="Line delay (s)"><input type="number" step="0.1" className="input" value={settings.lineDelay} onChange={(e) => update({ lineDelay: Number(e.target.value) })} disabled={running} /></Field>
                  <Field label="Whisper delay (s)"><input type="number" step="0.1" className="input" value={settings.whisperDelay} onChange={(e) => update({ whisperDelay: Number(e.target.value) })} disabled={running} /></Field>
                  <Field label="Cooldown (s)"><input type="number" className="input" value={settings.cooldown} onChange={(e) => update({ cooldown: Number(e.target.value) })} disabled={running} /></Field>
                  <Field label="Trade timeout (s)"><input type="number" className="input" value={settings.tradeTimeout} onChange={(e) => update({ tradeTimeout: Number(e.target.value) })} disabled={running} /></Field>
                </div>
              )}
            </div>

            {/* Team summary */}
            <div className="card mb-4 p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-semibold">Team to trade ({team.length})</span>
                <Link href="/" className="muted text-xs underline">Edit on the Team Builder →</Link>
              </div>
              {team.length === 0 ? (
                <p className="muted text-sm">No team loaded. Go to the Team Builder to build or load one.</p>
              ) : (
                <ol className="list-decimal space-y-2 pl-5 text-sm">
                  {team.map((m, i) => {
                    const inRoster = !!getSpecies(m.species);
                    const notInGame = inRoster && gameValidated && gkey ? !speciesInGame(m.species, gkey) : false;
                    const badSlots = inRoster && gameValidated && gkey && !notInGame
                      ? m.moves.map((mv, slot) => ({ mv, slot })).filter((x) => x.mv && !canLearnInGame(m.species, x.mv, gkey))
                      : [];
                    const ok = inRoster && !notInGame && badSlots.length === 0;
                    const options = badSlots.length ? legalOptionsFor(m.species, m.moves) : [];
                    return (
                      <li key={i}>
                        <span className="font-medium">{displayName(m)}</span>{" "}
                        {ok ? (
                          <span style={{ color: "#2ecc71" }}>✓ legal{gameValidated ? ` for ${currentGameLabel}` : ""}</span>
                        ) : !inRoster ? (
                          <span style={{ color: "#e74c3c" }}>⚠ not in the Champions roster</span>
                        ) : notInGame ? (
                          <span style={{ color: "#e74c3c" }}>
                            ⚠ not available in {currentGameLabel}{" "}
                            <button className="underline" onClick={() => removeMon(i)}>remove</button>
                          </span>
                        ) : (
                          <span style={{ color: "#e74c3c" }}>⚠ illegal move{badSlots.length > 1 ? "s" : ""} for {currentGameLabel}</span>
                        )}

                        {/* Inline fix: swap each illegal move for a legal one. */}
                        {badSlots.map(({ mv, slot }) => (
                          <div key={slot} className="mt-1 flex flex-wrap items-center gap-2 pl-1">
                            <span style={{ color: "#e74c3c" }}>✕ {mv}</span>
                            <span className="muted">→</span>
                            <select
                              className="input w-auto py-1 text-xs"
                              value=""
                              onChange={(e) => { if (e.target.value) replaceMove(i, slot, e.target.value === "__remove__" ? "" : e.target.value); }}
                            >
                              <option value="">Replace with a legal move…</option>
                              {options.map((n) => <option key={n} value={n}>{n}</option>)}
                              <option value="__remove__">(remove this move)</option>
                            </select>
                          </div>
                        ))}
                      </li>
                    );
                  })}
                </ol>
              )}
              <p className="muted mt-3 text-xs">
                {gameValidated
                  ? `Validated against ${currentGameLabel} learnsets (Serebii). Berichan does the final check.`
                  : "This game's learnsets aren't in the app yet — Berichan is the final legality check."}
              </p>
            </div>

            {/* Legality pre-flight */}
            {issues.length > 0 && (
              <div className="card mb-3 p-3" style={{ borderColor: "#e74c3c" }}>
                <div className="mb-1 text-sm font-semibold" style={{ color: "#e74c3c" }}>
                  ⚠ These won&apos;t legalize in {currentGameLabel} — fix them on the Team Builder first:
                </div>
                <ul className="muted list-disc pl-5 text-xs">
                  {issues.map((it, i) => (
                    <li key={i}><b>{it.pokemon}</b> — {it.reason}.</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Controls */}
            <div className="mb-3 flex items-center gap-2">
              {!running ? (
                <button
                  className="btn btn-primary"
                  onClick={start}
                  disabled={!team.length || !settings.tradeCode.trim() || issues.length > 0}
                >
                  ▶ Start Trading
                </button>
              ) : (
                <button className="btn" onClick={stop}>■ Stop</button>
              )}
              <span className="muted text-sm">{status}</span>
            </div>

            {progress.total > 0 && (
              <div className="mb-3 h-3 w-full overflow-hidden rounded-full" style={{ background: "var(--panel)" }}>
                <div className="h-full rounded-full transition-all" style={{ width: `${(progress.done / progress.total) * 100}%`, background: "var(--accent)" }} />
              </div>
            )}

            <button
              className="mb-3 w-full rounded-lg py-3 text-base font-bold"
              style={{ background: readyForTrade ? "#27ae60" : "var(--panel)", color: readyForTrade ? "#fff" : "var(--muted)", cursor: readyForTrade ? "pointer" : "not-allowed" }}
              onClick={tradeDone}
              disabled={!readyForTrade}
            >
              ✓ Trade Done — next Pokémon
            </button>

            {running && (
              <p className="muted mb-3 text-center text-xs">⚠ Keep this tab open and visible while trading.</p>
            )}

            {/* Log */}
            <div className="card max-h-72 overflow-y-auto p-3 font-mono text-xs">
              {logLines.length === 0 ? (
                <span className="muted">Log output appears here…</span>
              ) : (
                logLines.map((l, i) => <div key={i} style={{ color: LOG_COLOR[l.level] }}>{l.msg}</div>)
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="muted mb-1 block text-xs font-medium">{label}</label>
      {children}
    </div>
  );
}
