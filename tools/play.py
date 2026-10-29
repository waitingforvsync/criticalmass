"""A lookahead bot, to see whether critical mass can be reached: for each drop it tries every dropper
position (every 2 units), plays the move, the drop and the next 40 frames on a copy of the game (exactly
what will happen: the model is deterministic) and keeps the position whose result scores best.

	.venv/bin/python tools/play.py [--seed N] [--frames N] [--noise 3 --blur 0.5] [--video OUT.mp4
		[--clip FROM,TO] [--fps 25|50]] [--tools DIR]

--noise and --blur make it err: a gaussian aiming error (units), and a random error in judging each
position (times the spread of the positions' scores). --tools runs another copy of the model (one with
shapes.py changed, say). It prints a line every 100 drops, then the game's result. The video shows each
frame for the vsyncs main.6502 paces it at (2, or slow motion's 6), with the IRQ's palette at each (the
pulse, and the explosion's flash): at 25 fps, an image every other vsync; at 50, every vsync. --clip
keeps only the frames from FROM up to TO.
"""

import argparse
import copy
import math
import os
import random
import subprocess
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--tools", default="tools")
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--frames", type=int, default=30000)
ap.add_argument("--step", type=float, default=2.0)		# units between the positions tried
ap.add_argument("--wait", type=int, default=12)			# frames waited after each drop
ap.add_argument("--horizon", type=int, default=40)		# frames simulated after a drop, to judge it
ap.add_argument("--noise", type=float, default=0)		# units of aiming error (a gaussian's sigma)
ap.add_argument("--blur", type=float, default=0)		# judging error: each position's score times this, random
ap.add_argument("--video")
ap.add_argument("--clip", default="0,1000000")
ap.add_argument("--fps", type=int, default=25, choices=(25, 50))
ap.add_argument("--log", type=int, default=100)			# report every this many drops
args = ap.parse_args()
sys.path.insert(0, args.tools)

from game import DropperSpeed, Game, KeyDrop, KeyLeft, KeyRight, KeySlow, SlowSpeed
from physics import Floor, One, Params, Rim
from shapes import CriticalSize
from tables import WQ


human = random.Random(args.seed + 500)		# the erring bot's errors


def policy(g, target, wait):
	"""The keys, a frame at a time: to the target (fast, then slow), drop, then wait."""
	while True:
		lo, hi = g.dropper_limits()
		gap = min(max(target, lo), hi) - g.dropper_x
		if abs(gap) >= DropperSpeed:
			yield KeyLeft if gap < 0 else KeyRight
		elif abs(gap) * 2 >= SlowSpeed:
			yield (KeyLeft if gap < 0 else KeyRight) | KeySlow
		elif g.cooldown or g.held_grow < g.held or not g.released:
			yield 0
		else:
			break
	yield KeyDrop
	for _ in range(wait):
		yield 0


def frame(g, keys):
	g.keys(keys)
	g.step()
	if not g.over:
		g.held_shape()
	g.dying = []


def clone(g):
	memo = {id(g.shapes): g.shapes, id(g.patterns): g.patterns}
	return copy.deepcopy(g, memo)


def evaluate(g, worst_fail):
	"""Higher is better."""
	if g.over:
		return -1e9
	balls = g.world.order
	e = 0.0
	# critical mass: an explosion is the aim (its pieces alone would score worse than the 12 did)
	e += g.explosions * 2 * 3.0 ** CriticalSize / 30
	# room: the pile's top, and a steep price near the rim
	top = min(((b.y - (WQ[b.size] << 6)) / One for b in balls), default=Floor)
	e += 0.3 * top
	danger = max(0.0, Rim + 40 - top)
	e -= 0.5 * danger * danger
	e -= 2000 * worst_fail
	# fewer balls for the mass: each merge is a ball fewer
	e -= 25 * len(balls)
	# the balls' worth: bigger is better, much more than linearly
	e += sum(3.0 ** b.size for b in balls) / 30
	# duplicates of a size that aren't merging: stranded, the bigger the worse
	count = {}
	for b in balls:
		count[b.size] = count.get(b.size, 0) + 1
	for s, c in count.items():
		if c > 1:
			e -= (c - 1) * 4 * s * s
	# neighbours: a ball touching the next size up or down chains; a small one by a big one is in the way
	for i, a in enumerate(balls):
		for b in balls[i + 1:]:
			d = math.hypot(a.x - b.x, a.y - b.y) / One
			if d < a.r + b.r + 3:
				ds = abs(a.size - b.size)
				big = max(a.size, b.size)
				if ds == 0:
					e += 3 * big
				elif ds == 1:
					e += 2 * big
				else:
					e -= 0.6 * ds * ds
			# a small ball under a bigger one is buried
			if abs(a.x - b.x) / One < (a.r + b.r) * 0.8:
				under, over = (a, b) if a.y > b.y else (b, a)
				if under.size < over.size:
					e -= 3 * (over.size - under.size)
	return e


def try_drop(g, target, horizon):
	"""Play a drop at target on a copy: the copy afterwards, and the worst failing it saw."""
	c = clone(g)
	worst = 0
	for keys in policy(c, target, horizon):
		frame(c, keys)
		worst = max(worst, c.fail)
		if c.over:
			break
	return c, worst


def candidates(g, step):
	lo, hi = g.dropper_limits()
	xs = list(range(lo, hi + 1, round(step * One)))
	if xs[-1] != hi:
		xs.append(hi)
	return xs


def choose(g):
	scored = []
	for x in candidates(g, args.step):
		c, worst = try_drop(g, x, args.horizon)
		scored.append((evaluate(c, worst), x, c))
	live = sorted((e for e, _, _ in scored if e > -1e8), reverse=True)[:10]	# the spread of the best ten:
	if args.blur and len(live) > 1:												# not the outliers'
		mean = sum(live) / len(live)
		sd = math.sqrt(sum((e - mean) ** 2 for e in live) / len(live))
		scored = [(e + human.gauss(0, args.blur * sd) if e > -1e8 else e, x, c) for e, x, c in scored]
	scored.sort(key=lambda t: -t[0])
	return scored[0][1]


def irq_palette(vsync, white):
	"""The palette at a vsync, as the IRQ sets it (irq.6502): P, the size one merge from critical, white
	for 8 vsyncs and cyan for 8; and every ball colour white while the explosion's flash lasts."""
	from colours import B, C, G, M, P, Palette, R, W, Y
	from mode2 import Cyan, White
	pal = list(Palette)
	pal[P] = White if vsync & 15 < 8 else Cyan
	if white:
		for code in (R, G, B, Y, M, C, W, P):
			pal[code] = White
	return pal


FlashVsyncs = 6							# irq.6502's: white for the 5 vsyncs after the burst


def main():
	g = Game(seed=args.seed, params=Params(), hyst_x=2, hyst_y=2)
	clip = [int(v) for v in args.clip.split(",")]
	vsync = flash = 0
	video = screen = None
	if args.video:
		import model
		from mode2 import Columns, Lines, Screen
		screen = Screen()
		model.background(screen)
		h, w = Lines * 2, Columns * 2 * 2 * 2
		video = subprocess.Popen(
			["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
			 "-r", str(args.fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", args.video],
			stdin=subprocess.PIPE)
	drops = 0
	biggest = 0
	t0 = time.time()
	peak = {}
	while not g.over and g.step_no < args.frames:
		x = choose(g)
		last = g.last_drop
		if args.noise:
			x += round(human.gauss(0, args.noise) * One)
		for keys in policy(g, x, args.wait):
			g.keys(keys)
			explosions = g.explosions
			g.step()
			if video:
				g.draw(screen)
				if g.explosions != explosions:
					flash = FlashVsyncs
				for v in range(g.pace):			# the vsyncs it shows for (main.6502's pace)
					vsync += 1
					flash = max(0, flash - 1)
					if clip[0] <= g.step_no < clip[1] and (v % 2 == 0 or args.fps == 50):
						video.stdin.write(model.frame_rgb(screen, palette=irq_palette(vsync, flash)).tobytes())
			else:
				if not g.over:
					g.held_shape()
				g.dying = []
			for b in g.world.order:
				if b.size > biggest:
					biggest = b.size
					peak[biggest] = g.step_no
			if g.over:
				break
		if g.last_drop is not last:			# (the game refuses a drop with 38 balls in)
			drops += 1
		if drops % args.log == 0:
			sizes = sorted((b.size for b in g.world.order), reverse=True)
			top = min(((b.y - (WQ[b.size] << 6)) / One for b in g.world.order), default=Floor)
			print(f"drop {drops:4d} frame {g.step_no:5d} score {g.score:6d} explosions {g.explosions} "
				  f"biggest {biggest:2d} top {top:5.1f} balls {sizes}  ({time.time() - t0:.0f}s)", flush=True)
	if video:
		video.stdin.close()
		video.wait()
	sizes = sorted((b.size for b in g.world.order), reverse=True)
	print(f"END {os.path.basename(args.tools.rstrip('/'))} noise {args.noise} blur {args.blur} seed {args.seed}: "
		  f"{'game over' if g.over else 'stopped'} at frame {g.step_no} "
		  f"({g.step_no / 25 / 60:.1f} min), {drops} drops, score {g.score}, {g.merges} merges, "
		  f"{g.explosions} explosions, biggest {biggest} (critical {CriticalSize}), first reached at "
		  f"{ {s: round(f / 25 / 60, 1) for s, f in sorted(peak.items())} } min; left {sizes}; "
		  f"explosions at frames {[f for e, f in g.events if e == 'explode']}", flush=True)


main()
