"use client";

import { useEffect, useState } from "react";
import { Check, Loader2, Target } from "lucide-react";
import { Combobox } from "./ui/Combobox";
import { getMeta, getMetaIndex } from "@/lib/meta";
import { metaToCalcSide, toCalcSpecies } from "@/lib/matchups";
import { solveKO, solveSurvive, type KoResult, type SurviveResult } from "@/lib/optimize";
import type { CalcSide, FieldConfig } from "@/lib/calc";
import type { StatLabel } from "@/lib/stats";
import type { Species } from "@/lib/types";

const FC: FieldConfig = {
  doubles: true, weather: "", terrain: "", reflect: false, lightScreen: false,
  auroraVeil: false, helpingHand: false, crit: false,
};

interface Ctx {
  species: Species;
  level: number;
  nature: string;
  item: string;
  ability: string;
  sp: Record<StatLabel, number>;
  moves: string[];
  onApply: (patch: Partial<Record<StatLabel, number>>) => void;
}

export function EvOptimizer(ctx: Ctx) {
  const [names, setNames] = useState<string[]>([]);
  useEffect(() => { getMetaIndex().then((idx) => setNames(idx.filter((e) => !e.form).map((e) => e.name).sort())); }, []);

  const me = (): CalcSide => ({
    species: toCalcSpecies(ctx.species.name), level: ctx.level || 50, nature: ctx.nature,
    item: ctx.item, ability: ctx.ability, teraType: ctx.species ? "" : "", tera: false, status: "",
    sp: ctx.sp, boosts: {}, moves: ctx.moves.filter(Boolean),
  });

  return (
    <div className="card p-3">
      <div className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
        <Target size={15} style={{ color: "var(--accent)" }} /> Optimize Stat Points to a benchmark
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <SurviveTool names={names} me={me} onApply={ctx.onApply} />
        <KoTool names={names} moves={ctx.moves.filter(Boolean)} me={me} onApply={ctx.onApply} />
      </div>
      <p className="muted mt-2 text-[10px]">
        Uses each threat&apos;s most-used set (Doubles) and your current nature/item. &quot;Survive&quot; solves the fewest HP + defence SP to live the max roll; &quot;KO&quot; solves the fewest offence SP for a guaranteed KO.
      </p>
    </div>
  );
}

function SurviveTool({ names, me, onApply }: { names: string[]; me: () => CalcSide; onApply: Ctx["onApply"] }) {
  const [threat, setThreat] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<SurviveResult | "none" | null>(null);

  const solve = async () => {
    if (!threat) return;
    setBusy(true); setRes(null);
    const idx = await getMetaIndex();
    const e = idx.find((x) => x.name.toLowerCase() === threat.trim().toLowerCase());
    if (!e) { setRes("none"); setBusy(false); return; }
    const meta = await getMeta(e.name, "Doubles");
    setRes(solveSurvive(me(), metaToCalcSide(e, meta), FC) ?? "none");
    setBusy(false);
  };

  return (
    <div>
      <div className="muted mb-1 text-xs font-medium">Survive an attack</div>
      <div className="flex gap-1.5">
        <div className="flex-1"><Combobox value={threat} onChange={setThreat} options={names} placeholder="Threat, e.g. Flutter Mane" /></div>
        <button className="btn btn-primary" onClick={solve} disabled={!threat || busy}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : "Solve"}
        </button>
      </div>
      {res === "none" ? (
        <p className="mt-2 text-xs" style={{ color: "#e35d4a" }}>Can&apos;t survive its best hit even fully invested.</p>
      ) : res ? (
        <div className="mt-2 flex items-center justify-between gap-2 text-xs">
          <span>
            Survive <b>{res.move}</b>: <b className="accent-text">+{res.hpSp} HP / +{res.defSp} {res.defStat}</b>
            <span className="muted"> (max {Math.round(res.maxPct)}%)</span>
          </span>
          <button className="btn" onClick={() => onApply({ HP: res.hpSp, [res.defStat]: res.defSp })}><Check size={13} /> Apply</button>
        </div>
      ) : null}
    </div>
  );
}

function KoTool({ names, moves, me, onApply }: { names: string[]; moves: string[]; me: () => CalcSide; onApply: Ctx["onApply"] }) {
  const [target, setTarget] = useState("");
  const [move, setMove] = useState(moves[0] ?? "");
  const [hits, setHits] = useState(1);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<KoResult | "none" | null>(null);

  const solve = async () => {
    if (!target || !move) return;
    setBusy(true); setRes(null);
    const idx = await getMetaIndex();
    const e = idx.find((x) => x.name.toLowerCase() === target.trim().toLowerCase());
    if (!e) { setRes("none"); setBusy(false); return; }
    const meta = await getMeta(e.name, "Doubles");
    setRes(solveKO(me(), metaToCalcSide(e, meta), move, hits, FC) ?? "none");
    setBusy(false);
  };

  return (
    <div>
      <div className="muted mb-1 text-xs font-medium">Score a KO</div>
      <div className="flex gap-1.5">
        <div className="flex-1"><Combobox value={target} onChange={setTarget} options={names} placeholder="Target, e.g. Garchomp" /></div>
        <select className="input w-auto py-1 text-xs" value={hits} onChange={(e) => setHits(Number(e.target.value))}>
          <option value={1}>OHKO</option>
          <option value={2}>2HKO</option>
        </select>
      </div>
      <div className="mt-1.5 flex gap-1.5">
        <select className="input flex-1 py-1 text-xs" value={move} onChange={(e) => setMove(e.target.value)}>
          <option value="">Pick your move…</option>
          {moves.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <button className="btn btn-primary" onClick={solve} disabled={!target || !move || busy}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : "Solve"}
        </button>
      </div>
      {res === "none" ? (
        <p className="mt-2 text-xs" style={{ color: "#e35d4a" }}>Can&apos;t guarantee that KO even fully invested.</p>
      ) : res ? (
        <div className="mt-2 flex items-center justify-between gap-2 text-xs">
          <span>
            <b className="accent-text">+{res.atkSp} {res.atkStat}</b> for a {hits === 1 ? "OHKO" : "2HKO"}
            <span className="muted"> (min {Math.round(res.minPct)}%)</span>
          </span>
          <button className="btn" onClick={() => onApply({ [res.atkStat]: res.atkSp })}><Check size={13} /> Apply</button>
        </div>
      ) : null}
    </div>
  );
}
