// Cached proxy for competitive usage data (championsbattledata.com).
// Edge-cached (s-maxage) so repeated/other-user requests are served by Vercel's
// CDN and the upstream is hit at most ~once/day per Pokémon+format.

import { NextResponse } from "next/server";

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36";

interface Row {
  category?: string;
  name?: string;
  percentage_value?: number;
  hp_points?: number; attack_points?: number; defense_points?: number;
  sp_atk_points?: number; sp_def_points?: number; speed_points?: number;
}

function parseRows(rows: Row[]) {
  const out = {
    moves: [] as [string, number][],
    items: [] as [string, number][],
    abilities: [] as [string, number][],
    natures: [] as [string, number][],
    spreads: [] as [Record<string, number>, number][],
    teammates: [] as string[],
  };
  for (const r of rows) {
    const pct = r.percentage_value ?? 0;
    switch (r.category) {
      case "move": out.moves.push([r.name ?? "", pct]); break;
      case "held_item": out.items.push([r.name ?? "", pct]); break;
      case "ability": out.abilities.push([r.name ?? "", pct]); break;
      case "stat_alignment": out.natures.push([r.name ?? "", pct]); break;
      // Teammates are ranked but carry no percentage upstream — keep the order.
      case "teammate": if (r.name) out.teammates.push(r.name); break;
      case "stat_points":
        out.spreads.push([{
          HP: r.hp_points || 0, Atk: r.attack_points || 0, Def: r.defense_points || 0,
          SpA: r.sp_atk_points || 0, SpD: r.sp_def_points || 0, Spe: r.speed_points || 0,
        }, pct]);
        break;
    }
  }
  return out;
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const mon = (url.searchParams.get("mon") || "").toLowerCase();
  const format = url.searchParams.get("format") === "Singles" ? "Singles" : "Doubles";
  if (!mon) return NextResponse.json({ available: false }, { status: 400 });

  try {
    const upstream = `https://championsbattledata.com/api/battle/${format}/${encodeURIComponent(mon)}?season=Current`;
    // championsbattledata is behind Cloudflare, which blocks UA-less / datacenter
    // requests (Vercel) — send a browser User-Agent like the usage route does.
    const r = await fetch(upstream, {
      headers: { "User-Agent": UA, Accept: "application/json" },
      signal: AbortSignal.timeout(12000),
    });
    if (!r.ok) return NextResponse.json({ available: false });
    const data = await r.json();
    const body = { available: true, ...parseRows(data.rows || []) };
    return NextResponse.json(body, {
      headers: { "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=604800" },
    });
  } catch {
    return NextResponse.json({ available: false });
  }
}
