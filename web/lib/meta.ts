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
  teammates: string[];
}

const EMPTY: MetaData = { available: false, moves: [], items: [], abilities: [], natures: [], spreads: [], teammates: [] };
const cache = new Map<string, MetaData>();

export async function getMeta(speciesId: string, format: MetaFormat): Promise<MetaData> {
  const key = `${speciesId}:${format}`;
  const hit = cache.get(key);
  if (hit) return hit;
  try {
    const r = await fetch(`/api/meta?mon=${encodeURIComponent(speciesId)}&format=${format}`);
    const d = await r.json();
    const m: MetaData = d?.available
      ? { available: true, moves: d.moves ?? [], items: d.items ?? [], abilities: d.abilities ?? [], natures: d.natures ?? [], spreads: d.spreads ?? [], teammates: d.teammates ?? [] }
      : EMPTY;
    cache.set(key, m);
    return m;
  } catch {
    return EMPTY;
  }
}

/** A competitively-tracked Pokémon from the cached roster index. */
export interface MetaIndexEntry {
  name: string;        // battle name, e.g. "Alolan Ninetales" (what the usage API expects)
  slug: string;
  types: string[];
  bst: number;
  stats: number[];     // [HP, Atk, Def, SpA, SpD, Spe]
  formats: string[];   // formats this Pokémon has data for ("Doubles" / "Singles")
}

let indexCache: MetaIndexEntry[] | null = null;

export async function getMetaIndex(): Promise<MetaIndexEntry[]> {
  if (indexCache) return indexCache;
  try {
    const r = await fetch("/api/meta/index");
    const d = await r.json();
    indexCache = Array.isArray(d?.pokemon) ? (d.pokemon as MetaIndexEntry[]) : [];
  } catch {
    indexCache = [];
  }
  return indexCache;
}

/** Remote sprite asset, used as a fallback when we have no bundled local sprite. */
export function remoteSpriteUrl(name: string): string {
  return `https://championsbattledata.com/pokemon_champions_assets/pokemon/${encodeURIComponent(name)}.png`;
}

// --- usage ranking ---------------------------------------------------------
// The ranked ladder (pokechamdb) and the roster (championsbattledata) name a
// handful of regional/alternate forms differently, so we join on a normalized
// key: lowercase, regional words canonicalized, alnum tokens sorted. This never
// produces a wrong match — names that don't reconcile simply get no rank.

// Form descriptors that the two sources word differently (e.g. championsbattledata
// "Aegislash Shield Forme" vs pokechamdb "Aegislash", "Paldean Tauros Aqua Breed"
// vs "Tauros Paldea Aqua"). Dropping these collapses both spellings to the same
// key. Verified to introduce NO collisions on the roster — gender words are
// deliberately NOT dropped (Meowstic / Basculegion genders are distinct mons).
const DROP_TOKENS = new Set(["shield", "zero", "breed", "fancy", "pattern", "natural", "red", "flower"]);

export function normalizeMonName(name: string): string {
  let n = name.toLowerCase();
  for (const [a, b] of [["alolan", "alola"], ["galarian", "galar"], ["hisuian", "hisui"], ["paldean", "paldea"]] as const) {
    n = n.replaceAll(a, b);
  }
  n = n.replaceAll("jumbo", "super").replaceAll("variety", "").replaceAll("forme", "").replaceAll("form", "");
  const toks = (n.match(/[a-z0-9]+/g) ?? []).filter((t) => !DROP_TOKENS.has(t));
  return toks.sort().join("");
}

const usageCache = new Map<MetaFormat, Map<string, number>>();

/** Map of normalized Pokémon name -> 1-based usage rank for the format (lower = more used). */
export async function getUsageRanks(format: MetaFormat): Promise<Map<string, number>> {
  const hit = usageCache.get(format);
  if (hit) return hit;
  const ranks = new Map<string, number>();
  try {
    const r = await fetch(`/api/meta/usage?format=${format}`);
    const d = await r.json();
    const list: { name: string }[] = Array.isArray(d?.ranks) ? d.ranks : [];
    list.forEach((row, i) => {
      const rank = i + 1;
      const key = normalizeMonName(row.name);
      if (!ranks.has(key)) ranks.set(key, rank);
      // pokechamdb names the default gender bare (e.g. "Basculegion"), while the
      // roster spells it out ("Basculegion Male"). Register a "+male" alias so the
      // bare entry still matches — harmless for non-gendered species.
      if (!/\b(male|female)\b/i.test(row.name)) {
        const maleKey = normalizeMonName(`${row.name} male`);
        if (!ranks.has(maleKey)) ranks.set(maleKey, rank);
      }
    });
  } catch {
    /* fail soft — caller falls back to BST sort */
  }
  usageCache.set(format, ranks);
  return ranks;
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
