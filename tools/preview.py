"""Preview the shapes and colours: every size (check_runs checks both parities), and a mock well full of balls.

	.venv/bin/python tools/preview.py --out build/model
"""

import argparse
import math
import os
import random

from colours import Palette, SizeColours
from mode2 import Screen
from render import ball_bytes, ball_bytes_from_pixels, eor_ball
from shapes import CriticalSize, make_shapes, physics_radius


def check_runs(shapes):
	"""The run tables must draw exactly the bitmap, at both parities."""
	for s, sh in shapes.items():
		for px in (10, 11):
			assert ball_bytes(sh, px, 3, s) == ball_bytes_from_pixels(sh, px, 3, s), (s, px)


def sizes_sheet(shapes):
	scr = Screen()
	x, y, tallest = 1, 2, 0
	for s, sh in shapes.items():
		if x + sh.width + 2 > 128:
			x, y, tallest = 1, y + tallest + 3, 0
		tallest = max(tallest, sh.height)
		eor_ball(scr, sh, x, y, s)
		x += sh.width + 3
	return scr


def mock_well(shapes, seed=3):
	"""Balls dropped at random into a 64-pixel well, each settled as low as it fits without overlap."""
	rnd = random.Random(seed)
	scr = Screen()
	placed = []
	sizes = [rnd.choice([1, 1, 2, 2, 3, 3, 4, 4, 5, 6, 7, 8, 9]) for _ in range(60)]
	for s in sizes:
		r = physics_radius(s)
		best = None
		for _ in range(40):
			x = rnd.uniform(r, 128 - r)
			y = 216 - r
			while y > r + 30:
				if all((x - px) ** 2 + (y - py) ** 2 >= (r + pr) ** 2 for px, py, pr in placed):
					break
				y -= 1
			else:
				continue
			# fall from there to the lowest free place
			while y + 1 <= 216 - r and all((x - px) ** 2 + (y + 1 - py) ** 2 >= (r + pr) ** 2
										  for px, py, pr in placed):
				y += 1
			if best is None or y > best[1]:
				best = (x, y)
		if best:
			x, y = best
			placed.append((x, y, r))
			sh = shapes[s]
			px = round((x - sh.width) / 2)		# from the well's left (render.py adds its column)
			line = round(y - sh.height / 2)
			eor_ball(scr, sh, px, line, s)
	return scr


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--out", default="build/model")
	args = ap.parse_args()
	os.makedirs(args.out, exist_ok=True)
	shapes = make_shapes()
	check_runs(shapes)
	sizes_sheet(shapes).image(Palette, 3).save(os.path.join(args.out, "sizes.png"))
	mock_well(shapes).image(Palette, 3).save(os.path.join(args.out, "well.png"))
	print("run tables match the bitmaps; wrote sizes.png and well.png to", args.out)


if __name__ == "__main__":
	main()
