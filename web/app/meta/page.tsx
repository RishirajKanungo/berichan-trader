"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Boxes, Search, TrendingUp } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useTeam } from "@/components/team";
import { MetaDetail } from "@/components/MetaDetail";
import { MetaSprite } from "@/components/MetaSprite";
import {
  getMetaIndex, getUsageRanks, normalizeMonName,
  type MetaFormat, type MetaIndexEntry,
} from "@/lib/meta";
import { typeColor, typeGradient } from "@/lib/typeColors";
import type { Pokemon } from "@/lib/types";

type SortKey = "usage" | "bst" | "name" | "spe" | "atk" | "spa";
const SORTS: { key: SortKey; label: string; statIdx?: number }[] = [
  { key: "usage", label: "Usage" },
  { key: "bst", label: "Base Stat Total" },
  { key: "name", label: "Name (A–Z)" },
  { key: "spe", label: "Speed", statIdx: 5 },
  { key: "atk", label: "Attack", statIdx: 1 },
  { key: "spa", label: "Sp. Atk", statIdx: 3 },
];

type Ranked = MetaIndexEntry & { rank: number | null };

const MEDAL = ["#f5c518", "#c0c6d0", "#cd7f32"]; // gold / silver / bronze for the top 3

export default function MetaPage() {
  const { team, setTeam } = useTeam();
  const [all, setAll] = useState<MetaIndexEntry[] | null>(null);
  const [ranksByFormat, setRanksByFormat] = useState<Record<MetaFormat, Map<string, number> | undefined>>(
    {} as Record<MetaFormat, Map<string, number> | undefined>,
  );
  const [format, setFormat] = useState<MetaFormat>("Doubles");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("usage");
  const [selected, setSelected] = useState<MetaIndexEntry | null>(null);
  const [toast, setToast] = useState("");

  const flash = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 2200); };

  useEffect(() => { getMetaIndex().then(setAll); }, []);
  useEffect(() => {
    let active = true;
    getUsageRanks(format).then((m) => { if (active) setRanksByFormat((prev) => ({ ...prev, [format]: m })); });
    return () => { active = false; };
  }, [format]);

  const ranks = ranksByFormat[format] ?? null;
  const ranksLoaded = ranksByFormat[format] !== undefined;
  const usageAvailable = (ranks?.size ?? 0) > 0;

  const byName = useMemo(() => {
    const m = new Map<string, MetaIndexEntry>();
    for (const e of all ?? []) m.set(e.name.toLowerCase(), e);
    return m;
  }, [all]);

  const shown = useMemo<Ranked[]>(() => {
    if (!all) return [];
    const q = query.trim().toLowerCase();
    const list: Ranked[] = all
      .filter((e) => e.formats.includes(format) && (!q || e.name.toLowerCase().includes(q)))
      .map((e) => ({ ...e, rank: ranks?.get(normalizeMonName(e.name)) ?? null }));

    const def = SORTS.find((s) => s.key === sort)!;
    const effective: SortKey = sort === "usage" && ranksLoaded && !usageAvailable ? "bst" : sort;
    list.sort((a, b) => {
      if (effective === "usage") {
        // Ranked Pokémon first (ascending rank), then the rest by BST.
        if (a.rank == null && b.rank == null) return b.bst - a.bst;
        if (a.rank == null) return 1;
        if (b.rank == null) return -1;
        return a.rank - b.rank;
      }
      if (effective === "name") return a.name.localeCompare(b.name);
      if (def.statIdx !== undefined) return (b.stats[def.statIdx] ?? 0) - (a.stats[def.statIdx] ?? 0);
      return b.bst - a.bst;
    });
    return list;
  }, [all, format, query, sort, ranks, ranksLoaded, usageAvailable]);

  const usageUnavailable = ranksLoaded && !usageAvailable;

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
              Pokémon Champions · {format} · {usageAvailable ? "ranked by usage" : "what people are running"}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="muted text-sm">{team.length}/6 on team</span>
            <Link href="/" className="btn"><Boxes size={16} /> Team Builder</Link>
          </div>
        </header>

        {/* Controls bar */}
        <div className="surface mb-4 flex flex-wrap items-center gap-2 rounded-xl p-2">
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
            {SORTS.map((s) => (
              <option key={s.key} value={s.key} disabled={s.key === "usage" && usageUnavailable}>
                Sort: {s.label}{s.key === "usage" && usageUnavailable ? " (unavailable)" : ""}
              </option>
            ))}
          </select>
        </div>

        {all === null ? (
          <div className="card muted p-10 text-center">Loading the meta…</div>
        ) : shown.length === 0 ? (
          <div className="card muted p-10 text-center">No Pokémon match “{query}” in {format}.</div>
        ) : (
          <>
            <p className="muted mb-2 flex items-center gap-1.5 text-xs">
              {usageAvailable && <TrendingUp size={13} />}
              {shown.length} tracked Pokémon{usageAvailable ? ", ranked by ladder usage" : ""} · click one for its most-used moves, items, abilities, spreads &amp; partners — then build a set and add it to your team.
            </p>
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
              {shown.map((e) => (
                <MetaCard key={e.slug} entry={e} onClick={() => setSelected(e)} />
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
          rank={ranks?.get(normalizeMonName(selected.name)) ?? null}
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

function MetaCard({ entry, onClick }: { entry: Ranked; onClick: () => void }) {
  const top = entry.rank != null && entry.rank <= 3 ? MEDAL[entry.rank - 1] : null;
  return (
    <button
      className="card group relative flex items-center gap-2.5 overflow-hidden p-2.5 text-left transition-all duration-150 hover:-translate-y-0.5 hover:shadow-lg"
      style={{ borderColor: top ?? "var(--border)" }}
      onClick={onClick}
    >
      {/* Type-tinted accent strip down the left edge */}
      <span className="absolute inset-y-0 left-0 w-1" style={{ background: typeGradient(entry.types) }} />

      {/* Usage rank badge */}
      {entry.rank != null && (
        <span
          className="absolute right-1.5 top-1.5 rounded-md px-1.5 py-0.5 text-[10px] font-black tabular-nums"
          style={
            top
              ? { background: top, color: "#1b1b22" }
              : { background: "var(--panel)", color: "var(--muted)" }
          }
          title={`Usage rank #${entry.rank}`}
        >
          #{entry.rank}
        </span>
      )}

      <MetaSprite name={entry.name} size={52} className="shrink-0 transition-transform duration-150 group-hover:scale-110" />
      <div className="min-w-0">
        <div className="truncate pr-6 text-sm font-bold">{entry.name}</div>
        <div className="mt-0.5 flex items-center gap-1">
          {entry.types.map((t) => (
            <span
              key={t}
              className="rounded px-1 py-px text-[9px] font-bold uppercase tracking-wide text-white"
              style={{ background: typeColor(t) }}
            >
              {t}
            </span>
          ))}
        </div>
        <div className="muted mt-0.5 text-[10px] tabular-nums">BST {entry.bst}</div>
      </div>
    </button>
  );
}
