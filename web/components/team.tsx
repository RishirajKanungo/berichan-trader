"use client";

import { createContext, useContext, useState, type Dispatch, type SetStateAction } from "react";
import type { Pokemon } from "@/lib/types";

/** Current working team, shared across the Team and Trade pages. */
const TeamContext = createContext<{ team: Pokemon[]; setTeam: Dispatch<SetStateAction<Pokemon[]>> }>({
  team: [],
  setTeam: () => {},
});

export const useTeam = () => useContext(TeamContext);

export function TeamProvider({ children }: { children: React.ReactNode }) {
  const [team, setTeam] = useState<Pokemon[]>([]);
  return <TeamContext.Provider value={{ team, setTeam }}>{children}</TeamContext.Provider>;
}
