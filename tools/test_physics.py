"""Test the 6502's physics against the model, step by step: every ball's position, velocity, hit and age,
the order, and the merges found, after every step.

	.venv/bin/python tools/test_physics.py [--scenes 20] [--steps 40]

Scenes: balls at the well's limits moving fast enough that the move wraps past 65535 or below 0 (each of
integrate's four wrap paths), balls dropped at random (overlapping, so they push hard), and snapshots of a
bot's game (piles at rest, and balls landing on them). Also the cycles a step takes, against the balls and
contacts.
"""

import argparse
import random
import sys

from game import Game
from machine import Machine
from mode2 import Screen
from model import Bot, pct
from physics import Ball, Floor, One, Params, WellLeft, WellRight, World
from tables import RQ, WQ

Fields = ("XLo", "XHi", "YLo", "YHi", "VXLo", "VXHi", "VYLo", "VYHi", "Size", "Age", "Hit",
		  "IXLo", "IXHi", "IYLo", "IYHi")


def put(m, slot, b):
	vals = {"XLo": b.x, "XHi": b.x >> 8, "YLo": b.y, "YHi": b.y >> 8, "VXLo": b.vx, "VXHi": b.vx >> 8,
			"VYLo": b.vy, "VYHi": b.vy >> 8, "Size": b.size, "Age": b.age, "Hit": 0,
			"IXLo": 0, "IXHi": 0, "IYLo": 0, "IYHi": 0}
	for k, v in vals.items():
		m.poke(m["Ball" + k] + slot, v & 0xFF)


def get(m, slot):
	g = {k: m.peek(m["Ball" + k] + slot) for k in Fields}
	return {"x": g["XLo"] | g["XHi"] << 8, "y": g["YLo"] | g["YHi"] << 8,
			"vx": g["VXLo"] | g["VXHi"] << 8, "vy": g["VYLo"] | g["VYHi"] << 8,
			"age": g["Age"], "hit": g["Hit"] != 0}


def want(b):
	return {"x": b.x & 0xFFFF, "y": b.y & 0xFFFF, "vx": b.vx & 0xFFFF, "vy": b.vy & 0xFFFF,
			"age": b.age, "hit": b.hit}


def random_scene(rnd):
	balls = []
	for _ in range(rnd.randint(2, 30)):
		s = rnd.choice((1, 1, 2, 2, 3, 3, 4, 4, 5, 6, 7, 8, 9, 9, 10))
		r = RQ[s] / 4
		x = rnd.uniform(WellLeft + r, WellRight - r)
		y = rnd.uniform(r, Floor - r)
		balls.append(Ball(s, round(x * One), round(y * One), rnd.randint(-600, 600), rnd.randint(-600, 600),
						  age=rnd.choice((0, 3, 8, 50, 255))))
	return balls


def edge_scenes():
	"""Size-1 balls at each limit, flung at it: x + vx below 0 at the left wall, y + vy past 65535 at the
	floor, below 0 at the screen's top, and the right wall at full speed. (With x from the well's left, D18,
	the right wall is 128 units, and x + vx can't pass 65535 there: under 128 + 128 units.)"""
	w, r = WQ[1] << 6, RQ[1] << 6
	right, left, floor = WellRight * One - w, WellLeft * One + w, Floor * One - w
	assert right + 32767 <= 0xFFFF and left - 32000 < 0 and floor + 32000 > 0xFFFF and r - 32000 < 0
	return [[Ball(1, right, 100 * One, 32000, 0), Ball(1, left, 100 * One, -32000, 0),
			 Ball(1, 50 * One, floor, 0, 32000), Ball(1, 90 * One, r, 0, -32000)]]


def game_scenes(count, seed, every=40, skip=0):
	"""Snapshots of a bot's game, every `every` frames after the first `skip`."""
	g = Game(seed=seed, params=Params(), hyst_x=2, hyst_y=2)
	bot = Bot(g, seed + 1000)
	screen = Screen()						# (drawing grows the held ball in, which the bot waits for)
	out = []
	for step in range(skip + count * every):
		bot.act()
		if g.step() is None:
			break
		g.draw(screen)
		if step >= skip and step % every == every - 1:
			out.append([Ball(b.size, b.x, b.y, b.vx, b.vy, age=b.age) for b in g.world.order])
	return out


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--scenes", type=int, default=20)
	ap.add_argument("--steps", type=int, default=40)
	ap.add_argument("--seed", type=int, default=1)
	ap.add_argument("--late", action="store_true", help="only game scenes, every 100 frames from frame 300")
	args = ap.parse_args()
	rnd = random.Random(args.seed)
	m = Machine()
	if args.late:
		scenes = game_scenes(args.scenes, args.seed, every=100, skip=300)
	else:
		scenes = (edge_scenes() + [random_scene(rnd) for _ in range(args.scenes)]
				  + game_scenes(args.scenes, args.seed))
	fails = 0
	costs = []
	for n, balls in enumerate(scenes):
		w = World(Params(), "int")
		for slot, b in enumerate(balls):
			b.slot = slot
			w.add(b)
			put(m, slot, b)
			m.poke(m["Order"] + slot, slot)
		m.poke(m["NumBalls"], len(balls))
		for step in range(args.steps):
			merges = w.step()
			cyc = m.call("physics_step")
			costs.append((cyc, len(balls), w.stats.contacts, w.stats.pairs))
			order = [m.peek(m["Order"] + i) for i in range(len(balls))]
			bad = []
			if order != [b.slot for b in w.order]:
				bad.append(f"order {order} want {[b.slot for b in w.order]}")
			for b in w.order:
				got, exp = get(m, b.slot), want(b)
				if got != exp:
					bad.append(f"slot {b.slot} size {b.size}: got {got} want {exp}")
			nm = m.peek(m["NumMerges"])
			gm = [(m.peek(m["MergeA"] + i), m.peek(m["MergeB"] + i)) for i in range(nm)]
			wm = [(a.slot, b.slot) for a, b in merges][:16]
			if gm != wm:
				bad.append(f"merges {gm} want {wm}")
			if bad:
				fails += 1
				print(f"FAIL scene {n} step {step}: " + "; ".join(bad[:3]))
				break
	print(f"{len(scenes) - fails}/{len(scenes)} scenes match the model for {args.steps} steps each")
	cyc = [c for c, _, _, _ in costs]
	print(f"  a step: median {pct(cyc, 0.5)}, 95% {pct(cyc, 0.95)}, max {max(cyc)} cycles; "
		  f"balls median {pct([b for _, b, _, _ in costs], 0.5)}, contacts median {pct([c for _, _, c, _ in costs], 0.5)}")
	# a rough fit: cycles = base + per ball + per pair + per contact
	import numpy as np
	A = np.array([[1, b, p - c, c] for _, b, c, p in costs], dtype=float)
	y = np.array(cyc, dtype=float)
	coef, *_ = np.linalg.lstsq(A, y, rcond=None)
	print(f"  fit: {coef[0]:.0f} + {coef[1]:.0f} a ball + {coef[2]:.0f} a pair not touching + "
		  f"{coef[3]:.0f} a contact")
	sys.exit(1 if fails else 0)


if __name__ == "__main__":
	main()
