// Cached proxy for the competitive roster (championsbattledata.com/api).
// The upstream index is ~15 MB (it bundles learnable-move lists and forms); we
// trim it to a compact card list (~25 KB) so the Meta tab loads fast. Edge-cached
// like the per-Pokémon route so the heavy upstream fetch happens at most ~daily.
//
// IMPORTANT: the upstream `summary.primary` numbers are LEVEL-50 computed stats
// (neutral nature, 0 EVs, 31 IVs), NOT base stats — so its `base_stat_total` is
// inflated (e.g. Dragonite 775). The Lv50 formula is exactly reversible, so we
// recover the true base stats: non-HP base = stat − 20, HP base = stat − 75.
// Verified to reproduce the bundled Pokédex base stats for every overlapping mon.

import { NextResponse } from "next/server";

interface PrimaryForm {
  types?: string[];
  hp?: number; attack?: number; defense?: number;
  sp_attack?: number; sp_defense?: number; speed?: number;
}
interface IndexRecord {
  name?: string;
  battleName?: string;
  slug?: string;
  battleDataCsvs?: { format?: string }[];
  summary?: { primary?: PrimaryForm };
}

const baseFromLv50 = (stat: number, isHp: boolean) =>
  Math.max(0, (stat || 0) - (isHp ? 75 : 20));

export async function GET() {
  try {
    const r = await fetch("https://championsbattledata.com/api", { signal: AbortSignal.timeout(15000) });
    if (!r.ok) return NextResponse.json({ pokemon: [] });
    const data = await r.json();
    const pokemon = ((data.pokemon as IndexRecord[]) || []).map((rec) => {
      const p = rec.summary?.primary || {};
      const formats = [...new Set((rec.battleDataCsvs || []).map((c) => c.format).filter(Boolean))];
      const stats = [
        baseFromLv50(p.hp ?? 0, true),
        baseFromLv50(p.attack ?? 0, false),
        baseFromLv50(p.defense ?? 0, false),
        baseFromLv50(p.sp_attack ?? 0, false),
        baseFromLv50(p.sp_defense ?? 0, false),
        baseFromLv50(p.speed ?? 0, false),
      ];
      return {
        name: rec.battleName || rec.name || "",
        slug: rec.slug || "",
        types: p.types || [],
        bst: stats.reduce((s, v) => s + v, 0),
        stats,
        formats,
      };
    }).filter((p) => p.name);
    return NextResponse.json({ pokemon }, {
      headers: { "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=604800" },
    });
  } catch {
    return NextResponse.json({ pokemon: [] });
  }
}
