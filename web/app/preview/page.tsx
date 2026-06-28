"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowDownWideNarrow, ArrowUpWideNarrow, Shield, Swords, Wind, Zap } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useTeam } from "@/components/team";
import { MetaSprite } from "@/components/MetaSprite";
import { Combobox } from "@/components/ui/Combobox";
import { getMeta, getMetaIndex, type MetaFormat, type MetaIndexEntry } from "@/lib/meta";
import { metaToCalcSide, pokemonToCalcSide, bestHit, koLabel, koSeverity, type Hit } from "@/lib/matchups";
import { bestAnswer, callouts, effectiveSpe, type Callout } from "@/lib/preview";
import type { CalcSide, FieldConfig } from "@/lib/calc";
import { parseTeam } from "@/lib/teamParser";

interface Opp { name: string; sprite?: string; side: CalcSide }

const field = (doubles: boolean): FieldConfig => ({
  doubles, weather: "", terrain: "", reflect: false, lightScreen: false,
  auroraVeil: false, helpingHand: false, crit: false,
});

const chip = (sev: number, off: boolean): React.CSSProperties =>
  sev < 0 ? { background: "var(--panel)", color: "var(--muted)" }
  : { background: (off ? ["#2f6b3f", "#3a8f4f", "#4caf50", "#2e7d32"] : ["#7a3b34", "#b5503f", "#d4503a", "#b71c1c"])[sev], color: "#fff" };

export default function PreviewPage() {
  const { team } = useTeam();
  const [format, setFormat] = useState<MetaFormat>("Doubles");
  const [names, setNames] = useState<string[]>(["", "", "", "", "", ""]);
  const [index, setIndex] = useState<MetaIndexEntry[]>([]);
  const [opp, setOpp] = useState<Opp[]>([]);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [paste, setPaste] = useState("");

  const [yourTW, setYourTW] = useState(false);
  const [oppTW, setOppTW] = useState(false);
  const [trickRoom, setTrickRoom] = useState(false);

  useEffect(() => { getMetaIndex().then(setIndex); }, []);
  const rosterNames = useMemo(() => index.filter((e) => !e.form).map((e) => e.name).sort(), [index]);

  // Resolve opponent species → most-used set for the chosen format.
  useEffect(() => {
    let active = true;
    (async () => {
      const chosen = names.map((n) => index.find((e) => e.name.toLowerCase() === n.trim().toLowerCase())).filter(Boolean) as MetaIndexEntry[];
      const metas = await Promise.all(chosen.map((e) => getMeta(e.name, format)));
      if (!active) return;
      setOpp(chosen.map((e, i) => ({ name: e.name, sprite: e.sprite, side: metaToCalcSide(e, metas[i]) })));
    })();
    return () => { active = false; };
  }, [names, index, format]);

  const fc = field(format === "Doubles");
  const yours = useMemo(
    () => team.map((mon) => ({ name: mon.species, side: pokemonToCalcSide(mon) })),
    [team],
  );

  // Combined speed order.
  const speedRows = useMemo(() => {
    const rows = [
      ...yours.map((y, i) => ({ side: 0 as const, index: i, name: y.name, sprite: undefined as string | undefined, speed: effectiveSpe(y.side, yourTW), scarf: /choice scarf/i.test(y.side.item) })),
      ...opp.map((o, i) => ({ side: 1 as const, index: i, name: o.name, sprite: o.sprite, speed: effectiveSpe(o.side, oppTW), scarf: /choice scarf/i.test(o.side.item) })),
    ];
    rows.sort((a, b) => (trickRoom ? a.speed - b.speed : b.speed - a.speed));
    return rows;
  }, [yours, opp, yourTW, oppTW, trickRoom]);
  const maxSpe = Math.max(1, ...speedRows.map((r) => r.speed));

  // Per-opponent: your best answer + what it threatens on your side.
  const matchups = useMemo(() => opp.map((o) => {
    const answer = bestAnswer(yours.map((y) => y.side), o.side, fc);
    let threat: { name: string; hit: Hit } | null = null;
    for (const y of yours) {
      const hit = bestHit(o.side, y.side, fc);
      if (hit && (!threat || hit.maxPct > threat.hit.maxPct)) threat = { name: y.name, hit };
    }
    return { opp: o, answer, threat };
  }), [opp, yours, fc]);

  const notes: Callout[] = useMemo(() => callouts(opp.map((o) => ({ name: o.name, side: o.side }))), [opp]);

  const applyPaste = () => {
    const parsed = parseTeam(paste).map((m) => m.species).filter(Boolean);
    const lines = parsed.length ? parsed : paste.split("\n").map((l) => l.trim()).filter(Boolean);
    const next = ["", "", "", "", "", ""];
    lines.slice(0, 6).forEach((l, i) => {
      const match = index.find((e) => e.name.toLowerCase() === l.toLowerCase());
      next[i] = match ? match.name : l;
    });
    setNames(next);
    setPaste(""); setPasteOpen(false);
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl">
        <header className="mb-4 flex flex-wrap items-center gap-3">
          <div>
            <h1 className="text-2xl font-bold">Team Preview</h1>
            <p className="muted text-sm">Enter the opponent&apos;s six — see speed, threats, and what to lead. Uses each Pokémon&apos;s most-used set.</p>
          </div>
          <div className="ml-auto flex gap-1">
            {(["Doubles", "Singles"] as const).map((f) => (
              <button key={f} className="btn" onClick={() => setFormat(f)}
                style={format === f ? { background: "var(--accent)", color: "var(--on-accent)", borderColor: "transparent" } : undefined}>{f}</button>
            ))}
          </div>
        </header>

        {team.length === 0 && (
          <div className="card muted mb-4 p-4 text-sm">
            Build a team first (Team Builder) to see matchups against the opponent.
          </div>
        )}

        {/* Opponent input */}
        <div className="card mb-4 p-3">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-sm font-semibold" style={{ color: "#e35d4a" }}>Opponent&apos;s team</span>
            <button className="btn ml-auto" onClick={() => setPasteOpen((v) => !v)}>Paste species</button>
          </div>
          {pasteOpen && (
            <div className="mb-2 flex gap-2">
              <textarea className="input h-20 flex-1 font-mono text-xs" placeholder="One species per line, or paste a Showdown team" value={paste} onChange={(e) => setPaste(e.target.value)} />
              <button className="btn btn-primary self-start" onClick={applyPaste}>Fill</button>
            </div>
          )}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {names.map((n, i) => (
              <div key={i} className="flex items-center gap-2">
                {opp[i] ? <MetaSprite name={opp[i].name} src={opp[i].sprite} size={32} /> : <span className="inline-block h-8 w-8 rounded" style={{ background: "var(--panel)" }} />}
                <div className="flex-1"><Combobox value={n} onChange={(v) => setNames((p) => p.map((x, j) => (j === i ? v : x)))} options={rosterNames} placeholder={`Mon ${i + 1}`} /></div>
              </div>
            ))}
          </div>
        </div>

        {opp.length === 0 ? (
          <div className="card muted p-8 text-center text-sm">Add the opponent&apos;s Pokémon above to analyze the matchup.</div>
        ) : (
          <div className="space-y-4">
            {/* Callouts */}
            {notes.length > 0 && (
              <div className="card p-3">
                <div className="mb-2 text-sm font-semibold">Watch out for</div>
                <div className="flex flex-wrap gap-2">
                  {notes.map((c, i) => <CalloutChip key={i} c={c} />)}
                </div>
              </div>
            )}

            {/* Speed order */}
            <div className="card p-3">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold">Speed order</span>
                <div className="ml-auto flex flex-wrap gap-1.5">
                  <Toggle on={yourTW} onClick={() => setYourTW((v) => !v)} color="#2980ef"><Wind size={12} /> Your Tailwind</Toggle>
                  <Toggle on={oppTW} onClick={() => setOppTW((v) => !v)} color="#e35d4a"><Wind size={12} /> Their Tailwind</Toggle>
                  <Toggle on={trickRoom} onClick={() => setTrickRoom((v) => !v)} color="#704170">
                    {trickRoom ? <ArrowUpWideNarrow size={12} /> : <ArrowDownWideNarrow size={12} />} Trick Room
                  </Toggle>
                </div>
              </div>
              <div className="space-y-1">
                {speedRows.map((r) => (
                  <div key={`${r.side}-${r.index}`} className="flex items-center gap-2">
                    <MetaSprite name={r.name} src={r.sprite} size={24} className="shrink-0" />
                    <span className="w-28 shrink-0 truncate text-xs" style={{ color: r.side === 0 ? "#2980ef" : "#e35d4a" }}>{r.name}</span>
                    <div className="h-3 flex-1 overflow-hidden rounded-full" style={{ background: "var(--panel)" }}>
                      <div className="h-full rounded-full" style={{ width: `${(r.speed / maxSpe) * 100}%`, background: r.side === 0 ? "#2980ef" : "#e35d4a" }} />
                    </div>
                    {r.scarf && <span className="chip py-0 text-[9px]">Scarf</span>}
                    <span className="w-10 text-right text-xs font-bold tabular-nums">{r.speed}</span>
                  </div>
                ))}
              </div>
              <p className="muted mt-1.5 text-[10px]">{trickRoom ? "Under Trick Room the slowest acts first." : "Fastest first."} Blue = your team, red = opponent.</p>
            </div>

            {/* Matchups */}
            {team.length > 0 && (
              <div className="card overflow-x-auto p-0">
                <table className="w-full border-collapse text-sm">
                  <thead className="border-b" style={{ borderColor: "var(--border)" }}>
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold">Opponent</th>
                      <th className="px-3 py-2 text-left font-semibold"><span className="inline-flex items-center gap-1"><Swords size={13} style={{ color: "#3a8f4f" }} /> Your best answer</span></th>
                      <th className="px-3 py-2 text-left font-semibold"><span className="inline-flex items-center gap-1"><Shield size={13} style={{ color: "#d4503a" }} /> Threatens</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {matchups.map(({ opp: o, answer, threat }) => (
                      <tr key={o.name} className="border-t" style={{ borderColor: "var(--border)" }}>
                        <td className="px-3 py-1.5">
                          <div className="flex items-center gap-2">
                            <MetaSprite name={o.name} src={o.sprite} size={32} className="shrink-0" />
                            <span className="truncate font-medium" style={{ color: "#e35d4a" }}>{o.name}</span>
                          </div>
                        </td>
                        <td className="px-3 py-1.5">
                          {answer ? (
                            <div className="flex items-center gap-2">
                              <MetaSprite name={yours[answer.index].name} size={24} />
                              <span className="rounded px-1.5 py-0.5 text-[10px] font-bold" style={chip(koSeverity(answer.hit), true)}>{koLabel(answer.hit)}</span>
                              <span className="muted truncate text-[11px]">{answer.hit.move} {Math.round(answer.hit.maxPct)}%</span>
                            </div>
                          ) : <span className="muted text-xs">—</span>}
                        </td>
                        <td className="px-3 py-1.5">
                          {threat ? (
                            <div className="flex items-center gap-2">
                              <MetaSprite name={threat.name} size={24} />
                              <span className="rounded px-1.5 py-0.5 text-[10px] font-bold" style={chip(koSeverity(threat.hit), false)}>{koLabel(threat.hit)}</span>
                              <span className="muted truncate text-[11px]">{threat.hit.move} {Math.round(threat.hit.maxPct)}%</span>
                            </div>
                          ) : <span className="muted text-xs">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="muted text-[10px]">Damage assumes the opponent&apos;s most-used set vs your exact builds. KO counts ignore residual — use the full calc for precise rolls.</p>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function Toggle({ on, onClick, color, children }: { on: boolean; onClick: () => void; color: string; children: React.ReactNode }) {
  return (
    <button className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-medium" onClick={onClick}
      style={{ borderColor: on ? color : "var(--border)", background: on ? color : "transparent", color: on ? "#fff" : "var(--muted)" }}>
      {children}
    </button>
  );
}

const CALLOUT_COLOR: Record<string, string> = {
  fakeout: "#e67e22", intimidate: "#9141cb", redirect: "#e67e22", weather: "#2980ef",
  speed: "#704170", immune: "#3a8f4f", priority: "#b5503f",
};
function CalloutChip({ c }: { c: Callout }) {
  return (
    <span className="chip" style={{ borderColor: CALLOUT_COLOR[c.kind] }} title={c.mons.join(", ")}>
      {c.kind === "speed" ? <Zap size={12} style={{ color: CALLOUT_COLOR[c.kind] }} /> : null}
      <b style={{ color: CALLOUT_COLOR[c.kind] }}>{c.label}</b>
      <span className="muted">· {c.mons.join(", ")}</span>
    </span>
  );
}
