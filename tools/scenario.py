"""Scripted scenes for the model: set balls up by hand, run, and write a video and stills.

	.venv/bin/python tools/scenario.py critical --out build/model

critical: a pile, with two size-9 balls dropped into it side by side; they merge into the critical size,
which explodes.
"""

import argparse
import os
import random
import subprocess

from game import Game
from mode2 import Columns, Lines, Screen
from model import background, frame_rgb
from physics import Ball, Floor, One, Params, WellLeft
from shapes import CriticalSize


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("scene")
	ap.add_argument("--out", default="build/model")
	args = ap.parse_args()
	os.makedirs(args.out, exist_ok=True)
	game = Game(seed=9, params=Params(), hyst_x=2, hyst_y=2)
	game.held = game.next = 1
	screen = Screen()
	background(screen)
	path = os.path.join(args.out, f"scene-{args.scene}.mp4")
	h, wd = Lines * 2, Columns * 2 * 2 * 2
	video = subprocess.Popen(
		["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{wd}x{h}",
		 "-r", "25", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", path],
		stdin=subprocess.PIPE)
	w = game.world
	rnd = random.Random(4)
	for i in range(14):
		s = rnd.choice((1, 2, 3, 4))
		w.add(Ball(s, round((WellLeft + 10 + (i * 37) % 110) * One), round((Floor - 20 - (i // 4) * 25) * One),
				   age=255))
	for k in range(160):
		if k == 50:
			w.add(Ball(CriticalSize - 1, round((WellLeft + 32) * One), round(40 * One), age=255))
			w.add(Ball(CriticalSize - 1, round((WellLeft + 96) * One), round(40 * One), vx=-One // 2, age=255))
		game.step()
		f = game.draw(screen)
		if game.events and game.events[-1][1] == game.step_no:
			print(f"step {game.step_no}: {game.events[-1][0]}, {len(w.order)} balls")
		video.stdin.write(frame_rgb(screen).tobytes())
	video.stdin.close()
	video.wait()
	print(f"score {game.score}, {game.merges} merges, {game.explosions} explosions; wrote {path}")


if __name__ == "__main__":
	main()
