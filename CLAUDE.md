# Critical Mass → BBC Micro

Critical Mass is a version of *Marble Merger* (Eli Piilonen, PICO-8) for a stock BBC Model B: MODE 2, a
single screen buffer and 25 fps. A ball that reaches the critical size explodes into smaller ones. The
owner is Rich Talbot-Watkins, an expert BBC programmer and the author of BeebAsm and Baron, so pitch
explanations at that level.

## Read first
- `docs/brief.md`: what the game should be, in Rich's words. Only Rich changes it.
- `docs/decisions.md`: the decision log.
  - Record new decisions there.
  - Never mark your own recommendation as decided: it stays Proposed until Rich agrees.
- `docs/plan.md`: the design and the phases. `JOURNAL.md`: what's been done, with measurements. Keep it up
  to date.

## Rules
- **Emulator: jsbeeb-mcp only (D11).** Never launch b2 or talk to its HTTP API: other sessions use it.
  `make run` launches b2: it's for Rich, so never run it.
  Create one jsbeeb machine at a time and destroy it when you're done.
- **Memory and processes:** the machine has 12 GB, shared with other sessions. Run one heavy process at a
  time (no `xargs -P`, no parallel model runs) and at most one review agent at a time.
- **Review:** have an agent review new code as it's written (Rich, 2026-10-28).
- Rich makes the commits. Don't commit unless he asks.
- **Release (D15):** when `make test` passes after a change Rich wants out, `make release MSG="..."`
  copies the disc to `~/dev/waitingforvsync.github.io/beeb/criticalmass.ssd`, commits only that file there
  and pushes (teddyboy's releases share that repo). A jsbeeb link loads it from the site.

## Toolchain
- **Baron** (`baron` 0.6, source in `~/dev/baron`). Read `~/dev/baron/docs/guide.md` and `reference.md`
  before writing 6502.
  - There's no `ORG`, `SAVE` or `GUARD`: use `SECTION … ENDSECTION` with `org`, `filename` and `guard`.
  - NMOS only: never `cmos = TRUE`.
- **Python:** use `.venv/bin/python` (git-ignored, with py65, pillow and numpy). Recreate it with
  `python3 -m venv .venv && .venv/bin/pip install py65 pillow numpy`.
- **The model** (`tools/`, described in `docs/model.md`) is the reference. It does the physics in the same
  integer arithmetic as the 6502, and holds the screen as MODE 2 bytes.
  - `make model` writes a bot game's video and stats to `build/model/`.
  - `tools/gendata.py` writes `build/gen/` from it:
    - `data.6502`: the constants;
    - `tables.6502`: MASS's tables, placed under the screen;
    - `made.6502`: the loader's tables' places, up to &8000;
    - `tables.json`: every table's bytes;
    - `screen.bin` and `title.bin`: the screens.
  - Tables the loader can make in less than they take packed are its own (`entry.6502`'s `make_tables`;
    `made` in gendata). Rich wants MASS as small as possible.
  - **The screens are PNGs in `assets/`** (D18, D19), Rich's to retouch.
    - `screen.png` is the game's starting screen: 1024 × 896, 8 × 4 a MODE 2 pixel.
    - `title.png` is !BOOT's title.
    - `tools/screenpng.py` reads them. `layout.py`'s numbers for what the game draws on the screen must
      follow `screen.png`.
- **Tests:** `make test`, about eleven minutes, in py65 (`tools/machine.py` runs the real loader, from after
  its OS calls to `main`). It checks the 6502 against the model:
  - `test_tables.py`: every table in memory, the loader's own included;
  - `test_background.py`: the screen the loader unpacks, GAME OVER, and a new game's screen;
  - `test_plot.py`: every byte of the screen;
  - `test_physics.py`: every ball, every step;
  - `lockstep.py`: the whole game, every frame, balls, state and screen (`--scene critical` forces an
    explosion).
  - Costs come from `frames.py`, `bench_plot.py` and `profile.py`.
  - Any change to the 6502's behaviour needs the same change in the model, or lockstep fails.

## Style (D2: copy teddyboy)
- 6502 in `src/`: tabs, CamelCase constants, lower-case labels with underscores, and `\\` comment headers.
  - Each routine's header says what it's for, then lists its Inputs and Outputs.
  - `ZA_AUTO` goes in the smallest scope. `ZA_INTERRUPT` goes on the IRQ.
  - Workspace uses virtual sections.
  - Write it fast from the first line. Follow the flags. Use `SAME_PAGE` on hot branches.
- Hardware registers are written as literal addresses with a trailing comment: `STA &FE4D ; system VIA:
  IFR`.
- BBC addresses are written `&xxxx`.
- Python in `tools/`: plain, with no dependencies beyond the `.venv`. Paths are relative to the repo
  root.

## Layout
- `src/`: Baron sources.
  - `critical.6502` is the top level: MASS is one ZX02 payload (the code, its tables and the screen,
    contiguous from &140), then the loader (`entry.6502`), which unpacks it in place.
  - The memory map is in `memory.6502` (D14, D18):
    - stack &100-&13F;
    - code from &140, around the bytes that can't move;
    - MASS's tables up to the screen at &33E8 (the well's rows a page each, from &3400);
    - then the workspace, and the loader's tables up to &8000.
  - The 6502 draws by columns from the well's first, and x counts from the well's left.
  - `!BOOT` is `boot.6502`: the MODE 2 title, then MASS.
- `tools/`: Python. The model, the shape and table generators, the screen's layout, and the harnesses.
- `docs/`: design docs. `old/`: Rich's unfinished BeebAsm version, kept for reference.
