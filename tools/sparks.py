"""Sparks: the ring of particles a merge throws out, after the original's (P21).

Each merge's new ball throws a spark each way of 8, one every 45 degrees, from its edge. They slow by
1/8 a frame (rounded toward 0), drift down if Gravity's on, and go after 13 to 20 frames, or on leaving
the well. A spark is a pixel two lines tall, in the ball's colours as its stipple has them there.

Each frame, after the balls, every spark is EORed off with what it was EORed on with last frame, moved,
and EORed on with (the byte EOR its colour) AND its pixel's mask, which it keeps. So it shows its own
colour over anything, and since it's all EOR, the balls' drawing in between doesn't matter: off and on
always leave the screen as the balls alone. (Two sparks on one pixel can show the wrong colour for a
frame.) A new spark's kept values are 0, so it isn't EORed off before it's first on.

16 slots (the loader's tables, in the 6502): a merge's ring takes the free ones from the first, while there
are any.

A spark's place is in quarters of a unit, across from the well's left and down. The 6502 keeps units and
quarters in two bytes, so a place wraps at 256 units; a new spark keeps the quarters its slot had. Its
speed is in quarters of a unit a frame, signed.
"""

from colours import colour_bytes
from layout import FloorLine, WellCol

Slots = 16
# By direction (0 right, then clockwise, y down): each speed's code, 0, a, d, -a or -d, where a is the
# speed along an axis and d the diagonals' 3/4 of it; and the spark's life, in frames
DirX = (1, 2, 0, 4, 3, 4, 0, 2)
DirY = (0, 2, 1, 2, 0, 4, 3, 4)
DirLife = (13, 16, 19, 14, 17, 20, 15, 18)
Gravity = 0								# quarters of a unit a frame, added each frame (0 or 1: Rich, trying it off)


def eighth(v):
	"""v / 8, rounded toward 0."""
	return (v + 7) >> 3 if v < 0 else v >> 3


class Spark:
	__slots__ = ("x", "y", "vx", "vy", "life", "even", "odd", "kept")

	def __init__(self):
		self.x = self.y = self.vx = self.vy = self.life = self.even = self.odd = 0
		self.kept = (0, 0)				# what it was EORed on with, on its even line and the odd


class Sparks:
	def __init__(self):
		self.s = [Spark() for _ in range(Slots)]

	def live(self):
		return sum(1 for s in self.s if s.life)

	def throw(self, size, xu, yu, r):
		"""A merge's ring, from its ball's centre (units) and drawn radius r: thrown at r / 2 units a frame
		(2r quarters) from r out (half the speed in units), into the free slots from the first."""
		a = 2 * r
		d = a - (a >> 2)
		speed = (0, a, d, -a, -d)
		even, odd = colour_bytes(size)
		slot = 0
		for i in reversed(range(len(DirX))):
			while slot < Slots and self.s[slot].life:
				slot += 1
			if slot == Slots:
				return
			s = self.s[slot]
			s.life, s.even, s.odd, s.kept = DirLife[i], even, odd, (0, 0)
			s.vx, s.vy = speed[DirX[i]], speed[DirY[i]]
			s.x = ((xu + (s.vx >> 1)) & 0xFF) << 2 | s.x & 3
			s.y = ((yu + (s.vy >> 1)) & 0xFF) << 2 | s.y & 3

	@staticmethod
	def at(s):
		"""Its byte column, its even line, and its pixel's mask."""
		xu = s.x >> 2
		return WellCol + (xu >> 2), (s.y >> 2) & ~1, 0x55 if xu & 2 else 0xAA

	def frame(self, screen):
		"""Each frame, after the balls: every live spark off, moved, and on, the last slot first."""
		for s in reversed(self.s):
			if not s.life:
				continue
			if s.kept != (0, 0):
				col, line, _ = self.at(s)
				screen.eor(col, line, s.kept[0])
				screen.eor(col, line + 1, s.kept[1])
			s.life -= 1
			if not s.life:
				continue
			s.x = (s.x + s.vx) & 0x3FF
			s.vx -= eighth(s.vx)
			s.y = (s.y + s.vy) & 0x3FF
			s.vy -= eighth(s.vy)
			s.vy += Gravity
			if s.x >> 2 >= 128 or s.y >> 2 >= FloorLine:
				s.life = 0					# past a wall or the floor (or a wrap past 0)
				continue
			col, line, mask = self.at(s)
			k0 = (screen.get(col, line) ^ s.even) & mask
			screen.eor(col, line, k0)
			k1 = (screen.get(col, line + 1) ^ s.odd) & mask
			screen.eor(col, line + 1, k1)
			s.kept = (k0, k1)

	def end(self, screen):
		"""The game's end: every spark off, and gone."""
		for s in self.s:
			if s.life:
				s.life = 1
		self.frame(screen)
