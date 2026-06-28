"use client";

import { createContext, useContext, useEffect, useState } from "react";

// App-level UI scaling for accessibility / high-DPI (4K) displays. Implemented
// with CSS `zoom` on the document root, which scales everything uniformly —
// text, sprites, spacing — exactly like browser zoom, but persisted per-user and
// in-app. Falls back gracefully (older Firefox simply ignores `zoom`).

export type Scale = "1" | "1.1" | "1.25" | "1.5";
export const SCALES: { key: Scale; label: string }[] = [
  { key: "1", label: "100%" },
  { key: "1.1", label: "110%" },
  { key: "1.25", label: "125%" },
  { key: "1.5", label: "150%" },
];
const STORAGE_KEY = "berichan.uiScale";
const DEFAULT: Scale = "1";

const ScaleContext = createContext<{ scale: Scale; setScale: (s: Scale) => void }>({
  scale: DEFAULT,
  setScale: () => {},
});

export const useScale = () => useContext(ScaleContext);

function apply(scale: Scale) {
  // `zoom` accepts a unitless factor; keep "1" as the empty default.
  document.documentElement.style.zoom = scale === "1" ? "" : scale;
}

export function ScaleProvider({ children }: { children: React.ReactNode }) {
  // Read the saved scale up front (client only; SSR uses the default and the
  // pre-paint script in layout.tsx applies zoom before React hydrates).
  const [scale, setScaleState] = useState<Scale>(() => {
    if (typeof window === "undefined") return DEFAULT;
    return (window.localStorage.getItem(STORAGE_KEY) as Scale) || DEFAULT;
  });

  // Keep the DOM in sync (an allowed external side-effect, not a setState).
  useEffect(() => { apply(scale); }, [scale]);

  const setScale = (s: Scale) => {
    setScaleState(s);
    try { window.localStorage.setItem(STORAGE_KEY, s); } catch {}
  };

  return <ScaleContext.Provider value={{ scale, setScale }}>{children}</ScaleContext.Provider>;
}
