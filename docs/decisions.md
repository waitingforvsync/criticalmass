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

### D21. The limit at the top of the well is a blue line (2026-10-28)
Rich: "please amend the screen png so that the limit at the top of the playfield is a visible blue line".
Then, seeing it two lines thick: "do we need it in the png at all?" and "i only want a single pixel line".
So it's one line, drawn by the game, not in the PNG. The details are P22.

### D22. Sparks when balls merge (2026-10-28)
Rich, on P21 made faster and shorter: "This looks great". He committed it (a5c2b34) and it's released.

### D23. A 32-byte stack (2026-10-28)
Rich: "i think the stack can be reduced to just 32 bytes". &100-&11F; the code starts at &120. The most
measured is 11 bytes in lockstep, plus 9 for the IRQ; game over and a new game take at most 6.

### D24. Code on self-modified operands goes in zero page, if there's room (2026-10-28)
Rich, on the sparks' slots in zero page ("the sparks barely benefit from being zp as they are accessed via
,X and are no cheaper"): "any routine which self-modifies in a hot loop should go to zp if there is space",
and "if necessary, move routines with hot loops into their own file so they can be included in a more
fine-grained way". The details are P23.

### D25. A wipe at game over (2026-10-28)
Rich: "when the game ends, i would like to clear every alternate line of the jug from the bottom up, one
character row each frame (an animated effect), before the "game over" text is superimposed". The even
lines of each row of the well, a row a game frame from the bottom (27 frames, about a second), then
GAME OVER; RETURN counts once it's done.

### D26. log16 inlined into pair (2026-10-29)
Rich, on P24's log16 against D24's letter: "yes, inline log16". pair takes its self-modified jump; zero page
holds the plotter's EOR loops alone.

### D27. 11 sizes: today's size 11 removed, green with it (2026-10-29, supersedes D12's 12)
Rich, on P25: "keep the critical ball radius, and remove the size below. The colour I would like to remove
is pure green, we keep both yellow/green and sea green."
- Sizes 1 to 10 are as they were (4.48 to 27.52 in steps of 2.56). Critical mass is size 11, radius 36.48
  as before.
- The colours: red, yellow, violet, lime, azure, orange, pink, magenta, sea green, ice (pulsing), white.
- Rich on difficulty: "I don't want to make it too easy to reach critical mass either. It should happen
  once in a while when playing, not every time." To be tuned by his play.

### D28. Chain reactions score double each link; critical mass scores 1,000 (2026-10-29)
Rich: "can we improve the scoring mechanism so you get increasingly bigger scores for "chain reaction"
merges. And award a good bonus for reaching critical mass." He took Claude's proposal:
- Each ball has a link. A dropped ball's is 0. A merge's ball is a link past the larger of its two balls'
  links, counting only balls made within the last second (ChainAge, 25 frames); otherwise it's link 1.
- A merge scores its size times 1, 2, 4, 8... by link (size x 2^(link - 1)). A 3 cascading to a 7 scores
  3 + 8 + 20 + 48 + 112 = 191, against 25 before.
- An explosion's pieces are link 1, so the merges they set off chain too. This replaces the three-second
  multiplier after an explosion.
- The critical mass bonus is 1,000 (it was 100).

### D29. The explosion: the player stands still on the white ball, then it bursts (2026-10-29)
Rich: "on the moment of contact of the two flashing balls, they merge to the final big white ball ... I
think we should pause on the big white ball for half a second and then we want to throw other balls
outwards with force while the white ball shrinks to zero, maybe some particle effects too." He took
Claude's plan, with "no screen shake":
- The merge makes the white ball whole at once, with a rising tone. The player stands still for half a
  second at full speed (12 frames), no keys. (Rich tried a second, "Keep the white ball visible longer at
  full update speed", then "not hold the white ball so long before exploding, maybe about half a second
  is enough".) The physics runs on (Rich, after seeing it frozen: "i would just like to try
  continuing to simulate physics during the half second pause so it doesn't look quite so unnatural"),
  so the white ball pushes its neighbours aside rather than showing black where it overlaps them.
- Then, first thing in the frame after, the burst:
  - The white ball leaves the physics and is drawn a shape smaller each frame until it's gone.
  - Every other ball is kicked away from its centre at K/d (8 units a frame at 40 units), worked through
    the physics' log tables.
  - The pieces fly out faster than before (2.5 units a frame, plus 6 more at the edge).
  - Two rings of white sparks, the flash and the boom.
- Nothing fails from the frame critical mass is made until 50 frames after the burst, so what the burst
  throws above the rim can't end the game (and, the review's find, nor can a pile that's been failing for
  two seconds just as the critical ball forms).
- The colours stay as D27 has them "for the moment" (pink beside magenta).

### D30. Slow motion around critical mass: a frame every 6 vsyncs (2026-10-29)
Rich: "I still think it's over too quickly. Can we slow things down to half-speed update when the white
ball is present and exploding?" A half timestep was tried first (half the gravity, half the velocity's
way). Then Rich: "let's forget the half timestep, and just halve the framerate instead. The stop motion
look might work", then "let's exaggerate the slowdown even more, 6 frames between updates instead of 2
or 4", and "if it is the irq routine which normally sets the frame pacing, it would be good just to be
able to set the value directly that it uses".
- `main` paces a frame every `Pace` vsyncs: 2 (25 fps), or 6 in slow motion (8.3 a second). The game sets
  it: SlowPace at the burst, FramePace again when slow motion's over. The game's frame is unchanged:
  nothing is skipped, so slow motion costs nothing in a normal frame, and its frames have three times
  the time.
- Rich: "let's not slow down until the explosion". Slow motion is the burst's frame and the 11 after
  (`Slow`, 12): the shrinking white ball and what the burst throws.
- The IRQ's flash, pulse and sound run on at 50 Hz.

### D31. The shrinking white ball sheds sparks (2026-10-29)
Rich: "If we can add more particle effects during that time, that'd be great" (the slow motion).
- In each frame of its shrinking, the burst's white ball throws a ring of 8 white sparks. They live 3
  frames (ShedLife). At first each ring was thrown from its edge, so the rings shrank with it; Rich: "the
  sparks look like they're going inwards, but i would like them to look as if they are exploding
  outwards". Now every ring is thrown alike (ShedR, 24: from 24 units out at 12 a frame), so each is
  seen flying out, the newest inside the last. Until the
  burst's own sparks leave the well, the pool can't hold every ring, so an early one can come out partial.
- Two critical balls bursting together shed in the order they burst, in both the model and the 6502
  (`ShrinkSlot`): lockstep's `twin` scene checks it.
- There are 32 spark slots (16 before), in the loader's tables, which now have no bytes spare.
  `update_sparks` looks no higher than `SparkTop`, past the highest slot in use, so a normal frame
  doesn't pay for the extra slots.

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

### P20. A merge's ball flashes white for its first frame (2026-10-28, tried and dropped: Rich found it too quick to notice)
- The original covers its new ball with a flash-coloured disc for 4 frames at 60 Hz. Here the new ball's
  first frame is drawn in white (the critical ball's colours), still a size smaller as before, then its
  own colour for the second, then its full size.
- No physics changes: the merge happens when it did. The pair flashing before merging was the other
  choice. It costs two whole balls' recolouring in the frame before, and delays each merge a step.
- The cost: the merge frame is as before (white costs what any colour does). The second frame recolours
  one ball of the old size, about what drawing it new costs (bench_plot's "new": 3.2K cycles for size 3,
  9.2K for 7, 16.5K for 10). 8 bytes.
- The merge into critical mass doesn't flash: it's white already.

### P21. A merge throws a ring of sparks (2026-10-28, for D22)
- After the original's particles, simpler: the original throws 3 × the new radius of them, each with a
  random drift and life. Here each merge throws 8, one every 45 degrees, from the new ball's edge.
  - They move at r / 2 units a frame along an axis, 3/4 of that on the diagonals (r / 4 at first; Rich
    asked for faster and shorter: places in quarters of a unit rather than eighths, the same speeds).
  - They slow by 1/8 a frame (rounded toward 0). Gravity (an eighth of a unit a frame, each frame) was
    tried, then taken off for Rich to see them without it: `sparks.py`'s Gravity, 0 or 1, and the 6502
    follows.
  - They go after 13 to 20 frames (0.5 to 0.8 s, varying by direction; 25 to 39 at first), or on
    leaving the well. The ring spreads about 3.5 radii, as the original's does.
- Each spark is a pixel two lines tall in the new ball's colours, as its stipple has them there.
- **Drawing:** one pass a frame, after the balls.
  - Each spark is EORed off with what it was EORed on with, moved, and EORed on with (the byte EOR its
    colour) AND its pixel's mask, which it keeps.
  - So it shows its own colour over balls too, and since it's all EOR, the balls' drawing in between
    doesn't matter. Two sparks on one pixel can show the wrong colour for a frame.
- **Room:** 16 slots, in zero page (176 bytes, &4C-&FB; the pool is now &00-&4B and &FD-&FF), zeroed by
  the loader. A ring takes the free slots, so a third ring at once is cut short.
- **Code:** 184 bytes in `sparks.6502`, before &D00 (that gap now has 1 byte left), and `sparkthrow.6502`
  after `game.6502`. Plus 24 bytes of direction tables. About 60 bytes of code room are left in all.

### P22. The limit's line (2026-10-28, for D21)
- Dotted blue across the well's 32 byte columns on line 32 (`layout.py`'s `LimitLine` and `LimitByte`:
  &20, each byte's left pixel, as the checker's blue on even lines; Rich asked to see it dotted, after
  solid, &30): level with the bottom of the white ticks on the walls (31-32), and just under the held
  ball, whose lowest line is 31, so they never overlap.
- The game draws it: `new_screen` clears the well, then `draw_limit` (`limit.6502`, above &D00 to fit)
  draws the line, and `main` calls `new_screen` before the first game too. `screen.png`'s well stays clear;
  `gendata.py` asserts it.
- The model's `background` (what the tools start a game on) is `screen.png`'s plus the line.
- It's inside the well, where the balls are EORed, so a ball crossing it shows black there (any ball
  colour EOR blue is an even code). The sparks show their own colour over it.
- `test_background.py` now scribbles over the whole well before `new_screen`.
- First tried as two lines (32-33) in `screen.png`, read back by gendata: Rich wanted one, and none in
  the PNG.

### P23. What goes in zero page (2026-10-28, for D24)
- Nothing writes its own operands inside a loop: the patches are once a call. The loops that run on
  patched operands, and their sizes: the plotter's EOR loops `eor_up`/`eor_left`/`eor_right` (111 bytes,
  6 patches a `plot_runs` call), `log16` (71, its computed jump patched once a contact), the plotter's
  pixel paths (368, 16 patches a call) and `plot_vertical` (307, 10).
- Zero page holds the first two: `eor.6502` and `log16.6502`, split out of `plot.6502` and `physics.6502`
  and included by `zeropage.6502`, at &30-&E4 (181 bytes). (P24 has since inlined `log16` into `pair`:
  zero page holds `eor.6502` alone.) Each patch is a zero page store: a cycle and a
  byte less. The loops run no faster, but they can't cross a page there. The others don't fit.
- The image sits in the payload at `.lowspace`, where the near and merge lists go (scratch until the game
  runs), and the loader copies it down: no RAM of its own.
- The pool is &00-&2F (30 bytes used) and &FD-&FF; &E5-&FB is spare.
- The sparks' slots went back to the loader's table gaps (zp,X saved bytes, not cycles: about 30 bytes
  of code; a DEC costs a cycle more).
- The plotter now starts at &2FE, the lowest start where none of its hot loops crosses a page;
  `background.6502` fills the room before it.
- Code room went from about 45 bytes to about 227 (with D23's 32). The frames cost about 70 cycles more
  at the median (0.3%), most likely physics branches now crossing pages after `log16` left.

### P24. The optimisation round (2026-10-29, Rich asked for it: "both size and speed")
- Profiled first (seed 3's bot game, every cycle of game_frame by label; `tools/profile.py` now takes
  MASS's labels only, as !BOOT's lie over MASS's code): in the frames over 60,000 cycles, the physics was
  68% (pair 32%, apply 13.5%, sweep 8.4%, integrate 7.1%, log16 3.7%) and the drawing about 30%.
- Five agents, an area each, each checking its code against the old in py65; the lead integrated them,
  with `make test` after each. Every result is byte-identical to before: the model is unchanged.
- **The broad phase:** sort from the end with a sentinel past the end of Order; the sweep's inner loop
  rewritten (no y test: pair rejects those first; the x test by dx's sign; X the Order index); resweep
  counts down (the second pass's pushes sum the same in any order); the near lists each on one page with
  the byte before them (resweep reads NearA-1,X and NearB-1,X).
- **The per-ball physics:** apply with a fits-a-byte test and the push's sign deciding which wall to test;
  integrate with the size held in Y, and the floor or the top tested by the move's sign (and, after, the x
  walls too); age folded into integrate (so
  pair's merge test is against MergeAge + 1); each ball array in one page.
- **The contact solver:** pair rewritten: no R box test (d^2 >= R^2 covers it), the log of R^2 - d^2
  inlined from log16 (its high byte is always 1 there: the pointers take the 256), log d folded into each
  axis's index, the pushes by axis with the sign tested once, the first pass's work after the pushes. PairR
  and Times32Lo/Hi went; Times32M1 came. **Against D24's letter:** log16's self-modified jump is now in
  pair, which is too big for zero page; inlined it saves about 45 cycles a contact, against the 1 a zero
  page patch saved. Rich agreed: D26. Zero page holds `eor.6502` alone now, &9F-&FB is free.
- **The drawing:** the pixel paths without colhi (the same-colour paths are always in the well) and with a
  quick setup for the same shape; plot_vertical's boundary list with the kind folded into each entry
  (BndKind and BndCount gone: 829 bytes of tables); draw_balls with the anchors biased (one compare each),
  a flag for when there are dying balls, and the next ball skipped when it's unchanged.
- **The rest:** the score draws only the digits that changed (a buffer of what each cell shows) with a
  pre-coloured font; the IRQ's palette writes as loops over tables; do_fail's quick reject; sparks, sound,
  random, new_game, add_score, fill_box, main and the GAME OVER text tightened.
- **The result,** seed 3's lockstep game (1,100 frames): median 46,480 -> 35,858 cycles, 95% 84,086 ->
  63,850, the most 116,853 -> 92,735, over 80,000 84 -> 5. The repeated-explosion scene: 109 -> 56 of 250
  over. Code room about 184 bytes -> 57 + 40 + 96 under &D00 + 958 above it; MASS's tables 829 bytes
  smaller.
- **Then** (Rich: "do the first two"): integrate tests only the x wall a ball's moving towards (every ball
  starts a step in the well: lockstep's `inject` clamps its balls now, as the game's own are), and BallRU
  and BallSize16 are set in add_ball, not every step (`test_physics.put` and lockstep's critical scene poke
  them). Seed 3: median 35,834 -> 35,404, 95% 63,812 -> 63,119.
- **Not done yet** (each small): Times6 biased, H stored as 255 - H, a high-byte table for pair's log, the
  sweep entering pair after its first store, NumNear/NumMerges in zero page, the pixel path's go blocks
  duplicated, a table for the sparks' decay, the IRQ saving X and Y in zero page.

### P25. One size fewer, so critical mass can be reached (2026-10-29, for D27: (b))
- Rich: "My feeling is that it probably is not, and we may need to tune it a bit, maybe removing one of
  the ball sizes". The journal (2026-10-29) has the games.
- With 12 sizes, a lookahead bot that sees each drop's result exactly (`tools/play.py`) reached critical
  mass in 2 of 3 games: 3 explosions, the first at 4.4 and 4.9 minutes. A critical ball takes at least 330
  drops' mass, and it needed about 333. Given aiming and judging errors, it never did (0 of 3). It reached
  11 at about 2.5 minutes and lost about 2 minutes later.
- With 11 sizes (critical mass at 11: half the mass), the erring bot reached it in all 6 games:
  - (a) **the same range**, steps of 2.84 (the biggest playable ball stays 30.08): 4 explosions in 3
    games, the first at 2.1 to 2.6 minutes; games of 5 to 7 minutes.
  - (b) **today's size 11 removed** (sizes 1 to 10 unchanged, critical mass after 10): 10 explosions in 3
    games; games of about 8 minutes, and one alive at the 15-minute cap.
- **Proposed:** (b). It played best, and it's the smaller change: the shapes of sizes 1 to 10 and the
  critical ball stay as they are, and one shape and colour go (the pulsing ice would go to size 10).
  Whether the critical ball should stay 36.48 or shrink to one step past 10 (30.08) is open.
- The 6502 takes the critical size from gendata (`GenCriticalSize`), so it's mostly `shapes.py` and
  `colours.py`; the tables and tests follow.

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
