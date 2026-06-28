# Berichan Auto Cross-Transfer

A Windows desktop app that builds Pokémon teams and **auto-trades them into your
Switch games** through the [BerichanDev Twitch channel](https://www.twitch.tv/berichandev) —
so you can move a whole team from Pokémon Champions into Scarlet/Violet (and other
mainline games) with almost no manual work.

**What it does:**
1. Build a team in the app (or import a Pokémon Showdown export).
2. Click **Start** — the app posts each Pokémon to Berichan's Twitch chat and
   whispers your trade code automatically.
3. When a trade is ready, it plays a sound and lights up a **Trade Done** button.
4. You do the actual trade on your Switch, click **Trade Done**, and it moves on
   to the next Pokémon.

---

## Download & install

1. Go to the [**Releases**](../../releases) page.
2. Download **`BerichanCrossTransfer.exe`** from the latest release.
3. Double-click it. **No installer, no Python, no admin rights** — it's a single file.

> **First-run warning:** Windows SmartScreen may say *“Windows protected your PC.”*
> This is normal for a free, unsigned app. Click **More info → Run anyway**.
> (See [Is this safe?](#is-this-safe) — the app is open source and built
> automatically from this repo.)

Nothing is installed on your system. The app only saves your settings and teams to
`%APPDATA%\BerichanCrossTransfer\`. To uninstall, just delete the `.exe`.

### If Windows blocks it (Smart App Control)

Some Windows 11 PCs have **Smart App Control (SAC)** turned on. Unlike the
SmartScreen warning above, SAC **blocks unsigned apps and scripts with no “Run
anyway” option** — that includes `.exe`, `.bat`, and `.ps1` files (you may see
*“An Application Control policy has blocked this file”* or a *dangerous file
extension* message). There is no double-click workaround for an unsigned app under
SAC; that's what SAC is designed to do.

You can still run the app, because **SAC allows commands typed into a trusted
program** like PowerShell (and `python.exe` is trusted):

1. Install [Python](https://www.python.org/downloads/) once — tick **“Add Python
   to PATH”** during install.
2. On the [Releases](../../releases) page, download **Source code (zip)** and
   extract it.
3. Open the extracted folder, **Shift + right-click → “Open PowerShell window
   here”**, and paste:
   ```powershell
   pip install -r requirements.txt
   python -m berichan.gui
   ```
   The first line is a one-time install. After that, just `python -m berichan.gui`
   opens the app.

> Tip: right-clicking the downloaded **`.zip` → Properties → Unblock** *before*
> extracting sometimes lets `Run-Berichan-Trader.bat` run by double-click under SAC,
> but it isn't guaranteed — the PowerShell method above always works.

The only ways to make a click-to-run file work under SAC are to **code-sign the
app** or **turn SAC off** in Windows Security (a **permanent** switch — it can't be
re-enabled without resetting Windows), so the PowerShell method is the safe choice.

> **Not on Smart App Control?** If you just have the normal SmartScreen prompt, you
> don't need any of this — and `Run-Berichan-Trader.bat` (in the source download)
> launches the app from source with a single double-click.

---

## First-time setup (built-in wizard)

The first time you open the app, a short **setup wizard** walks you through
connecting your Twitch account. You'll need a free Twitch "Client ID" — the wizard
guides you through creating one, step by step:

1. It opens the Twitch Developer Console for you.
2. You register a free application (the wizard shows the exact redirect URL to
   paste, with a copy button).
3. You paste the **Client ID** into the wizard.
4. Click **Connect Twitch** to authorize — your token is captured automatically.

That's it. Your token is **encrypted on your own PC** (Windows DPAPI) and never
leaves it. You can re-run the wizard or change anything later under **Settings**.

---

## Using the app

The app has three sections in the left sidebar:

### 🧩 Team
The built-in team builder, modeled on Pokémon Showdown's:
- **+ Add Pokémon** opens a searchable picker of the legal **Pokémon Champions**
  roster (with sprites). Picking one opens an editor that limits abilities and
  moves to that species' real movepool, with item effects, ability descriptions,
  and type / Physical-Special-Status icons.
- Stats use the Champions **Stat Point** system (66 total, 32 per stat) with two
  editing modes — a **slider** view and an interactive **pie/radial** view — both
  showing live Level-50 stats. These are converted to legal in-game EVs
  automatically when traded.
- Save / load named teams, reorder Pokémon, or **Import from Showdown**.

### 🔄 Trade
- Pick your target game, review the team, and hit **Start**.
- The window stays responsive while it waits. When a trade is ready you'll hear a
  sound and the **Trade Done** button lights up — do the trade on your Switch,
  then click it to continue.

### ⚙ Settings
- Twitch account (re-authenticate, check connection), channel / bot / trade code,
  and all timing values.
- **Ready sound** — three soft built-in chimes or your own `.wav`/`.mp3`, with a
  volume slider and a test button.
- **Appearance** — themes: **Windows** (native, default), **Material**, or
  **Glass** (frosted dark).

---

## Is this safe?

Yes — and you don't have to take our word for it:

- The released `.exe` is **built automatically by GitHub Actions from this public
  source** (see the **Actions** tab), so the download provably matches the code
  you can read here. It isn't uploaded by hand.
- It's **fully open source** — inspect it or build it yourself.
- **No credentials are bundled.** You sign in to Twitch yourself on first run;
  your token is encrypted with Windows DPAPI and stored only on your PC.
- Every release includes a **SHA-256 checksum**. To verify your download, run in
  PowerShell:
  ```powershell
  Get-FileHash .\BerichanCrossTransfer.exe -Algorithm SHA256
  ```
  The value must match the `.sha256` file attached to the release.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| SmartScreen blocks the app | Click **More info → Run anyway** (normal for unsigned apps). |
| "Token expired" / can't connect | Open **Settings → Re-authenticate**. |
| Whisper not sending | Your Twitch account needs **phone verification** enabled. |
| Wrong bot / no queue confirmation | Confirm the bot username in **Settings** (check the live stream); the bot may be offline. |
| Trade set too long | Shorten nicknames/moves — Twitch limits a chat message to 500 characters (the editor shows a live count). |

---

## Building from source (for developers)

The app is a Python / PySide6 project. To run or build it yourself:

```bash
pip install -r requirements.txt
python -m berichan.gui          # run the desktop app
python -m pytest                # run the tests
```

Build the distributable executable:

```bash
pip install -r requirements-dev.txt
pyinstaller berichan.spec        # -> dist/BerichanCrossTransfer.exe
```

The teambuilder data (Champions roster, items, moves, abilities, sprites, icons,
and competitive meta) is bundled and committed under `assets/`. Regenerate it with
the scripts in `tools/` (e.g. `python tools/gen_pokedex.py`).

### Releasing

Releases are automated. Push a version tag and GitHub Actions builds the exe, runs
the tests, smoke-tests that it launches, computes the SHA-256, and publishes
everything to a GitHub Release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## Phase 2 — Controller automation (planned)

The long-term goal is to automate the Switch button presses for the Link Trade
itself so the process is fully hands-off. The most promising approach on Windows
is a **Raspberry Pi Zero running [nxbt](https://github.com/Brikwerk/nxbt)**
(emulating a Pro Controller over Bluetooth), driven by this app over the local
network. Not yet implemented.
