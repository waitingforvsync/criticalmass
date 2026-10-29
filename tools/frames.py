"""What a frame really costs on the 6502: a bot plays the model, and every frame the 6502's physics runs on
the same balls (checked against the model's step) and its plotter draws the frame's changes (checked
against the model's screen).

	.venv/bin/python tools/frames.py [--frames 1500] [--seed 2]

The game's own logic (dropper, merges, explosions, keys, score) isn't counted: it's small beside these.
Nor are the sparks (P21): the model doesn't draw them here, as the 6502 isn't given them.
"""

import argparse
import sys

from game import Game
from machine import Machine
from mode2 import ScreenBase, ScreenSize, Screen
from model import Bot, background, pct
from physics import Params
from test_physics import get, put, want


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--frames", type=int, default=1500)
	ap.add_argument("--seed", type=int, default=2)
	args = ap.parse_args()
	game = Game(seed=args.seed, params=Params(), hyst_x=2, hyst_y=2)
	game.sparks.frame = lambda screen: None	# (no sparks: see above)
	bot = Bot(game, args.seed + 1000)
	screen = Screen()
	background(screen)
	m = Machine()
	mem = m.mpu.memory
	mem[ScreenBase:ScreenBase + ScreenSize] = list(screen.mem)
	names = [f"plot_ball.{k}{s}" for s in "ab" for k in ("shape", "colour", "px", "line")]
	rows = []
	for frame in range(args.frames):
		bot.act()
		game.before_step()					# (slow motion, and critical mass's stand-still and burst)
		w = game.world
		# the 6502 gets the balls as they are before the step, in the same order
		for slot, b in enumerate(w.order):
			b.slot = slot
			put(m, slot, b)
			m.poke(m["Order"] + slot, slot)
		m.poke(m["NumBalls"], len(w.order))
		before = list(w.order)
		phys = m.call("physics_step")
		w.step()							# the world's step alone, to check against
		for b in before:
			if get(m, b.slot) != want(b):
				print(f"FAIL physics at frame {frame}: slot {b.slot}")
				sys.exit(1)
		# the game's step is before_step, the world's step just taken, and after_step: so the bot's game goes
		# on as usual
		game.after_step()
		if game.over:
			break
		balls = game.dying + w.order + [game.held_ball, game.next_ball]
		olds = [b.drawn for b in balls]
		game.draw(screen)
		plot = 0
		for b, old in zip(balls, olds):
			if old != b.drawn:
				vals = list(old or (0, 0, 0, 0)) + list(b.drawn or (0, 0, 0, 0))
				plot += m.call("plot_ball", **dict(zip(names, vals)))
		# the score's text is plain stores, not the plotter's: copy the model's lines of it
		from layout import BestLine, BoxCol, BoxCols, ScoreLine
		for line in list(range(ScoreLine, ScoreLine + 10)) + list(range(BestLine, BestLine + 10)):
			for col in range(BoxCol, BoxCol + BoxCols):
				off = (line >> 3) * 512 + col * 8 + (line & 7)
				mem[ScreenBase + off] = screen.mem[off]
		if bytes(mem[ScreenBase:ScreenBase + ScreenSize]) != bytes(screen.mem):
			print(f"FAIL screen at frame {frame}")
			sys.exit(1)
		rows.append((phys, plot, len(before), w.stats.contacts))
	tot = [p + d for p, d, _, _ in rows]
	print(f"{len(rows)} frames: physics and drawing both matched the model every frame")
	for name, v in (("physics", [r[0] for r in rows]), ("drawing", [r[1] for r in rows]), ("total", tot)):
		print(f"  {name:8s} median {pct(v, 0.5):6d}  90% {pct(v, 0.9):6d}  95% {pct(v, 0.95):6d}  "
			  f"max {max(v):6d}")
	print(f"  over 80,000: {sum(t > 80000 for t in tot)} frames; balls up to {max(r[2] for r in rows)}")


if __name__ == "__main__":
	main()
