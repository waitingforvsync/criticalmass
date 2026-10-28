"""Replay a model game's drawing through the 6502's plotter: every frame's moves, its cycles, and the
screen checked against the model's after every frame.

	.venv/bin/python tools/replay.py [--steps 1500] [--seed 2]

This is the plotter's end-to-end test and its budget: what drawing a real game costs a frame.
"""

import argparse
import sys

from game import Game
from machine import Machine
from mode2 import ScreenBase, ScreenSize, Screen
from model import Bot, background, pct
from physics import Params


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--steps", type=int, default=1500)
	ap.add_argument("--seed", type=int, default=2)
	args = ap.parse_args()
	game = Game(seed=args.seed, params=Params(), hyst_x=2, hyst_y=2)
	bot = Bot(game, args.seed + 1000)
	screen = Screen()
	background(screen)
	m = Machine()
	mem = m.mpu.memory
	mem[ScreenBase:ScreenBase + ScreenSize] = list(screen.mem)
	names = [f"plot_ball.{k}{s}" for s in "ab" for k in ("shape", "colour", "px", "line")]
	frames, kinds = [], {}
	for step in range(args.steps):
		bot.act()
		if game.step() is None:
			break
		balls = game.dying + game.world.order + [game.held_ball]
		before = [b.drawn for b in balls]
		game.draw(screen)
		total = 0
		for b, old in zip(balls, before):
			new = b.drawn
			if old == new:
				continue
			# the model's drawing is (shape, colour, px, line)
			vals = list(old or (0, 0, 0, 0)) + list(new or (0, 0, 0, 0))
			cyc = m.call("plot_ball", **dict(zip(names, vals)))
			total += cyc
			if old is None or new is None:
				kind = "new/gone"
			elif old[1] != new[1]:
				kind = "recolour"
			elif old[0] == new[0] and old[2] == new[2]:
				kind = "vertical"
			else:
				kind = "other"
			kinds.setdefault(kind, []).append(cyc)
		frames.append(total)
		got = bytes(mem[ScreenBase:ScreenBase + ScreenSize])
		if got != bytes(screen.mem):
			bad = sum(1 for i in range(ScreenSize) if got[i] != screen.mem[i])
			print(f"FAIL at frame {step}: {bad} bytes differ from the model")
			sys.exit(1)
	print(f"{len(frames)} frames drawn; the screen matched the model's after every one")
	print(f"  drawing a frame: median {pct(frames, 0.5)}, 90% {pct(frames, 0.9)}, 95% {pct(frames, 0.95)}, "
		  f"max {max(frames)} cycles")
	for kind, v in sorted(kinds.items()):
		print(f"  {kind:9s} {len(v):5d} moves: median {pct(v, 0.5):6d}  90% {pct(v, 0.9):6d}  max {max(v):6d}")


if __name__ == "__main__":
	main()
