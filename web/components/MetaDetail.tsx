"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, Plus } from "lucide-react";
import { getMeta, recommended, type MetaData, type MetaFormat, type MetaIndexEntry } from "@/lib/meta";
import { getMove, getSpecies, itemIconUrl, moveSummary } from "@/lib/data";
import { categoryIconUrl, typeIconUrl } from "@/lib/assets";
import {
  calcAllStatsSp, LABEL_TO_KEY, spToEv, STAT_KEYS, STAT_ORDER, spSpreadToEvs,
  type StatKey, type StatLabel,
} from "@/lib/stats";
import { chatMessage, newPokemon, syncLines, toShowdown, TWITCH_MAX_CHAT_LENGTH } from "@/lib/teamParser";
import type { Pokemon } from "@/lib/types";
import { Modal } from "./ui/Modal";
import { MetaSprite } from "./MetaSprite";

const TYPES = ["Normal","Fire","Water","Electric","Grass","Ice","Fighting","Poison","Ground","Flying","Psychic","Bug","Rock","Ghost","Dragon","Dark","Steel","Fairy","Stellar"];

const emptySpread = (): Record<StatLabel, number> => ({ HP: 0, Atk: 0, Def: 0, SpA: 0, SpD: 0, Spe: 0 });

export function MetaDetail({
  entry, format, setFormat, onAdd, canAdd, onSelectMon, onClose,
}: {
  entry: MetaIndexEntry;
  format: MetaFormat;
  setFormat: (f: MetaFormat) => void;
  onAdd: (mon: Pokemon) => void;
  canAdd: boolean;
  onSelectMon: (name: string) => void;
  onClose: () => void;
}) {
  const speciesName = getSpecies(entry.name)?.name ?? entry.name;
  const baseStats = useMemo<Record<StatKey, number>>(() => ({
    hp: entry.stats[0] ?? 0, atk: entry.stats[1] ?? 0, def: entry.stats[2] ?? 0,
    spa: entry.stats[3] ?? 0, spd: entry.stats[4] ?? 0, spe: entry.stats[5] ?? 0,
  }), [entry]);

  const [meta, setMeta] = useState<MetaData | null>(null);
  const [loadedFor, setLoadedFor] = useState("");
  const loadKey = `${entry.name}:${format}`;
  const loading = meta === null || loadedFor !== loadKey;

  // The user's in-progress set, seeded from the most-used ("recommended") set.
  const [moves, setMoves] = useState<string[]>([]);
  const [ability, setAbility] = useState("");
  const [item, setItem] = useState("");
  const [nature, setNature] = useState("");
  const [spread, setSpread] = useState<Record<StatLabel, number>>(emptySpread);
  const [tera, setTera] = useState("");
  const [level, setLevel] = useState(50);

  useEffect(() => {
    let active = true;
    getMeta(entry.name, format).then((m) => {
      if (!active) return;
      setMeta(m);
      setLoadedFor(`${entry.name}:${format}`);
      // Seed the builder with what people actually run for this format.
      const rec = recommended(m);
      setMoves(rec.moves);
      setAbility(rec.ability);
      setItem(rec.item);
      setNature(rec.nature);
      setSpread(rec.spread ? { ...rec.spread } : emptySpread());
    });
    return () => { active = false; };
  }, [entry.name, format]);

  const toggleMove = (mv: string) =>
    setMoves((prev) => prev.includes(mv) ? prev.filter((m) => m !== mv) : (prev.length >= 4 ? prev : [...prev, mv]));

  const spreadKey = (s: Record<StatLabel, number>) => STAT_ORDER.map((l) => s[l] ?? 0).join("/");
  const sameSpread = (s: Record<StatLabel, number>) => spreadKey(s) === spreadKey(spread);

  const applyRecommended = () => {
    if (!meta?.available) return;
    const rec = recommended(meta);
    setMoves(rec.moves);
    setAbility(rec.ability);
    setItem(rec.item);
    setNature(rec.nature);
    setSpread(rec.spread ? { ...rec.spread } : emptySpread());
    setTera("");
  };

  const build = (): Pokemon =>
    syncLines(newPokemon({
      species: speciesName,
      nickname: speciesName,
      item: item.trim(),
      ability: ability.trim(),
      level,
      teraType: tera.trim(),
      nature: nature.trim(),
      evs: spSpreadToEvs(spread),
      moves: moves.map((m) => m.trim()).filter(Boolean),
    }));

  const preview = build();
  const charLen = chatMessage(preview).length;
  const over = charLen > TWITCH_MAX_CHAT_LENGTH - 12;
  const bst = STAT_KEYS.reduce((s, k) => s + (baseStats[k] || 0), 0);
  const finalStats = calcAllStatsSp(baseStats, spread, level, nature);
  const hasSpread = STAT_ORDER.some((l) => (spread[l] || 0) > 0);

  return (
    <Modal
      open
      onClose={onClose}
      className="max-w-5xl"
      title={
        <div className="flex items-center gap-3">
          <MetaSprite name={entry.name} size={40} />
          <div>
            <div className="leading-tight">{speciesName}</div>
            <div className="muted flex items-center gap-1.5 text-xs font-normal">
              {entry.types.map((t) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={t} src={typeIconUrl(t)} alt={t} className="h-3.5" />
              ))}
              <span className="ml-1">BST {bst}</span>
            </div>
          </div>
        </div>
      }
      footer={
        <>
          <span className="mr-auto text-xs" style={{ color: over ? "#e74c3c" : "var(--muted)" }}>
            {charLen} / {TWITCH_MAX_CHAT_LENGTH} chars
          </span>
          <button className="btn" onClick={onClose}>Close</button>
          <button
            className="btn btn-primary"
            disabled={!canAdd || !moves.filter(Boolean).length}
            onClick={() => { onAdd(build()); }}
            title={!canAdd ? "Team is full (6)" : moves.filter(Boolean).length ? "" : "Pick at least one move"}
          >
            <Plus size={16} /> Add to team
          </button>
        </>
      }
    >
      <div className="mb-4 flex flex-wrap items-center gap-3">
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
        <span className="muted text-xs">Tap anything below to build your set — it&apos;s pre-filled with the most-used set.</span>
        <button className="btn ml-auto" onClick={applyRecommended} disabled={!meta?.available}>Reset to most-used</button>
      </div>

      {!meta || loading ? (
        <p className="muted py-10 text-center text-sm">Loading usage data…</p>
      ) : !meta.available ? (
        <p className="muted py-10 text-center text-sm">No usage data for {speciesName} in {format}.</p>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
          {/* What people run — selectable */}
          <div className="space-y-4">
            <Section title="Moves" hint={`${moves.filter(Boolean).length}/4 selected`}>
              <div className="grid gap-1.5 sm:grid-cols-2">
                {meta.moves.slice(0, 18).map(([name, pct]) => {
                  const m = getMove(name);
                  const sel = moves.includes(name);
                  const dim = !sel && moves.filter(Boolean).length >= 4;
                  return (
                    <SelRow key={name} selected={sel} dim={dim} pct={pct} onClick={() => toggleMove(name)}>
                      {m && (
                        <>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={typeIconUrl(m.type)} alt={m.type} className="h-3.5 shrink-0" />
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={categoryIconUrl(m.category)} alt={m.category} className="h-3.5 shrink-0" title={moveSummary(name)} />
                        </>
                      )}
                      <span className="truncate">{name}</span>
                    </SelRow>
                  );
                })}
              </div>
            </Section>

            <div className="grid gap-4 sm:grid-cols-2">
              <Section title="Abilities">
                {meta.abilities.slice(0, 5).map(([name, pct]) => (
                  <SelRow key={name} selected={ability === name} pct={pct} onClick={() => setAbility(name)}>
                    <span className="truncate">{name}</span>
                  </SelRow>
                ))}
              </Section>

              <Section title="Items">
                {meta.items.slice(0, 6).map(([name, pct]) => {
                  const icon = itemIconUrl(name);
                  return (
                    <SelRow key={name} selected={item === name} pct={pct} onClick={() => setItem(item === name ? "" : name)}>
                      {icon && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={icon} alt="" width={18} height={18} className="shrink-0" />
                      )}
                      <span className="truncate">{name}</span>
                    </SelRow>
                  );
                })}
              </Section>

              <Section title="Natures">
                {meta.natures.slice(0, 6).map(([name, pct]) => (
                  <SelRow key={name} selected={nature === name} pct={pct} onClick={() => setNature(nature === name ? "" : name)}>
                    <span className="truncate">{name}</span>
                  </SelRow>
                ))}
              </Section>

              <Section title="Stat spreads (SP)">
                {meta.spreads.slice(0, 6).map(([sp, pct], i) => (
                  <SelRow key={i} selected={sameSpread(sp)} pct={pct} onClick={() => setSpread({ ...sp })}>
                    <span className="truncate font-mono text-[11px]">{spreadKey(sp)}</span>
                  </SelRow>
                ))}
              </Section>
            </div>

            {meta.teammates.length > 0 && (
              <Section title="Common teammates" hint="tap to view">
                <div className="flex flex-wrap gap-2">
                  {meta.teammates.slice(0, 10).map((name) => (
                    <button
                      key={name}
                      className="chip flex-col gap-0.5 py-1.5"
                      style={{ height: "auto" }}
                      onClick={() => onSelectMon(name)}
                      title={`View ${name}`}
                    >
                      <MetaSprite name={name} size={40} />
                      <span className="max-w-[72px] truncate text-[10px]">{name}</span>
                    </button>
                  ))}
                </div>
              </Section>
            )}
          </div>

          {/* Your set — sticky summary + final stats + preview */}
          <div className="lg:sticky lg:top-0 lg:self-start">
            <div className="card p-3">
              <div className="mb-2 text-sm font-semibold">Your set</div>

              <div className="mb-2 flex flex-wrap gap-1.5">
                {moves.filter(Boolean).length === 0 && <span className="muted text-xs">No moves yet</span>}
                {moves.filter(Boolean).map((m) => (
                  <button key={m} className="chip" onClick={() => toggleMove(m)} title="Remove">
                    {m} <span className="muted">×</span>
                  </button>
                ))}
              </div>

              <dl className="muted space-y-0.5 text-xs">
                <Row label="Ability" value={ability} />
                <Row label="Item" value={item || "—"} />
                <Row label="Nature" value={nature || "—"} />
                <Row label="Tera" value={tera || "—"} />
              </dl>

              {/* Final stats from the chosen spread + nature. */}
              <div className="mt-3 space-y-1">
                {STAT_ORDER.map((label) => {
                  const total = finalStats[LABEL_TO_KEY[label]];
                  return (
                    <div key={label} className="flex items-center gap-2">
                      <span className="muted w-8 text-[10px] font-bold">{label}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: "var(--panel)" }}>
                        <div className="h-full rounded-full" style={{ width: `${Math.min(100, (total / 255) * 100)}%`, background: "var(--accent)" }} />
                      </div>
                      <span className="w-7 text-right text-[10px] font-semibold">{total}</span>
                      <span className="muted w-9 text-right text-[10px]">{hasSpread ? `${spToEv(spread[label] || 0)}ev` : ""}</span>
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2">
                <label className="block">
                  <span className="muted mb-0.5 block text-[10px] font-medium">Tera Type</span>
                  <select className="input py-1 text-xs" value={tera} onChange={(e) => setTera(e.target.value)}>
                    <option value="">—</option>
                    {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="muted mb-0.5 block text-[10px] font-medium">Level</span>
                  <input type="number" min={1} max={100} className="input py-1 text-xs" value={level} onChange={(e) => setLevel(Number(e.target.value) || 50)} />
                </label>
              </div>

              <details className="mt-3">
                <summary className="muted cursor-pointer text-[11px]">Showdown preview</summary>
                <pre className="panel mt-1 overflow-x-auto rounded-md p-2 text-[10px] leading-snug">{toShowdown(preview)}</pre>
              </details>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-sm font-semibold">{title}</span>
        {hint && <span className="muted text-[11px]">{hint}</span>}
      </div>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function SelRow({
  selected, dim, pct, onClick, children,
}: {
  selected: boolean;
  dim?: boolean;
  pct: number;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={dim}
      className="flex w-full items-center gap-1.5 rounded-md border px-2 py-1.5 text-left text-xs transition-colors disabled:opacity-40"
      style={{
        borderColor: selected ? "var(--accent)" : "var(--border)",
        background: selected ? "color-mix(in srgb, var(--accent) 16%, transparent)" : "var(--panel)",
      }}
    >
      <span className="flex min-w-0 flex-1 items-center gap-1.5">{children}</span>
      {pct > 0 && <span className="muted shrink-0 text-[10px]">{Math.round(pct)}%</span>}
      {selected && <Check size={13} className="shrink-0" style={{ color: "var(--accent)" }} />}
    </button>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt>{label}</dt>
      <dd className="truncate text-right font-medium" style={{ color: "var(--text)" }}>{value}</dd>
    </div>
  );
}
