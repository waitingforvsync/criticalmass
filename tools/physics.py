"""The physics, as the 6502 will do it: the original's soft pushes, in 8.8 fixed point at 25 Hz.

Units are scanlines (half a MODE 2 pixel), measured from the screen's top-left corner. A step:

1. Integrate: vy += gravity; x += vx; y += vy; clamp to the walls and floor, bouncing at half speed.
2. Sort `order` by bottom edge, lowest on the screen first (an insertion sort: it's nearly sorted).
3. Sweep: each ball against those after it, until one's bottom is above this one's top.
   - A pair is out if |dx| or |dy| >= R, or dx^2 + dy^2 >= R^2: the squares are exact, in quarter units.
   - Otherwise the push is (dx, dy)/d * (R^2 - d^2)/2R, split by weight (P3): the unit vector times the
     overlap, which (R^2 - d^2)/2R is near contact. In `int` mode that's done with the log tables, log d
     from the logs of |dx| and |dy| (tables.log_d); in `float` mode exactly.
4. Apply each ball's summed push: kp of it to the position, kv to the velocity.
5. Merge touching pairs of the same size that are both old enough.

`mode='float'` is the same scheme with exact arithmetic: the yardstick for `int`.
"""

import math
from dataclasses import dataclass, field

from shapes import CriticalSize, physics_radius
from tables import C, EXP, L8, RQ, SQ, WQ, exp_clamped, log16, log_d, pair_r

One = 256								# 8.8 fixed point

# The well, in units from the screen's top-left: byte columns 2 to 33 inside, the floor at row 27
WellLeft = 2 * 4
WellRight = WellLeft + 128
Floor = 27 * 8
Rim = 32								# a ball whose top is above this, touching another, is failing


@dataclass
class Params:
	rate: int = 25						# steps a second: one a 25 fps frame
	gravity: float = 288.0				# units/s^2: the original's 0.05 px/frame^2 at 60 Hz, 1.6 units a px
	kp: float = 0.7						# share of the summed push applied to position
	kv: float = 0.75					# and to velocity: about twice the original's, so piles squash less
	passes: int = 2						# sweeps a step
	reuse: bool = True					# later passes revisit only the pairs that touched in the first
	deep: int = 0						# ... and only those overlapping this deep or more: diff >= deep * R
	max_near: int = 160					# ... and only the first this many (the 6502's MaxNear; capping it
										# lower shakes the pile: tried 16-32)
	bounce: float = 0.5
	merge_age: int = 4					# steps before a new ball can merge (the original's 10 at 60 Hz)

	def gravity_raw(self):
		return round(self.gravity / (self.rate * self.rate) * One)


@dataclass
class Ball:
	size: int
	x: int								# 8.8, units
	y: int
	vx: int = 0
	vy: int = 0
	age: int = 0
	hit: bool = False
	failing: int = 0
	ix: float = 0						# summed push: 32nds of a unit (int mode) or units (float)
	iy: float = 0
	dead: bool = False
	slot: int = -1
	drawn: object = None				# what the renderer last drew: (shape, colour, px, line) or None
	anchor: tuple = (0, 0)				# the position (units) it was drawn from: the hysteresis' centre
	grow: int = 0						# steps it's still drawn a size smaller: a merge's animation

	@property
	def rq(self):
		return RQ[self.size]

	@property
	def r(self):
		return self.rq / 4


@dataclass
class Stats:
	pairs: int = 0						# sweep iterations
	box_out: int = 0					# out by |dx| or |dy|
	d2_out: int = 0						# out by d^2
	contacts: int = 0
	compares: int = 0					# insertion sort
	swaps: int = 0
	merges: int = 0

	def add(self, other):
		for k in self.__dataclass_fields__:
			setattr(self, k, getattr(self, k) + getattr(other, k))


class World:
	def __init__(self, params=None, mode="int"):
		self.p = params or Params()
		self.mode = mode
		self.order = []					# live balls, sorted by bottom edge, lowest first
		self.merges = []				# (a, b) found this step
		self.stats = Stats()

	def add(self, ball):
		self.order.append(ball)

	# --- 1. integrate ---

	def integrate(self):
		g = self.p.gravity_raw()
		for b in self.order:
			r = WQ[b.size] << 6			# quarter units -> 8.8: the walls and floor at the drawn radius
			b.vy += g
			assert -32768 <= b.vy < 32768, "the 6502's velocities are 16 bits, signed"
			b.x += b.vx
			b.y += b.vy
			if b.y + r > Floor * One:
				b.y = Floor * One - r
				b.vy = -self.half(abs(b.vy))
			if b.y < b.rq << 6:				# the screen's top: only pieces flung up get there
				b.y = b.rq << 6
				b.vy = self.half(abs(b.vy))
			if b.x < WellLeft * One + r:
				b.x = WellLeft * One + r
				b.vx = self.half(abs(b.vx))
			if b.x + r > WellRight * One:
				b.x = WellRight * One - r
				b.vx = -self.half(abs(b.vx))
			assert 0 <= b.x < 65536 and 0 <= b.y < 65536

	def half(self, v):
		return int(v * self.p.bounce)

	# --- 2. sort ---

	def sort(self):
		st = self.stats
		o = self.order
		for i in range(1, len(o)):
			b = o[i]
			key = b.y + (b.rq << 6)
			j = i - 1
			while j >= 0:
				st.compares += 1
				if o[j].y + (o[j].rq << 6) >= key:
					break
				o[j + 1] = o[j]
				st.swaps += 1
				j -= 1
			o[j + 1] = b

	# --- 3. sweep ---

	def sweep(self):
		st = self.stats
		o = self.order
		n = len(o)
		self.near = []
		for i in range(n):
			a = o[i]
			top = (a.y - (a.rq << 6)) >> 8
			for j in range(i + 1, n):
				b = o[j]
				if (b.y + (b.rq << 6)) >> 8 < top:
					break
				st.pairs += 1
				self.pair(a, b)

	def resweep(self):
		for a, b in self.near:
			self.stats.pairs += 1
			self.pair(a, b, again=True)

	def pair(self, a, b, again=False):
		st = self.stats
		if a.size >= CriticalSize and b.size >= CriticalSize:
			return						# two critical balls (R would pass 255): let them be
		dx = a.x - b.x
		dy = a.y - b.y
		R = pair_r(a.size, b.size)
		adx, ady = abs(dx), abs(dy)
		qx, qy = (adx + 32) >> 6, (ady + 32) >> 6	# quarter units, rounded
		if qx >= R or qy >= R:					# (R is at most 255: past it is always out)
			st.box_out += 1
			return
		if qx == 0 and qy == 0:
			# on top of each other (clamped into the same corner): push apart up and down
			qy = 1
			dy = 1
		if self.mode == "int":
			d2 = SQ[qx] + SQ[qy]
			R2 = SQ[R]
			if d2 >= R2:
				st.d2_out += 1
				return
			diff = R2 - d2
			lx = L8[qx] if qx else None
			ly = L8[qy] if qy else None
			ld = log16(diff) - log_d(lx, ly)
			sa = ld + C[a.size][b.size]
			sb = ld + C[b.size][a.size]
			pax = exp_clamped(sa + lx) if lx is not None else 0
			pay = exp_clamped(sa + ly) if ly is not None else 0
			pbx = exp_clamped(sb + lx) if lx is not None else 0
			pby = exp_clamped(sb + ly) if ly is not None else 0
		else:
			fx, fy = dx / One, dy / One
			if fx == 0 and fy == 0:
				fy = 1 / 4
			Rf = pair_r(a.size, b.size) / 4
			d2 = fx * fx + fy * fy
			if d2 >= Rf * Rf:
				st.d2_out += 1
				return
			k = (Rf * Rf - d2) / (2 * Rf * math.sqrt(d2))
			wa, wb = a.rq, b.rq
			pax = abs(fx) * k * wb / (wa + wb)
			pay = abs(fy) * k * wb / (wa + wb)
			pbx = abs(fx) * k * wa / (wa + wb)
			pby = abs(fy) * k * wa / (wa + wb)
		st.contacts += 1
		a.hit = b.hit = True
		if (not again and (self.mode != "int" or diff >= self.p.deep * R)
				and len(self.near) < self.p.max_near):
			self.near.append((a, b))		# the second pass revisits the pairs that touched (deep enough)
		if dx >= 0:
			a.ix += pax
			b.ix -= pbx
		else:
			a.ix -= pax
			b.ix += pbx
		if dy >= 0:
			a.iy += pay
			b.iy -= pby
		else:
			a.iy -= pay
			b.iy += pby
		if (not again and a.size == b.size and a.size < CriticalSize and a.age >= self.p.merge_age
				and b.age >= self.p.merge_age and len(self.merges) < 16):	# (the 6502's MaxMerges)
			self.merges.append((a, b))

	# --- 4. apply ---

	def clamp(self, b):
		"""Inside the well after the pushes too: the drawing must never leave it."""
		r = WQ[b.size] << 6
		b.x = min(max(b.x, WellLeft * One + r), WellRight * One - r)
		b.y = min(max(b.y, b.rq << 6), Floor * One - r)

	def apply(self):
		for b in self.order:
			if self.mode == "int":
				# pushes are 32nds of a unit, so 8.8 is 8 times that: x += ix * 8 * kp16 / 16, the
				# shift flooring as the 6502's would
				kp16, kv16 = round(self.p.kp * 16), round(self.p.kv * 16)
				assert all(-32768 <= v * kp16 < 32768 for v in (b.ix, b.iy)), "the 6502's t * kp16 is 16 bits"
				b.x += (b.ix * kp16) >> 1
				b.y += (b.iy * kp16) >> 1
				b.vx += (b.ix * kv16) >> 1
				b.vy += (b.iy * kv16) >> 1
			else:
				kp, kv = round(self.p.kp * 16) / 16, round(self.p.kv * 16) / 16
				b.x += round(b.ix * One * kp)
				b.y += round(b.iy * One * kp)
				b.vx += round(b.ix * One * kv)
				b.vy += round(b.iy * One * kv)
			b.ix = b.iy = 0
			assert -32768 <= b.vx < 32768 and -32768 <= b.vy < 32768, "the 6502's velocities are 16 bits, signed"
			self.clamp(b)

	# --- the step ---

	def step(self):
		self.stats = Stats()
		self.merges = []
		self.integrate()
		for b in self.order:
			b.hit = False
		for k in range(self.p.passes):
			if k == 0 or not self.p.reuse:
				self.sort()
				self.sweep()
			else:
				self.resweep()
			self.apply()
		for b in self.order:
			b.age = min(255, b.age + 1)
		return self.merges
