// Global usage ranking for the Meta tab.
//
// No public/official API exposes a cross-Pokémon usage ranking for Pokémon
// Champions. championsbattledata.com (the API we use everywhere else) only has
// per-Pokémon usage, so the ranked ladder is sourced from pokechamdb.com, which
// renders it server-side. We pin the parse to its ranked-row anchor
// (/en/pokemon/<slug>?...format=...) — present for every Pokémon regardless of
// which sprite host it uses (some forms, e.g. Basculegion, fall back to Showdown
// sprites) — and read rank straight from document order (most-used first).
//
// The latest season is detected from the page (its season picker lists every
// season id), so this tracks the current ladder automatically as new seasons
// ship — no hard-coded season to go stale.
//
// This route is purely additive and fail-soft: any error returns an empty list,
// and the Meta tab falls back to sorting by base-stat total. It can never break
// the page or surface a wrong rank (unmatched Pokémon simply get no rank).

import { NextResponse } from "next/server";

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36";

// Each ranked row is an anchor to the Pokémon's page followed by its sprite img
// whose alt text is the display name. Anchoring on the href (not the sprite URL)
// captures rows that use a Showdown sprite instead of the PokéAPI one.
// e.g. href="/en/pokemon/basculegion?season=M-3&amp;format=double" … alt="Basculegion"
const ROW = /href="\/en\/pokemon\/([^"?]+)\?[^"]*format=[^"]*"[\s\S]*?alt="([^"]+)"/g;

async function fetchPage(format: string, season: string | null): Promise<string | null> {
  const q = season ? `&season=${encodeURIComponent(season)}` : "";
  try {
    const r = await fetch(`https://pokechamdb.com/en?format=${format}&view=pokemon${q}`, {
      headers: { "User-Agent": UA, Accept: "text/html" },
      signal: AbortSignal.timeout(12000),
    });
    return r.ok ? await r.text() : null;
  } catch {
    return null;
  }
}

/** Latest season id (e.g. "M-3") from the page's season picker, or null. */
function latestSeason(html: string): string | null {
  let max = 0;
  for (const m of html.matchAll(/\bM-(\d+)\b/g)) {
    const n = Number(m[1]);
    if (n > max && n < 1000) max = n; // sanity cap
  }
  return max ? `M-${max}` : null;
}

function parseRows(html: string): { name: string; slug: string }[] {
  const ranks: { name: string; slug: string }[] = [];
  const seen = new Set<string>();
  for (const m of html.matchAll(ROW)) {
    const slug = m[1].trim();
    const name = m[2].trim();
    const key = name.toLowerCase();
    if (!name || seen.has(key)) continue; // first occurrence wins (the ranked ladder)
    seen.add(key);
    ranks.push({ name, slug });
  }
  return ranks;
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const format = url.searchParams.get("format") === "Singles" ? "single" : "double";

  try {
    // First hit discovers the available seasons (the default page is an older
    // season, so we re-fetch the latest unless it happens to be the default).
    const first = await fetchPage(format, null);
    if (!first) return NextResponse.json({ ranks: [] });

    const season = latestSeason(first);
    let html = first;
    if (season && !first.includes(`season=${season}`)) {
      const latest = await fetchPage(format, season);
      if (latest) html = latest;
    }

    const ranks = parseRows(html);
    // Guard against a markup change silently returning a near-empty list.
    if (ranks.length < 30) return NextResponse.json({ ranks: [] });

    return NextResponse.json({ format, season, ranks }, {
      headers: { "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=604800" },
    });
  } catch {
    return NextResponse.json({ ranks: [] });
  }
}
