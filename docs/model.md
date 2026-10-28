# The model

The Python model in `tools/` is the reference for the 6502. It holds:
- the physics, in the same integer arithmetic the 6502 will use;
- the screen, as the real MODE 2 bytes, drawn by EOR from the same run tables the plotter will read;
- a bot that plays, and a count of what each frame costs.

| File | What |
|---|---|
| `mode2.py` | The screen's memory (&33E8, 64 × 28, D18), the pixel bits, and the palette bytes. |
| `shapes.py` | Ball shapes and their run tables (lead, single, full, and a mask for each run). |
| `colours.py` | The logical codes, the palette, and each size's dither pair. |
| `render.py` | Balls as EOR bytes, from the run tables, checked against the bitmaps. |
| `tables.py` | SQ, L8, log16, EXP, the radii in quarter units (physics and drawn), and the per-pair constants C. |
| `physics.py` | The world: integrate, sort, sweep, push, apply, clamp. |
| `game.py` | The dropper, merges, critical mass, failing, score, drawing state, hysteresis. |
| `model.py` | Bot games: `make model`, or `--video` for an MP4. |
| `tune.py` | The stack test: physics settings, measured on the drawn circles (P12). |
| `compare.py` | The same drops under several physics settings, side by side in a video. |
| `scenario.py` | Scripted scenes (`critical`: an explosion). |
| `layout.py` | The screen's layout (D13, D18): the well, the panel's boxes, and where the game draws. The starting screen itself is `assets/screen.png`. |
| `screenpng.py` | PNGs to MODE 2 bytes: `assets/screen.png` and `title.png` (`--compose` drew `screen.png`'s first version). |
| `font.py` | The panel's 3 × 5 font. The 6502 has only the digits and GAME OVER's letters. |
| `gendata.py` | Writes `build/gen/`: `data.6502` (constants), `tables.6502` (MASS's tables, under the screen), `made.6502` (the loader's, up to &8000), `tables.json` (every table's bytes, for the test), and `screen.bin` and `title.bin`. |
| `machine.py` | py65 with MASS loaded and the real loader run, from after its OS calls to `main`. |
| `test_tables.py`, `test_background.py` | Every table in memory after the loader (its own included), and the screen it unpacks, against the model. |
| `test_plot.py`, `bench_plot.py`, `replay.py` | The plotter against the model: cases, a benchmark, a game's frames. |
| `test_physics.py`, `frames.py` | The physics against the model, step by step, with the cost. |
| `lockstep.py` | The whole 6502 game against the model, every frame (`--scene critical` forces an explosion). |
| `profile.py` | Cycles by label, in py65. |
| `preview.py` | `sizes.png` and `well.png`. |

## The shapes and colours

- The shapes are made from the drawn radius (D12). Sizes 1 to 11 run in equal steps of 2.56 units, from the
  original's size 1, 1.6 (0.8 + 2) = 4.48 units, to its size 9, 30.08. The critical ball (12) is 36.48, one
  of the original's steps past its size 10. Balls collide at r(s) + 0.75 (P12).
  - Two of the largest touching must stay under 64 units for the collision maths. That's why the range
    stays put and the steps got smaller.
  - For each size the generator picks whichever width and height parity fits the circle best.
  - The sizes come out 4×8, 7×14, 10×20, 12×24, 14×29, 17×34, 19×39, 22×45, 24×49, 27×55, 30×60 and
    36×72 (pixels × lines).
  - Size 3 is drawn by hand (D16): its raster, 9×19, looked like a hexagon. Its radius is the shape's,
    10 units.
- **The run format** has five numbers for each byte column: lead, single, full, smask and fmask.
  - The single run sets only the pixel with the longer span.
  - The full run sets both pixels, or just one in an edge column, where the other pixel is empty. That
    case is why there's a mask for each run: it lets heights be odd.
  - `preview.py` checks that the runs draw exactly the bitmap at both parities.
- **The palette (D10):**
  - The ball codes are the odd-parity logical colours: R 1, G 2, B 4, Y 7, M 8, C 11 and W 13, plus P 14,
    a second white.
  - P is used only by size 9, so the IRQ can make the balls one merge from critical pulse.
  - Every even code is black.
- **The sizes:**
  - 1 is red and 2 is yellow, both solid.
  - Then the dithers: 3 violet (B/M), 4 lime (G/Y), 5 azure (B/C), 6 orange (R/Y), 7 pink (M/W), 8 sea
    green (G/C) and 9 ice (C/P).
  - 10, the critical size, is white.
  - Neighbouring sizes differ in hue, so a pair to merge stands out.

## The physics: what the model settled

**1. The push has to be normalised by d, not by R.** P3 first had the push as (dx, dy)(R² − d²)/2R². That
dies away as two balls meet in the middle, so at 25 Hz balls that hit hard sank into each other and
stayed there, with overlaps of up to 28 units.
- The push is now (dx/d)·(R² − d²)/2R.
- log d comes from the logs of |dx| and |dy| through a 256-byte table, H: log d = log max + H[log max −
  log min]. That's within 1.8% at the 99th percentile, which is plenty for a direction. It replaced
  `log16(d²)/2`, which cost a second `log16`. The constant is C = 32 (log2 share + 2 − log2 Rq).
- When two balls sit exactly on top of each other (dx = dy = 0), they're pushed apart vertically.

**2. The physics is one step a frame (25 Hz), with two passes; the second recomputes the pairs that
touched in the first (P5).** It used the original's constants: kp 0.7 (11/16), kv 0.35 (6/16) and
gravity 288 units/s². kv is now 12/16 (item 4). The stack test (`tune.py`, before item 4, overlaps on the
physics circles), averaged over six seeds:

| | overlap | wobble | moves a ball-step |
|---|---|---|---|
| **25 Hz, two passes, the second over the touching pairs** | **7.0** | **0.26** | **0.05** |
| 50 Hz, one pass | 5.3 | 0.52 | 0.12 |
| 25 Hz, one pass | 11 | 0.7 or more | |
| 25 Hz, second pass only over contacts diff >= 8R / 16R / 32R | 6.9 / 9.2 / 10.8 | 1.6 / 4.2 / 4.8 | |
| 25 Hz, second pass only over the first 32 / 24 / 16 contacts | 7.7 / 9.4 / 12.1 | 0.9 / 0.7 / 1.5 | |
| quarter-unit positions per ball | 7.3 | 0.44 | 0.10 |

The second pass over every touching pair is what keeps the pile calm. Every cheaper version tried
shook it.

Positions are clamped to the well again after the pushes. Otherwise a push could carry a ball past the
floor, and its drawing would EOR into the wall or run off the screen.

**3. Hysteresis: 2 units across and 2 lines down.** A ball is redrawn only once it's a pixel across or 2
lines down from where it was drawn. That cut redraws of balls at rest from 8.4% to 2.8%.

| hysteresis (x, y) | redraws at rest | median cycles |
|---|---|---|
| 2, 1 | 8.4% | 24,400 |
| **2, 2** | **2.8%** | **23,200** |
| 4, 2 | 2.4% | 22,400 |

**4. Balls collide 0.75 units outside their drawn circle, and kv is 12/16 (P12).** Rich found the balls
overlapped too much and weren't repulsive enough.
- The overlap at rest comes from kv. A ball's weight is carried by kv × its push, so a stack's overlap
  is about g/kv for each ball above. So kv went from 6/16 to 12/16. kp hardly matters at rest, and raising
  it adds jitter.
- The margin hides what overlap is left. The walls and floor clamp at the drawn radius.
- The stack test, now measured on the drawn circles, with the same drops for every setting (`tune.py`):

| | deepest | 90% | landing | wobble | gap > 1 unit |
|---|---|---|---|---|---|
| margin 0, kv 6/16 | 6.9 | 5.1 | 9.5 | 0.26 | 0% |
| kv 12/16 | 4.6 | 2.9 | 7.4 | 0.38 | 0% |
| **margin 0.75, kv 12/16** | **3.9** | **1.6** | **5.9** | **0.38** | **21%** |
| margin 1, kv 12/16 | 3.6 | 1.3 | 5.7 | 0.54 | 43% |
| kv 16/16 | 3.8 | 2.5 | 6.8 | 4.84 | 0% |

- The pile stands taller: 26 balls now stand as high as 32 did.

## The budget: measured on the 6502

The model's cycle estimates were replaced by measurements of the 6502 in py65.
- `tools/frames.py` and `tools/lockstep.py` run real games and check every frame against the model.
- The physics costs about 830 cycles a ball and 870 a contact each pass.
- The plotter costs:
  - a move down 2 lines, summed over sizes 1 to 9: 32,000 cycles;
  - a one-pixel move across, likewise: 37,800 cycles;
  - drawing anew: about 28 cycles a byte.

| | median | 95% | over 80,000 |
|---|---|---|---|
| a typical board (seed 2) | 18,600 | 34,200 | none |
| a crowded board (seed 3) | 62,800 | 90,200 | 16.5% |

That's O2 in `decisions.md`.

## Critical mass

- Two size-11 balls merge into a size-12 ball. It shows white for 6 frames (CriticalHold) and is solid for
  that time, then explodes. Its pairs' R is capped at 255 quarter units, so it can overlap its neighbours
  by up to about 4 units in that time.
- One of eight patterns replaces it, each 5 to 7 pieces of sizes 1 to 4. The pieces are placed largest
  first without touching, cover 35% to 70% of the big ball's area, and fly outwards and upwards.
  - The patterns are stored a byte a number: offsets in half units, velocities in eighths of a unit a
    step.
- Score: each merge scores its size. An explosion scores 100. Merges within 3 s of an explosion are a
  chain, and score their size × (1 + chain count).
- `scenario.py critical` shows one.

## Videos

`make model` and `tools/model.py --video` write `build/model/game-<seed>.mp4`. `scenario.py critical`
writes `scene-critical.mp4`. They're 25 fps at 2× scale, with each MODE 2 pixel 2 TV pixels wide.

`lockstep.py` checks the 6502's screen against the model's every frame. So these videos show exactly what
the BBC draws, palette effects aside (the size-9 pulse and the explosion's flash happen in the IRQ, not in
the screen's memory):
- `build/model/game-2-tonight.mp4`: 90 seconds of the bot playing, with the physics before P12.
- `build/model/scene-critical.mp4`: an explosion.
- `build/model/game-2-stiff.mp4`: 90 seconds with P12's physics.
- `build/model/compare-squish.mp4` (and a still, `.png`): the same drops under the old physics and P12's,
  side by side, from `tools/compare.py`. Each frame is drawn fresh, so there's no hysteresis.
