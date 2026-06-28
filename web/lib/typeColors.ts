// Canonical Pokémon type colors, used for accents/gradients in the Meta tab.

export const TYPE_COLORS: Record<string, string> = {
  Normal: "#9fa19f", Fire: "#e62829", Water: "#2980ef", Electric: "#fac000",
  Grass: "#3fa129", Ice: "#3dcef3", Fighting: "#ff8000", Poison: "#9141cb",
  Ground: "#915121", Flying: "#81b9ef", Psychic: "#ef4179", Bug: "#91a119",
  Rock: "#afa981", Ghost: "#704170", Dragon: "#5060e1", Dark: "#624d4e",
  Steel: "#60a1b8", Fairy: "#ef70ef", Stellar: "#40b5a5",
};

export function typeColor(type: string): string {
  return TYPE_COLORS[type] ?? "#888";
}

/** A soft two-stop gradient from a Pokémon's type(s), for card accents. */
export function typeGradient(types: string[]): string {
  const a = typeColor(types[0] ?? "Normal");
  const b = typeColor(types[1] ?? types[0] ?? "Normal");
  return `linear-gradient(135deg, ${a}, ${b})`;
}
