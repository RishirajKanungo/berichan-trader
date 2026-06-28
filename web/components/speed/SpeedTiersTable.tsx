"use client";

import { useMemo, useState } from "react";
import { Search, Swords, X } from "lucide-react";
import { MetaSprite } from "@/components/MetaSprite";
import { Combobox } from "@/components/ui/Combobox";
import { typeColor } from "@/lib/typeColors";
import { DEFAULT_SORT_COL, SPEED_COLS, speedStat, type NatureDir } from "@/lib/speed";
import { normalizeMonName, type MetaIndexEntry } from "@/lib/meta";

type Row = MetaIndexEntry & { rank: number | null; vals: Record<string, number> };

export function SpeedTiersTable({
  entries, format, ranks,
}: {
  entries: MetaIndexEntry[];
  format: "Doubles" | "Singles";
  ranks: Map<string, number> | null;
}) {
  const [query, setQuery] = useState("");
  const [sortCol, setSortCol] = useState(DEFAULT_SORT_COL);

  // Comparison Pokémon ("my mon vs the field").
  const [cmpName, setCmpName] = useState("");
  const [cmpDir, setCmpDir] = useState<NatureDir>("plus");
  const [cmpSp, setCmpSp] = useState(32);
  const [cmpScarf, setCmpScarf] = useState(false);

  const names = useMemo(() => entries.map((e) => e.name).sort(), [entries]);
  const cmpEntry = useMemo(
    () => entries.find((e) => e.name.toLowerCase() === cmpName.trim().toLowerCase()) ?? null,
    [entries, cmpName],
  );
  const cmpSpeed = useMemo(() => {
    if (!cmpEntry) return null;
    const s = speedStat(cmpEntry.stats[5], cmpSp, cmpDir);
    return cmpScarf ? Math.floor(s * 1.5) : s;
  }, [cmpEntry, cmpSp, cmpDir, cmpScarf]);

  const rows = useMemo<Row[]>(() => {
    const q = query.trim().toLowerCase();
    const list = entries
      .filter((e) => e.formats.includes(format) && (!q || e.name.toLowerCase().includes(q)))
      .map((e) => {
        const vals: Record<string, number> = {};
        for (const c of SPEED_COLS) vals[c.key] = c.calc(e.stats[5]);
        // Megas inherit their base species' usage rank (you bring the base mon).
        return { ...e, rank: ranks?.get(normalizeMonName(e.baseName ?? e.name)) ?? null, vals };
      });
    list.sort((a, b) => b.vals[sortCol] - a.vals[sortCol] || a.name.localeCompare(b.name));
    return list;
  }, [entries, format, query, sortCol, ranks]);

  return (
    <div>
      {/* Comparison builder */}
      <div className="card mb-3 p-3">
        <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
          <Swords size={15} /> Compare a Pokémon vs the field
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[180px] flex-1">
            <label className="muted mb-1 block text-[11px]">Pokémon</label>
            <Combobox value={cmpName} onChange={setCmpName} options={names} placeholder="e.g. Garchomp" />
          </div>
          <div>
            <label className="muted mb-1 block text-[11px]">Speed nature</label>
            <div className="flex gap-1">
              {([["plus", "+"], ["neutral", "0"], ["minus", "−"]] as const).map(([d, sym]) => (
                <button
                  key={d}
                  className="btn px-3"
                  onClick={() => setCmpDir(d)}
                  style={cmpDir === d ? { background: "var(--accent)", color: "var(--on-accent)", borderColor: "transparent" } : undefined}
                >
                  {sym}
                </button>
              ))}
            </div>
          </div>
          <div className="w-28">
            <label className="muted mb-1 block text-[11px]">SP {cmpSp}</label>
            <input type="range" min={0} max={32} value={cmpSp} onChange={(e) => setCmpSp(Number(e.target.value))} className="w-full" style={{ accentColor: "var(--accent)" }} />
          </div>
          <label className="flex items-center gap-1.5 pb-2 text-sm">
            <input type="checkbox" checked={cmpScarf} onChange={(e) => setCmpScarf(e.target.checked)} style={{ accentColor: "var(--accent)" }} /> Scarf
          </label>
          {cmpEntry && cmpSpeed != null && (
            <div className="ml-auto flex items-center gap-2 pb-1">
              <div className="accent-text text-right">
                <span className="text-2xl font-black tabular-nums">{cmpSpeed}</span>
                <span className="muted ml-1 text-xs">Spe</span>
              </div>
              <button className="btn btn-icon" onClick={() => setCmpName("")} aria-label="Clear"><X size={14} /></button>
            </div>
          )}
        </div>
        {cmpSpeed != null && (
          <p className="muted mt-2 text-xs">
            Rows tinted <span style={{ color: "#3fa129" }}>green</span> are slower than your {cmpSpeed} Spe (you move first), <span style={{ color: "#e62829" }}>red</span> are faster, in the <b>{SPEED_COLS.find((c) => c.key === sortCol)?.label}</b> column.
          </p>
        )}
      </div>

      {/* Search */}
      <div className="relative mb-2 max-w-xs">
        <Search size={15} className="muted pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2" />
        <input className="input pl-8" placeholder="Filter Pokémon…" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="max-h-[68vh] overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead className="sticky top-0 z-10" style={{ background: "var(--surface)" }}>
              <tr>
                <th className="px-3 py-2 text-left font-semibold">Pokémon</th>
                {SPEED_COLS.map((c) => (
                  <th
                    key={c.key}
                    className="group relative cursor-pointer select-none px-2 py-2 text-right font-semibold whitespace-nowrap"
                    title={`${c.full} — ${c.help}`}
                    onClick={() => setSortCol(c.key)}
                    style={sortCol === c.key ? { color: "var(--accent)" } : undefined}
                  >
                    {c.label}{sortCol === c.key ? " ▾" : ""}
                    {/* Hover tooltip — explains the abbreviated column with an example. */}
                    <span
                      className="surface pointer-events-none invisible absolute right-0 top-full z-30 mt-1 w-56 whitespace-normal rounded-lg p-2.5 text-left text-[11px] font-normal normal-case opacity-0 shadow-xl transition-opacity duration-150 group-hover:visible group-hover:opacity-100"
                    >
                      <b>{c.full}</b>
                      <span className="muted mt-1 block leading-snug">{c.help}</span>
                      <span className="muted mt-1.5 block text-[10px]">Click the header to sort by this tier.</span>
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const cmpVal = r.vals[sortCol];
                let tint: string | undefined;
                if (cmpSpeed != null) {
                  tint =
                    cmpSpeed > cmpVal ? "color-mix(in srgb, #3fa129 13%, transparent)"
                    : cmpSpeed < cmpVal ? "color-mix(in srgb, #e62829 12%, transparent)"
                    : "color-mix(in srgb, #fac000 16%, transparent)";
                }
                return (
                  <tr key={r.slug} className="border-t" style={{ borderColor: "var(--border)", background: tint }}>
                    <td className="px-3 py-1.5">
                      <div className="flex items-center gap-2">
                        <MetaSprite name={r.name} src={r.sprite} size={32} className="shrink-0" />
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            {r.rank != null && <span className="muted text-[10px] tabular-nums">#{r.rank}</span>}
                            <span className="truncate font-medium">{r.name}</span>
                            {r.form && <span className="rounded px-1 text-[8px] font-bold uppercase text-white" style={{ background: "#9141cb" }}>{r.form}</span>}
                          </div>
                          <div className="mt-0.5 flex gap-1">
                            {r.types.map((t) => (
                              <span key={t} className="rounded px-1 text-[8px] font-bold uppercase text-white" style={{ background: typeColor(t) }}>{t}</span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </td>
                    {SPEED_COLS.map((c) => (
                      <td
                        key={c.key}
                        className="px-2 py-1.5 text-right tabular-nums"
                        style={sortCol === c.key ? { fontWeight: 700 } : { color: "var(--muted)" }}
                      >
                        {r.vals[c.key]}
                      </td>
                    ))}
                  </tr>
                );
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={SPEED_COLS.length + 1} className="muted p-8 text-center text-sm">
                    No Pokémon to show{query ? ` for “${query}”` : ""} in {format}.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <p className="muted mt-2 text-xs">{rows.length} Pokémon · all values at Level 50. Click a column header to sort by that tier.</p>
    </div>
  );
}
