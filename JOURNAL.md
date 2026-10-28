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
- **The fix:** `do_keys` clears DropperX's high byte when the move left borrows. That leaves it under every
  left limit (each over One), and `clamp_dropper` puts it at the limit. 7 bytes: 211 free before the
  baked tables.
- **A new lockstep scene,** `--scene walls` (seed 7, whose first ball is size 1): each held ball pushed at
  full speed into one wall, then the other, and dropped there. It failed at frame 8 before the fix. It's in
  `make test`, which passes.
