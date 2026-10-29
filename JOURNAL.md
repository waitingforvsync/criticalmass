# Journal

What was done each session and what was learnt, newest last. Measurements go here; decisions go in
`docs/decisions.md`.

## 2026-10-27/28: the plan

- Decoded the original from its cart. Rich then supplied it as `docs/src.lua`.
- Compared collision methods (`tools/collide_cmp.py`). The sketch's trig chain is 0.5 units rms out in the
  overlap. Exact squares at quarter-unit precision are 0.10 units out. Logs are no good for the distance,
  but fine for the products. Hence P3.
- Wrote `docs/plan.md`. Rich answered its questions, and the answers are in `docs/brief.md` and
  `docs/decisions.md`.
- Added jsbeeb-mcp to the project's local config (D11).

## 2026-10-28 (night, unsupervised): phase 0, then the model

- Phase 0:
  - `git init`, with nothing committed.
  - `.gitignore`, `.venv` (py65 1.2, pillow 13, numpy 2.5), `Makefile`, `CLAUDE.md`.
  - `docs/brief.md`, `docs/decisions.md`, `docs/README.md`.
- **Phase 1, the model** (`docs/model.md` has the details):
  - Shapes come from the radius, with the best width and height parity for each size. The run format has a
    mask for each run, so odd heights work. The runs are checked against the bitmaps.
  - Colours: red and yellow are solid, then violet, lime, azure, orange, pink, sea green and ice (pulsing),
    and white for critical. Previews are `build/model/sizes.png` and `well.png`.
  - The physics found a flaw in P3. Normalising the push by R where it should be d made balls that met hard
    sink into each other: overlaps up to 28 units at 25 Hz. Fixed: log d = log16(d²)/2.
  - The physics runs at 50 Hz, two steps a frame, with the original's constants. Its overlap, 2.8 units, is
    the original's 2.9. It's cheaper than 3 passes at 25 Hz: a median of 25,600 cycles a frame against
    33,600.
  - Hysteresis of 2 units across and 2 lines down: balls at rest redraw 2.8% of the time, down from 8.4%.
  - Estimated cost, 60 s of bot play: a median of 19,400 cycles a frame, 36,200 at the 95th percentile and
    62,900 at worst, against 80,000. These are estimated costs, until the 6502 can be measured.
  - Critical mass works in the model (`scenario.py critical`). There are six explosion patterns of 5 to 7
    pieces, sizes 1 to 4, placed largest first.
- **Phase 2, the display skeleton**, in `src/`:
  - `!BOOT` shows a MODE 7 title and *RUNs MASS, which loads at &1900. Its loader shuts the OS down, copies
    the code to &0E00, builds the squares, clears the screen, draws the well, sets the CRTC (64 × 28) and the
    parity palette, and starts a vsync IRQ.
  - The main loop runs at 25 fps.
  - Booted in jsbeeb-mcp. The screen matched the model's background byte for byte (all 14,336 bytes, bar the
    loop's blinking mark).
- **The model review** (agent) found these, all fixed:
  - Two critical balls could meet: R passed 255 and the int path crashed. Critical balls now neither meet
    each other nor merge.
  - Nothing stopped a ball at the screen's top.
  - The held ball could grow into the wall.
  - Quarter units were floored, making pushes 9% too strong. They're rounded now, and a pair is out from
    63 units.
  - The float yardstick used other radii and factors.
  - There were floats in the int game path: the patterns and the dropper are 8.8 now.
  - The cycle model left out the per-ball cost of each substep.
  - The preview never showed parity 0.
- **Phase 3, the plotter** (`src/plot.6502`):
  - The first version merged the two balls' byte-column runs (Rich's scheme). It was right first time
    against the model, but slow: about 250 cycles of setup a column and 120 a boundary. A small move down
    cost a median of 16,400 cycles.
  - Measured in the model, moves are 49% straight up or down and 42% across with the same shape and colour.
    New, gone and recolours are the other 9%.
  - So now:
    - Same colour: each pixel column changes by the symmetric difference of its two spans, which is two
      bands. The dither is anchored to the screen, so a move only touches the edges.
    - Straight up or down: each byte column's run boundaries shift by dy, which is 2 to 4 bands of dy lines.
    - Alone (new, gone, or one side of a recolour): each byte column is three contiguous runs.
  - `tools/test_plot.py`: 320 cases on a screen of random bytes, every byte against the model. All pass.
  - `tools/replay.py` replays 1,500 frames of a bot game through the 6502's plotter. The screen matched the
    model's after every frame.

    | | median | 90% | 95% | max |
    |---|---|---|---|---|
    | cycles drawing a frame | 13,800 | 29,100 | 36,500 | 67,200 |

    | move | median cycles |
    |---|---|
    | vertical | 3,000 |
    | across or growing | 5,200 |
    | new or gone | 2,100 |
- **Plotter, further:**
  - The pixel path now reads spans from tables padded with 3 empty columns either side, uses left and
    right copies of `eor_up` patched once a call, and is unrolled in pixel pairs. Moves of more than 3
    pixels erase and redraw.
  - Measured on `bench_plot.py`, summed over sizes 1 to 9: a one-pixel move across costs 43,500 cycles,
    down from 61,100.
  - The replay is still byte-exact.

    | | median | 95% | max |
    |---|---|---|---|
    | cycles drawing a frame | 12,400 | 31,900 | 63,200 |

- **The phase 2 review** (agent) found no bugs. Fixed anyway:
  - the ACIA is reset, so no stray IRQs;
  - the OS vector is read without zero page while the MOS still runs;
  - the `vsyncs` comment;
  - the copy-down assert is exact now;
  - MainVars stays clear of &287 (the *FX247 BREAK intercept);
  - `CLD` in the IRQ.
- **Phase 4, the physics in 6502** (`src/physics.6502`, `src/balls.6502`):
  - It follows `physics.py`'s int mode exactly. `tools/test_physics.py` compares every ball's position,
    velocity, hit flag and age, the order and the merges, after every step, on random scenes and on
    snapshots of bot games. It matched first time once it built (the build errors were `INC abs,Y`, which
    doesn't exist, and a variable named `a`).
  - It was much slower than estimated: 36,700 cycles a step for 14 balls and 16 contacts, about 1,000 a
    ball and 1,000 a contact.
  - Optimised, all still exact against the model:
    - log d from the logs of |dx| and |dy| through a 256-byte H table, in place of `log16(d²)`. It's within
      1.8% of the true d at the 99th percentile. This changed the model.
    - `log16` jumps into a chain of shifts, chosen by a bit-length table.
    - The EXPs are inline.
    - The sweep pre-checks the high bytes, which can only skip pairs the box test would reject anyway.
    - Clamps check the high bytes first.
    - A push that fits a signed byte uses ×3 and ×11/2 tables. kp = 12/16 would have been simpler, but over
      six seeds it doubled the wobble.
  - **The physics is now 25 Hz with two passes**, the second over the pairs the first found near. Over
    six seeds of the stack test:

    | | overlap | wobble |
    |---|---|---|
    | 50 Hz, one pass | 5.3 | 0.52 |
    | 25 Hz, two passes | 6.8 | 0.26 |

    It saves an integrate, a sort and a broad sweep each frame, and the halved wobble means fewer redraws.
    The model's defaults and the 6502 both changed (gravity 118 8.8 units a step², merge age 4).
  - Cost now, on late-game scenes: about 830 cycles a ball and 950 a contact per pass. That's a median of
    53,600 cycles a frame for 16 balls and 19 contacts. Still too much: next, the contact's cost.
- **Real frame costs** (`tools/frames.py`): a bot game, with the 6502's physics and plotter run on every
  frame and checked against the model.
  - The second pass now revisits only the pairs that touched in the first (overlap 7.0, wobble 0.26: the
    same feel).
  - Over 1,500 frames:

    | | median | 95% | max |
    |---|---|---|---|
    | cycles a frame | 40,900 | 71,500 | 110,100 |

    26 frames went over 80,000.
- **Physics experiments that failed:**
  - A second pass over only the deep contacts (any threshold) multiplies the wobble 6 to 18 times.
  - Quarter-unit positions per ball (so |dx| is a subtract) doubles the wobble.
  - Both reverted.
- **Physics, optimised further** (still exact):
  - A size-pair table index gives R, R² and both log constants.
  - |dx| is rounded in one pass, with the negative case as ~dx + 33.
  - The slots go to `pair` in X and Y.
  - The model lost its "out from 63 units" check, which it never needed.
  - A contact is about 870 cycles a pass, down from 950, which is near this scheme's floor.
- **The plotter review** (agent) found no bugs in about 9,500 more stress cases. It prototyped seven
  speed-ups: per-shape boundary lists for the vertical path, the pixel path's loops inlined, the padding
  shared between shapes (PixPad 4), and tables kept on a page. Applied, with the boundary lists made by
  `gendata.py`. Summed over sizes 1 to 9, a move down 2 costs 32,000 cycles, down from 41,700.
  - Also: `SAME_PAGE` on all 20 hot-loop branches (`plot.6502` now comes first in the code); `plot_ball`'s
    input limits written down; the test's "grow" case is a true same-colour growth now.
  - MASS now loads at &1200: the code and tables had outgrown &1900 to &4800.
- **Phase 5, the game in 6502** (`src/game.6502`, `src/main.6502`):
  - Keys (Z, X, SHIFT, RETURN), the dropper with grow-in, drop jitter, merges with chains, BCD score,
    critical mass (8 patterns), failing and game over (RETURN restarts), and drawing with hysteresis.
  - The model was made 6502-shaped for this: the same 16-bit Galois LFSR, a game driven by key flags (the
    bot presses keys), and 8 patterns picked by 3 random bits.
  - **`tools/lockstep.py`** runs the 6502's `game_frame` beside the model's with the bot's keys. Each frame
    it compares every ball, the game's state and the whole screen.
    - Seed 2, 400 frames: all exact.
    - Seed 3, 3,000 frames, 135 merges: all exact.
  - It plays in jsbeeb (screenshots in the session): drops, moves, landing and bouncing.
  - **Budget:** seed 3's game crowds the board. Before the latest physics work, game_frame took a median of
    64,700 cycles, and 612 of 3,000 frames went over 80,000. The crowded board is the open problem: a
    contact costs about 870 cycles a pass, and the second pass is what keeps the pile calm.
- **MASS packed by ZX02** (P9): the code and tables had grown to 13.6K and no longer fit between &1200
  and the screen.
  - MainCode is now a `zx02` section, using teddyboy's compressor and dmsc's unpacker.
  - MASS (7.4K) loads into the screen's memory at &4800, and the loader unpacks it to &0E00. main then
    clears the screen, the loader with it.
  - `machine.py` runs the real unpacker in py65. It boots in jsbeeb.
- **The panel** (P10): NEXT with the next ball, SCORE and BEST, in a 3 × 5 font with its rows doubled,
  shared by the model and the 6502 (`tools/font.py`).
  - Bug found by lockstep: the digits weren't blanked, because a `DEC` came between the `AND` and its test.
  - GAME OVER and RETURN show in the panel at the end. BEST keeps the higher score.
  - In jsbeeb, a restart cleared the board and BEST showed 42. Bug found there: the RETURN that
    restarted also dropped the new game's first ball. Fixed: it must be let go first.
- **The model's explosion** still called `rnd.choice`: an earlier edit had missed it on indentation.
  None of the bot's lockstep runs had had an explosion. **`lockstep.py --scene critical`** forces one: a
  pile and two size-9 balls. Over 250 frames, 4 merges and the explosion all matched.
  - The explosion's frame costs 98,900 cycles, which is over budget for that one frame.
- **Effects in the IRQ:**
  - The size-9 ball pulses: logical 14 swings between white and cyan every 8 vsyncs.
  - An explosion flashes every ball white for 6 vsyncs.
- **Sound** (`src/sound.6502`): one effect per channel, each with a pitch slide and a volume decay.
  - The effects: a drop thud, a merge plink (lower for bigger balls), an explosion's noise and a falling
    tone for game over.
  - As in teddyboy, the IRQ reads the keys and then gives port A to the sound chip; only the IRQ touches
    port A.
  - jsbeeb's sound capture showed the drop effect's writes as intended.
- **Failed experiment:** capping the second pass at the first K contacts (the lowest). Wobble went to 0.73
  to 1.49, so it was dropped. The cap stays at 160, the 6502's MaxNear, so the model matches the 6502
  exactly even then. The model's merges are capped at 16 likewise (the 6502's MaxMerges).
- **Where it stands (02:40):**
  - `make test` passes: the plotter, the physics, lockstep over 400 frames, and the forced explosion.
  - `frames.py`, seed 2 (up to 22 balls): game frames take a median of 48,400 cycles (38,400 of it physics)
    and 82,400 at the 95th percentile. 6% of frames are over 80,000.
  - A crowded board (seed 3) has 16.5% over: O2.

### Morning summary for Rich

1. **It plays.** `make`, then boot `build/mass.ssd` in jsbeeb. Z and X move, SHIFT moves slowly, RETURN
   drops.
   - The panel has NEXT, SCORE and BEST, and GAME OVER, after which RETURN restarts.
   - There's sound for drops, merges, explosions and game over.
   - The size-9 ball pulses. Critical mass (two 9s) explodes into pieces, with a flash and a bonus.
2. **It's verified.** Everything the 6502 does matches the Python model, frame by frame, byte for byte
   (`make test`). So `build/model/game-2-tonight.mp4` is exactly what the BBC draws.
3. **For you to judge, the feel:** the physics is 25 Hz with two passes (P5). Every proposal (P1 to P11)
   is in `docs/decisions.md`.
4. **For you to decide:**
   - **O2:** crowded boards still overrun 25 fps on 6.7% of frames after the last speed-up. Explosions
     are the worst. The options are in `decisions.md`.
   - **O3:** critical size 10 or 9. The bot never reached 10.
5. **Not done yet:** a title screen; the merge's own animation beyond the shape step; particles; and
   more physics optimisation, waiting on O2.
- **Bigger balls (O2b), in the model:** radii 12% bigger and critical mass at 9.
  - Seed 2 got about 30% fewer contacts.
  - Seed 3 was no better.
  - With critical mass at 10 the bot never reached it in 2 minutes; at 9 it did, once or twice. That's
    O3 in `decisions.md`.
- **The game and physics review** (agent): its harness put a pile and pairs of size-9 balls in both sides.
  Over 300 frames with 12 explosions, everything matched. Bugs found, all fixed and all in lockstep:
  - `held_shape` didn't clamp the held ball's grow-in to its size. After a drop that merged at once, the
    next held ball was drawn too big.
  - A merged ball wasn't clamped. The critical ball could be drawn into the floor or a wall, or above
    line 0. The model and the 6502 now both clamp it.
  - `integrate` had no wrap check on x. A ball flung left fast enough wrapped round and was clamped to the
    right wall.
  - At game over, the drop key stayed "released", so a held RETURN restarted the game at once. A restart
    mid-flash left the palette white.
  - A merge could find no free slot on a full board, losing both balls. The merged ball now takes a's
    slot, drawn from where a was (EOR's deltas come out the same).
  - The chain broke when the frame count wrapped, after about 44 minutes. It's a down-counter now, in the
    model too, with the same meaning.
  - `do_keys` read `Keys` four times while the IRQ writes it: now copied once a frame.
  - Main's catch-up after a slow patch is capped at one frame's worth.
  - `lockstep.py --scene explosions` (after its harness) is in `make test`: over 250 frames, 4 explosions
    and 37 merges matched.
- **Its physics speed-up**, measured and exact, applied:
  - The rounding to quarter units comes from two byte tables, with no 16-bit negate.
  - A wide EXP table (L −299 to 290, the clamping built in) is read through each ball's log as a pointer.
    `gendata.py` now checks, over every size pair and every touching |dx| and |dy|, that the table covers
    every index. It does, exactly.
  - The pushes are added straight from it.
  - `apply`'s table path is inline.
  - It measured 14% off a step on late-game scenes.
- **Memory is tight:** main RAM's code and tables now end at about &4770, 140 bytes under the screen.
  - The old EXP table and the dead `times` entry are gone.
  - The full-page tables sit back to back.
  - MASS is 7.8K packed.
  - More code will need tables built by the loader, or something cut.
- **A bug from the slot reuse**, caught by a 3,000-frame crowded lockstep at frame 1045.
  - The merged ball takes slot a. A later merge record in the same frame naming slot a then saw a live
    ball, and merged it: the model skips it, because its a is dead.
  - Fixed exactly: `do_merges` also checks both balls' ages, as the sweep did. A ball from a merge is age
    0.
  - 1,100 frames of seed 3 are now in `make test`. It has seven checks and takes about 11 minutes. All
    pass.
- **The crowded game after the speed-up** (seed 3, 3,000 frames):

  | | median | 95% | over 80,000 |
  |---|---|---|---|
  | before | 62,800 | 90,200 | 16.5% |
  | after | 56,300 | 81,800 | 6.7% |

- The final build boots and plays in jsbeeb, with the yellow CRITICAL MASS name in the panel.

## 2026-10-28 (morning): firmer balls (P12)

Rich, on the first pass: "I feel they overlap a bit too much at times and maybe are not quite repulsive
enough. Can we try making their real radii a bit greater than what is rendered, and make them less
squishy".

- **Two radii.**
  - `shapes.py` has `draw_radius` (the shapes, unchanged) and `physics_radius` = drawn + `Margin`.
  - `tables.py` has `RQ`, the physics radius, and `WQ`, the drawn one. `pair_r` caps R at 255 quarter
    units, so the critical ball against a 9 fits a byte.
  - The collisions, the sort, the sweep and the screen's top use RQ.
  - Whatever is about what's seen uses WQ: the walls, the floor, the rim's game-over test, the held ball
    and the dropper's limits.
  - With the margin at 0, the disc came out byte-identical to the night's.
- **Why kv:** at rest a ball's weight is carried by kv × its push, so a stack's overlap is about g/kv for
  each ball above it. kp hardly matters at rest, and raising it only adds jitter.
- **The search:**
  - The stack test, rewritten to measure the drawn circles (`tune.py`), with bot games alongside.
  - kv 6/16 to 16/16: 16 shakes the pile.
  - kp 8/16 to 16/16: more than 11 adds jitter.
  - Margins 0 to 2 units.
  - Normalising the push by 2d instead of 2R.
  - Picked: margin 0.75 (3 quarter units), kv 12/16, kp 11/16 as before. A margin of 1 lost a bot game
    early. The /2d push was no better than kv and needs a wider EXP table.
- **The result** (numbers in P12): between settled balls, the visible overlap fell from a median of about
  4 units to about 1, and at the 99th percentile from 8–11 to 4–5.
  - Piles are calmer: fewer redraws at rest.
  - Piles stand taller: 26 balls now stand as high as 32 did.
  - Lightly touching balls can show a gap of up to 1.5 units.
- **The 6502:**
  - kv's ×3 table became ×6, and `timesbig` doubles its t·3.
  - Left/Right/Floor and the game's Drop/HeldY/Rim/RimTwo tables come from `GenWallQ`.
  - ExpW grew 2 bytes (−300 to 291).
  - 149 bytes are left below the screen, and 44 in the padding before the page-aligned tables.
- **The review** (agent):
  - **A bug, now fixed:** `integrate` took any carry from y += vy to mean a negative velocity that didn't
    borrow. A ball pinned to the floor whose positive vy carried y past 65535 was clamped to the screen's
    top; the model put it on the floor. kv 12 made that reachable in `test_physics.py`'s random scenes
    (seed 3, scene 154), though not seen in games.
    - The move now adds the high byte by the velocity's sign: a carry from a positive one is past 65535
      (to the floor, or the right wall for x), and no borrow from a negative one is past 0. That's the
      second reviewer's shape. It's 4 cycles a ball cheaper per axis on the common paths than before.
    - `test_physics.py` has an edge scene that runs all four wrap paths. It fails on the old code.
    - The model asserts that velocities and `timesbig`'s t·11 fit 16 bits, signed.
  - **The rim, the held ball and the dropper** moved to the drawn radius, as above.
  - Two stale comments were fixed.
- **The second review** (agent), of those fixes: no errors in them. It found:
  - **A soft-lock, older than P12.** The held ball hides while the last drop's top is within 2 lines of
    the rim, and hidden it can't be dropped. Failing needs a top above the rim. So a drop that settles
    with its top in those 2 lines locked the game.
    - The held ball now waits 50 frames (2 s) at most: `HoldLeft`, set by the drop.
    - My first go tested the drop's age, but a dropped ball is born at age 255 (so it can merge at
      once). So it never waited, and every game changed. `make test` still passed, since both sides
      agreed; I caught it from the changed scores. In normal play the cap now never triggers: the bot
      games score as before.
  - `tune.py` and `compare.py` placed drops by the physics radius, so the drops differed between margins.
    They now use the drawn radius, as the game does. The stack test's numbers moved a little: wobble 0.38,
    not 0.59.
- **Tests:** `make test` passes, now with the edge scene. Random physics scenes, 891 of them at 40 steps
  over seeds 3 and 5, match too.
- **The budget** (O2): identical piles cost about 8% less, but the luck of the game decides it.
  - Seed 3's 3,000-frame game is 4.5% over, against 6.7% before.
  - A build in between played that seed differently and was 22.6% over.
- **The worst overlaps left** are a merge's new ball, which appears at the midpoint on top of its
  neighbours: 15–20 units for a frame or two, as before. Growing its collision radius over its grow-in
  frames would soften them. That's not done.
- **New tool:** `tools/compare.py` plays the same drops under several settings, side by side.
  - `build/model/compare-squish.mp4` (and `.png`) is the old physics against P12's.
  - `build/model/game-2-stiff.mp4` is 90 seconds of a bot game.
- It boots and plays in jsbeeb.

## 2026-10-28 (morning): the repo and `make run`
- The repo is on GitHub, private, MIT: waitingforvsync/criticalmass. `docs/src.lua` is Eli Piilonen's, so it
  comes out before any public release.
- `make run` boots the disc in b2 for Rich, as a Model B with the Acorn 1770 DFS (b2 has no 8271).
  - `b2 -0 … -b` always starts a new process. Only a lone file argument hands the disc to a running b2,
    over its HTTP port.
  - The rule closes the b2 the last `make run` started (`build/b2.pid`), but only if its command line
    still names the disc. Any other b2 is left alone.
  - Then it waits up to 5 s for that b2 to exit, because b2 rewrites its config file in place as it
    quits. A new b2 that read it half-written wouldn't open a window. (The review caught this, and an
    error message when the old b2 had already gone.)
  - A b2 started when no other is running gets b2's HTTP port (48075), so other sessions' tools, such as
    teddyboy's `make run`, would drive it.
  - Checked with a stand-in for b2; Claude never runs it (D11). The disc boots on jsbeeb's B1770 too.

## 2026-10-28 (late morning): the prototype's screen, 12 sizes, the memory map (D12-D15, P13-P15)
Rich asked for four things at once, then refined them while I worked:
- the screen modelled on his prototype: a checker over everything outside the well, with a margin left;
- a few more sizes, with critical mass one larger;
- a new memory map: stack &100-&13F, code from &140 with IRQ1V in it, the tables generated and below the
  screen;
- and the screen's static parts copied to the screen by the loader and then discarded.

I asked four questions (sizes, how many, the panel, the walls); his answers are D12 and D13. I built and
looked at his prototype (`old/`, BeebAsm) in jsbeeb first.

- **12 sizes (D12).** The collision maths needs two touching balls under 64 units, and today's largest
  pair was already at it. So sizes 1-11 fill the old range in steps of 2.56 (not 3.2), and critical mass is
  one of the original's steps bigger, 36.48.
  - Drops became 1-5 (P13), the same range of radii as 1-4 before.
  - Two colours were added (P14).
  - The critical ball's shape no longer fits PixTop's page with the others, so it's left out of the
    plotter's two-band and vertical paths. Its moves (6 frames a time) go old-away, new-in.
- **The screen (D13)** is `tools/layout.py`. The well moved right a byte.
- **The memory map (D14, P15).**
  - `main` sits before &204, then IRQ1V, then MainVars to &257, &258 = 2, and `random.6502`.
  - The review found that a soft BREAK keeps &27E-&29B (the MOS clears from &400 and resets page 2 only
    below &27E). The code there now leaves *TV, the language ROM and the like wrong after a BREAK. I
    started a fix (the loader saving and restoring them), but Rich: "i don't consider what happens after
    BREAK a bug". So it's backed out, along with the &287 = 0 I'd kept for the BREAK intercept.
  - Then the plotter at &290 (the only start near there where no hot loop crosses a page), the rest
    before and after &D00's RTI, then the workspace, then the tables.
  - `gendata.py` now generates every table and places them all below the screen. The 9,506 bytes waste 41
    on padding, and no table of a page or less crosses one.
- **The loader makes tables (Rich: "If the code to generate them is bigger than the actual tables let's just
  leave them embedded").** I measured each table's cost in the packed MASS by zeroing it and rebuilding:
  - RoundP/N, BitLen, H and the font pack to under 75 bytes each, so they stay.
  - The squares, Times6/11, PairR, PairR², the PairC pointers (from a 144-byte matrix) and RowHi are made:
    MASS 8,632 → 7,693 bytes.
  - Still possible: L8 by deltas (166 packed), and the shapes' tables from their spans (1,331 packed).
- **The starting screen** is an image (`ui.bin`, `layout.background()`), packed into MASS (423 bytes).
  - MASS lives in screen memory, so the loader parks the packed screen in the workspace and its last
    stage (the unpacker and a stub) in the free space under the tables.
  - It unpacks the code and the tables from there and makes its tables. The last stage unpacks the
    screen over everything, zeroes the workspace and starts the game.
  - The game's own drawing is now the well cleared for a new game, the next ball's box, and GAME OVER's
    box (cut out of the checker, then put back).
  - The 6502's font is 20 glyphs: O is 0 and S is 5.
- **A bug the new sizes exposed:** merges add their size to the BCD score, written for sizes up to 9. A
  size-11 merge left `&9B` in it, and the lockstep state check read that as 101, so it looked right. Only
  the screen showed the stale digits.
  - Fixed (sizes 10 and up converted).
  - `lockstep.py` now rejects a score that isn't BCD.
- **The harness** (`machine.py`) now runs the real loader, from `entry.take_over` (after the OS calls) to
  `main`. Its stack is at &13F, and it measures each call's deepest stack: 11 bytes in the explosions scene.
  - `test_tables.py` checks all 73 tables in memory against `tables.json`.
  - `test_background.py` checks the unpacked screen, GAME OVER and `new_screen`.
- **Tests:** every step of `make test` passes:
  - tables;
  - the screen;
  - plot, 328 cases;
  - physics, 21 scenes;
  - lockstep: 400 frames, the critical scene, the explosions scene, and seed 3's 1,100 frames.
- **It boots and plays in jsbeeb** (Model B, DFS 1.2, the OS calls and all).
- **The budget (O2)** is worse on crowded boards: seed 3's 1,100 frames are 8.5% over.
- **Also:** `make run` (b2, for Rich), and `make release` (D15).

## 2026-10-28 (midday): rounder purple balls, a drop's random fraction, GAME OVER in the well (D16, D17)
- **The purple balls** (size 3, violet) looked like hexagons.
  - The raster, 9 × 19, has 11-line straight sides. The dither makes it worse: blue is dark against
    black, so the eye follows the magenta checker.
  - I drew eight candidates in all four dither phases. A 10 × 20 hand-drawn shape reads roundest
    (`Overrides` in `shapes.py`, D16). Only the drawing changed.
- **A drop's random fraction (D17).** The old jitter, ±8/256 units from the LFSR, vanished in the
  collisions' quarter units, so drops at one place stacked balanced.
  - A drop now adds T1's low byte (&FE44), signed: ±0.5 units.
  - `lockstep.py` pokes the byte and passes the model the same; the model alone draws its own.
- **GAME OVER** moved to the middle of the well, in a black box (Rich), and RETURN's text went.
  - The panel's fifth box went with it, and `fill_box` now only blacks out, at any column.
  - The font is 17 glyphs. MASS is 7,654 bytes.
- **The generator** used to fill the top page exactly, by chance (Times16 and RETURN's text in PixTop's
  23 spare bytes). It now pads the tables up to the screen.
- **The review** found two problems, both fixed:
  - T1 alone gives only four values at the drop's point in the frame (a frame is 39,936 µs, T1's period
    10,000 µs), so one pair of drops in four would still balance. The drop now takes T1 EOR an LFSR
    byte.
  - The hand-drawn size 3 was half a unit bigger than its radius: a 0.25-unit physics margin, and it
    could touch the held ball at the rim. Its radius is now the shape's, 10 units (RQ 43, WQ 40).

## 2026-10-28 (afternoon): the screen as a PNG, unpacked with the code; a MODE 2 title (D18, D19)
- **The screen is `assets/screen.png`** (Rich), the whole runtime screen, at his previews' scale (8 × 4 a MODE
  2 pixel).
  - `screenpng.py --compose` drew it from the layout, with his logo (`assets/logo.png`, 48 × 32) at the top
    of the panel and a block of checker round it. The boxes kept their rows.
  - From now on it's the source: `gendata.py` converts it, and the model's `background()` reads it.
- **One payload** (Rich's design): the code, MASS's tables and the screen, contiguous from &140, packed as
  one ZX02 stream and unpacked in place.
  - The screen is at &33E8, so the well starts on a page, an even one: the plotter's `ORA colhi` holds.
  - The drawing routines and the plotter count columns from the well's first. The physics' x counts from
    the well's left edge (WellLeft 0), so a ball's x is the plotter's directly.
  - The model's `render.py` adds the well's column when it draws.
  - MASS loads so that the payload ends 16 bytes past the screen's end; the loader follows it.
- **The catch:** the loader sits just above the payload, where the tables it makes would go. So the
  workspace goes first above the screen, with the loader inside it, and the made tables go above that, up to
  &8000.
  - Nothing needs zeroing: the game sets everything it reads.
  - The workspace didn't fit under the made tables (1,763 bytes in 1,608), so the near and merge lists
    (354) moved into the room before &D00.
- **The title (D19)** is MODE 2, in !BOOT.
  - It sets the CRTC to 64 × 8 characters with the display off, the ULA by OSBYTE 154, and the palette by
    &FE21, then unpacks the title to &7000 and turns the display on.
  - MASS loads under it (&50F7-&6EE1), and the title stays up until the payload is unpacked. The loader
    then waits for a vsync, turns the display off and sets the game's CRTC.
- **Sizes:** MASS is 7,658 bytes with the screen in it, and !BOOT 1,321. Loading takes 1.25M cycles.
- **Spare memory:** 218 bytes between the code and its tables, 185 before &D00, about 200 in the
  workspace.
- **A test that changed:** `test_physics.py`'s edge scene had a ball carry past &FFFF at the right wall.
  With x from the well's left that can't happen (128 + under 128 units), so the scene now checks the
  right wall at full speed instead.
- **jsbeeb:** the title shows while MASS loads, then the game with the logo, and it plays.

- **The review** of this found the 16-byte slack is only enough because this payload's tail packs well.
  ZX02's runs cap at 256, so 3,000 random bytes need 20.
  - `tools/check_inplace.py` now runs the loader's decoder at every `make`. This payload needs 2.
  - The tests now start from junk-filled memory, with the title at &7000, as on the machine. That at once
    showed the pair tables' "no pair" entries (two critical balls' R must be 0) relying on zeros that are
    no longer there. `make_tables` now zeroes its region first.
  - The harness's symbols now prefer MASS's: !BOOT's `zx.*` had shadowed them.
- **The labels (D20)** are in a font of their own, now that they're only in the PNG: 4 × 5, white over cyan,
  with a blue shadow (P19), centred in their boxes. The score's digits are centred too.
- The log now keeps Rich's calls (D16-D20) apart from Claude's details (P16-P19), as CLAUDE.md asks.

## 2026-10-28: the smallest ball no longer wraps off the left wall

- **The bug (Rich):** pressing Z with a size-1 ball held, at the left wall, sent it to the right wall.
  - Since x counts from the well's left (D18), the smallest ball's left limit (1,408 in 8.8) is less than
    a full-speed move (1,966). The move borrowed, wrapped to about 65,000, passed the low test, and was
    clamped to the right limit. Every other size's limit is at least 2,048, so only size 1 did it.
  - The model's integers don't wrap, so it was right all along. Lockstep missed it because the bot slows
    as it nears its target and never pushes into a wall.
- **The fix:** `do_keys` moves right first, then left, and clears DropperX's high byte when the move left
  borrows. That leaves it under every left limit (each over 255), and `clamp_dropper` puts it at the limit.
  - Right comes first because the review found that with left first, Z and X held together at the left
    limit came out up to 3 units right (the model's net move is 0). Now left borrows only when the net move
    goes past the left edge. The right limit plus a move stays under 65536.
  - 7 bytes: 211 free before the baked tables.
- **A new lockstep scene,** `--scene walls`, a 50-frame cycle: each drop size in turn (set in both, so the
  seed's draw doesn't matter) pushed at full speed into one wall, then the other, Z and X held together
  there, then dropped, the walls taking turns.
  - It failed at frame 8 before the fix, and at frame 294 with left first (2,176 against 1,408).
  - It's in `make test` at 500 frames.

## 2026-10-28: a merge's ball flashing white (P20), tried and dropped

- **The original's merge, compared:** the physics matches in intent. It merges on contact once both
  balls are old enough, at the midpoint, at rest, with the full collision radius at once, after that
  step's pushes. The drawing differs:
  - The original draws its new ball full size at once, with a flash-coloured disc over it for 4 frames,
    then the old colour shrinking to the centre.
  - The two old balls slide in under it, and a ring of 3 × radius particles bursts out.
- **Tried (Rich asked to see it):** a merge's ball is drawn in white (the critical ball's colours) for its
  first frame, still a size smaller. Then it takes its own colour, then its full size.
  - Seen in jsbeeb: white for two paints (40 ms), its own colour at the old size for two, then full size.
  - 8 bytes in `draw_balls` (203 free before the baked tables).
- **The cost:** in lockstep, before and after:
  - seed 2's 400 frames: median 22,149 -> 22,526 cycles;
  - seed 3's 1,100 frames: median 45,911 -> 46,104, and 71 -> 75 frames over 80,000;
  - the repeated-explosion scene: 94 -> 99 of 250 over.
- `make test` passed. Rich found it too quick to notice, so it's taken out again.

## 2026-10-28: a merge throws a ring of sparks (P21, to try)

- **What it does:** each merge's new ball throws 8 sparks from its edge, one every 45 degrees. They slow
  by 1/8 a frame, drift down, and go after 25 to 39 frames or on leaving the well. Each is a pixel two
  lines tall in the new ball's colours. `tools/sparks.py` is the model; `src/sparks.6502` (each frame's
  pass) and `src/sparkthrow.6502` (the throw, and all off at the game's end) match it.
- **How it's drawn:** one pass a frame, after the balls. Each spark is EORed off with what it was EORed on
  with, moved, then EORed on with (the byte EOR its colour) AND its pixel's mask, which it keeps. It shows
  its own colour over balls too, and the screen always comes back to the balls alone, whatever the
  balls' drawing did in between.
  - A first version stored sparks over the screen, keeping the bytes, and put them back before the balls
    were drawn. It was 382 bytes, against about 390 left.
  - EOR in one pass, the address worked out again rather than kept, and the slots in zero page (zp,X
    addressing): 338 bytes, then 317 in two files.
- **Room:**
  - 16 slots in zero page, 176 bytes at &4C-&FB; the allocator's pool is now &00-&4B and &FD-&FF (MASS
    uses &00-&1D). The loader zeroes them.
  - `sparks.6502` is before &D00: that gap has 1 byte left. `sparkthrow.6502` is after `game.6502`: 32
    bytes left before the baked tables. Plus 24 bytes of direction tables, and 13 and 15 in the small
    gaps: about 61 bytes of code room left in all.
- **The cost:** in lockstep, before and after:
  - seed 2's 400 frames: median 22,149 -> 24,671 cycles;
  - seed 3's 1,100 frames: median 45,911 -> 47,485, and 71 -> 98 frames over 80,000;
  - the repeated-explosion scene: 94 -> 115 of 250 over.
- **Checked:** `make test` passes (lockstep matches the screen every frame with the sparks). In jsbeeb a
  chain of merges throws two rings, which spread, drift down and fade, over the balls as well.
- **The review** found no bugs. From it:
  - lockstep now ends each run with `sparks_off` in both, comparing the screen (the explosion and walls
    scenes end with 8 and 15 sparks live);
  - gendata asserts what the 6502 assumes (a spark's speed and eighths add without overflow; gravity is an
    INC);
  - `tools/sparks.py` is a prerequisite of the generated files.
  - Not done: `update_sparks` crosses a page (&B00), about 40 cycles a frame, but there's no room to move
    it. A live spark costs about 490 cycles a frame, so 16 of them about 7,900.
- **Without gravity** (Rich asked to see it): `Gravity` is 0 in `sparks.py`, and gendata's
  `GenSparkGravity` leaves the 6502's INC out (2 bytes). The ring keeps its shape, slows, and drifts on
  outward until each spark's life is up; a spark slower than 8 eighths a frame isn't slowed any further.
- **Faster and shorter** (Rich): a spark's place is in quarters of a unit, not eighths, so the same speeds
  (2r a frame) go twice as far: r / 2 units a frame. Lives halved, to 13 to 20 frames. The ring now
  spreads about 3.5 radii before it goes, as the original's does (3.6). No more code (the position's
  shift is two places now, inline, and the speed's / 8 is inline too): the gap before &D00 has 4 bytes.
  `make test` passes.

## 2026-10-28: the limit's line (D21, P22)

- A blue line across the well at the limit, line 32: under the held ball (which reaches line 31) and level
  with the bottom of the wall ticks.
- First two lines (32-33) in `assets/screen.png`, read back by gendata. Rich found it double height and
  asked whether it needed to be in the PNG at all: now one line, drawn by the game (`layout.py`'s
  constants, `limit.6502`'s `draw_limit`, called by `new_screen`, which `main` now calls before the first
  game too). The PNG is back to Rich's; gendata asserts its well is clear.
- A ball crossing it shows black where they overlap (EOR); seen in jsbeeb, the line is whole again once
  the ball's past.
- Room: 1 byte before &D00, 17 after the code above it, 10 in `main`'s gap before IRQ1V and 15 before the
  plotter. `make test` passes.
- Then dotted (Rich asked to see it): `LimitByte` &20, each byte's left pixel blue. No code change.

## 2026-10-28: a 32-byte stack (D23), code in zero page (D24, P23), and a wipe at game over (D25)

- **The stack** is &100-&11F; the code starts at &120 (32 more bytes below IRQ1V). The most measured is
  20 bytes with the IRQ.
- **Zero page:** the sparks' slots were there to save code bytes (zp,X is 2 bytes, but no faster than
  abs,X). Rich: code on self-modified operands goes there instead. `eor_up`/`eor_left`/`eor_right` and
  `log16` moved (181 bytes at &30-&E4), split into `eor.6502` and `log16.6502`. Their image is in the
  payload where the near and merge lists go, copied down by the loader. The sparks' slots are back in
  the loader's table gaps. The plotter now starts at &2FE (no hot loop crossing a page; found by search),
  with `background.6502` in the room before it.
- **Room:** 42 bytes before IRQ1V (24 after the wipe), 46 before the plotter (20), 63 under &D00, 76
  above it: about 227 before the wipe.
- **The cost:** about 70 cycles more a frame at the median, the same frames over budget.
- **The wipe at game over:** `wipe_row` (26 bytes) clears a row's even lines (every other byte of its
  page), a row a frame from the bottom; `main` runs it from the game's end, then GAME OVER. Seen in
  jsbeeb: the balls go striped from the bottom up, then GAME OVER; RETURN starts a clean game.
  `test_background.py` checks the wipe on a scribbled well, GAME OVER over it, then `new_screen`.

## 2026-10-29: the optimisation round (P24)

- Rich: "get a bunch of agents to go through the code looking for optimisations, both size and speed ...
  If we can speed up the render or the physics solver that would be great". Profiled first: a scratch
  profiler plays seed 3's bot game in the model and the 6502 together and charges every cycle of
  game_frame to its label. `tools/profile.py` had been charging MASS's cycles to !BOOT's labels where they
  lie over MASS's code: it takes MASS's labels only now.
- Five agents, one area each (pair and log16; apply, integrate, age and resweep; sweep and sort; the
  plotter and draw_balls; the rest and size), each read-only on the repo, checking its own code against
  the old in py65. Integrated one area at a time, with `make test` after each:

  | after | median | 95% | most | over 80,000 |
  |---|---|---|---|---|
  | before | 46,480 | 84,086 | 116,853 | 84 |
  | the broad phase | 44,832 | 80,344 | 113,949 | 58 |
  | the drawing | 42,667 | 77,545 | 111,802 | 41 |
  | the per-ball physics | 39,987 | 73,014 | 108,157 | 26 |
  | the rest (score, IRQ, size) | 39,472 | 71,795 | 97,356 | 18 |
  | the contact solver | 35,858 | 63,850 | 92,735 | 5 |

  (seed 3's lockstep game, 1,100 frames.) The average frame: 47,549 -> 36,618 cycles. The explosion scene:
  109 -> 56 of 250 over 80,000.
- Every result byte-identical: no model change. jsbeeb: the palette, the drop's sound and the explosion's
  flash as before.
- Rich's own find: draw_glyph's CLC after two ASLs on a glyph under 64.
- log16 is inlined into pair now (faster by about 45 cycles a contact), which takes its self-modified jump
  out of zero page: against D24's letter, so it's Rich's call (P24).
- Code room: 57 before IRQ1V, 40 before the plotter, 96 under &D00 (with 75 more if the near and merge
  lists were arranged so NearB needn't be padded onto its own page), 958 above it (the tables 829
  bytes smaller).
- **Two more** (Rich: "do the first two"): integrate tests only the x wall a ball moves towards, and
  BallRU and BallSize16 are set in add_ball. lockstep's `inject` now clamps its balls into the well, as the
  game's are; `test_physics.put` and the critical scene poke the two arrays. Seed 3's median 35,834 ->
  35,404, 95% 63,812 -> 63,119. The bytes integrate saved went to apply's page padding (59 bytes now):
  moving apply to avoid it trips other routines' page checks, and there's room enough (914 above &D00).

## 2026-10-29: can critical mass be reached? (P25)

- Rich: "can you do a playthrough to see if it's actually possible to reach critical mass? My feeling is
  that it probably is not, and we may need to tune it a bit, maybe removing one of the ball sizes".
- The bound: a critical ball is 2,048 size-1s of mass, and a drop brings 6.2 on average (sizes 1 to 5
  evenly), so it takes at least 330 drops. The smallest pile before the last cascade (one each of 11 down
  to 1) fits easily: dropped where each lands lowest, its top settles at line 90, against the rim's 32.
- `tools/play.py`, a lookahead bot. For each drop it plays every dropper position (every 2 units) on a copy
  of the game: the move, the drop and 40 frames, exactly as they'll happen. It keeps the best by a
  heuristic: explosions first, then the pile's height, the number of balls, bigger balls, duplicates that
  can't merge, touching neighbours a size apart, and small balls buried under big ones. It drops about
  every 0.8 s. `--noise 3 --blur 0.5` makes it err: an aiming error of 3 units (sigma), and half the
  spread of the ten best positions' scores as noise in judging them. That isn't calibrated against a
  person.
- The review found the first version gave an explosion no credit: the pieces score worse than the 12, so
  the bot steered away from exploding within its 40 frames. Fixed and every game re-run; the figures here
  are the re-run's.
- The one-size-fewer variants were copies of `tools/` with only `shapes.py` changed: **same range** is 11
  sizes over today's range (steps of 2.84, the biggest playable ball still 30.08); **size 11 removed**
  keeps sizes 1 to 10 as they are, with critical mass after 10 (36.48, as now).
- Each game was capped at 15 minutes. Explosions at minutes:

  | sizes | bot | seed 1 | seed 2 | seed 3 |
  |---|---|---|---|---|
  | 12 (now) | exact | 4.4, 9.0; over at 13.8 | none; over at 5.6 | 4.9; over at 8.3 |
  | 12 | erring | none; over at 4.5 | none; over at 4.3 | none; over at 4.6 |
  | 11, same range | exact | 2.2, 4.6; over at 7.4 | | |
  | 11, same range | erring | 2.1, 4.4; over at 7.0 | 2.6; over at 4.9 | 2.2; over at 5.3 |
  | 11, size 11 removed | exact | 6 (2.0 to 13.7); alive at 15 | | |
  | 11, size 11 removed | erring | 2.5, 5.1; over at 7.9 | 6 (2.7 to 13.6); alive at 15 | 2.3, 4.8; over at 8.0 |

- So critical mass can be reached now, but only with near-perfect play: the exact bot's first came at
  about drop 333, right at the bound. The erring bot never got there: it reached 11 at about 2.5
  minutes each time, and lost about 2 minutes later building the second 11.
- With one size fewer, the erring bot reached it in all six games. Removing size 11 did best: 10
  explosions in its three games against 4, and longer games (two of about 8 minutes and one past 15). Its
  biggest playable ball is smaller, so there's more room.
- Every game ends the same way: the board fills with leftovers, 20 to 30 balls, mostly sizes 1 to 6 with
  duplicates that never met.
- The video: `build/model/critical-seed1.mp4` (12 sizes, seed 1, the first bot; the explosion is at 4:27)
  and `critical-seed1-clip.mp4` (a minute around it). The two 11s span the well, each resting on a
  smaller ball in a corner.

## 2026-10-29: 11 sizes (D27)

- Rich, on P25: "keep the critical ball radius, and remove the size below. The colour I would like to remove
  is pure green". `shapes.py`: CriticalSize 11, sizes 1 to 10 in steps of 2.56 as before (checked: the same
  shapes, RQ, WQ and C as before for sizes 1 to 10, and the critical ball's). `colours.py`: green gone, so 8
  is magenta, 9 sea green, 10 the pulsing ice, 11 white.
- The 6502 needed nothing: it takes the critical size from gendata. `make test` passes. MASS's tables are
  smaller by the shape and the pairs (they start at &2011 now), so there are 1,321 bytes free above &D00.
- Pink (7) and magenta (8) are neighbours now. Pink's white dither keeps them apart, but swapping orange
  and pink would keep the hues apart too: Rich's call.
- `docs/model.md`'s shapes and colours were still the 10-size ones: brought up to date.

## 2026-10-29: chain scoring and the explosion (D28, D29)

- Rich: "increasingly bigger scores for "chain reaction" merges", "a good bonus for reaching critical
  mass", and the explosion "more spectacular": stand still on the white ball for half a second, then throw
  the balls out while it shrinks away, with particles. No screen shake; the colours as D27 has them.
- **Scoring (D28):** each ball has a link (`BallLink`; `Ball.link`). A merge's ball is a link past the
  larger of its two balls' links (those made within 25 frames), or link 1, and scores its size × 2^(link
  − 1), doubled in BCD (`add_points` adds three bytes). The pieces are link 1. The bonus is 1,000. The old
  three-second chain after an explosion is gone. Seed 3's lockstep game, 1,100 frames: 630 points against
  162; a bot game made a seven-link chain into critical mass that scored 640 on its own.
- **The explosion (D29):**
  - On the merge, `Freeze` = 12. `game_frame` does nothing while it counts down (no keys, physics or
    drawing), then `do_bursts`.
  - The burst: the critical ball goes to `StateShrink` and `draw_balls` draws it a shape smaller each
    frame, in white, until it's freed; `blast` kicks every other ball at K/d through L8, H and ExpW; the
    pieces fly out faster (2.5 + 6 d/R units a frame); two rings of white sparks; the bonus, the flash
    and the boom. `Calm` = 50: nothing fails meanwhile.
  - A rising tone (`SoundRise`, channel 2) plays through the stand-still.
  - The model does the same: `Game.freeze`, `frozen`, `burst`, `blast`, `shrinking`, `calm`. Lockstep
    compares the links, the freeze and the calm too.
- Seen in jsbeeb: the white ball, the stand-still with the rising tone, the whole screen flashing white
  with the boom, the score up 1,000, the white ball shrinking as the pieces punch through it. Where a ball
  sits under the white one, the EOR shows black through the stand-still: a big hole if it's well under.
- `tools/play.py --video` is 50 fps now, with the IRQ's pulse and flash in its palette (`irq_palette`),
  and `--clip`. `build/model/explosion.mp4`: seed 1's first explosion.
- The review found no mismatch. It led to:
  - the model capping a burst's pieces by the 6502's slots;
  - nothing failing on the frame critical mass is made;
  - the rising tone requested after the frame's merges, so a later merge's sound can't replace it;
  - headers.
- Costs: the burst frame of the critical scene is 80,166 cycles; the repeated-explosion scene is 29 of
  250 frames over 80,000, against 74 (its frozen frames cost nothing). Code room: 871 bytes above &D00.
- **Then** (Rich: "continuing to simulate physics during the half second pause so it doesn't look quite so
  unnatural"): only the player stands still now. `game_frame` skips the keys while `Freeze` counts down,
  and the burst comes first thing in the frame after; the physics, merges and drawing run on. The white
  ball pushes its neighbours aside in the first few frames, so the black where it overlaps them clears.
  Nothing fails while it stands. The rising tone is requested only on the frame `Freeze` is set (it's
  CriticalHold then), as `do_merges` runs during the hold now. The critical scene's slowest frame: 84,021
  cycles. `tools/play.py --video` is 25 fps by default (a frame each, in the palette at its first vsync):
  `build/model/explosion-25.mp4`.

## 2026-10-29: slow motion around critical mass (D30)

- Rich: "why does the size of the ball affect the performance of the physics? or are you referring to
  just the render aspect?" Profiled the critical scene frame by frame: in the 12 frames standing still,
  the physics took 2,300 to 10,500 cycles and the drawing 56,000 to 67,000. It's the white ball's redraw:
  its shape isn't in the plotter's fast paths (it used to show for only 6 still frames), so each move
  redraws all of it.
- Rich: "slow things down to half-speed update when the white ball is present and exploding". There's
  one step a frame, so the step is halved: half the gravity, and half the velocity's way. It runs from
  critical mass through the 12 frames and 24 after the burst (even, so the burst's frame is one where the
  shrinking and the sparks step); the shrinking and the sparks go every other frame.
- `integrate`'s y and x sites are branches a whole step never takes (`BEQ` after `LDY BallSize,X`, `BCS`
  after a `CLC`), each through a stub to the half step's code (`integrate_half`, after `apply`: inside
  `integrate` it pushed the hot branches out of range and across pages). `set_speed` flips them to `BNE`
  and `BCC` while `Slow` is non-zero. The first version overwrote `CLC:LDA` with a `JMP`, which Baron
  couldn't see; Rich: "if you're patching a jump, you'll need ZA_CANJUMP to mark it". Each site now carries
  one (Baron keeps a branch's fall-through and replaces only its taken edge). A whole step costs 2 cycles
  a site a ball; `set_speed` about 20 a frame.
- The review found no bugs. From its suggestions: the half step's y falls straight into its x; SlowAfter
  is even; `test_physics.py` runs every scene in half steps too (42/42).
- The critical scene's slowest frame: 78,386 cycles (84,021 before). `build/model/explosion-slow.mp4`:
  seed 1's first explosion, 25 fps.
- **Then** Rich: "let's forget the half timestep, and just halve the framerate instead. The stop motion
  look might work." The half step is gone (`physics.6502` and `test_physics.py` as they were). In slow
  motion `game_frame` returns at once on every other frame, so the shrinking white ball and the sparks
  slow with the rest, and a normal frame costs nothing more. The hold is 6 updates (still half a second),
  then 12 updates of slow motion after the burst. An update has 160,000 cycles then: the critical scene's
  slowest, 94,812, fits. `build/model/explosion-stop.mp4`, 25 fps.
- **Then** Rich: "6 frames between updates instead of 2 or 4", and "if it is the irq routine which
  normally sets the frame pacing, it would be good just to be able to set the value directly that it
  uses". The IRQ counts vsyncs; `main`'s loop paced a frame every 2. It reads `Pace` now: FramePace (2),
  or SlowPace (6), which the critical merge sets and the end of `Slow` puts back. So `game_frame` skips
  nothing, and the model has no still frames: `Game.pace` is only for the videos (`play.py` shows each
  frame for its pace) and lockstep compares it. The hold is 4 frames (half a second at 6 vsyncs), then 12
  frames after the burst. `build/model/explosion-stop3.mp4`.
- The review of the in-between version (every other frame skipped) found `tools/frames.py` calling
  `after_step` without the freeze's countdown: the game's pre-step part is `Game.before_step` now, which
  `frames.py` calls too. `frames.py` had been failing since the sparks (D22): the 6502 isn't given them,
  so the model doesn't draw them there now. Seed 2, 1,500 frames: physics median 21,346, drawing 10,590.

## 2026-10-29: the hold at full speed, slow motion from the burst, shed sparks (D29, D30, D31)

- Rich: "let's not slow down until the explosion. Keep the white ball visible longer at full update
  speed, and then the explosion/shrink at reduced frame rate. If we can add more particle effects during
  that time, that'd be great."
- The hold is 25 frames at full speed (a second); the rising tone is stretched to match (slide -10,
  decay 4). Slow motion (Pace 6) is set by the burst and lasts 12 frames.
- The shrinking white ball throws a ring of white sparks from its edge each frame (`throw_sparks.lived`:
  a ring whose sparks live 3 frames). The spark slots are 32, so the shed rings find room beside the
  burst's two; the loader's tables now fill their space exactly. `update_sparks` loops from `SparkTop`
  (past the highest live slot), which `throw_sparks` raises.
- `build/model/explosion-shed.mp4`, 25 fps.
- The review found the high-water mark and `.lived` sound, and one real lockstep risk: with two critical
  balls bursting together, the model shed their rings in burst order and the 6502 in slot order, and a
  ring in other slots lands elsewhere (a new spark keeps its slot's quarters). The 6502 now keeps the
  shrinking balls in a list in burst order (`ShrinkSlot`, `NumShrink`), as the model's `shrinking`, and
  draws and sheds from it; the dying scan is as it was. Lockstep's new `twin` scene (two pairs of size-10
  balls, both critical on frame 36, two shrinking at once) checks it, in `make test`. Also an assert on
  the sparks' tables' layout (the EOR trick), and comments.
- Until the burst's own sparks leave the well, the 32 slots can't hold every shed ring (the last two
  frames' are live when the next is thrown, beside the burst's 16): an early ring can come out partial.
- Rich: "the sparks look like they're going inwards, but i would like them to look as if they are
  exploding outwards". Each shed ring had been thrown from the shrinking ball's edge at r / 2 a frame, so
  each was smaller and slower than the last. Now they're all thrown alike, ShedR 24 (from 24 units out,
  12 a frame), just outside the white ball: the newest inside the last, each flying out.
- Rich: "let's just not hold the white ball so long before exploding, maybe about half a second is
  enough". CriticalHold 12 (full speed), and the rising tone back to its half second (slide -20, decay 2).

## 2026-10-29: 12 sizes again, the larger ones closer together (D32)

- Rich reached critical mass on his first game with D27's 11 sizes: "bring back the ball that we deleted
  before, but somehow make it a little less difficult". Variants as copies of the model, the erring bot,
  seeds 1 to 3: D12's 12 sizes, none (4.3 to 4.6 minutes); every size compressed into 4.48 to 27.52,
  critical mass in seed 1, but the small sizes rasterise boxy (6 by 13 with four full columns); drops of 1
  to 6, lost at 2.4 minutes (big leftovers); both, five explosions in 15 minutes.
- Rich: keep the small sizes, compress the larger ones, keep the physics margin, and make sure they look
  round. Sizes 1 to 5 as they were, 6 to 11 in equal steps to 27.52: one explosion in three games (at 5.9
  minutes), games of 5 to 10.6 minutes. The rasters of 6 to 11 look round, and a scan of radii within
  0.4 of each found none rounder. Green is back at 8.
- `ShrinkSlot`'s assert is CriticalHold >= CriticalSize now (12 and 12): a burst's balls are freed on
  the draw of its frame + CriticalSize - 1, and the next burst is CriticalHold frames after a merge.
- `preview.py`'s sheet now wraps rows at the well's width (its x is from the well's left).
