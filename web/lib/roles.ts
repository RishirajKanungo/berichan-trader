// Derive a Pokémon's competitive roles from its usage data (most-used moves +
// abilities). Used by the Meta tab's role filters and the Cores view. Roles are
// computed lazily for the top-usage Pokémon (one /api/meta call each, cached).

import { getMeta, type MetaData, type MetaFormat, type MetaIndexEntry } from "./meta";
import { REDIRECTION, WEATHER_ABILITY } from "./preview";

export type RoleId = "tr" | "tailwind" | "fakeout" | "redirect" | "intimidate" | "weather" | "priority";

export const ROLES: { id: RoleId; label: string }[] = [
  { id: "tr", label: "Trick Room setter" },
  { id: "tailwind", label: "Tailwind" },
  { id: "fakeout", label: "Fake Out" },
  { id: "redirect", label: "Redirection" },
  { id: "intimidate", label: "Intimidate" },
  { id: "weather", label: "Weather setter" },
  { id: "priority", label: "Priority attacker" },
];

const PRIORITY_MOVES = new Set([
  "Extreme Speed", "Sucker Punch", "Aqua Jet", "Bullet Punch", "Mach Punch", "Ice Shard",
  "Shadow Sneak", "Jet Punch", "Grassy Glide", "Accelerock", "Vacuum Wave", "Water Shuriken",
]);

/** Roles for one Pokémon from its most-used set (moves seen in ≥5% of teams). */
export function detectRoles(meta: MetaData): Set<RoleId> {
  const roles = new Set<RoleId>();
  if (!meta.available) return roles;
  const moves = meta.moves.filter(([, p]) => p >= 5).map(([n]) => n);
  const abilities = meta.abilities.map(([n]) => n);

  if (moves.includes("Trick Room")) roles.add("tr");
  if (moves.includes("Tailwind")) roles.add("tailwind");
  if (moves.includes("Fake Out")) roles.add("fakeout");
  if (moves.some((m) => REDIRECTION.has(m))) roles.add("redirect");
  if (abilities.includes("Intimidate")) roles.add("intimidate");
  if (abilities.some((a) => WEATHER_ABILITY[a])) roles.add("weather");
  if (moves.some((m) => PRIORITY_MOVES.has(m))) roles.add("priority");
  return roles;
}

export interface RoleInfo { roles: Set<RoleId>; teammates: string[] }

/**
 * Fetch + analyse the top-`limit` usage Pokémon for the format, returning their
 * roles and teammates keyed by Pokémon name. Cached per format so it only runs
 * once. `ranked` is the index sorted by usage (most-used first).
 */
const cache = new Map<string, Map<string, RoleInfo>>();

export async function loadRoleData(ranked: MetaIndexEntry[], format: MetaFormat, limit: number): Promise<Map<string, RoleInfo>> {
  const key = `${format}:${limit}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const top = ranked.slice(0, limit);
  const metas = await Promise.all(top.map((e) => getMeta(e.name, format)));
  const out = new Map<string, RoleInfo>();
  top.forEach((e, i) => out.set(e.name, { roles: detectRoles(metas[i]), teammates: metas[i].teammates ?? [] }));
  cache.set(key, out);
  return out;
}
