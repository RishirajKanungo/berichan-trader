// Cached proxy for the competitive roster (championsbattledata.com/api).
// The upstream index is ~15 MB (it bundles learnable-move lists and forms); we
// trim it to a compact card list (~25 KB) so the Meta tab loads fast. Edge-cached
// like the per-Pokémon route so the heavy upstream fetch happens at most ~daily.

import { NextResponse } from "next/server";

interface PrimaryForm {
  types?: string[];
  base_stat_total?: number;
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

export async function GET() {
  try {
    const r = await fetch("https://championsbattledata.com/api", { signal: AbortSignal.timeout(15000) });
    if (!r.ok) return NextResponse.json({ pokemon: [] });
    const data = await r.json();
    const pokemon = ((data.pokemon as IndexRecord[]) || []).map((rec) => {
      const p = rec.summary?.primary || {};
      const formats = [...new Set((rec.battleDataCsvs || []).map((c) => c.format).filter(Boolean))];
      return {
        name: rec.battleName || rec.name || "",
        slug: rec.slug || "",
        types: p.types || [],
        bst: p.base_stat_total || 0,
        stats: [p.hp || 0, p.attack || 0, p.defense || 0, p.sp_attack || 0, p.sp_defense || 0, p.speed || 0],
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
