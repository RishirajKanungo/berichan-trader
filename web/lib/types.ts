import type { StatKey, StatLabel } from "./stats";

/** A single Pokémon set (mirrors berichan/team_parser.Pokemon). */
export interface Pokemon {
  nickname: string;
  species: string;
  lines: string[];
  rawBlock: string;
  gender: string; // "M" | "F" | ""
  item: string;
  ability: string;
  level: number; // 0 = unspecified
  shiny: boolean;
  teraType: string;
  nature: string;
  evs: Record<StatLabel, number>;
  ivs: Record<StatLabel, number>;
  moves: string[];
}

/** A legal Champions species (from champions.json). */
export interface Species {
  id: string;
  name: string;
  num: number;
  types: string[];
  abilities: string[];
  baseStats: Record<StatKey, number>;
  moves: string[];
}

export interface ItemData {
  id: string;
  name: string;
  desc: string;
}

export interface MoveData {
  name: string;
  type: string;
  category: string; // Physical | Special | Status
  power: number;
  accuracy: number | string;
  pp: number;
  priority: number;
  desc: string;
  longDesc?: string;
  flags?: string[];
}

export interface AbilityData {
  name: string;
  desc: string;
}

/** A saved, named team (localStorage). */
export interface SavedTeam {
  name: string;
  showdown: string;
}
