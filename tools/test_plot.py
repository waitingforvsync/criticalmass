"""Test the 6502's plotter against the model: every byte of the screen, and its cycles.

	.venv/bin/python tools/test_plot.py [--cases 600] [--seed 1]

The screen starts as random bytes, so EOR, not store, is what's checked. Each case moves a ball from an
old drawing to a new one (either may be none) and compares all of the screen's memory with the model's
before EOR old EOR new. The cases: random pairs; no move; small moves down, up and across, as the physics
makes; a size's step up in place (a merge's growth); a colour change; drawing from nothing; and taking
away to nothing. Every shape at both parities is drawn.
"""

import argparse
import random
import sys

from machine import Machine
from mode2 import ScreenBase, ScreenSize, Screen
from render import ball_bytes
from shapes import CriticalSize, make_shapes

WellPx, WellPxEnd, Floor = 0, 64, 216				# the well, in pixels from its left (D18), and its floor


def expected(before, old, new, shapes):
	scr = bytearray(before)
	for d in (old, new):
		if d is None:
			continue
		shape, colour, px, line = d
		for (col, y), v in ball_bytes(shapes[shape], px, line, colour).items():
			scr[(y >> 3) * 512 + col * 8 + (y & 7)] ^= v
	return scr


def place(rnd, shapes, shape, px=None, line=None):
	sh = shapes[shape]
	if px is None:
		px = rnd.randint(WellPx, WellPxEnd - sh.width)
	if line is None:
		line = rnd.randint(0, Floor - sh.height)
	px = min(max(px, WellPx), WellPxEnd - sh.width)
	line = min(max(line, 0), Floor - sh.height)
	return px, line


def cases(rnd, shapes, n):
	out = []
	for s in range(1, CriticalSize + 1):
		for px in (WellPx, WellPx + 1):					# every shape, both parities, from and to nothing
			d = (s, s, px, 5)
			out += [("new", None, d), ("gone", d, None)]
	kinds = ["random", "still", "down", "up", "across", "grow", "recolour"]
	for i in range(n):
		kind = kinds[i % len(kinds)]
		s = rnd.randint(1, CriticalSize)
		px, line = place(rnd, shapes, s)
		old = (s, s, px, line)
		if kind == "random":
			s2 = rnd.randint(1, CriticalSize)
			new = (s2, rnd.randint(1, CriticalSize), *place(rnd, shapes, s2))
		elif kind == "still":
			new = old
		elif kind in ("down", "up"):
			dy = rnd.randint(1, 12) * (1 if kind == "down" else -1)
			new = (s, s, *place(rnd, shapes, s, px + rnd.randint(-1, 1), line + dy))
		elif kind == "across":
			new = (s, s, *place(rnd, shapes, s, px + rnd.choice((-2, -1, 1, 2)), line + rnd.randint(-2, 2)))
		elif kind == "grow":
			# a merge's growth: the same colour, the next shape at about the same centre (as the game
			# draws it a shape smaller for two frames)
			s2 = min(CriticalSize, s + 1)
			sh, sh2 = shapes[s], shapes[s2]
			cx, cy = 2 * px + sh.width, 2 * line + sh.height		# centre, doubled
			old = (s, s2, px, line)
			new = (s2, s2, *place(rnd, shapes, s2, (cx - sh2.width) // 2 + rnd.randint(-1, 1),
								  (cy - sh2.height) // 2 + rnd.randint(-3, 3)))
		else:
			new = (s, rnd.randint(1, CriticalSize), px, line)
		out.append((kind, old, new))
	return out


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--cases", type=int, default=600)
	ap.add_argument("--seed", type=int, default=1)
	args = ap.parse_args()
	rnd = random.Random(args.seed)
	shapes = make_shapes()
	m = Machine()
	mem = m.mpu.memory
	before = bytes(rnd.randrange(256) for _ in range(ScreenSize))
	mem[ScreenBase:ScreenBase + ScreenSize] = list(before)
	fails, stats = 0, {}
	for kind, old, new in cases(rnd, shapes, args.cases):
		screen = bytes(mem[ScreenBase:ScreenBase + ScreenSize])
		want = expected(screen, old, new, shapes)
		a = old or (0, 0, 0, 0)
		b = new or (0, 0, 0, 0)
		cyc = m.call("plot_ball", **{
			"plot_ball.shapea": a[0], "plot_ball.coloura": a[1], "plot_ball.pxa": a[2], "plot_ball.linea": a[3],
			"plot_ball.shapeb": b[0], "plot_ball.colourb": b[1], "plot_ball.pxb": b[2], "plot_ball.lineb": b[3]})
		got = bytes(mem[ScreenBase:ScreenBase + ScreenSize])
		if got != want:
			fails += 1
			bad = [i for i in range(ScreenSize) if got[i] != want[i]]
			if fails <= 5:
				print(f"FAIL {kind}: old {old} new {new}: {len(bad)} bytes, first at &{ScreenBase + bad[0]:04X}"
					  f" got &{got[bad[0]]:02X} want &{want[bad[0]]:02X}")
			mem[ScreenBase:ScreenBase + ScreenSize] = list(want)		# carry on from the right screen
		changed = sum(1 for i in range(ScreenSize) if screen[i] != want[i])
		stats.setdefault(kind, []).append((cyc, changed))
	total = sum(len(v) for v in stats.values())
	print(f"{total - fails}/{total} cases match the model")
	for kind, v in stats.items():
		cyc = sorted(c for c, _ in v)
		byt = sum(b for _, b in v)
		print(f"  {kind:9s} {len(v):4d} cases: cycles median {cyc[len(cyc) // 2]:6d} max {cyc[-1]:6d}; "
			  f"{sum(cyc) / max(1, byt):5.1f} cycles a changed byte")
	sys.exit(1 if fails else 0)


if __name__ == "__main__":
	main()
