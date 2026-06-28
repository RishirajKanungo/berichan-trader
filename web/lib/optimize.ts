// Stat-Point benchmark solvers — the "EV-ing to a goal" workflow VGC players
// live in: find the minimum investment to survive a specific attack, or to score
// a clean KO on a target. Uses the same @smogon/calc engine as everything else.

import { calcMove, type CalcSide, type FieldConfig } from "./calc";
import { bestHit, type Hit } from "./matchups";
import { SP_MAX_PER_STAT, type StatLabel } from "./stats";
import { getMove } from "./data";

function withSp(base: CalcSide, patch: Partial<Record<StatLabel, number>>): CalcSide {
  return { ...base, sp: { ...base.sp, ...patch } };
}

export interface SurviveResult {
  hpSp: number;
  defSp: number;
  defStat: "Def" | "SpD";
  move: string;
  maxPct: number; // worst-case damage at the solved spread
}

/**
 * Minimum HP + defence Stat Points for `me` to survive `attacker`'s most
 * damaging move (max roll < 100%). Searches HP 0–32 and, per HP, binary-searches
 * the least defence needed (damage is monotonic in defence) and keeps the
 * smallest total. Returns null if it can't survive even fully invested.
 */
export function solveSurvive(me: CalcSide, attacker: CalcSide, fc: FieldConfig): SurviveResult | null {
  const threat = bestHit(attacker, me, fc);
  if (!threat) return null;
  const cat = getMove(threat.move)?.category;
  const defStat: "Def" | "SpD" = cat === "Special" ? "SpD" : "Def";

  const maxRoll = (hp: number, def: number): number => {
    const r = calcMove(attacker, withSp(me, { HP: hp, [defStat]: def }), threat.move, fc);
    return r?.maxPct ?? 0;
  };

  let best: SurviveResult | null = null;
  for (let hp = 0; hp <= SP_MAX_PER_STAT; hp++) {
    // Least defence (0–32) that survives at this HP.
    if (maxRoll(hp, SP_MAX_PER_STAT) >= 100) continue; // unsurvivable even maxed here
    let lo = 0, hi = SP_MAX_PER_STAT;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (maxRoll(hp, mid) < 100) hi = mid; else lo = mid + 1;
    }
    const total = hp + lo;
    if (!best || total < best.hpSp + best.defSp || (total === best.hpSp + best.defSp && hp > best.hpSp)) {
      best = { hpSp: hp, defSp: lo, defStat, move: threat.move, maxPct: maxRoll(hp, lo) };
    }
  }
  return best;
}

export interface KoResult {
  atkSp: number;
  atkStat: "Atk" | "SpA";
  move: string;
  minPct: number;
  maxPct: number;
}

/**
 * Minimum attack Stat Points for `me` to guarantee an `n`-hit KO on `defender`
 * with `move` (the calc's min roll reaches 100/n %). Binary search (damage is
 * monotonic in the attacking stat). Returns null if it can't even fully invested.
 */
export function solveKO(me: CalcSide, defender: CalcSide, move: string, hits: number, fc: FieldConfig): KoResult | null {
  const cat = getMove(move)?.category;
  if (!cat || cat === "Status") return null;
  const atkStat: "Atk" | "SpA" = cat === "Special" ? "SpA" : "Atk";
  const need = 100 / hits;

  const roll = (atk: number): Hit | null => {
    const r = calcMove(withSp(me, { [atkStat]: atk }), defender, move, fc);
    return r ? { move, minPct: r.minPct, maxPct: r.maxPct } : null;
  };

  if ((roll(SP_MAX_PER_STAT)?.minPct ?? 0) < need) return null; // can't guarantee even maxed
  let lo = 0, hi = SP_MAX_PER_STAT;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if ((roll(mid)?.minPct ?? 0) >= need) hi = mid; else lo = mid + 1;
  }
  const r = roll(lo)!;
  return { atkSp: lo, atkStat, move, minPct: r.minPct, maxPct: r.maxPct };
}
