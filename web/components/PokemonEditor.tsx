"use client";

import { useEffect, useMemo, useState } from "react";
import {
  abilityDesc, allItems, describeItem, getMove, itemIconUrl, moveSummary,
} from "@/lib/data";
import { getMeta, recommended, type MetaData, type MetaFormat } from "@/lib/meta";
import { canLearn, loadLegality } from "@/lib/legality";
import { categoryIconUrl, spriteUrl, typeIconUrl } from "@/lib/assets";
import {
  NATURE_NAMES, STAT_KEYS, STAT_LABELS, STAT_ORDER, evToSp, spSpreadToEvs,
  type StatLabel,
} from "@/lib/stats";
import { TWITCH_MAX_CHAT_LENGTH, chatMessage, newPokemon, syncLines } from "@/lib/teamParser";
import type { Pokemon, Species } from "@/lib/types";
import { Combobox } from "./ui/Combobox";
import { Modal } from "./ui/Modal";
import { StatSpread } from "./StatSpread";

const TYPES = ["Normal","Fire","Water","Electric","Grass","Ice","Fighting","Poison","Ground","Flying","Psychic","Bug","Rock","Ghost","Dragon","Dark","Steel","Fairy","Stellar"];

export function PokemonEditor({
  open, mon, species, onSave, onClose,
}: {
  open: boolean;
  mon: Pokemon | null;
  species: Species | null;
  onSave: (mon: Pokemon) => void;
  onClose: () => void;
}) {
  const init = mon ?? newPokemon({ species: species?.name ?? "" });
  const [nickname, setNickname] = useState(init.nickname === init.species ? "" : init.nickname);
  const [gender, setGender] = useState(init.gender || "—");
  const [item, setItem] = useState(init.item);
  const [ability, setAbility] = useState(init.ability);
  const [level, setLevel] = useState(init.level || 50);
  const [shiny, setShiny] = useState(init.shiny);
  const [tera, setTera] = useState(init.teraType);
  const [nature, setNature] = useState(init.nature);
  const [moves, setMoves] = useState<string[]>([0, 1, 2, 3].map((i) => init.moves[i] ?? ""));
  const [sp, setSp] = useState<Record<StatLabel, number>>(() => {
    const out = {} as Record<StatLabel, number>;
    for (const label of Object.values(STAT_LABELS)) out[label] = evToSp(init.evs[label] ?? 0);
    return out;
  });

  const itemNames = useMemo(() => allItems().map((i) => i.name), []);
  const speciesName = species?.name ?? init.species;

  // Lazy-load legality data so we can warn about moves the species can't learn
  // (these won't legalize when traded into the mainline games).
  const [, forceLegality] = useState(0);
  useEffect(() => { loadLegality().then(() => forceLegality((n) => n + 1)); }, []);

  // Competitive usage data (cached proxy). Loads once per species+format.
  const [metaFormat, setMetaFormat] = useState<MetaFormat>("Doubles");
  const [meta, setMeta] = useState<MetaData | null>(null);
  useEffect(() => {
    if (!species) return;
    setMeta(null);
    let active = true;
    getMeta(species.id, metaFormat).then((m) => { if (active) setMeta(m); });
    return () => { active = false; };
  }, [species, metaFormat]);

  const applyRecommended = () => {
    if (!meta?.available) return;
    const rec = recommended(meta);
    if (rec.ability) setAbility(rec.ability);
    if (rec.item) setItem(rec.item);
    if (rec.nature) setNature(rec.nature);
    if (rec.spread) setSp({ ...rec.spread });
    setMoves([0, 1, 2, 3].map((i) => rec.moves[i] ?? ""));
  };

  const build = (): Pokemon =>
    syncLines(
      newPokemon({
        species: speciesName,
        nickname: nickname.trim() || speciesName,
        gender: gender === "—" ? "" : gender,
        item: item.trim(),
        ability: ability.trim(),
        level,
        shiny,
        teraType: tera.trim(),
        nature: nature.trim(),
        evs: spSpreadToEvs(sp),
        moves: moves.map((m) => m.trim()).filter(Boolean),
      }),
    );

  const charLen = chatMessage(build()).length;
  const over = charLen > TWITCH_MAX_CHAT_LENGTH - 12;
  const itemIcon = item ? itemIconUrl(item) : null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={speciesName ? `Edit ${speciesName}` : "Add Pokémon"}
      className="max-w-4xl"
      footer={
        <>
          <span className="mr-auto text-xs" style={{ color: over ? "#e74c3c" : "var(--muted)" }}>
            {charLen} / {TWITCH_MAX_CHAT_LENGTH} chars
          </span>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => { if (speciesName) { onSave(build()); onClose(); } }}>
            Save
          </button>
        </>
      }
    >
      {species && (
        <div className="card mb-4 flex items-center gap-4 p-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={spriteUrl(species.id)} alt={species.name} width={80} height={80} />
          <div>
            <div className="text-xl font-bold">{species.name}</div>
            <div className="mt-1 flex gap-1.5">
              {species.types.map((t) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={t} src={typeIconUrl(t)} alt={t} className="h-4" />
              ))}
            </div>
            <div className="muted mt-1.5 text-xs">
              {STAT_KEYS.map((k) => `${STAT_LABELS[k]} ${species.baseStats[k]}`).join("   ")}
              {"   ·   BST "}{STAT_KEYS.reduce((s, k) => s + (species.baseStats[k] || 0), 0)}
            </div>
          </div>
        </div>
      )}

      {/* Recommended (meta) — what people actually run, from cached usage data. */}
      {species && (
        <div className="card mb-4 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm font-semibold">Recommended (meta)</span>
            <div className="flex items-center gap-2">
              <select
                className="input w-auto py-1 text-xs"
                value={metaFormat}
                onChange={(e) => setMetaFormat(e.target.value as MetaFormat)}
              >
                <option value="Doubles">Doubles</option>
                <option value="Singles">Singles</option>
              </select>
              <button className="btn btn-primary" onClick={applyRecommended} disabled={!meta?.available}>Apply set</button>
            </div>
          </div>
          {meta === null ? (
            <p className="muted text-xs">Loading usage data…</p>
          ) : !meta.available ? (
            <p className="muted text-xs">No usage data for this Pokémon in {metaFormat}.</p>
          ) : (
            <div className="muted space-y-0.5 text-xs">
              <div><b>Moves:</b> {meta.moves.slice(0, 4).map(([n, p]) => `${n} ${Math.round(p)}%`).join(" · ") || "—"}</div>
              {meta.items[0] && <div><b>Item:</b> {meta.items.slice(0, 2).map(([n, p]) => `${n} ${Math.round(p)}%`).join(" · ")}</div>}
              {meta.abilities[0] && <div><b>Ability:</b> {meta.abilities.slice(0, 2).map(([n, p]) => `${n} ${Math.round(p)}%`).join(" · ")}</div>}
              {meta.natures[0] && <div><b>Nature:</b> {meta.natures.slice(0, 2).map(([n, p]) => `${n} ${Math.round(p)}%`).join(" · ")}</div>}
              {meta.spreads[0] && (
                <div><b>Spread:</b> {STAT_ORDER.map((s) => meta.spreads[0][0][s] ?? 0).join("/")} SP ({Math.round(meta.spreads[0][1])}%)</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Two columns on wide screens: details on the left, stats on the right. */}
      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-3">
          <Field label="Nickname"><input className="input" value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder={speciesName} /></Field>

          <Field label="Ability">
            <Combobox value={ability} onChange={setAbility} options={species?.abilities ?? []} placeholder="Ability" />
            {abilityDesc(ability) && <p className="muted mt-1 text-xs">{abilityDesc(ability)}</p>}
          </Field>

          <Field label="Item">
            <div className="flex items-center gap-2">
              {itemIcon && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={itemIcon} alt={item} width={28} height={28} className="shrink-0" />
              )}
              <div className="flex-1"><Combobox value={item} onChange={setItem} options={itemNames} placeholder="Held item" /></div>
            </div>
            {describeItem(item) && <p className="muted mt-1 text-xs">{describeItem(item)}</p>}
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Gender">
              <select className="input" value={gender} onChange={(e) => setGender(e.target.value)}>
                <option>—</option><option>M</option><option>F</option>
              </select>
            </Field>
            <Field label="Level">
              <input type="number" min={1} max={100} className="input" value={level} onChange={(e) => setLevel(Number(e.target.value) || 50)} />
            </Field>
            <Field label="Tera Type"><Combobox value={tera} onChange={setTera} options={TYPES} placeholder="Tera" /></Field>
            <Field label="Nature">
              <select className="input" value={nature} onChange={(e) => setNature(e.target.value)}>
                {NATURE_NAMES.map((n) => <option key={n || "neutral"} value={n}>{n || "—"}</option>)}
              </select>
            </Field>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={shiny} onChange={(e) => setShiny(e.target.checked)} style={{ accentColor: "var(--accent)" }} /> Shiny
          </label>
        </div>

        <div>
          <div className="mb-1.5 text-sm font-semibold">Stats — Stat Points (32 max each, 66 total)</div>
          <div className="card p-4">
            <StatSpread baseStats={species?.baseStats ?? ({} as Species["baseStats"])} level={level} nature={nature} value={sp} onChange={setSp} />
          </div>
        </div>
      </div>

      {/* Moves — full width, two per row on wide screens, with descriptions + flags. */}
      <div className="mt-5">
        <div className="mb-2 text-sm font-semibold">Moves</div>
        <div className="grid gap-3 md:grid-cols-2">
          {moves.map((mv, i) => {
            const m = getMove(mv);
            return (
              <div key={i} className="card p-3">
                <Combobox
                  value={mv}
                  onChange={(v) => setMoves((prev) => prev.map((x, j) => (j === i ? v : x)))}
                  options={species?.moves ?? []}
                  placeholder={`Move ${i + 1}`}
                />
                {m && (
                  <div className="mt-2 space-y-1.5">
                    <div className="flex items-center gap-1.5">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={typeIconUrl(m.type)} alt={m.type} className="h-3.5" />
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={categoryIconUrl(m.category)} alt={m.category} className="h-3.5" />
                      <span className="muted text-[11px]">{moveSummary(mv)} · {m.pp} PP</span>
                    </div>
                    {m.desc && <p className="text-xs leading-snug">{m.desc}</p>}
                    {m.flags && m.flags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {m.flags.map((f) => <span key={f} className="chip">{f}</span>)}
                      </div>
                    )}
                  </div>
                )}
                {mv && !canLearn(speciesName, mv) && (
                  <p className="mt-1.5 text-xs font-medium" style={{ color: "#e74c3c" }}>
                    ⚠ {speciesName} can&apos;t learn {mv} — this won&apos;t legalize when traded.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </Modal>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="muted mb-1 block text-xs font-medium">{label}</label>
      {children}
    </div>
  );
}
