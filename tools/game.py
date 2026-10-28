"""The game around the physics: the dropper, merges, critical mass, failing, the score, and the drawing.

Times are in steps at 25 Hz; the original's frame counts at 60 Hz are converted (x 25/60).
"""

import math
import random
from dataclasses import dataclass, field

from colours import SizeColours
from physics import Ball, Floor, One, Params, Rim, Stats, WellLeft, WellRight, World
from render import ball_bytes
from shapes import CriticalSize, make_shapes, physics_radius
from tables import WQ
from font import draw_text, score_text
from layout import BestLine, LabelCol, NextX, NextY, ScoreLine

DropSizes = (1, 2, 3, 4, 5)			# sizes 1 to 5 now span what 1 to 4 did before 12 sizes
PatternCount = 8
DropCooldown = 8						# the original's 20 frames
FailSteps = 50							# the original's 120 frames
CriticalHold = 6						# steps the critical ball shows before it explodes
HoldWait = 50							# frames the held ball waits at most for the last drop to fall clear
CriticalBonus = 100
ChainSteps = 75							# merges this soon after an explosion are a chain
MaxBalls = 48
DropperSpeed = round(7.68 * One)		# 8.8 units a frame: the original's 2 px a frame
SlowSpeed = round(1.152 * One)			# with the slow key: the original's 0.3 px a frame

# The keys, as the 6502 reads them into a byte
KeyLeft, KeyRight, KeySlow, KeyDrop = 1, 2, 4, 8


class Rng:
	"""A 16-bit Galois LFSR (taps &B400), eight shifts a byte: the 6502's random."""

	def __init__(self, seed=0xACE1):
		self.s = seed & 0xFFFF or 1

	def byte(self):
		for _ in range(8):
			out = self.s & 1
			self.s >>= 1
			if out:
				self.s ^= 0xB400
		return self.s & 0xFF


@dataclass
class Piece:
	size: int
	dx: int								# 8.8 units from the critical ball's centre, in half units (PieceDX)
	dy: int
	vx: int								# 8.8 units a 25 Hz frame, in eighths (PieceVX): each fits a byte
	vy: int


def make_patterns(count=PatternCount, seed=7):
	"""Explosion patterns: sizes 1 to 4 packed inside the critical ball without touching, moving out."""
	rnd = random.Random(seed)
	R = physics_radius(CriticalSize)
	big = math.pi * R * R
	patterns = []
	while len(patterns) < count:
		# a mix of sizes, the largest placed first so they find room
		mix = [4] * rnd.randint(1, 2) + [3] * rnd.randint(1, 2) + [2] * rnd.randint(1, 3) + [1] * rnd.randint(1, 2)
		pieces = []
		for s in mix:
			r = physics_radius(s)
			for _ in range(400):
				a = rnd.uniform(0, 2 * math.pi)
				d = rnd.uniform(0, R - r - 0.5)
				x, y = round(2 * d * math.cos(a)) / 2, round(2 * d * math.sin(a)) / 2
				if all(math.hypot(x - p.dx / One, y - p.dy / One) >= r + physics_radius(p.size) + 1 for p in pieces):
					speed = 1.5 + 4.0 * d / R
					pieces.append(Piece(s, round(x * One), round(y * One), round(8 * speed * math.cos(a)) * 32,
										round(8 * (speed * math.sin(a) - 3.0)) * 32))
					break
		area = sum(math.pi * physics_radius(p.size) ** 2 for p in pieces)
		if len(pieces) == len(mix) and 0.35 * big <= area <= 0.7 * big:
			patterns.append(pieces)
	return patterns


@dataclass
class Frame:
	"""What one step cost, for the budget."""
	physics: Stats
	balls: int
	drawn: int = 0						# balls whose drawing changed
	columns: int = 0					# byte columns the plotter walked
	bytes: int = 0						# bytes it wrote


class Game:
	def __init__(self, seed=1, params=None, mode="int", hyst_x=2, hyst_y=2):
		self.rnd = Rng(seed * 7919 + 1)
		self.via_rnd = random.Random(seed)		# the VIA's T1, for runs of the model alone
		self.via = 0
		self.world = World(params or Params(), mode)
		self.shapes = make_shapes()
		self.patterns = make_patterns()
		self.hyst_x, self.hyst_y = hyst_x, hyst_y
		self.score = 0
		self.step_no = 0
		self.fail = 0
		self.over = False
		self.held = self.drop_size()
		self.next = self.drop_size()
		self.released = True				# the drop key's been let go since the last drop
		self.dropper_x = (WellLeft + WellRight) // 2 * One
		self.cooldown = 0
		self.critical = []				# (ball, steps left)
		self.chain_left = 0						# frames of a chain left: merges then multiply
		self.chain = 0
		self.explosions = 0
		self.merges = 0
		self.dying = []					# balls gone, still drawn
		self.held_ball = Ball(self.held, 0, 0)
		self.next_ball = Ball(self.next, 0, 0)
		self.held_grow = self.held
		self.last_drop = None
		self.hold_left = 0						# frames the held ball may still wait for it
		self.events = []
		self.best = 0							# shown in the panel
		self.shown = None						# the score and best last drawn

	# --- the player's side ---

	def drop_size(self):
		"""1 to 5, evenly: a byte's low 3 bits, again while they're 5 or more."""
		while True:
			v = self.rnd.byte() & 7
			if v < len(DropSizes):
				return v + 1

	def keys(self, keys, via=None):
		"""A frame's keys: move the dropper, and drop. via: the system VIA's T1 low byte as the 6502 reads it
		(a drop's random fraction); a run of the model alone makes its own."""
		self.via = self.via_rnd.randrange(256) if via is None else via
		speed = SlowSpeed if keys & KeySlow else DropperSpeed
		if keys & KeyLeft:
			self.dropper_x -= speed
		if keys & KeyRight:
			self.dropper_x += speed
		self.clamp_dropper()
		if keys & KeyDrop:
			if self.released and self.drop():
				self.released = False
		else:
			self.released = True

	def held_y(self, size):
		"""The held ball's centre, 8.8: resting on the rim."""
		return Rim * One - (WQ[size] << 6)	# (the drawn radius: what's seen)

	def dropper_limits(self):
		r = WQ[self.held] << 6
		return WellLeft * One + r + One, WellRight * One - r - One

	def clamp_dropper(self):
		lo, hi = self.dropper_limits()
		self.dropper_x = min(max(self.dropper_x, lo), hi)

	def move_dropper(self, target):
		"""Move towards target (units); True once there."""
		lo, hi = self.dropper_limits()
		target = min(max(round(target * One), lo), hi)
		step = max(-DropperSpeed, min(DropperSpeed, target - self.dropper_x))
		self.dropper_x += step
		return abs(target - self.dropper_x) < One // 2

	def drop(self):
		if self.cooldown > 0 or self.held_grow < self.held or len(self.world.order) >= MaxBalls - 10:
			return False
		v = self.rnd.byte() ^ self.via		# a random fraction, -0.5 to 0.5 units, so drops at one place
		x = self.dropper_x + v - (v & 0x80) * 2	# don't stack exactly balanced (the VIA's T1 and the LFSR)
		b = Ball(self.held, x, self.held_y(self.held), age=255)
		self.world.add(b)
		self.last_drop = b
		self.hold_left = HoldWait
		self.held = self.next
		self.next = self.drop_size()
		self.clamp_dropper()
		self.cooldown = DropCooldown
		return True

	# --- a step ---

	def step(self):
		if self.over:
			return None
		w = self.world
		total = Stats()
		substeps = max(1, w.p.rate // 25)
		for k in range(substeps):
			w.step()
			total.add(w.stats)
			if k < substeps - 1:
				self.merge(w.merges)
		w.stats = total
		self.after_step()
		return total

	def after_step(self):
		"""The game's side of a frame, once the world has taken its (last) step."""
		self.step_no += 1
		self.cooldown = max(0, self.cooldown - 1)
		self.chain_left = max(0, self.chain_left - 1)
		self.merge(self.world.merges)
		self.explode()
		self.update_fail()

	def merge(self, merges):
		w = self.world

		# merges: each ball once, the new one at the midpoint and at rest, as the original
		for a, b in merges:
			if a.dead or b.dead:
				continue
			a.dead = b.dead = True
			w.order.remove(a)
			w.order.remove(b)
			self.dying += [a, b]
			size = a.size + 1
			c = Ball(size, (a.x + b.x) // 2, (a.y + b.y) // 2, grow=2)
			w.clamp(c)							# (a bigger ball at the midpoint may reach a wall)
			w.add(c)
			chained = self.chain_left > 0
			self.chain = self.chain + 1 if chained else 0
			self.score += a.size * (1 + self.chain)
			self.merges += 1
			if size == CriticalSize:
				c.grow = 0
				self.critical.append([c, CriticalHold + 1])

	def explode(self):
		"""Critical balls explode after showing for CriticalHold frames."""
		w = self.world
		shift = {25: 0, 50: 1}[w.p.rate]	# the patterns' velocities are a 25 Hz frame's
		for entry in list(self.critical):
			c, left = entry
			entry[1] -= 1
			if entry[1] > 0:
				continue
			self.critical.remove(entry)
			if c.dead:
				continue
			c.dead = True
			w.order.remove(c)
			self.dying.append(c)
			pattern = self.patterns[self.rnd.byte() & (PatternCount - 1)]
			for p in pattern:
				piece = Ball(p.size, c.x + p.dx, c.y + p.dy, p.vx >> shift, p.vy >> shift)
				w.clamp(piece)
				w.add(piece)
			self.score += CriticalBonus
			self.explosions += 1
			self.chain_left = ChainSteps + 1
			self.events.append(("explode", self.step_no))

	def update_fail(self):
		w = self.world
		# failing: a ball poking above the rim while touching another, for FailSteps
		any_failing = False
		for b in w.order:
			if b.hit and b.y - (WQ[b.size] << 6) < Rim * One:	# its drawn top
				b.failing += 1
				any_failing = True
			else:
				b.failing = 0
		self.fail = self.fail + 1 if any_failing else 0
		if self.fail > FailSteps:
			self.over = True

	# --- drawing ---

	def target(self, shape, colour, cx, cy):
		"""Where a ball is drawn: (shape, colour, left pixel, top line), from its centre in units."""
		sh = self.shapes[shape]
		px = (int(cx) - sh.width + 1) >> 1
		line = (2 * int(cy) - sh.height + 1) >> 1
		return (shape, colour, px, line)

	def held_shape(self):
		"""The held ball's shape, or 0 while hidden: it comes back once the last drop has fallen clear
		of it (for HoldWait frames at most: one resting just under the rim mustn't hide it for ever, as
		hidden it can't be dropped), then grows in through the smaller shapes, a step each."""
		last = self.last_drop
		if last is not None and not last.dead and self.hold_left > 0:
			self.hold_left -= 1
			if last.y - (WQ[last.size] << 6) < (Rim + 2) * One:
				self.held_grow = 0
				return 0
		self.held_grow = min(self.held, self.held_grow + 1)
		return self.held_grow

	def draw(self, screen):
		"""Bring the screen up to date, as the plotter would, and count the cost."""
		f = Frame(self.world.stats, len(self.world.order))

		def move(b, new):
			old = b.drawn
			if old == new:
				return
			a = ball_bytes(self.shapes[old[0]], old[2], old[3], old[1]) if old else {}
			c = ball_bytes(self.shapes[new[0]], new[2], new[3], new[1]) if new else {}
			changed = {k for k in a.keys() | c.keys() if a.get(k, 0) != c.get(k, 0)}
			for col, y in changed:
				screen.eor(col, y, a.get((col, y), 0) ^ c.get((col, y), 0))
			cols = {k[0] for k in a} | {k[0] for k in c}
			f.drawn += 1
			f.columns += len(cols)
			f.bytes += len(changed)
			b.drawn = new

		for b in self.dying:
			move(b, None)
		self.dying = []
		for b in self.world.order:
			shape = b.size - 1 if b.grow > 0 else b.size
			b.grow = max(0, b.grow - 1)
			xu, yu = b.x >> 8, b.y >> 8
			if b.drawn is not None and b.drawn[0] == shape and b.drawn[1] == b.size:
				ax, ay = b.anchor
				if abs(xu - ax) < self.hyst_x and abs(yu - ay) < self.hyst_y:
					continue
			b.anchor = (xu, yu)
			move(b, self.target(shape, b.size, xu, yu))
		# the held ball, over the rim
		hb = self.held_ball
		shape = 0 if self.over else self.held_shape()
		move(hb, self.target(shape, self.held, self.dropper_x >> 8, self.held_y(self.held) >> 8) if shape else None)
		# the next, in the panel
		move(self.next_ball, self.target(self.next, self.next, NextX, NextY))
		# the score and the best, when they've changed
		if self.shown != (self.score, self.best):
			draw_text(screen, score_text(self.score), LabelCol, ScoreLine)
			draw_text(screen, score_text(self.best), LabelCol, BestLine)
			self.shown = (self.score, self.best)
		return f
