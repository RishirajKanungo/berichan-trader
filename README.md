# Berichan Auto Cross-Transfer

Automates trading a full Pokemon Showdown team through the [BerichanDev Twitch channel](https://www.twitch.tv/berichandev).

**What it does:**
1. You paste your Showdown team export.
2. The script posts each Pokemon's block to the Twitch chat and whispers the trade code to BerichanBot automatically.
3. It monitors the chat and beeps + prints a banner when it's your turn.
4. You do the actual trade on your Switch. Press ENTER when done.
5. It waits the cooldown and moves to the next Pokemon.

---

## Setup

### 1. Install Python 3.11+
Download from [python.org](https://www.python.org/downloads/). During install, check **"Add Python to PATH"**.

### 2. Install dependencies
```
pip install -r requirements.txt
```

### 3. Create a Twitch Developer App
1. Go to [dev.twitch.tv/console](https://dev.twitch.tv/console) → **Register Your Application**
2. Set **OAuth Redirect URL** to `http://localhost:3000`
3. Copy the **Client ID**

### 4. Run the auth setup (one time)
```
python setup_auth.py
```
This opens your browser to authorize the app and writes your token to `.env`.

### 5. Edit `.env`
```
cp .env.example .env
```
Key settings to verify:
| Variable | Default | Notes |
|---|---|---|
| `TRADE_CODE` | `24932000` | Your 8-digit Link Trade code in Scarlet/Violet |
| `BOT_USERNAME` | `BerichanBot` | Verify on the live stream — may be `Bot_RocketGrunt` |
| `INTER_TRADE_DELAY` | `120` | Seconds between Pokemon (2 min is safe) |

---

## Usage

### Desktop app (recommended)

A Windows GUI wraps the whole flow so you're not tied to the terminal:

```
python -m src.gui
```
or double-run `run_gui.ps1`.

The app has a left sidebar with three sections:

- **Team** — the built-in team builder, modeled on Showdown's. **+ Add Pokémon**
  opens a searchable picker of the **legal Pokémon Champions roster** (with
  sprites); choosing one opens an editor that constrains abilities and the four
  move slots to that species' real movepool. Stats use the Champions **Stat Point
  (SP)** system (66 total, 32 per stat — no IVs) with **two editing modes**: a
  Showdown-style **slider** view and an interactive **pie/radial** view, both
  showing live Level-50 stats. You can also **Import from Showdown**. Edit /
  reorder / remove Pokémon as cards, **Save**/**Load** named teams, and **Export**
  back to Showdown.
- **Trade** — pick the game, review the team, **Start / Stop** (the window stays
  responsive during the wait), and click the big **Trade Done** button when each
  trade finishes. A configurable **ready sound** (three soft built-in chimes or your
  own `.wav`/`.mp3`, with volume + test) replaces the old harsh triple beep.
- **Settings** — Twitch username / Client ID / token (with **Re-authenticate…** and
  **Check connection**), channel / bot / trade code, all timing values, the ready
  sound, and **Appearance** (theme).

**First run** launches a short **setup wizard** that walks you through creating a
Twitch Developer App (Client ID), copying the redirect URL, and authorizing — no
manual `.env` editing. It's re-runnable from Settings.

**Themes** (Settings → Appearance): **Windows** (native, default), **Material**
(flat dark), and **Glass** (frosted dark). Switching is live and reliable.

Settings are saved to `%APPDATA%\BerichanCrossTransfer\settings.json` (migrated
automatically from your existing `.env` on first launch). **Your Twitch token is
encrypted at rest** using the Windows Data Protection API (DPAPI), tied to your
Windows account — a copied settings file can't be decrypted by anyone else.

### Build a standalone .exe

To share the app with people who don't have Python:

```
pip install pyinstaller
pyinstaller berichan.spec
```

The executable lands in `dist/`. The build bundles the sound, Pokédex and sprite
assets and **excludes `.env`**, so no credentials ship inside the binary — each
user runs the setup wizard and their token stays encrypted on their own machine.

### Pokédex data (teambuilder)

The teambuilder reads a bundled, offline dataset built from Serebii's Pokémon
Champions Pokédex — `assets/data/champions.json` (roster, types, base stats,
abilities, movepools) and `assets/sprites/*.png`. These are committed, so the app
never hits the network. To regenerate after a game update:

```
python tools/gen_pokedex.py    # rebuild champions.json
python tools/gen_sprites.py    # rebuild sprites
```

Stats use the Champions **Stat Point** system and are converted to standard EVs
(`EV = SP × 8`, capped 252; IVs always perfect) when the set is sent to Berichan,
so the traded Pokémon matches what you built.

### Terminal (CLI)

**Interactive (paste team):**
```
python -m src.main
```

**From a file:**
```
python -m src.main team.txt
```

**Override trade code for this run:**
```
python -m src.main --code 87654321
```

When it's your turn you'll hear 3 beeps and see:
```
══════════════════════════════════════════════════════════════
  TRADE READY: PENATRATOR
  Use code   : 24932000  on your Switch
  Search for the trade NOW, then press ENTER when done.
══════════════════════════════════════════════════════════════
```

---

## Showdown format example

Paste the export exactly as Pokemon Showdown generates it:

```
PENATRATOR (Excadrill) (M) @ No Item
Ability: Sand Rush
Level: 50
Shiny: Yes
Tera Type: Ground
EVs: 4 HP / 252 Atk / 252 Spe
Adamant Nature
- Rock Slide
- Protect
- High Horsepower
- Iron Head

Grimmsnarl (M) @ Light Clay
Ability: Prankster
...
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Whisper not sending | Ensure your Twitch account has phone verification enabled |
| Bot username wrong | Check the live stream — the bot may be `Bot_RocketGrunt` instead of `BerichanBot`. Update `BOT_USERNAME` in `.env` |
| No queue confirmation | The bot may be offline. The script will still wait for "Initializing trade" |
| Token expired | Re-run `python setup_auth.py` |

---

## Phase 2 — Controller automation (planned)

The long-term goal is to automate the Switch button presses for the Link Trade itself so you're fully hands-off. The best approach on Windows is a **Raspberry Pi Zero running [nxbt](https://github.com/Brikwerk/nxbt)** (emulates a Pro Controller over Bluetooth), controlled over the local network by this script. Arduino/Teensy USB controller emulators are an alternative. This is not yet implemented.
