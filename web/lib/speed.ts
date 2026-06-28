// Speed-tier math for the Speed tab — base speed, the common investment spreads,
// and the in-battle modifiers used by the turn simulator. All level-50, matching
// the Champions stat system (perfect IVs, Stat Points; 32 SP ≈ a maxed stat).
//
// Verified against known values, e.g. Garchomp (base 102): neutral/0 = 122,
// neutral/+32 = 154, +nature/+32 = 169, +nature/+32 + Scarf = 253.

import { CHAMPIONS_LEVEL, PERFECT_IV } from "./stats";

export type NatureDir = "plus" | "neutral" | "minus";
const NATURE_MOD: Record<NatureDir, number> = { plus: 1.1, neutral: 1.0, minus: 0.9 };

/** Speed stat at a given level for a base speed + Stat-Point investment + nature. */
export function speedStat(base: number, sp: number, dir: NatureDir, level = CHAMPIONS_LEVEL): number {
  const common = Math.floor(((2 * base + PERFECT_IV) * level) / 100);
  return Math.floor((common + 5 + sp) * NATURE_MOD[dir]);
}

// --- speed-tier columns ----------------------------------------------------

export interface SpeedCol {
  key: string;
  /** Short header for the table. */
  label: string;
  /** Full description (tooltip / comparison builder). */
  full: string;
  /** Compute the tier value from a base speed. */
  calc: (base: number) => number;
}

const scarf = (v: number) => Math.floor(v * 1.5);

// The tiers requested, ordered slow → fast. `full` is a one-line title; `help`
// is the hover-tooltip explanation (concise, with an example) so the abbreviated
// headers are never ambiguous.
export const SPEED_COLS: (SpeedCol & { help: string })[] = [
  { key: "base", label: "Base", full: "Base Speed stat", help: "The species' raw base Speed — before level, nature or investment. (Garchomp = 102.)", calc: (b) => b },
  { key: "min", label: "−Nat 0", full: "Minus nature, 0 SP", help: "Slowest build: a Speed‑lowering nature and no investment. Best under Trick Room, where the slowest mon moves first.", calc: (b) => speedStat(b, 0, "minus") },
  { key: "neut0", label: "Neut 0", full: "Neutral, uninvested", help: "Neutral nature with 0 Speed points — the Speed you keep if you invest everything elsewhere.", calc: (b) => speedStat(b, 0, "neutral") },
  { key: "neutMax", label: "Neut +32", full: "Neutral, max invest", help: "Neutral nature with full Speed investment (32 SP / 252 EVs).", calc: (b) => speedStat(b, 32, "neutral") },
  { key: "max", label: "Max", full: "Max Speed", help: "Fastest standard build: a Speed‑boosting nature (Jolly/Timid) + full investment. (Garchomp hits 169.)", calc: (b) => speedStat(b, 32, "plus") },
  { key: "neutScarf", label: "Neut +32 Scarf", full: "Neutral + Choice Scarf", help: "Neutral nature, full Speed investment, holding a Choice Scarf (×1.5).", calc: (b) => scarf(speedStat(b, 32, "neutral")) },
  { key: "maxScarf", label: "Max Scarf", full: "Max + Choice Scarf", help: "Speed‑boosting nature, full investment, Choice Scarf (×1.5) — the fastest a Pokémon can reach.", calc: (b) => scarf(speedStat(b, 32, "plus")) },
];

export const DEFAULT_SORT_COL = "max";

// --- turn simulator --------------------------------------------------------

export type Weather = "none" | "sun" | "rain" | "sand" | "snow";
export type Terrain = "none" | "grassy" | "electric" | "psychic" | "misty";

/** Minimal move shape the simulator needs (from the bundled move data). */
export interface MoveLite {
  name: string;
  type: string;
  category: string; // Physical | Special | Status
  priority: number;
  flags?: string[];
}

export interface AbilityDef {
  id: string;
  label: string;
  /** Doubles Speed while this weather is active. */
  weather?: Weather;
  /** Speed multiplier always applied (e.g. Unburden when its condition is met). */
  speedMult?: number;
  /** Adds priority to moves matching `test`. */
  prio?: { bonus: number; test: (m: MoveLite) => boolean };
  /** Always acts last within its priority bracket (Stall). */
  orderLast?: boolean;
  /** Status moves act last within their bracket (Mycelium Might). */
  statusLast?: boolean;
  note?: string;
}

export const ABILITIES: AbilityDef[] = [
  { id: "none", label: "None" },
  // Speed-doubling weather abilities.
  { id: "swiftswim", label: "Swift Swim", weather: "rain" },
  { id: "chlorophyll", label: "Chlorophyll", weather: "sun" },
  { id: "sandrush", label: "Sand Rush", weather: "sand" },
  { id: "slushrush", label: "Slush Rush", weather: "snow" },
  { id: "unburden", label: "Unburden (item used)", speedMult: 2 },
  // Priority-changing abilities.
  { id: "prankster", label: "Prankster (+1 status)", prio: { bonus: 1, test: (m) => m.category === "Status" }, note: "Prankster status moves fail vs Dark-types." },
  { id: "galewings", label: "Gale Wings (+1 Flying @full HP)", prio: { bonus: 1, test: (m) => m.type === "Flying" }, note: "Only at full HP." },
  { id: "triage", label: "Triage (+3 healing)", prio: { bonus: 3, test: (m) => (m.flags ?? []).includes("Heal") } },
  // Order-within-bracket abilities.
  { id: "stall", label: "Stall (moves last)", orderLast: true },
  { id: "myceliummight", label: "Mycelium Might (status last)", statusLast: true, note: "Status moves act last in their bracket (and ignore the foe's ability)." },
  { id: "quickdraw", label: "Quick Draw (30% first)", note: "30% chance to act first in bracket (random)." },
];

export const ABILITY = (id: string) => ABILITIES.find((a) => a.id === id) ?? ABILITIES[0];

/** Within-bracket item effects + Choice Scarf (speed) handled separately. */
export const ITEMS: { id: string; label: string; speedMult?: number; orderLast?: boolean; note?: string }[] = [
  { id: "none", label: "No item" },
  { id: "scarf", label: "Choice Scarf (×1.5)", speedMult: 1.5 },
  { id: "ironball", label: "Iron Ball (×0.5)", speedMult: 0.5 },
  { id: "lagging", label: "Lagging Tail (moves last)", orderLast: true },
  { id: "quickclaw", label: "Quick Claw (20% first)", note: "20% chance to act first in bracket (random)." },
  { id: "custap", label: "Custap Berry (first @low HP)", note: "Acts first in bracket when HP ≤ 25%." },
];
export const ITEM = (id: string) => ITEMS.find((i) => i.id === id) ?? ITEMS[0];

/** Redirection moves pull single-target attacks from foes onto the user. */
export const REDIRECTION_MOVES = new Set(["Rage Powder", "Follow Me", "Spotlight"]);

/** Effective priority of a move given the user's ability and the terrain. */
export function effectivePriority(move: MoveLite | null, abilityId: string, terrain: Terrain): number {
  if (!move) return 0;
  let p = move.priority || 0;
  const ab = ABILITY(abilityId);
  if (ab.prio && ab.prio.test(move)) p += ab.prio.bonus;
  // Grassy Glide gains +1 priority in Grassy Terrain.
  if (terrain === "grassy" && move.name === "Grassy Glide") p += 1;
  return p;
}

/** Standard ±stage speed multipliers. */
export function stageMult(stage: number): number {
  const s = Math.max(-6, Math.min(6, stage));
  return s >= 0 ? (2 + s) / 2 : 2 / (2 - s);
}

export interface Combatant {
  base: number;
  sp: number;
  dir: NatureDir;
  item: string;           // an ITEMS id
  tailwind: boolean;
  paralyzed: boolean;
  booster: boolean;       // Protosynthesis / Quark Drive on Speed (×1.5)
  ability: string;        // an ABILITIES id
  stage: number;          // -6..+6
  quash: boolean;         // forced to act last this turn
  afterYou: boolean;      // forced to act next/first this turn
}

export function effectiveSpeed(c: Combatant, weather: Weather): number {
  let s = speedStat(c.base, c.sp, c.dir);
  s = Math.floor(s * stageMult(c.stage));
  let mult = 1;
  const item = ITEM(c.item);
  if (item.speedMult) mult *= item.speedMult;
  if (c.tailwind) mult *= 2;
  if (c.booster) mult *= 1.5;
  const ab = ABILITY(c.ability);
  if (ab.weather && ab.weather === weather) mult *= 2;
  if (ab.speedMult) mult *= ab.speedMult;
  if (c.paralyzed) mult *= 0.5; // Gen 7+: paralysis halves Speed
  return Math.floor(s * mult);
}

export interface Resolved {
  index: number;
  priority: number;
  speed: number;
  last: boolean;   // acts last within its bracket
  bucket: number;  // -1 After You (first), 0 normal, 1 Quash (last)
  pos: number;     // 1-based move-order position (ties share a position)
  tie: boolean;    // genuine speed tie (resolved 50/50 in-game)
}

/**
 * Full turn-order resolution. Precedence, highest first:
 *   1. After You (forced first) → normal → Quash (forced last)
 *   2. priority bracket (Trick Room never flips this)
 *   3. "moves last in bracket" effects (Stall, Lagging Tail, Mycelium Might status)
 *   4. Speed — Trick Room reverses Speed only, within the bracket
 */
export function resolveOrder(
  list: { combatant: Combatant; move: MoveLite | null }[],
  opts: { trickRoom: boolean; weather: Weather; terrain: Terrain },
): Resolved[] {
  const rows = list.map((x, index) => {
    const c = x.combatant;
    const ab = ABILITY(c.ability);
    const last = !!ab.orderLast || !!ITEM(c.item).orderLast || (!!ab.statusLast && x.move?.category === "Status");
    return {
      index,
      priority: effectivePriority(x.move, c.ability, opts.terrain),
      speed: effectiveSpeed(c, opts.weather),
      last,
      bucket: c.afterYou ? -1 : c.quash ? 1 : 0,
    };
  });
  rows.sort((a, b) =>
    a.bucket !== b.bucket ? a.bucket - b.bucket
    : a.priority !== b.priority ? b.priority - a.priority
    : a.last !== b.last ? (a.last ? 1 : -1)
    : opts.trickRoom ? a.speed - b.speed : b.speed - a.speed,
  );
  const sig = (r: (typeof rows)[number]) => `${r.bucket}|${r.priority}|${r.last}|${r.speed}`;
  return rows.map((r) => {
    const first = rows.findIndex((y) => sig(y) === sig(r));
    return { ...r, pos: first + 1, tie: rows.filter((y) => sig(y) === sig(r)).length > 1 };
  });
}
