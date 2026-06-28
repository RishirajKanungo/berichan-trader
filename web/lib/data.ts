// Loads the bundled datasets (champions/items/moves/abilities) from public/data
// and exposes lookups. Ported from berichan/pokedex.py + items.py.
//
// Data is fetched once on the client and cached at module scope; call loadData()
// (the DataProvider does this) before using the sync getters.

import { itemIconUrlById } from "./assets";
import type { AbilityData, ItemData, MoveData, Species } from "./types";

function toId(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, "");
}

let _species: Species[] = [];
let _speciesByName = new Map<string, Species>();
let _items = new Map<string, ItemData>();
let _moves = new Map<string, MoveData>();
let _abilities = new Map<string, AbilityData>();
let _loaded = false;
let _loading: Promise<void> | null = null;

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(path);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function loadData(): Promise<void> {
  if (_loaded) return;
  if (_loading) return _loading;
  _loading = (async () => {
    const [dex, items, moves, abilities] = await Promise.all([
      fetchJson<{ species: Species[] }>("/data/champions.json"),
      fetchJson<{ items: ItemData[] }>("/data/items.json"),
      fetchJson<{ moves: MoveData[] }>("/data/moves.json"),
      fetchJson<{ abilities: AbilityData[] }>("/data/abilities.json"),
    ]);

    _species = dex?.species ?? [];
    _speciesByName = new Map();
    for (const sp of _species) {
      _speciesByName.set(sp.name.toLowerCase(), sp);
      _speciesByName.set(sp.id.toLowerCase(), sp);
    }
    _items = new Map();
    for (const it of items?.items ?? []) {
      _items.set(it.name.toLowerCase(), it);
      _items.set(it.id.toLowerCase(), it);
      _items.set(toId(it.name), it);
    }
    _moves = new Map((moves?.moves ?? []).map((m) => [m.name.toLowerCase(), m]));
    _abilities = new Map((abilities?.abilities ?? []).map((a) => [a.name.toLowerCase(), a]));
    _loaded = true;
  })();
  return _loading;
}

export const isLoaded = () => _loaded;

// --- species ---
export function allSpecies(): Species[] {
  return [..._species].sort((a, b) => (a.num ?? 0) - (b.num ?? 0));
}
export function searchSpecies(query: string): Species[] {
  const q = query.trim().toLowerCase();
  const all = allSpecies();
  return q ? all.filter((s) => s.name.toLowerCase().includes(q)) : all;
}
export function getSpecies(name: string): Species | undefined {
  return _speciesByName.get(name.trim().toLowerCase());
}

// --- items ---
export function allItems(): ItemData[] {
  return [...new Set(_items.values())].sort((a, b) => a.name.localeCompare(b.name));
}
export function getItem(name: string): ItemData | undefined {
  if (!name) return undefined;
  return _items.get(name.trim().toLowerCase()) ?? _items.get(toId(name));
}
export function describeItem(name: string): string {
  return getItem(name)?.desc ?? "";
}
export function itemIconUrl(name: string): string | null {
  const it = getItem(name);
  return it ? itemIconUrlById(it.id) : null;
}

// --- moves ---
export function getMove(name: string): MoveData | undefined {
  return name ? _moves.get(name.trim().toLowerCase()) : undefined;
}
export function allMoveNames(): string[] {
  return [...new Set([..._moves.values()].map((m) => m.name))].sort();
}
export function moveSummary(name: string): string {
  const m = getMove(name);
  if (!m) return "";
  const bits: string[] = [m.type, m.category];
  if (m.power) bits.push(`${m.power} BP`);
  bits.push(typeof m.accuracy === "number" ? `${m.accuracy}%` : "—");
  if (m.priority) bits.push(`Pri ${m.priority > 0 ? "+" : ""}${m.priority}`);
  return bits.filter(Boolean).join("  ·  ");
}
export function moveTooltip(name: string): string {
  const m = getMove(name);
  if (!m) return "";
  return `${moveSummary(name)}\nPP ${m.pp ?? 0}\n${m.desc ?? ""}`;
}

// --- abilities ---
export function getAbility(name: string): AbilityData | undefined {
  return name ? _abilities.get(name.trim().toLowerCase()) : undefined;
}
export function abilityDesc(name: string): string {
  return getAbility(name)?.desc ?? "";
}
