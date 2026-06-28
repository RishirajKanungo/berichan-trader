// Team sharing: import from / export to Poképaste, and build shareable app links
// that load a team straight from the URL (?paste=<id>).

export interface PasteData { paste: string; title: string }

/** Fetch a Poképaste's Showdown text via our proxy. Accepts a URL or bare id. */
export async function importFromPokepaste(urlOrId: string): Promise<PasteData> {
  const r = await fetch(`/api/pokepaste?url=${encodeURIComponent(urlOrId)}`);
  const d = await r.json();
  if (!r.ok) throw new Error(d?.error || "Couldn't import that Poképaste.");
  return { paste: d.paste ?? "", title: d.title ?? "" };
}

/** Create a Poképaste from Showdown text; returns its id + url. */
export async function exportToPokepaste(paste: string, title = ""): Promise<{ id: string; url: string }> {
  const r = await fetch("/api/pokepaste", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paste, title }),
  });
  const d = await r.json();
  if (!r.ok) throw new Error(d?.error || "Couldn't create a shareable link.");
  return { id: d.id, url: d.url };
}

/** A link to this app that auto-loads the given Poképaste id. */
export function appShareLink(pasteId: string): string {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}/?paste=${pasteId}`;
}
