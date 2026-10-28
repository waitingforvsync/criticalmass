# Critical Mass: plan

Critical Mass is a BBC Micro version of *Marble Merger*, Eli Piilonen's PICO-8 Suika-style game, for a stock
Model B, written with Baron. This is a draft for discussion (2026-10-28). Where it says **Proposed**, that's my
recommendation, waiting for Rich to agree.

The original's source is `docs/src.lua`.

## The game

- Rules as in the original:
  - Drop marbles into the well.
  - Two marbles of the same size that touch merge into one of the next size up. Score += the smaller
    size.
  - You lose when any ball pokes above the rim while touching another for 2 seconds (120 frames at 60 Hz).
- The original's numbers:
  - Board 80 × 120.
  - Radius 0.8 + 2·size, and weight = radius (not area).
  - Gravity 0.05 a frame². The walls and floor bounce at 0.5.
  - Pushes go 0.7 into position and 0.35 into velocity, all applied after one pass over every pair.
  - New balls can't merge for 10 frames.
  - The drop size is random, 1 to 4, and the dropper has a 20-frame cooldown.
  - Colours cycle every 7 sizes, and sizes above 7 are dithered.
- **Look (Rich, decided):** flat circles with a checkerboard dither and no highlight.

## Critical mass (Rich, decided: the idea; Proposed: the details)

- **The idea:** this is the change that gives the game its name. When a merge makes the critical size, the
  ball explodes into a number of balls of various sizes and scores a big bonus.
- **The critical size:** call it C, so the biggest ball that stays on the board is C − 1.
  - Proposed: start with C = 10. Size 9 is 30 pixels across, nearly half the well.
  - The model will tune it. A smaller C means more explosions and a less crowded board.
- **The pieces:** I'd use a few patterns made in advance rather than packing them at run time.
  - The Python generator would make perhaps 4 to 8 of them. Each one lists every piece's size, its offset
    from the centre and its velocity outwards.
  - The pieces sit inside the big ball's circle without touching, so nothing starts overlapping.
  - Their sizes are 1 to 4 (the drop sizes), and their total area is a fraction of the big ball's, so an
    explosion clears room.
  - One pattern is picked at random.
- **Chains:** pieces of the same size that land together can merge again.
  - Proposed: give pieces the usual 10-frame grace before they can merge.
  - Merges within a few seconds of an explosion score a chain multiplier. That makes going critical a
    combo, not just a clear-out.
- **The bonus:** a large flat score for the explosion, plus the chain. The numbers come from play.
- **Showing it:**
  - Size C − 1 uses the spare odd-parity logical colour, set to a flashing physical colour, so the
    biggest ball pulses: one more merge and it goes critical.
  - The explosion takes the big ball out and puts the pieces in. That's one area's redraw, the cost of a
    merge, and can be spread over two frames.
  - Particles, and a noise-channel bang.

## Screen (Proposed: keep the old layout)

- MODE 2, 64 characters × 28 rows (128 × 224 pixels), with the screen at &4800 to &7FFF (14K, 512 bytes a
  row).
- The well is 32 bytes (64 pixels) inside, with 1-byte walls and a floor in the bottom row. A 30-byte panel on
  the right holds the score, the next ball, the best score and the size chart.
- **Units:** 1 unit is one scanline, which is half a MODE 2 pixel, so space is square, as in the old code.
  - x runs 0 to 127 across the well. The byte column is x/4 and the pixel is x/2.
  - y runs 0 to 215 down the well.
  - Positions and velocities are 8.8 fixed point.
- **Scale:** 1.6 units to a PICO-8 pixel, so the board's 80 becomes 128.
  - The radius is r(s) = 1.28 + 3.2·s units.
  - Sizes 1 to 11 come out 4.5, 7.7, 10.9, 14.1, 17.3, 20.5, 23.7, 26.9, 30.1, 33.3 and 36.5 pixels
    across.
  - The board's depth of 120 becomes 192 lines. That leaves about 24 lines above the rim for the dropper,
    whose biggest ball is 28 lines tall. It's tight, so the model will settle the depth.
- **Sizes (Rich, decided): whatever looks circular.** The original's proportions above are only a starting
  point.
  - The generator draws each size's shape, and we pick by eye from the model's PNGs.
  - Each physics radius is then worked out from its drawn shape.

## Rendering: your delta plotter on one buffer

- Keep the idea in `old/spriteroutine.6502`:
  - Each ball is drawn as the EOR difference between how it was drawn last time and how it is now.
  - It works column by column, merging the two shapes' runs (gap, single pixel, full byte). Runs where the
    two agree are skipped.
  - Each byte goes straight from old to new, so a single buffer doesn't flicker. A ball at rest costs
    nothing.
- The dither is anchored to the screen: even and odd lines swap the pixel pair. A moving ball therefore
  only touches its edges, and its inside never changes. A colour change (a merge) redraws the area once.
- The plotter stays in zero page, using its self-modified operands as pointers. In Baron it's a nested
  section rephased to zero page, which the loader copies down. That replaces COPYBLOCK.
- **Shapes:** for each drawn radius and pixel parity, three counts for each byte column. A Python generator
  writes them for both the 6502 and the model. The sizes' own shapes double as the frames of the grow-in
  and merge animations. That's about 1K in all.
- Each slot keeps what's drawn (x, y, shape, colour) and what should be. The renderer draws the
  difference, then copies the new state over the old.

### Overlaps (Rich, decided: the parity palette)

- With EOR, two balls that overlap show a third colour, and the original's soft physics does overlap,
  most of all at the bottom of a stack. The palette can fix that:
  - Give balls only the odd-parity logical colours: 1, 2, 4, 7, 8, 11, 13 and 14.
  - Map every even-parity colour to black.
- Two overlapping balls then always EOR to even parity, which shows as black. A contact looks like a thin
  black seam, as if the two balls were just apart.
- That leaves 8 logical colours for the 7 physical ones, plus one spare. The spare is the flashing colour
  for the ball one merge from critical mass. Any two of the eight can make a dither.
- Where three balls overlap, a ball colour shows. That should be rare.

## Ball storage (decided: Rich asked me to make the call)

- **No linked list.**
  - Slots are a structure of arrays indexed by X. A slot stays one ball for its whole life, so the drawn
    state and the merge animation can refer to it.
  - `order` is a byte list of the live slots, sorted by bottom edge. An insertion sort keeps it in order
    each step.
- The physics sweep needs that order anyway.
- The list is nearly sorted, so the insertion sort costs about N compares and a few one-byte swaps.
- Walking it with `LDX order,Y` costs the same as `LDX next,X`.
- Deletes are rare: one per merge.
- Rendering follows the same order. If tearing shows, we can chase the beam without any new structure. I
  don't expect to need to.

## Collisions: squares and logs, not trig or sqrt

**The problem:** the push depends on the overlap, R − d. Here R is up to about 70 units, and a resting
overlap is only 0.5 to 3 units. The overlap is a small difference of two big numbers, so d is needed to
within about 0.1 unit. Noise in d becomes jitter at rest.

`tools/collide_cmp.py` measures the error in the overlap over 20,000 random contacts (sizes 1 to 9,
overlaps 0 to 3 units):

| Method | Inputs | rms error | worst |
|---|---|---|---|
| Sketch (ratio → atan → cos → divide) | whole units, as the sketch stores them | 0.50 | 1.59 |
| Sketch | half units | 0.26 | 0.82 |
| 8-bit logs for the distance | half units | 0.32 | 1.28 |
| Exact squares, d² against R² | half units | 0.19 | 0.55 |
| Exact squares | quarter units | 0.10 | 0.26 |

- **Trig against sqrt:** the trig chain suits the 6502 better than the original's sqrt, because it avoids
  a 16-bit square root and a divide. But it stacks four 8-bit roundings, so its distance is too noisy for
  R − d. Logs for the distance have the same trouble.
- **Recommended (Proposed):**
  1. The quarter-square table already gives exact squares: x² = multab[2x].
  2. Reject a pair when d² = dx² + dy² ≥ R². R² depends only on the two sizes. No square root is needed,
     and this is the cheapest early-out.
  3. Take the push as (dx, dy) · (R² − d²) / 2R², a linearised spring. It differs from the true overlap
     only by a smooth ov²/2R, which makes the spring slightly softer and adds no noise.
- **Logs are good where 2% will do:** the products.
  - The 1/2R² factor and the mass share (weight depends only on size) fold into two logs for each size
    pair.
  - Each contact then takes one LOG of (R² − d²), log|dx| and log|dy|, a few adds and four EXP lookups. The
    sketch needs 8 to 10 quarter-square multiplies.
- **Rough cost:**
  - A near miss is rejected in about 45 cycles: two square lookups, an add and a compare.
  - A contact costs about 250 cycles, against 350 to 450 for the sketch.
  - These are estimates. Phase 1 measures them.
- Keep the sketch's structure around it: the |dx| and |dy| box tests first, the signs taken from dx and dy,
  and the four accumulators.

## Physics and timing

- **25 fps fixed (Rich, decided):** 80,000 cycles a frame.
  - A first estimate for 30 balls is about 31K for the physics: the sort, the integration, about 150
    candidate pairs and about 75 contacts.
  - The rendering takes 5K to 20K, and a merge frame about 25K more.
  - That leaves headroom, but the model will give the real counts.
- **Squishiness:** a resting overlap grows with the gravity added each step, and stacks add it up layer by
  layer.
  - At 60 Hz that's about 0.46 units a layer.
  - A straight 25 Hz port of the original's constants is 5.76 times squishier: about 16 lines at the bottom
    of a six-ball stack.
  - So the model has to retune it: a stiffer push, a second pass over the contact list, or two physics
    steps a frame if the budget allows.
- **Hysteresis:** a ball's drawn position follows its physics position only once it has moved a full unit.
  Otherwise a ball at rest shimmers a line up and down, and pays to be redrawn.
- **Merges:** gathered during the sweep and applied after it.
- **Fail:** a ball above the rim that's touching another, for 2 seconds, ends the game. The warning flashes
  through the palette, which costs nothing.

## The rest of the game

- **Dropper:** the held ball is an ordinary slot moving across above the rim. When it's dropped, it becomes
  live in the same slot. The next ball grows in through the size shapes over the cooldown.
- **Merge animation:** one slot moves to the midpoint and steps up to the new size, and the other shrinks to
  nothing. Both cost very little with the delta plotter.
- **Keys (Rich, decided):** Z and X to move, SHIFT to move slowly, RETURN to drop. No joystick.
- **Panel:** score, best and next, with digits in a small MODE 2 font.
- **Sound:** SN76489 through the System VIA, with a player in the IRQ.
  - Merges get a pitch for each size.
  - A drop clicks, and impacts tap louder as they hit harder.
  - Game over gets a jingle.
- **Title screen:** the original's falling balls, which the plotter does for free.
- **Particles:** if the budget allows.

## Memory map (first cut)

| Address | What |
|---|---|
| &0000 | Zero page: the plotter's code (the old one ran from &6B into page 1) and the ZA_POOL. &FC is left for the MOS's IRQ entry. |
| &0100 | The plotter's overflow, then the stack. |
| &0200 | IRQ1V at &204. Ball arrays go in the gaps, as in the old `defines.6502`. |
| &0300 | Tables the loader builds: the quarter squares (2K) and the logs and exps (about 1K). |
| about &1100 | Code, shapes, ball arrays and the loader, which is thrown away after it runs. |
| &4800 | The screen. |

## Tools and tests

- **Build:** a Makefile (`make`, `make test`) and a `.venv` with py65, pillow and numpy. The disc is booted
  through jsbeeb-mcp.
  - Baron writes `build/mass.ssd`, a `-v` listing and the symbols.
- **The Python model** is the reference. Its integer physics matches the 6502's exactly, with the same
  tables, and it has a screen model that turns the plotter's output into MODE 2 bytes and a PNG or GIF.
  A bot drops balls into it.
- **py65 harnesses** (after teddyboy's `machine.py`):
  - The plotter is checked against the screen model byte for byte: every size, parity and offset, plus
    random old/new pairs.
  - The physics is checked against the model, which must give the same state after every step.
- **jsbeeb, through jsbeeb-mcp (Rich, decided):** the only emulator for this project. It's used for frame
  timing, the whole game and screenshots. Nothing here uses b2.
- **Repo docs:** `CLAUDE.md`, `docs/brief.md` (Rich's words), and `docs/decisions.md`, a decision log
  kept as in teddyboy.

### Emulators alongside another session

- **Only jsbeeb-mcp (Rich, decided, 2026-10-28).** It's in this project's local config as `jsbeeb`
  (`npx -y jsbeeb-mcp`). Each Claude session starts its own copy, so it can't clash with another session.
- **Never b2.**
  - Its HTTP API listens on one fixed port, 48075.
  - Teddyboy's and portal's `make run` reset whatever b2 answers there and load their own disc into it.
  - So the Makefile here has no `run` target that touches b2.
- **py65** runs in-process for the unit harnesses, so it shares nothing. Run one set at a time: the
  machine has 12 GB.

## Phases

Status at 2026-10-28, 02:30. The night's account is in `JOURNAL.md` and the decisions in `decisions.md`.
- Phases 0 to 5 are done.
  - The game plays on the 6502, in jsbeeb.
  - It matches the model frame for frame (`make test`).
- Phase 6 is partly done: sound, the panel and the effects are in; there's no title screen yet.
- The open problem is O2: crowded boards go over the 25 fps budget.
- The physics' feel (the phase 1 gate) is still Rich's to judge: `build/model/game-2-tonight.mp4`, or
  play it.

0. **Set-up:**
   - `git init` (Rich commits).
   - The Makefile, `CLAUDE.md`, `docs/brief.md`, `docs/decisions.md` and the `.venv`.
1. **Python model:** the main de-risking step.
   - It settles:
     - the frame rate, the steps per frame and the stiffness;
     - the precision (half or quarter units);
     - the sizes and the well's depth;
     - the hysteresis;
     - the critical size and the piece patterns.
   - It measures, for each frame: the pairs, the contacts, the moving balls and the bytes plotted. Those give
     the cycle budget.
   - **Gate:** Rich watches the GIFs and likes the feel.
2. **Display skeleton:**
   - `!BOOT` and `MASS`. The loader shuts the OS down (from `old/entry.6502`) and builds the tables.
   - CRTC and palette, the raster T1 interrupt, and the well and panel drawn.
   - Checked in jsbeeb.
3. **Plotter:**
   - Port `spriteroutine.6502` to Baron.
   - py65 tests against the model, then cycle counts.
   - A demo of balls moving with no physics.
4. **Physics:**
   - Integration, sort, sweep, contacts and merges.
   - A py65 test that matches the model step for step, then cycle counts.
5. **Game:** keys, the dropper, the next ball, merges, critical mass and its chains, the fail warning, game
   over, the panel and the 25 fps loop. **Playable at the end.**
6. **Polish:** sound, the title screen, particles if they fit, and the best score.
7. **Optimisation reviews**, in teddyboy's style.

## Style (Rich, decided: copy teddyboy)

- Tabs, CamelCase constants and lower-case labels with underscores.
- `\\` comment headers: each file's header says what's in it. Each routine's header says what it's for,
  then lists its Inputs and Outputs.
- Baron's modern features:
  - `ZA_AUTO` declared in the smallest scope, with `ZA_INTERRUPT` on the IRQ.
  - Virtual sections for workspace, claimed where they're used.
  - Nested sections for the code that's relocated.
  - `FUNCTION`s and lists for tables made at assembly time.
- The big tables are built at run time by the loader, which is then thrown away.
- Hot branches get `SAME_PAGE` checks, and the `-v` listing's `[auto]` lines are checked by hand.

## Decided on 2026-10-28

1. 25 fps fixed.
2. Sizes: whatever looks circular.
3. Critical mass: at the critical size a ball explodes into balls of various sizes, for a big bonus. The
   details above are Proposed, and the model and play will tune them.
4. Keys: Z/X, SHIFT, RETURN. No joystick.
5. Style: copy teddyboy.
6. The parity palette.
7. Emulator: jsbeeb-mcp only.
