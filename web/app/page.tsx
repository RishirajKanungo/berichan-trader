"use client";

import { useState } from "react";
import { Download, FolderOpen, Plus, Save, Upload } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/auth";
import { useTeam } from "@/components/team";
import { PokemonCard } from "@/components/PokemonCard";
import { PokemonEditor } from "@/components/PokemonEditor";
import { SpeciesPicker } from "@/components/SpeciesPicker";
import { Modal } from "@/components/ui/Modal";
import { getSpecies } from "@/lib/data";
import { parseTeam, teamToShowdown } from "@/lib/teamParser";
import { deleteTeam, listTeams, loadTeam, saveTeam } from "@/lib/teams";
import type { Pokemon, Species } from "@/lib/types";

export default function Page() {
  const { authEnabled, signedIn } = useAuth();
  const cloud = authEnabled && signedIn;
  const { team, setTeam } = useTeam();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [editor, setEditor] = useState<{ open: boolean; mon: Pokemon | null; species: Species | null; index: number }>(
    { open: false, mon: null, species: null, index: -1 },
  );
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const [loadOpen, setLoadOpen] = useState(false);
  const [savedNames, setSavedNames] = useState<string[]>([]);
  const [toast, setToast] = useState("");

  const flash = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 2200); };

  const openAdd = (species: Species) => setEditor({ open: true, mon: null, species, index: -1 });
  const openEdit = (i: number) =>
    setEditor({ open: true, mon: team[i], species: getSpecies(team[i].species) ?? null, index: i });

  const handleSave = (mon: Pokemon) => {
    setTeam((prev) => (editor.index >= 0 ? prev.map((m, i) => (i === editor.index ? mon : m)) : [...prev, mon]));
  };

  const move = (i: number, d: number) => {
    setTeam((prev) => {
      const j = i + d;
      if (j < 0 || j >= prev.length) return prev;
      const next = [...prev];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  };

  const doImport = () => {
    const parsed = parseTeam(importText);
    if (!parsed.length) { flash("No Pokémon found in that text."); return; }
    setTeam(parsed);
    setImportText("");
    setImportOpen(false);
    flash(`Imported ${parsed.length} Pokémon.`);
  };

  const doExport = async () => {
    if (!team.length) return;
    await navigator.clipboard.writeText(teamToShowdown(team));
    flash("Showdown export copied to clipboard.");
  };

  const doSave = async () => {
    if (!team.length) { flash("Add some Pokémon first."); return; }
    const name = window.prompt("Save team as:");
    if (!name?.trim()) return;
    try {
      await saveTeam(cloud, name.trim(), team);
      flash(`Saved “${name.trim()}”${cloud ? " to your account" : ""}.`);
    } catch (e) {
      flash(e instanceof Error ? e.message : "Save failed.");
    }
  };

  const openLoad = async () => {
    try {
      setSavedNames(await listTeams(cloud));
      setLoadOpen(true);
    } catch {
      flash("Could not load saved teams.");
    }
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <header className="mb-5 flex flex-wrap items-center gap-3">
          <div>
            <h1 className="text-2xl font-bold">Team Builder</h1>
            <p className="muted text-sm">Pokémon Champions · {team.length} on team</p>
          </div>
          <div className="ml-auto flex flex-wrap gap-2">
            <button className="btn" onClick={() => setImportOpen(true)}><Upload size={16} /> Import</button>
            <button className="btn" onClick={doExport} disabled={!team.length}><Download size={16} /> Export</button>
            <button className="btn" onClick={doSave} disabled={!team.length}><Save size={16} /> Save</button>
            <button className="btn" onClick={openLoad}><FolderOpen size={16} /> Load</button>
            <button className="btn btn-primary" onClick={() => setPickerOpen(true)}><Plus size={16} /> Add Pokémon</button>
          </div>
        </header>

        {team.length === 0 ? (
          <div className="card muted p-10 text-center">
            No Pokémon yet. Click <span className="accent-text font-semibold">Add Pokémon</span> or Import a Showdown team.
          </div>
        ) : (
          <div className="space-y-2">
            {team.map((mon, i) => (
              <PokemonCard
                key={i}
                mon={mon}
                index={i}
                total={team.length}
                onEdit={() => openEdit(i)}
                onRemove={() => setTeam((prev) => prev.filter((_, j) => j !== i))}
                onMoveUp={() => move(i, -1)}
                onMoveDown={() => move(i, 1)}
              />
            ))}
          </div>
        )}
      </div>

      <SpeciesPicker open={pickerOpen} onClose={() => setPickerOpen(false)} onPick={openAdd} />

      <PokemonEditor
        open={editor.open}
        mon={editor.mon}
        species={editor.species}
        onSave={handleSave}
        onClose={() => setEditor((e) => ({ ...e, open: false }))}
      />

      <Modal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="Import from Showdown"
        footer={<><button className="btn" onClick={() => setImportOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={doImport}>Import</button></>}
      >
        <p className="muted mb-2 text-sm">Paste a Showdown team export. This replaces the current team.</p>
        <textarea className="input h-56 font-mono text-xs" value={importText} onChange={(e) => setImportText(e.target.value)} placeholder="Paste here…" />
      </Modal>

      <Modal open={loadOpen} onClose={() => setLoadOpen(false)} title="Load a saved team">
        {savedNames.length === 0 ? (
          <p className="muted text-sm">No saved teams yet.</p>
        ) : (
          <div className="space-y-1">
            {savedNames.map((name) => (
              <div key={name} className="flex items-center gap-2">
                <button
                  className="btn flex-1 justify-start"
                  onClick={async () => { setTeam(await loadTeam(cloud, name)); setLoadOpen(false); flash(`Loaded “${name}”.`); }}
                >
                  {name}
                </button>
                <button className="btn btn-icon" onClick={async () => { await deleteTeam(cloud, name); setSavedNames(await listTeams(cloud)); }} aria-label="Delete">✕</button>
              </div>
            ))}
          </div>
        )}
      </Modal>

      {toast && (
        <div className="surface fixed bottom-5 left-1/2 -translate-x-1/2 rounded-lg px-4 py-2 text-sm shadow-xl">{toast}</div>
      )}
    </AppShell>
  );
}
