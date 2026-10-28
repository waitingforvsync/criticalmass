"""Physics settings side by side: the same drops (no merges) under each, drawn as the BBC draws them (each
frame drawn fresh, so without the hysteresis).

	.venv/bin/python tools/compare.py [--out build/model/compare.mp4] [--balls 26] [--seed 4]
		[label=margin,kp16,kv16 ...]

With no settings it compares the physics before P12 (margin 0, kv 6/16) with the game's.
"""

import argparse
import random
import subprocess

import numpy as np
from PIL import Image, ImageDraw

import shapes
import tables
from model import background, frame_rgb
from mode2 import Screen
from physics import Ball, One, Params, Rim, World, WellLeft, WellRight
from render import eor_ball

Scale = 2
Crop = 36 * 2 * 2 * Scale				# byte columns 0-35, the well and its walls: 2 pixels a byte, 2 TV pixels a pixel
Height = 216 * Scale					# down to the floor
Head = 16								# the labels' strip
Every = 15								# frames between drops


def set_margin(m):
	shapes.Margin = m
	tables.build()


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--out", default="build/model/compare.mp4")
	ap.add_argument("--balls", type=int, default=26)
	ap.add_argument("--seed", type=int, default=4)
	ap.add_argument("settings", nargs="*")
	args = ap.parse_args()
	settings = []
	for arg in args.settings:
		label, spec = arg.split("=")
		m, kp, kv = (float(v) for v in spec.split(","))
		settings.append((label, m, kp, kv))
	if not settings:
		now = Params()
		settings = [("before P12: margin 0, kv 6/16", 0.0, 11, 6),
					(f"now: margin {shapes.Margin}, kv {round(now.kv * 16)}/16", shapes.Margin,
					 round(now.kp * 16), round(now.kv * 16))]
	margin = shapes.Margin
	rnd = random.Random(args.seed)
	drops = [(rnd.choice((1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 7)), rnd.uniform(0, 1)) for _ in range(args.balls)]
	worlds = [World(Params(kp=kp / 16, kv=kv / 16, merge_age=999)) for _, _, kp, kv in settings]
	shp = shapes.make_shapes()
	width = len(settings) * (Crop + 8) - 8
	video = subprocess.Popen(
		["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
		 "-s", f"{width}x{Height + Head}", "-r", "25", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
		 "-crf", "16", args.out], stdin=subprocess.PIPE)
	gap = np.full((Height + Head, 8, 3), 60, dtype=np.uint8)
	frames = len(drops) * Every + 150
	for t in range(frames):
		parts = []
		for (label, m, _, _), world in zip(settings, worlds):
			set_margin(m)
			if t % Every == 0 and t // Every < len(drops):
				s, u = drops[t // Every]
				r = shapes.draw_radius(s)
				x = WellLeft + r + 1 + u * (WellRight - WellLeft - 2 * r - 2)
				world.add(Ball(s, round(x * One), round((Rim - r) * One)))
			world.step()
			screen = Screen()
			background(screen)
			for b in world.order:
				sh = shp[b.size]			# placed as game.py's target does
				px = ((b.x >> 8) - sh.width + 1) >> 1
				line = (2 * (b.y >> 8) - sh.height + 1) >> 1
				eor_ball(screen, sh, px, line, b.size)
			strip = Image.new("RGB", (Crop, Head))
			ImageDraw.Draw(strip).text((20, 2), label, fill=(255, 255, 255))
			if parts:
				parts.append(gap)
			parts.append(np.vstack([np.asarray(strip), frame_rgb(screen, Scale)[:Height, :Crop]]))
		video.stdin.write(np.hstack(parts).tobytes())
	video.stdin.close()
	video.wait()
	set_margin(margin)
	print(f"{frames} frames: {args.out}")


if __name__ == "__main__":
	main()
