// Client access to competitive usage data via the cached /api/meta proxy.
// Results are cached per species+format in memory so opening the same Pokémon's
// editor never re-requests.

import type { StatLabel } from "./stats";

export type MetaFormat = "Doubles" | "Singles";

export interface MetaData {
  available: boolean;
  moves: [string, number][];
  items: [string, number][];
  abilities: [string, number][];
  natures: [string, number][];
  spreads: [Record<StatLabel, number>, number][];
}

const EMPTY: MetaData = { available: false, moves: [], items: [], abilities: [], natures: [], spreads: [] };
const cache = new Map<string, MetaData>();

export async function getMeta(speciesId: string, format: MetaFormat): Promise<MetaData> {
  const key = `${speciesId}:${format}`;
  const hit = cache.get(key);
  if (hit) return hit;
  try {
    const r = await fetch(`/api/meta?mon=${encodeURIComponent(speciesId)}&format=${format}`);
    const d = await r.json();
    const m: MetaData = d?.available
      ? { available: true, moves: d.moves ?? [], items: d.items ?? [], abilities: d.abilities ?? [], natures: d.natures ?? [], spreads: d.spreads ?? [] }
      : EMPTY;
    cache.set(key, m);
    return m;
  } catch {
    return EMPTY;
  }
}

export interface Recommended {
  moves: string[];
  item: string;
  ability: string;
  nature: string;
  spread: Record<StatLabel, number> | null;
}

export function recommended(m: MetaData): Recommended {
  return {
    moves: m.moves.slice(0, 4).map((x) => x[0]),
    item: m.items[0]?.[0] ?? "",
    ability: m.abilities[0]?.[0] ?? "",
    nature: m.natures[0]?.[0] ?? "",
    spread: m.spreads[0]?.[0] ?? null,
  };
}
