# Decisions

This is the design decision log. Each entry is one of these:

- **Decided:** Rich has made the call. To change it, add a new entry that supersedes the old one.
- **Proposed:** Claude's recommendation, waiting for Rich. When Rich accepts it, it moves to Decided with a
  new D number and keeps its P number in brackets.
- **Open:** it needs a measurement or a preference first.

---

## Decided

### D1. Target: a stock BBC Model B (2026-10-27)
- NMOS 6502 only: never `cmos = TRUE`.
- 2 MHz, 32K of RAM, no shadow RAM, so a single screen buffer.

### D2. Assembler: Baron, in teddyboy's style (2026-10-28)
- Tabs, CamelCase constants, lower-case labels with underscores, and `\\` headers with Inputs and Outputs.
- `ZA_AUTO` in the smallest scope, virtual sections for workspace, and nested sections for relocated
  code.

### D3. MODE 2, drawn by EOR deltas on one buffer (2026-10-27)
Each ball is drawn as the difference between its old and new shapes (Rich's run-merging plotter, in
`old/spriteroutine.6502`). Nothing is erased and then redrawn.

### D4. Flat circles with a checkerboard dither, no highlight (2026-10-27)
Keep it colourful: 16 logical colours over 8 physical ones, with good dither pairs (Rich, 2026-10-28).

### D5. No linked list (2026-10-28; Rich asked Claude to make the call)
- Slots are a structure of arrays, indexed by X.
- `order` is a byte list of the live slots, sorted by bottom edge with an insertion sort each step.
- The physics sweep and the drawing both walk it.

### D6. 25 fps fixed (2026-10-28)

### D7. Sizes: whatever looks circular (2026-10-28)

### D8. Critical mass (2026-10-28)
At a certain size a ball explodes into a number of balls of various sizes and scores a big bonus. The
details are P4.

### D9. Keys: Z/X to move, SHIFT for slow, RETURN to drop. No joystick (2026-10-28)

### D10. The parity palette (2026-10-28)
- Balls use only the 8 odd-parity logical colours (1, 2, 4, 7, 8, 11, 13, 14). The even ones are all black.
- Where two balls overlap, their EOR is even, so the overlap shows as a black seam.

### D11. Emulator: jsbeeb-mcp only, never b2 (2026-10-28)
Other sessions drive b2 through its fixed HTTP port.

---

## Proposed

### P1. The screen: the old layout
- 64 characters by 28 rows (128 × 224 pixels), with the screen at &4800.
- The well is 32 bytes inside, with 1-byte walls. A 30-byte panel sits on the right.

### P2. Units: 1 unit = 1 scanline = half a MODE 2 pixel
- Space is square, as in the old code.
- Positions and velocities are 8.8 fixed point.

### P3. Collisions: exact squares, then logs
- Reject a pair when dx² + dy² ≥ R², with the squares from the quarter-square table.
- The push is (dx, dy)(R² − d²)/2R².
- The products use log and exp tables, with the mass share and 1/2R² folded into constants for each size
  pair.
- Measured against the sketch's trig chain in `tools/collide_cmp.py`.

### P4. Critical mass details
- Critical size C = 10 to start with.
- The pieces come from patterns made in advance: sizes 1 to 4, placed without touching and moving
  outwards.
- Chains score a multiplier.
- The model and play will tune all of it.

### P5. Physics: 25 Hz, two passes, the second over the pairs that touched (2026-10-28, replaces O1)
- One step a frame with the original's constants (kp 0.7 as 11/16, kv 0.35 as 6/16, gravity 288
  units/s²).
- The second pass recomputes the pairs that touched in the first.
- Over six seeds of the stack test: overlap 7.0 and wobble 0.26 units, against 5.3 and 0.52 at 50 Hz with
  one pass.
- It's cheaper than 50 Hz, and calmer, which saves redraws.
- Cheaper second passes (deep contacts only) and quarter-unit positions per ball both made it wobble a
  lot more, so both were dropped.

### P6. The push normalised by d; log d from H (2026-10-28, refines P3)
- The push is (dx, dy)/d · (R² − d²)/2R.
- log d = log max(|dx|,|dy|) + H[log max − log min], from a 256-byte table. That's within 1.8% at the 99th
  percentile.
- Normalising by R (P3 as first written) let balls that hit hard sink into each other.

### P7. Drawing: hysteresis of one pixel across and two lines down (2026-10-28)
Balls at rest redraw 1.2% of the time.

### P8. The plotter (2026-10-28)
- Same colour (a move, or a merge's growth):
  - Each pixel column changes by the symmetric difference of its two spans: two bands.
  - Straight up or down, it walks each shape's boundary list instead.
- New, gone or recoloured: each ball alone, from its byte columns' runs.
- Byte-exact against the model; `SAME_PAGE` on its 20 hot loops.

### P9. MASS packed by ZX02, loaded into the screen's memory (2026-10-28)
- The code and tables unpack to &0E00 to about &4300.
- The packed image (7.4K) and the loader sit in the screen's memory at &4800, which is unused while
  loading. MODE 7's title is at &7C00, above it.
- main clears the screen, and the loader with it.

### P10. The panel: NEXT with the next ball, SCORE and BEST (2026-10-28)
- In a 3 × 5 font with its rows doubled (`tools/font.py`).
- Best is kept while the machine's on.

### P11. Scoring (2026-10-28)
- A merge scores its size, times (1 + the chain).
- An explosion scores 100 and starts a 3-second chain.
- Critical size 10. There are 8 explosion patterns of 5 to 7 pieces (sizes 1 to 4).

### P12. Balls collide 0.75 units outside their drawn circle, with kv at 12/16 (2026-10-28, refines P5)
Rich asked for this: "they overlap a bit too much at times and maybe are not quite repulsive enough. Can
we try making their real radii a bit greater than what is rendered, and make them less squishy". The
numbers are Claude's.
- **The margin:**
  - Balls collide at their drawn radius plus 0.75 units (3 quarter units).
  - Whatever is about what's seen still uses the drawn radius. That's the walls and the floor, the
    game-over test (a top above the rim), the held ball's place on the rim and the dropper's limits.
  - A pair with the critical ball has R capped at 255 quarter units, so it fits a byte. That's 1 unit
    short for a 10 against a 9.
- **The stiffness:** kv, the push's share that goes into velocity, goes from 6/16 to 12/16.
  - At rest a ball's weight is carried by kv × its push, so the overlap under a stack is about g/kv for
    each ball above.
  - kp barely matters at rest, and raising it adds jitter. kv 16/16 shakes the pile.
- **The stack test** (`tune.py`, six seeds, measured on the drawn circles):
  - deepest overlap 6.9 → 3.9 units;
  - 90th percentile 5.1 → 1.6;
  - deepest while landing 9.5 → 5.9;
  - wobble 0.26 → 0.38.
- **Bot games** (four seeds, 3,000 steps each): each step's deepest visible overlap between settled
  balls, both at least 8 steps old.

  | | median | 90% | 99% |
  |---|---|---|---|
  | before | 3.6–4.6 | 6.5–8.1 | 7.7–10.7 |
  | now | 0.6–1.5 | 2.4–3.9 | 3.7–4.8 |

  - Redraws at rest fall from about 3% to under 2%.
  - **Unchanged:** a merge's new ball appears at the midpoint on top of its neighbours. It overlaps them
    by up to 15–20 units for a frame or two (drawn a size smaller), until it pushes them out. Those are
    the worst overlaps left.
  - Growing the new ball's collision radius over its grow-in frames would soften them. That's not done.
- **The cost:**
  - There's no new code: only tables, and a doubling in `timesbig`.
  - For identical piles, it makes about 8% fewer contacts.
  - Games, though, tend to keep a ball or two more in play late on (see O2).
- **Side effects:**
  - The pile stands taller: 26 balls now stand as high as 32 did. So the well holds fewer, and the game
    is harder.
  - Balls touching lightly can show a gap of up to 1.5 units: 21% of touching pairs in the stack test
    show more than 1.
- **Tried and dropped:**
  - Normalising the push by 2d instead of 2R, which is stiffer when deep. It was no better than kv
    alone and needs a wider EXP table.
  - A margin of 1 unit: one bot game ended early.
- **To tune:** `Margin` in `shapes.py`, and kv in `physics.py`'s Params (with `Times6` and `timesbig` in
  the 6502).
- **To compare:**
  - `build/model/compare-squish.mp4` shows the same drops both ways. `tools/compare.py` makes it, for any
    settings.
  - `game-2-stiff.mp4` is a 90-second bot game.

---

## Open

### O3. The critical size: 10 or 9?
- With 10, the bot never reached critical mass in 2-minute games (seeds 2 and 3, 3,000 frames each). It
  happens only in the forced scene.
- With 9 (and 12% bigger balls), it exploded once or twice a game.
- A person may play better than the bot, but 10 may make the game's namesake rare. It's your call: it
  changes the sizes and colours, and the tables follow from `shapes.py`.

### O2. Crowded boards go over the 25 fps budget
- On a crowded board (seed 3's bot game, 3,000 frames), game_frame takes a median of 56,300 cycles and
  81,800 at the 95th percentile. 6.7% of frames are over 80,000. That's after the review's speed-up;
  before it, the median was 62,800 and 16.5% of frames were over.
- Typical boards fit: seed 2's first 400 frames have a median of 18,600 cycles and none over.
- **With P12's physics** (the final build):

  | | median | 95% | over 80,000 |
  |---|---|---|---|
  | seed 2, `frames.py`, 1,500 frames | 44,300 | 66,700 | 0.5% |
  | seed 3, `frames.py`, 1,500 frames | 30,400 | 73,600 | 2.2% |
  | seed 3, lockstep, 3,000 frames | 46,100 | 79,200 | 4.5% |

  - The luck of the game swings this a lot. A build in between, the same physics but with the held ball
    0.75 units higher, played seed 3 differently: it kept more balls in play and was 22.6% over.
  - Identical piles cost about 8% less (fewer contacts). So it's how crowded the board gets that decides
    it, as before.
  - The repeated-explosion scene now peaks at 141K cycles.
- Explosions are the worst frames: a repeated-explosion stress scene peaked around 200K cycles before P12.
- The cost is the physics, at about 750 cycles a contact each pass.
- Options:
  - (a) Accept that a crowded frame takes three vsyncs. The game slows slightly then; the physics' pace is
    per frame.
  - (b) Bigger balls, so fewer fit: fewer contacts. But R must stay under 256 quarter units.
    - Tried in the model: radii 12% bigger, with critical mass at 9.
    - Seed 2: a median of 12 balls against 16, a median of 26 contacts against 38, and the estimated physics
      at the 95th percentile 47K against 77K.
    - Seed 3: no better (66K against 66K).
    - So it helps on some boards but isn't a fix.
  - (c) More optimisation of the contact. It's near this scheme's floor, so perhaps 10-20%.
  - (d) A cheaper physics scheme.
