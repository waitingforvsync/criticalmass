"""The integer tables the physics uses, exactly as the 6502 will have them (P3).

Quarter units: the collision test works in quarter units (a quarter of a scanline), with |dx|, |dy| and R
each in a byte. That holds while R = r0 + r1 < 64 units; pair_r caps the critical ball's pairs there.

Logs are 32nds of an octave: L(v) = round(32 log2 v). A push comes out of EXP in 32nds of a unit.
"""

import math

from shapes import CriticalSize, draw_radius, physics_radius

LogScale = 32							# log steps an octave

# Squares: SQ[v] = v * v for v in 0..255, from the quarter-square table (multab[2v] = v*v)
SQ = [v * v for v in range(256)]

# L8[v] = round(32 log2 v), v in 1..255 (L8[0] unused). The top few round to 256: clamp to 255.
L8 = [0] + [min(255, round(LogScale * math.log2(v))) for v in range(1, 256)]

# EXP[L] = round(2 ** (L / 32)), L in 0..255: a push in 32nds of a unit
EXP = [round(2 ** (L / LogScale)) for L in range(256)]


# H[D] = round(32 * log2(1 + 2^(-2D/32)) / 2): log d from the logs of |dx| and |dy|, D their difference:
# log d = log max + H[log max - log min] (log sqrt(a^2 + b^2) = log a + log sqrt(1 + (b/a)^2))
H = [round(LogScale * 0.5 * math.log2(1 + 2 ** (-2 * D / LogScale))) for D in range(256)]


def log_d(lx, ly):
	"""log d from L8 of |dx| and |dy| (None for a zero), as the 6502 does it."""
	if lx is None:
		return ly
	if ly is None:
		return lx
	hi, lo = max(lx, ly), min(lx, ly)
	return hi + H[hi - lo]


def log16(v):
	"""L of a 16-bit value, as the 6502 does it: the top 8 significant bits through L8, plus 32 an
	octave shifted off."""
	assert 0 < v < 65536
	n = max(0, v.bit_length() - 8)
	return LogScale * n + L8[v >> n]


def exp_clamped(L):
	if L < 0:
		return 0
	return EXP[min(L, 255)]


# Radii in quarter units, by size: RQ the physics radius (collisions, the sort, the sweep, the screen's
# top), WQ the drawn one (the walls and the floor, which are hard: no reason to stop short of them)
RQ = [0] * (CriticalSize + 1)
WQ = [0] * (CriticalSize + 1)

# The weight of a ball is its radius, as in the original. C[a][b] is the log constant for the push on a
# ball of size a from one of size b. The push is the unit vector times the overlap, the overlap taken as
# (R^2 - d^2) / 2R (exact at contact, half the truth when the balls coincide), all in quarter units:
#   push32 = (|dx|q / dq) * (diff / 2Rq) / 4 * share * 32 = |dx|q * diff * share * 4 / (dq * Rq)
#   L(push32) = L8[|dx|q] + log16(diff) - log16(d2) / 2 + C[a][b], C = 32 (log2 share + 2 - log2 Rq)
C = [[0] * (CriticalSize + 1) for _ in range(CriticalSize + 1)]


def pair_r(a, b):
	"""R for a pair, quarter units: it has to fit a byte, so a pair with the critical ball may be a little
	short (it's there for only a few frames)."""
	return min(255, RQ[a] + RQ[b])


def build():
	"""Fill RQ, WQ and C from the shapes' radii (in place: the physics holds these lists)."""
	for s in range(1, CriticalSize + 1):
		RQ[s] = round(4 * physics_radius(s))
		WQ[s] = round(4 * draw_radius(s))
	for a in range(1, CriticalSize + 1):
		for b in range(1, CriticalSize + 1):
			share = RQ[b] / (RQ[a] + RQ[b])
			C[a][b] = round(LogScale * (math.log2(share) + 2 - math.log2(pair_r(a, b))))


build()
