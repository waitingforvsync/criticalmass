# Brief: Critical Mass for the BBC Micro

These are Rich's words, collected from the first session (2026-10-27/28). Only Rich changes this file.

## Aim

> We are going to do a version of "Marble Merger" (https://www.lexaloffle.com/bbs/?pid=136646) a pico-8 game
> for the BBC Micro, renaming it Critical Mass.

> I was thinking to change the game design a bit, hence the name "critical mass" - when we reach a certain
> size, it explodes into a number of various sized balls and gives you a big bonus.

## Starting points

> I sketched out a possible variation on the algorithm in docs/sketch.py which might work better in 6502.
> The .6502 files here are unfinished BeebAsm files. I had started to create a sprite routine which would
> draw the difference between different sized circles, so that hopefully we could render this on a single
> screen buffer in mode 2 on a stock BBC B (the target platform). Use this as a starting point for a new
> implementation using my Baron assembler.

The original's source is `docs/src.lua`. The old BeebAsm files are in `old/`.

## Target and tools

- A stock BBC Model B, in MODE 2, with a single screen buffer.
- Baron (`~/dev/baron`). Style: "copy teddyboy" (`~/dev/teddyboy`).
- > we will exclusively use [jsbeeb-mcp] to avoid clashes with b2 in the other project.

## Look

> Design-wise, the balls will be flat circles but with checkerboard dither, no highlight as per the
> original.

> regarding colours - try to keep it colourful. remember we have 16 logical colours available rather than
> 8, and 8 physical colours. Make some nice dither pairs.

Sizes: "we can go with whatever looks circular, I don't think it's important."

## Answers to the first plan (2026-10-28)

1. 25 fps fixed: yes.
2. Sizes: whatever looks circular.
3. Critical mass, as above.
4. Keys: Z/X, SHIFT for slow, RETURN to drop are fine. No joystick.
5. Style: copy teddyboy.
6. The parity palette: yes.

## Ball storage

> I can see I was holding the balls as a linked list. I assume the reason for that was to have them sorted by
> y for raster chasing. But that might not be necessary in the end. Make a call!

## Working rules (2026-10-28)

> be extra careful not to spawn too many processes and run out of memory. always get an agent to review new
> code as you write it. ... Write up your progress as you go.
