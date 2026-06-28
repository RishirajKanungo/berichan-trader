// Move-legality check so sets actually legalize when traded into the mainline
// games. Berichan injects into Scarlet/Violet etc., where a Pokémon can only
// have moves it can genuinely learn — broader Champions movepools cause PKHeX to
// reject the trade ("Unable to legalize"). Data: assets/data/legality.json
// (per-species learnable move ids). Loaded lazily.

import { displayName } from "./teamParser";
import type { Pokemon } from "./types";

function toId(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, "");
}

let cache: Record<string, Set<string>> | null = null;
let loading: Promise<void> | null = null;

export function loadLegality(): Promise<void> {
  if (cache) return Promise.resolve();
  if (loading) return loading;
  loading = (async () => {
    try {
      const r = await fetch("/data/legality.json");
      const d = await r.json();
      const out: Record<string, Set<string>> = {};
      for (const [k, v] of Object.entries(d.species ?? {})) out[k] = new Set(v as string[]);
      cache = out;
    } catch {
      cache = {};
    }
  })();
  return loading;
}

/** True if the species can learn the move (or we can't tell yet / unknown species). */
export function canLearn(speciesName: string, moveName: string): boolean {
  if (!cache || !speciesName || !moveName) return true;
  const set = cache[toId(speciesName)];
  if (!set) return true; // species not in data → don't flag
  return set.has(toId(moveName));
}

export interface LegalityIssue {
  pokemon: string;
  move: string;
}

/** Moves on the team that the species can't learn (won't legalize). */
export function teamIssues(team: Pokemon[]): LegalityIssue[] {
  const issues: LegalityIssue[] = [];
  for (const mon of team) {
    for (const mv of mon.moves) {
      if (mv && !canLearn(mon.species, mv)) issues.push({ pokemon: displayName(mon), move: mv });
    }
  }
  return issues;
}
