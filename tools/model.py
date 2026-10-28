"""Run the model: a bot plays, the screen model draws it, and the cost of every step is counted.

	.venv/bin/python tools/model.py --out build/model [--steps 3000] [--seed 1] [--mode int|float]
		[--kp 0.7 --kv 0.75 --passes 2 --gravity 288] [--hyst 2,1] [--video]

It writes `game-<seed>.mp4` (with --video) and prints a summary: the game, the squishiness (the deepest
overlaps at rest), the jitter (redraws of balls at rest), and the estimated cycles a step.
"""

import argparse
import math
import os
import random
import subprocess

import numpy as np

from colours import Palette
from layout import background		# (the tools import it from here)
from game import DropperSpeed, DropSizes, Game, KeyDrop, KeyLeft, KeyRight, KeySlow
from mode2 import Columns, Lines, PhysicalRGB, Screen, byte_pixels
from physics import Floor, One, Params, Rim, WellLeft, WellRight
from shapes import draw_radius, physics_radius
from tables import pair_r

# Rough NMOS cycle costs, to be replaced by measured ones once the 6502 exists
Cost = {
	"integrate": 110, "apply": 90,		# each ball, each substep (apply: each pass)
	"compare": 25, "swap": 25,			# the sort
	"pair": 30, "box_out": 25, "d2_out": 45, "contact": 260,
	"drawn": 150, "column": 150, "byte": 20,
	"frame": 3000,						# the IRQ, the keys, the dropper, the score
}


def cycles(f, substeps=2, passes=1):
	p = f.physics
	per_ball = substeps * (Cost["integrate"] + passes * Cost["apply"])
	return (Cost["frame"] + per_ball * f.balls + Cost["compare"] * p.compares + Cost["swap"] * p.swaps
			+ Cost["pair"] * p.pairs + Cost["box_out"] * p.box_out + Cost["d2_out"] * p.d2_out
			+ Cost["contact"] * p.contacts + Cost["drawn"] * f.drawn + Cost["column"] * f.columns
			+ Cost["byte"] * f.bytes)


class Bot:
	"""Aims each drop where it lands deepest, much preferring a ball of its own size to land on."""

	def __init__(self, game, seed):
		self.g = game
		self.rnd = random.Random(seed)
		self.target = None
		self.wait = 0

	def landing(self, x, r):
		best_y, touched = Floor - r, None
		for b in self.g.world.order:
			bx, by, rb = b.x / One, b.y / One, b.r
			if abs(x - bx) < r + rb:
				y = by - math.sqrt((r + rb) ** 2 - (x - bx) ** 2)
				if y < best_y:
					best_y, touched = y, b
		return best_y, touched

	def choose(self):
		g = self.g
		r = physics_radius(g.held)
		best = None
		x = WellLeft + r + 1
		while x <= WellRight - r - 1:
			y, touched = self.landing(x, r)
			score = y + self.rnd.uniform(0, 12)
			if touched is not None and touched.size == g.held:
				score += 50
			if y - r < Rim + 4:
				score -= 100
			if best is None or score > best[0]:
				best = (score, x)
			x += 2
		return best[1]

	def act(self):
		"""This frame's keys, given to the game."""
		self.g.keys(self.decide())

	def decide(self):
		g = self.g
		if self.wait > 0:
			self.wait -= 1
			return 0
		if self.target is None:
			self.target = self.choose()
		lo, hi = g.dropper_limits()
		target = min(max(round(self.target * One), lo), hi)
		gap = target - g.dropper_x
		if gap <= -DropperSpeed // 2:
			return KeyLeft | (KeySlow if gap > -DropperSpeed else 0)
		if gap >= DropperSpeed // 2:
			return KeyRight | (KeySlow if gap < DropperSpeed else 0)
		if g.cooldown or g.held_grow < g.held:
			return 0
		if not g.released:
			return 0						# let go first
		self.target = None
		self.wait = self.rnd.randint(4, 20)
		return KeyDrop


_codes = np.array([byte_pixels(v) for v in range(256)], dtype=np.uint8)
_rgb = np.array(PhysicalRGB, dtype=np.uint8)


def frame_rgb(screen, scale=2):
	mem = np.frombuffer(bytes(screen.mem), dtype=np.uint8).reshape(28, Columns, 8)
	grid = mem.transpose(0, 2, 1).reshape(Lines, Columns)
	codes = _codes[grid].reshape(Lines, Columns * 2)
	pal = np.array(Palette, dtype=np.uint8)
	rgb = _rgb[pal[codes]]
	rgb = rgb.repeat(2 * scale, axis=1).repeat(scale, axis=0)
	return rgb


def overlaps(world):
	"""Each touching pair's overlap as it's seen, in units: the drawn circles', which can be negative (a gap)
	as the physics circles are bigger (P12)."""
	out = []
	o = world.order
	for i, a in enumerate(o):
		for b in o[i + 1:]:
			d = math.hypot((a.x - b.x) / One, (a.y - b.y) / One)
			if d < pair_r(a.size, b.size) / 4:
				out.append(draw_radius(a.size) + draw_radius(b.size) - d)
	return out


def pct(values, q):
	if not values:
		return 0
	v = sorted(values)
	return v[min(len(v) - 1, int(q * len(v)))]


def run(args):
	params = Params(kp=args.kp, kv=args.kv, passes=args.passes, gravity=args.gravity, rate=args.rate,
					reuse=bool(args.reuse), merge_age=round(10 * args.rate / 60))
	hx, hy = (int(v) for v in args.hyst.split(","))
	game = Game(seed=args.seed, params=params, mode=args.mode, hyst_x=hx, hyst_y=hy)
	bot = Bot(game, args.seed + 1000)
	screen = Screen()
	background(screen)
	video = None
	if args.video:
		os.makedirs(args.out, exist_ok=True)
		h, w = Lines * 2, Columns * 2 * 2 * 2
		path = os.path.join(args.out, f"game-{args.seed}{args.tag}.mp4")
		video = subprocess.Popen(
			["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
			 "-s", f"{w}x{h}", "-r", "25", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
			 "-crf", "16", path], stdin=subprocess.PIPE)
	frames, cyc, rest_redraws, rest_steps, deep = [], [], 0, 0, []
	for step in range(args.steps):
		bot.act()
		before = {id(b): b.drawn for b in game.world.order}
		if game.step() is None:
			break
		f = game.draw(screen)
		frames.append(f)
		cyc.append(cycles(f, max(1, args.rate // 25), args.passes))
		# jitter: redraws of balls that were drawn and are nearly still
		for b in game.world.order:
			still = abs(b.vx) < One // 8 and abs(b.vy) < One // 4 and b.age > 50
			if still and id(b) in before:
				rest_steps += 1
				if before[id(b)] != b.drawn:
					rest_redraws += 1
		if step % 25 == 0:
			deep.append(max(overlaps(game.world), default=0))
		if video:
			video.stdin.write(frame_rgb(screen).tobytes())
	if video:
		video.stdin.close()
		video.wait()

	n = len(frames)
	balls = [f.balls for f in frames]
	print(f"seed {args.seed} mode {args.mode} rate {args.rate} kp {args.kp} kv {args.kv} "
		  f"passes {args.passes}{' reused' if args.reuse else ''} g {args.gravity} hyst {hx},{hy}")
	print(f"  {n} steps ({n / 25:.0f} s){' game over' if game.over else ''}: score {game.score}, "
		  f"{game.merges} merges, {game.explosions} explosions, up to {max(balls)} balls")
	print(f"  deepest drawn overlap (sampled each second): median {pct(deep, 0.5):.1f}, "
		  f"90% {pct(deep, 0.9):.1f}, max {max(deep):.1f} units")
	print(f"  jitter: {rest_redraws} redraws in {rest_steps} ball-steps at rest "
		  f"({100 * rest_redraws / max(1, rest_steps):.2f}%)")
	for key in ("pairs", "contacts"):
		v = [getattr(f.physics, key) for f in frames]
		print(f"  {key:9s} median {pct(v, 0.5):4d}  95% {pct(v, 0.95):4d}  max {max(v):4d}")
	for key in ("drawn", "columns", "bytes"):
		v = [getattr(f, key) for f in frames]
		print(f"  {key:9s} median {pct(v, 0.5):4d}  95% {pct(v, 0.95):4d}  max {max(v):4d}")
	print(f"  cycles    median {pct(cyc, 0.5):6d}  95% {pct(cyc, 0.95):6d}  max {max(cyc):6d}  "
		  f"(budget 80000; over: {sum(c > 80000 for c in cyc)} steps)")
	return game, frames, cyc


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--out", default="build/model")
	ap.add_argument("--steps", type=int, default=3000)
	ap.add_argument("--seed", type=int, default=1)
	ap.add_argument("--mode", default="int")
	ap.add_argument("--kp", type=float, default=0.7)
	ap.add_argument("--kv", type=float, default=0.75)
	ap.add_argument("--passes", type=int, default=2)
	ap.add_argument("--reuse", type=int, default=1)
	ap.add_argument("--rate", type=int, default=25)
	ap.add_argument("--gravity", type=float, default=288.0)
	ap.add_argument("--hyst", default="2,2")
	ap.add_argument("--video", action="store_true")
	ap.add_argument("--tag", default="")
	run(ap.parse_args())


if __name__ == "__main__":
	main()
