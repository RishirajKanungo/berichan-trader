// Poképaste bridge (CORS + POST happen server-side).
//   GET  /api/pokepaste?url=<paste url or id>  → { paste, title }
//   POST /api/pokepaste { paste, title }        → { id, url }
// pokepast.es serves a paste's data at <url>/json and creates pastes via a
// form POST to /create that 302-redirects to the new paste.

import { NextResponse } from "next/server";

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36";

/** Pull the paste id out of a full URL, a bare id, or a /raw|/json variant. */
function pasteId(input: string): string | null {
  const s = input.trim();
  const m = s.match(/pokepast\.es\/([A-Za-z0-9]+)/) ?? s.match(/^([A-Za-z0-9]{6,})$/);
  return m ? m[1] : null;
}

export async function GET(req: Request) {
  const id = pasteId(new URL(req.url).searchParams.get("url") || "");
  if (!id) return NextResponse.json({ error: "Not a valid Poképaste link." }, { status: 400 });
  try {
    const r = await fetch(`https://pokepast.es/${id}/json`, { headers: { "User-Agent": UA }, signal: AbortSignal.timeout(12000) });
    if (!r.ok) return NextResponse.json({ error: "Poképaste not found." }, { status: 404 });
    const d = await r.json();
    return NextResponse.json({ paste: d.paste ?? "", title: d.title ?? "" }, {
      headers: { "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=604800" },
    });
  } catch {
    return NextResponse.json({ error: "Couldn't reach Poképaste." }, { status: 502 });
  }
}

export async function POST(req: Request) {
  try {
    const { paste, title } = await req.json();
    if (!paste || typeof paste !== "string") return NextResponse.json({ error: "Nothing to share." }, { status: 400 });
    const body = new URLSearchParams({ paste, title: title || "", author: "", notes: "" });
    // Let fetch follow the create → paste redirect; the final URL carries the id.
    const r = await fetch("https://pokepast.es/create", {
      method: "POST",
      headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded" },
      body,
      signal: AbortSignal.timeout(12000),
    });
    const id = pasteId(r.url) ?? (r.headers.get("location") ? pasteId(r.headers.get("location")!) : null);
    if (!id) return NextResponse.json({ error: "Poképaste didn't return a link." }, { status: 502 });
    return NextResponse.json({ id, url: `https://pokepast.es/${id}` });
  } catch {
    return NextResponse.json({ error: "Couldn't reach Poképaste." }, { status: 502 });
  }
}
