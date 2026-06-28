"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Boxes, Search } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useTeam } from "@/components/team";
import { MetaDetail } from "@/components/MetaDetail";
import { MetaSprite } from "@/components/MetaSprite";
import { getMetaIndex, type MetaFormat, type MetaIndexEntry } from "@/lib/meta";
import { typeIconUrl } from "@/lib/assets";
import type { Pokemon } from "@/lib/types";

type SortKey = "bst" | "name" | "spe" | "atk" | "spa";
const SORTS: { key: SortKey; label: string; statIdx?: number }[] = [
  { key: "bst", label: "Base Stat Total" },
  { key: "name", label: "Name (A–Z)" },
  { key: "spe", label: "Speed", statIdx: 5 },
  { key: "atk", label: "Attack", statIdx: 1 },
  { key: "spa", label: "Sp. Atk", statIdx: 3 },
];

export default function MetaPage() {
  const { team, setTeam } = useTeam();
  const [all, setAll] = useState<MetaIndexEntry[] | null>(null);
  const [format, setFormat] = useState<MetaFormat>("Doubles");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("bst");
  const [selected, setSelected] = useState<MetaIndexEntry | null>(null);
  const [toast, setToast] = useState("");

  const flash = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 2200); };

  useEffect(() => { getMetaIndex().then(setAll); }, []);

  const byName = useMemo(() => {
    const m = new Map<string, MetaIndexEntry>();
    for (const e of all ?? []) m.set(e.name.toLowerCase(), e);
    return m;
  }, [all]);

  const shown = useMemo(() => {
    if (!all) return [];
    const q = query.trim().toLowerCase();
    const list = all.filter((e) =>
      e.formats.includes(format) && (!q || e.name.toLowerCase().includes(q)),
    );
    const def = SORTS.find((s) => s.key === sort)!;
    list.sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      if (def.statIdx !== undefined) return (b.stats[def.statIdx] ?? 0) - (a.stats[def.statIdx] ?? 0);
      return b.bst - a.bst;
    });
    return list;
  }, [all, format, query, sort]);

  const canAdd = team.length < 6;

  const addToTeam = (mon: Pokemon) => {
    if (team.length >= 6) { flash("Team is full (6)."); return; }
    setTeam((prev) => [...prev, mon]);
    flash(`Added ${mon.species} to your team.`);
  };

  const selectByName = (name: string) => {
    const e = byName.get(name.toLowerCase());
    if (e) setSelected(e);
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl">
        <header className="mb-5 flex flex-wrap items-center gap-3">
          <div>
            <h1 className="text-2xl font-bold">Meta</h1>
            <p className="muted text-sm">
              Pokémon Champions · {format} · what people are running
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="muted text-sm">{team.length}/6 on team</span>
            <Link href="/" className="btn"><Boxes size={16} /> Team Builder</Link>
          </div>
        </header>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <div className="flex gap-1">
            {(["Doubles", "Singles"] as const).map((f) => (
              <button
                key={f}
                className="btn"
                onClick={() => setFormat(f)}
                style={format === f ? { background: "var(--accent)", color: "var(--on-accent)", borderColor: "transparent" } : undefined}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="relative min-w-[180px] flex-1">
            <Search size={15} className="muted pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              className="input pl-8"
              placeholder="Search Pokémon…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <select className="input w-auto" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
            {SORTS.map((s) => <option key={s.key} value={s.key}>Sort: {s.label}</option>)}
          </select>
        </div>

        {all === null ? (
          <div className="card muted p-10 text-center">Loading the meta…</div>
        ) : shown.length === 0 ? (
          <div className="card muted p-10 text-center">No Pokémon match “{query}” in {format}.</div>
        ) : (
          <>
            <p className="muted mb-2 text-xs">
              {shown.length} tracked Pokémon · click one to see its most-used moves, items, abilities, spreads &amp; partners — then build a set and add it to your team.
            </p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
              {shown.map((e) => (
                <button
                  key={e.slug}
                  className="card flex items-center gap-2.5 p-2.5 text-left transition-colors hover:border-[var(--accent)]"
                  style={{ borderColor: "var(--border)" }}
                  onClick={() => setSelected(e)}
                >
                  <MetaSprite name={e.name} size={48} className="shrink-0" />
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{e.name}</div>
                    <div className="mt-0.5 flex items-center gap-1">
                      {e.types.map((t) => (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img key={t} src={typeIconUrl(t)} alt={t} className="h-3.5" />
                      ))}
                    </div>
                    <div className="muted mt-0.5 text-[10px]">BST {e.bst}</div>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Remount per Pokémon so the set builder always reflects the chosen one. */}
      {selected && (
        <MetaDetail
          key={selected.slug}
          entry={selected}
          format={format}
          setFormat={setFormat}
          onAdd={addToTeam}
          canAdd={canAdd}
          onSelectMon={selectByName}
          onClose={() => setSelected(null)}
        />
      )}

      {toast && (
        <div className="surface fixed bottom-5 left-1/2 -translate-x-1/2 rounded-lg px-4 py-2 text-sm shadow-xl">{toast}</div>
      )}
    </AppShell>
  );
}
