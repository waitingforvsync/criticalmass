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
Other sessions drive b2 through its fixed HTTP port. `make run` (b2, a window of its own) is Rich's: Claude
never runs it.

### D12. 12 sizes in the same range; critical mass one step bigger (2026-10-28, supersedes O3)
Rich: "a few more distinct sizes of balls, and the biggest ball (critical mass) should be one larger". He
chose "more sizes, same range" and 12 sizes over the other options.
- Sizes 1 to 11 run in equal steps of 2.56 units (radius), from the original's size 1 (4.48) to its size 9
  (30.08). Before, there were 9 steps of 3.2.
- Critical mass is size 12: radius 36.48, one of the original's steps past its size 10. Its pairs' R is
  capped at 255 quarter units (it overlaps by up to about 4 units for the 6 frames before it explodes).
- The physics is unchanged. Two touching balls must sum under 64 units, which is why the range stays put.

### D13. The screen, after Rich's prototype (2026-10-28, supersedes P1's walls)
Rich: "clear the rest of the screen to a checkerboard 4x8 mode 2 pixels black/dark blue (where dark blue is
in fact stippled blue/black)", with "a small margin of that on the left side of the playfield too". He chose
the prototype's thin white walls and black boxes for the panel.
- The checker: blocks of two byte columns by a character row, black and blue stippled with black. The top
  left block is dark.
- One block of margin, then the left wall at column 2 (its inner pixel white), the well at columns 3 to 34,
  the right wall at 35.
- A two-line white floor, then two black lines, then the checker. The rim is a white tick out from each
  wall, two lines deep.
- The panel: black boxes cut out of the checker on its blocks, at columns 40 to 59. They hold the name, NEXT
  (with the next ball), SCORE and BEST.
- GAME OVER goes in the middle of the well, in a black box over the balls (Rich: "move the game over text
  to the centre of the playfield (drop the RETURN text)"). A new game clears the well, and the box with it.
- `tools/layout.py` has it all.

### D14. The memory map, and a loader that makes what it can (2026-10-28, supersedes P9)
Rich:
- "We will reserve 64 bytes stack from &100-&13F. The code org will be &140, it will directly contain the
  set IRQ vector (see teddyboy), fit routines around the places that can't move like IRQ1V, &258, &D00
  (NMI RTI)".
- "make sure all the tables are generated, and put them directly below the screen memory". And: "If the
  code to generate them is bigger than the actual tables let's just leave them embedded."
- "The UI should largely be copied to screen in entry.6502 and then discarded… Just digits (score) and the
  glyphs we need for GAME OVER."

The rest, as built (P15 has Claude's details):
- The code runs from &140 with IRQ1V at &204 its own, MainVars at &206 to &257, &258 = 2 (*FX200: clear
  memory on BREAK), and RTI at &D00. What a BREAK leaves isn't a concern (Rich).
- Then the workspace (the balls), the free space, and the tables up to &4800.
- MASS holds the code, the tables and the starting screen, each packed by ZX02, then the loader.
- The loader makes the tables that cost more packed than made.
- The screen's static parts are only ever the loader's. The 6502's font is the digits and GAME OVER's
  letters (O is 0): 17 glyphs.

### D16. Rounder purple balls (2026-10-28)
Rich: "can you make the purple balls look more round. They currently look more like hexagons". Claude's
answer is P16, waiting for Rich.

### D17. A drop's random fraction, from the VIA (2026-10-28)
Rich: "add some random pixel fraction to the start position… currently they all balance precisely which I
don't want. You can get randomness from a VIA timer." How much, and how it's mixed, is P17.

### D18. The screen is a PNG, unpacked with the code; the memory map round it (2026-10-28, supersedes D14's map)
Rich:
- "create a png of the entire screen which we will convert to bbc screen format and INCBIN to the end of
  the code. It will then be zx02 compressed and entry will decompress it directly to the screen."
- "logo_preview.png… at the top of the sidebar (with a character margin all the way round)". "Once it is
  a png we can keep on retouching it until we have what we need." The PNG has "the dimensions of the
  runtime screen", "along with the playfield boundaries, score/next/etc text, checkerboard and so on".
- "We place the code, baked tables and screen contiguously in memory, ideally that the screen is at &XXE8
  so that the start of the playfield is page aligned, for ease. Then generated tables and workspace live
  above the screen. We will need to arrange for the compressed payload to end at least at the screen end
  address, if not above." The decompressor "can sit above the compression payload as always".
- So: `assets/screen.png` is the starting screen and the source. The code, MASS's tables and the screen
  are one ZX02 payload from &140, unpacked in place to the screen at &33E8. The workspace and the loader's
  tables are above it. P18 has Claude's details.

### D19. The loading title is MODE 2 (2026-10-28)
Rich: "I also have a mode 2 title screen in docs/title_preview.png which I would like to use instead of the
mode 7 text… We don't need the interrupt, just set the screen via CRTC direct writing to the image
dimensions, set the Video ULA via OSBYTE 154, and the palette via FE21 writes. Don't enable screen (CRTC
R8) until image is decompressed."
- `assets/title.png` is 128 × 64 pixels, 64 characters by 8 rows. It's packed in !BOOT and unpacked to
  &7000, centred as the game's screen is.
- The palette is logical = physical.

### D20. The labels in a stylised font, centred (2026-10-28)
Rich: "please change the text "NEXT", "SCORE", "BEST" to a different font. We don't need to try to emulate
the pico-8. Something centred and more stylised is fine, now that we don't rely on drawing it ourselves".
The font is P19.

### D15. Releases go to the site's staging folder (2026-10-28)
Rich: "publish the disk image to ~/dev/waitingforvsync.github.io/beeb/ in the same way that teddyboy does, as
part of the release workflow".
- `make release MSG="..."` copies the disc there as `criticalmass.ssd`, commits only that file (the commit
  names this repo's), and pushes.
- Run it after `make test` passes.

---

## Proposed

### P1. The screen: the old layout
- 64 characters by 28 rows (128 × 224 pixels), with the screen at &4800.
- The well is 32 bytes inside, with 1-byte walls. A 30-byte panel sits on the right. (D13 has the walls and
  the panel now.)

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

### P13. Drops are sizes 1 to 5 (2026-10-28)
With 12 sizes, sizes 1 to 5 (radius 4.48 to 14.72) span what 1 to 4 did (4.48 to 14.08), so the drops look
as they did.
- The 6502 takes a random byte's low 3 bits, again while they're 5 or more, as `game.py` does.
- Critical mass is two more merges away than it was: still rare (O3's worry). Drop sizes are the knob.

### P14. The colours for 12 sizes (2026-10-28)
Red, yellow, violet, lime, azure, orange, pink, green, magenta, sea green, ice (pulsing), white (critical).
- Green and magenta are new and solid, between pink and sea green.
- Neighbours differ in hue, except sea green and ice, as before.
- The checker's blue is CodeB, a ball colour, so it flashes white with an explosion (the walls are white,
  so they don't show it).

### P15. The memory map's details, and the loader (2026-10-28, under D14)
- **The code's places:**
  - `main` before &204, with 16 bytes spare.
  - `random.6502` (`rand`, `drop_size`) after &258, then 15 spare.
  - The plotter at &290, where none of its hot loops crosses a page.
  - The IRQ, the screen's routines, the score and the sound before &D00 (539 bytes spare), then the physics
    and the game.
- **The tables:** `gendata.py` places them, from the top down.
  - The full-page ones go on the top pages (the pixel columns and the physics' nine pages).
  - The big ones (more than a page) go under those.
  - The rest are packed into pages, largest first, so no table of a page or less crosses one. 41 bytes are
    lost to padding.
- **What the loader makes,** and what each saves in MASS:

  | Tables | Packed |
  |---|---|
  | the squares | 291 |
  | Times6 and Times11 | 383 |
  | PairR² (from the squares) | 196 |
  | PairR | 101 |
  | the four PairC pointer tables (from a 144-byte matrix) | 329 |
  | RowHi | 56 |

  - Together that's 3,216 bytes of tables, and MASS went from 8,632 to 7,693 bytes (7,654 with D16 and
    RETURN gone).
  - Left embedded, because they pack small: RoundP/N (13 bytes), BitLen (14), H (25), the font (71).
  - Not yet made: L8 (166 packed, deltas), and the shapes' tables from their spans: Runs (526), the
    boundaries (510) and PixTop/PixBot (295).
- **The loader:** D18 replaced its three stages with one in-place unpack. Loading takes 1.25M cycles
  (0.6 s) once MASS is in.
- **To fit the tables:**
  - The critical ball's shape is left out of the plotter's two-band and vertical paths: its few frames of
    moves go old-away, new-in. Otherwise PixTop would need a second page.
  - The explosion patterns are a byte a number (240 bytes less).
- **The stack's deepest is 11 bytes** in the explosions scene, plus the IRQ's 9.
- **Spare memory (D18's map):** 218 bytes between the code and its tables, 185 before &D00 (after the near
  lists), 13 in the tables, about 200 in the workspace, and 320 among the loader's tables.

### P16. Size 3 drawn by hand, 10 by 20 (2026-10-28, for D16)
- The raster was 9 by 19, its sides 11 lines straight. Its blue pixels are dark, so the eye follows the
  magenta checker's outline: a hexagon.
- Claude drew eight candidates in all four dither phases. Spans `8 14 18 20 20 20 20 18 14 8`, 10 by 20,
  read roundest.
- Its radius is the shape's: 10 units, not 9.6. So the physics keeps its 0.75-unit margin, and the walls,
  the rim and the dropper's limits follow. (The review found that 9.6 left a 0.25 margin, and let it touch
  the held ball at the rim.)
- `Overrides` in `shapes.py`. The azure size 5 (blue and cyan) has the same look and could have the same
  treatment.

### P17. The drop's fraction: T1 EOR the LFSR, ±half a unit (2026-10-28, for D17)
- A drop adds a random byte EOR the system VIA's T1 low byte (&FE44), signed, as 256ths of a unit: up to
  half a unit either way, a quarter of a pixel.
- It replaces the original's ±8/256 jitter, which the collisions' quarter units rounded away.
- T1 alone isn't enough (the review): it runs at the MOS's 10,000 µs and a frame is 39,936 µs. At the
  drop's place in a frame, its low byte comes round to four values a quarter unit apart, give or take a
  few cycles, so one pair of drops in four would still balance. The LFSR's byte mixes it.
- In lockstep the harness pokes the T1 byte and gives the model the same. A run of the model alone draws
  its own.

### P18. D18's details (2026-10-28)
- **`assets/screen.png`:** 1024 × 896, 8 × 4 image pixels a MODE 2 pixel; any whole scale reads.
  - `tools/screenpng.py --compose` drew it from `layout.py`, with the logo at columns 38-61, rows 1-4, and a
    block of checker round it.
  - `layout.py`'s numbers for what the game draws (the next ball, the score, GAME OVER) must follow it.
- **The well:** its first byte is &3400, an even page. So each row of the well is a page, and the plotter's
  `ORA colhi` still works.
  - The 6502 draws by columns from the well's first, and x in units counts from the well's left edge.
- **Above the screen:** the workspace first, then the loader's tables up to &8000.
  - The loader runs inside the workspace while MASS loads, so its tables can't reach it.
  - The workspace isn't zeroed: the game sets everything it reads (the review checked).
  - `make_tables` zeroes its own region first, because the pair tables' "no pair" entries must be 0. The
    tests now start from junk-filled memory with the title in place, which is how that was found.
  - The near and merge lists moved to the room the code leaves before &D00 (LowSpace), so the workspace
    fits under the loader's tables.
- **Unpacking in place:** MASS loads so that the packed payload ends 16 bytes past the screen's end, the
  loader after it.
  - This payload needs 2. A tail that packs badly needs more: ZX02's runs are at most 256, and 3,000 random
    bytes needed 20.
  - `tools/check_inplace.py` runs the loader's decoder at every `make` and fails if its writing ever
    catches its reading.
- **The title:** !BOOT's title is at &7000 while MASS loads, so all of MASS (its last sector included)
  stays under it, and the title stays up until the payload's unpacked.

### P19. The labels' font (2026-10-28, for D20)
- 4 × 5 pixels, each row two lines, centred on the boxes' middle.
- A white top row over cyan, with a blue shadow a pixel right and two lines down, as the logo's CRITICAL.
- `font.py`'s `LabelGlyphs`. It's in `screen.png` only, so the PNG can be retouched freely.
- The score's 6-digit field is centred too: column 44.

---

## Open

### O3. The critical size: 10 or 9? (superseded by D12: 12 sizes)
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
- **With D12 to D14** (12 sizes, drops 1 to 5): seed 3's lockstep game, 1,100 frames, has a median of
  52,600 cycles, 83,500 at the 95th percentile, and 8.5% of frames over. The repeated-explosion scene is 43%
  over, peaking at 175K.
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
