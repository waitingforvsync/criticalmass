"""The whole game in lockstep: the 6502's game_frame against the model's, with the bot's keys, every frame.

	.venv/bin/python tools/lockstep.py [--frames 3000] [--seed 2]

Both start from the same seed (the 6502's Seed is the model's Rng). Each frame the bot decides its keys
from the model; both get them; then every ball (in Order), the game's state (score, held, next, the
dropper, cooldown, grow-in, fail) and the whole screen are compared. Then the frame's cycles: what
game_frame costs, all in (keys, physics, merges, explosions, drawing).
"""

import argparse
import sys

from game import Game
from machine import Machine
from mode2 import ScreenBase, ScreenSize, Screen
from model import Bot, background, pct
from physics import Params
from test_physics import get, want


def bcd(m, addr, n):
	v = 0
	for i in reversed(range(n)):
		b = m.peek(addr + i)
		if b >> 4 > 9 or b & 15 > 9:
			return f"not BCD: &{b:02X}"
		v = v * 100 + (b >> 4) * 10 + (b & 15)
	return v


def state(m):
	return {"score": bcd(m, m["Score"], 3), "held": m.peek(m["Held"]), "next": m.peek(m["Next"]),
			"dropper": m.peek(m["DropperX"]) | m.peek(m["DropperX"] + 1) << 8,
			"cooldown": m.peek(m["Cooldown"]), "grow": m.peek(m["HeldGrow"]), "fail": m.peek(m["Fail"]),
			"over": m.peek(m["Over"]) != 0, "balls": m.peek(m["NumBalls"])}


def model_state(g):
	return {"score": g.score, "held": g.held, "next": g.next, "dropper": g.dropper_x, "cooldown": g.cooldown,
			"grow": g.held_grow, "fail": min(g.fail, 255), "over": g.over, "balls": len(g.world.order)}


def scene_critical(g, m):
	"""A small pile, and two balls a merge from critical mass dropped into it: they merge to critical mass,
	which explodes."""
	from physics import Ball, One, WellLeft
	from shapes import CriticalSize
	big = CriticalSize - 1
	balls = [(2, 30, 200), (3, 60, 196), (1, 90, 205), (4, 110, 190), (2, 48, 180), (3, 80, 175),
			 (big, 40, 40), (big, 100, 60)]
	for slot, (size, x, y) in enumerate(balls):
		b = Ball(size, (WellLeft + x) * One, y * One, age=255)
		g.world.add(b)
		for k, v in (("XLo", b.x), ("XHi", b.x >> 8), ("YLo", b.y), ("YHi", b.y >> 8), ("Size", size),
					 ("Age", 255), ("State", 1)):
			m.poke(m["Ball" + k] + slot, v & 0xFF)
		for k in ("VXLo", "VXHi", "VYLo", "VYHi", "IXLo", "IXHi", "IYLo", "IYHi", "Hit", "Grow"):
			m.poke(m["Ball" + k] + slot, 0)
		m.poke(m["DrawnShape"] + slot, 0)
		m.poke(m["Order"] + slot, slot)
	m.poke(m["NumBalls"], len(balls))


def inject(m, g, size, x, y, vx=0):
	"""A ball into both: the 6502's through its own alloc and add_ball."""
	from physics import Ball
	m.call("alloc")
	assert m.mpu.p & 1, "no free slot"
	slot = m.mpu.x
	for k, v in (("Size", size), ("XLo", x), ("XHi", x >> 8), ("YLo", y), ("YHi", y >> 8), ("Age", 255)):
		m.poke(m["Ball" + k] + slot, v & 0xFF)
	m.mpu.x = slot
	m.call("add_ball")
	m.poke(m["BallVXLo"] + slot, vx & 0xFF)
	m.poke(m["BallVXHi"] + slot, (vx >> 8) & 0xFF)
	g.world.add(Ball(size, x, y, vx, 0, age=255))


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--frames", type=int, default=3000)
	ap.add_argument("--seed", type=int, default=2)
	ap.add_argument("--scene", default="",
					help="critical: a pile and two size-9 balls, no keys; explosions: a pile, two size-9 balls "
						 "every 60 frames, and the bot (after the review's harness)")
	args = ap.parse_args()
	g = Game(seed=args.seed, params=Params())
	bot = Bot(g, args.seed + 1000)
	screen = Screen()
	background(screen)
	m = Machine()
	mem = m.mpu.memory
	mem[ScreenBase:ScreenBase + ScreenSize] = list(screen.mem)
	# the model's Rng before it drew its first two sizes: the 6502 starts from the same
	seed = (args.seed * 7919 + 1) & 0xFFFF or 1
	m.poke(m["Seed"], seed & 0xFF)
	m.poke(m["Seed"] + 1, seed >> 8)
	m.call("new_game")
	if args.scene == "critical":
		scene_critical(g, m)
	elif args.scene == "explosions":
		import random
		from physics import Floor, One, WellLeft
		rnd = random.Random(4)
		for i in range(14):
			inject(m, g, rnd.choice((1, 2, 3, 4)), round((WellLeft + 10 + (i * 37) % 110) * One),
				   round((Floor - 12 - (i // 6) * 22) * One))
	g.draw(screen)						# the model's first drawing: the held ball and the next
	keys0 = 0
	m.poke(m["Keys"], keys0)
	m.call("draw_frame")				# and the 6502's
	costs = []
	import random
	via_rnd = random.Random(args.seed * 31 + 7)
	for frame in range(args.frames):
		if args.scene == "explosions" and frame % 60 == 10 and len(g.world.order) < 36:
			from physics import One, WellLeft
			from shapes import CriticalSize
			inject(m, g, CriticalSize - 1, round((WellLeft + 32) * One), round(40 * One))
			inject(m, g, CriticalSize - 1, round((WellLeft + 96) * One), round(40 * One), vx=-One // 2)
		keys = 0 if args.scene == "critical" else bot.decide()
		via = via_rnd.randrange(256)		# the system VIA's T1 low byte, as the drop reads it
		m.poke(0xFE44, via)
		g.keys(keys, via)
		g.step()
		g.draw(screen)
		m.poke(m["Keys"], keys)
		costs.append(m.call("game_frame"))
		bad = []
		got, exp = state(m), model_state(g)
		if got != exp:
			bad.append(f"state {got} want {exp}")
		order = [m.peek(m["Order"] + i) for i in range(m.peek(m["NumBalls"]))]
		for i, b in enumerate(g.world.order):
			if i >= len(order):
				break
			slot = order[i]
			gb = get(m, slot)
			wb = want(b)
			gb["size"], wb["size"] = m.peek(m["BallSize"] + slot), b.size
			if gb != wb:
				bad.append(f"ball {i} (slot {slot}): got {gb} want {wb}")
				break
		if bytes(mem[ScreenBase:ScreenBase + ScreenSize]) != bytes(screen.mem):
			diff = [i for i in range(ScreenSize) if mem[ScreenBase + i] != screen.mem[i]]
			bad.append(f"screen: {len(diff)} bytes, first &{ScreenBase + diff[0]:04X}")
		if bad:
			print(f"FAIL frame {frame} (keys {keys}): " + "; ".join(bad[:3]))
			sys.exit(1)
		if g.over:
			break
	print(f"{len(costs)} frames in lockstep: balls, state and screen matched the model every frame; "
		  f"score {g.score}, {g.merges} merges, {g.explosions} explosions{', game over' if g.over else ''}")
	print(f"  game_frame: median {pct(costs, 0.5)}, 90% {pct(costs, 0.9)}, 95% {pct(costs, 0.95)}, "
		  f"max {max(costs)} cycles; over 80,000: {sum(c > 80000 for c in costs)}")
	print(f"  stack: {m.stack_depth} bytes at most (of 64; the IRQ adds 9), the return address included")


if __name__ == "__main__":
	main()
