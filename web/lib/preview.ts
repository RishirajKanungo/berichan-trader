// Team-preview analysis: combined speed order, best answers / biggest threats,
// and ability/immunity callouts — the things you scan for in the 90-second pick
// phase. Pure logic over calc sides; reuses the shared @smogon/calc engine.

import { sideStats, type CalcSide, type FieldConfig } from "./calc";
import { bestHit, type Hit } from "./matchups";

export interface SpeedEntry {
  side: 0 | 1;     // 0 = you, 1 = opponent
  index: number;   // index within that team
  name: string;
  sprite?: string;
  speed: number;
  scarf: boolean;
}

/** Effective Speed for the chart: real stat + Choice Scarf + that side's Tailwind. */
export function effectiveSpe(side: CalcSide, tailwind: boolean): number {
  let spe = sideStats(side)?.spe ?? 0;
  if (/choice scarf/i.test(side.item)) spe = Math.floor(spe * 1.5);
  if (tailwind) spe *= 2;
  return spe;
}

export interface Answer { index: number; hit: Hit }

/** The team member that does the most to `target` (your best answer to a threat). */
export function bestAnswer(team: CalcSide[], target: CalcSide, fc: FieldConfig): Answer | null {
  let best: Answer | null = null;
  team.forEach((m, index) => {
    const hit = bestHit(m, target, fc);
    if (hit && (!best || hit.maxPct > best.hit.maxPct)) best = { index, hit };
  });
  return best;
}

// --- callouts --------------------------------------------------------------

export const INTIMIDATE = "Intimidate";
export const REDIRECTION = new Set(["Rage Powder", "Follow Me", "Spotlight"]);
export const WEATHER_ABILITY: Record<string, string> = {
  Drought: "Sun", "Orichalcum Pulse": "Sun", Drizzle: "Rain",
  "Sand Stream": "Sandstorm", "Snow Warning": "Snow",
};
export const IMMUNITY_ABILITY: Record<string, string> = {
  Levitate: "Ground", "Flash Fire": "Fire", "Water Absorb": "Water", "Storm Drain": "Water",
  "Dry Skin": "Water", "Volt Absorb": "Electric", "Lightning Rod": "Electric", "Motor Drive": "Electric",
  "Sap Sipper": "Grass", "Earth Eater": "Ground", "Well-Baked Body": "Fire", "Wind Rider": "Wind moves",
};
const SPEED_CONTROL: Record<string, string> = {
  "Trick Room": "Trick Room", Tailwind: "Tailwind", "Icy Wind": "Icy Wind",
  Electroweb: "Electroweb", "Thunder Wave": "paralysis", Nuzzle: "paralysis", Glare: "paralysis",
};

export type CalloutKind = "fakeout" | "intimidate" | "redirect" | "weather" | "speed" | "immune" | "priority";

export interface Callout {
  kind: CalloutKind;
  label: string;
  mons: string[]; // opponent Pokémon names this applies to
}

const PRIORITY_MOVES = new Set(["Extreme Speed", "Sucker Punch", "Aqua Jet", "Bullet Punch", "Mach Punch", "Ice Shard", "Shadow Sneak", "Jet Punch", "Grassy Glide", "Accelerock"]);

/** Notable threats to keep in mind, derived from the opponent's most-used sets. */
export function callouts(opp: { name: string; side: CalcSide }[]): Callout[] {
  const add = (map: Map<string, string[]>, key: string, name: string) => {
    const arr = map.get(key) ?? []; arr.push(name); map.set(key, arr);
  };
  const fakeout: string[] = [], intim: string[] = [], redirect: string[] = [], priority: string[] = [];
  const weather = new Map<string, string[]>(), speed = new Map<string, string[]>(), immune = new Map<string, string[]>();

  for (const { name, side } of opp) {
    const moves = side.moves;
    if (moves.includes("Fake Out")) fakeout.push(name);
    if (side.ability === INTIMIDATE) intim.push(name);
    if (moves.some((m) => REDIRECTION.has(m))) redirect.push(name);
    if (moves.some((m) => PRIORITY_MOVES.has(m))) priority.push(name);
    if (WEATHER_ABILITY[side.ability]) add(weather, WEATHER_ABILITY[side.ability], name);
    if (IMMUNITY_ABILITY[side.ability]) add(immune, `${side.ability} (immune to ${IMMUNITY_ABILITY[side.ability]})`, name);
    for (const m of moves) if (SPEED_CONTROL[m]) add(speed, SPEED_CONTROL[m], name);
  }

  const out: Callout[] = [];
  if (fakeout.length) out.push({ kind: "fakeout", label: "Fake Out", mons: fakeout });
  if (intim.length) out.push({ kind: "intimidate", label: "Intimidate (lowers your Attack)", mons: intim });
  if (redirect.length) out.push({ kind: "redirect", label: "Redirection (Rage Powder / Follow Me)", mons: redirect });
  if (priority.length) out.push({ kind: "priority", label: "Priority attacker", mons: priority });
  for (const [w, mons] of weather) out.push({ kind: "weather", label: `${w} setter`, mons });
  for (const [s, mons] of speed) out.push({ kind: "speed", label: `Speed control: ${s}`, mons });
  for (const [a, mons] of immune) out.push({ kind: "immune", label: a, mons });
  return out;
}
