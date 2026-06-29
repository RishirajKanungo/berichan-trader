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

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36";

interface PrimaryForm {
  types?: string[];
  image_path?: string;
  hp?: number; attack?: number; defense?: number;
  sp_attack?: number; sp_defense?: number; speed?: number;
}
interface FormSummary extends PrimaryForm {
  form_name?: string;
  form_kind?: string;
  slug?: string;
}

// Build an absolute URL to the upstream sprite from its stored path so every
// form (base, regional, Mega) renders from the same authoritative asset set.
function spriteFromPath(path?: string): string {
  if (!path) return "";
  const clean = path.replace(/\\/g, "/").split("/").map(encodeURIComponent).join("/");
  return `https://championsbattledata.com/${clean}`;
}
interface IndexRecord {
  name?: string;
  battleName?: string;
  slug?: string;
  battleDataCsvs?: { format?: string }[];
  summary?: { primary?: PrimaryForm; forms?: FormSummary[] };
}

const baseFromLv50 = (stat: number, isHp: boolean) =>
  Math.max(0, (stat || 0) - (isHp ? 75 : 20));

const statsOf = (f: PrimaryForm) => [
  baseFromLv50(f.hp ?? 0, true),
  baseFromLv50(f.attack ?? 0, false),
  baseFromLv50(f.defense ?? 0, false),
  baseFromLv50(f.sp_attack ?? 0, false),
  baseFromLv50(f.sp_defense ?? 0, false),
  baseFromLv50(f.speed ?? 0, false),
];

export async function GET() {
  try {
    // The upstream index is ~15 MB — bigger than Next's 2 MB fetch-cache limit,
    // so we must opt out of fetch caching (otherwise the cache layer fails and the
    // route returns empty). Edge caching is handled by the Cache-Control header below.
    // Send a browser UA — championsbattledata's Cloudflare blocks UA-less requests.
    const r = await fetch("https://championsbattledata.com/api", {
      headers: { "User-Agent": UA, Accept: "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(20000),
    });
    if (!r.ok) return NextResponse.json({ pokemon: [] });
    const data = await r.json();
    const pokemon = ((data.pokemon as IndexRecord[]) || []).flatMap((rec) => {
      const name = rec.battleName || rec.name || "";
      if (!name) return [];
      const p = rec.summary?.primary || {};
      const formats = [...new Set((rec.battleDataCsvs || []).map((c) => c.format).filter(Boolean))];

      const base = {
        name, slug: rec.slug || "", baseName: name, form: null as string | null,
        types: p.types || [], stats: statsOf(p), bst: statsOf(p).reduce((s, v) => s + v, 0), formats,
        sprite: spriteFromPath(p.image_path),
      };

      // Mega Evolutions live only in `summary.forms` and carry their own stats —
      // include them so the speed tiers (and the simulator) cover Megas. Their
      // usage rank is inherited from the base species (you bring the base mon).
      const megas = (rec.summary?.forms || [])
        .filter((f) => (f.form_kind || "").startsWith("Mega"))
        .map((f) => {
          const stats = statsOf(f);
          return {
            name: f.form_name || `Mega ${name}`,
            slug: f.slug || `${rec.slug || name}-${(f.form_kind || "mega").toLowerCase().replace(/\s+/g, "-")}`,
            baseName: name,
            form: f.form_kind || "Mega",
            types: f.types || p.types || [],
            stats,
            bst: stats.reduce((s, v) => s + v, 0),
            formats,
            sprite: spriteFromPath(f.image_path),
          };
        });

      return [base, ...megas];
    });
    // A few base entries list the same Mega twice — keep one per slug so React
    // keys stay unique (duplicate keys break per-row style updates downstream).
    const seenSlugs = new Set<string>();
    const deduped = pokemon.filter((p) => (p.slug && !seenSlugs.has(p.slug) ? (seenSlugs.add(p.slug), true) : false));
    return NextResponse.json({ pokemon: deduped }, {
      headers: { "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=604800" },
    });
  } catch {
    return NextResponse.json({ pokemon: [] });
  }
}
