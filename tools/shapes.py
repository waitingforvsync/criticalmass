"""The balls' shapes: a symmetric bitmap for each size, and the run tables the 6502's plotter reads.

Units: 1 unit = 1 scanline = half a MODE 2 pixel (P2). A shape W pixels wide and H lines tall has its
centre at its middle. Pixel i's centre is 2i + 1 - W units from it across, and line j's is j + 0.5 - H/2
down. A pixel is in if its centre is within the drawn radius.

The plotter works in byte columns. For a shape whose left pixel is the left (parity 0) or right (parity 1)
pixel of a byte, each column is: lead lines empty, single lines, full lines, single again, lead again. Each
run has a mask for the pixels it sets (&AA left, &55 right, &FF both): the single run sets only the pixel
with the longer span, and the full run both, or only one in an edge column where the other is empty.
"""

import math
from dataclasses import dataclass, field

# Drawn radius for each size, in units, from the original's 0.8 + 2s at 1.6 units a PICO-8 pixel (its
# 80-pixel board is our 128-unit well). Size CriticalSize explodes (D8, P4). Sizes 1 to 10 run in equal
# steps of 2.56 from the original's size 1 (D12: its 9 steps to its size 9 made 11 steps; D27 took the
# largest away, as with it critical mass took near-perfect play). Two of the largest touching must stay
# under 64 units for the collision maths (tables.py). The critical ball is one of the original's steps
# past its size 10.
CriticalSize = 11
MaxSize = CriticalSize
SmallRadius = 1.6 * (0.8 + 2 * 1)		# 4.48
Step = 1.6 * 2 * 8 / 10					# 2.56
CriticalRadius = 1.6 * (0.8 + 2 * 11)	# 36.48

Margin = 0.75							# units the physics circle is outside the drawn one (3 quarter units)

# Shapes drawn by hand where the raster doesn't look round, as (radius, each pixel column's span, height).
# Size 3 (violet) rasterised 9 by 19, its sides 11 lines straight, and looked like a hexagon (Rich): its
# blue pixels are dark, so the eye follows the magenta checker's outline. 10 by 20 reads rounder; its
# radius is the shape's, 10 units (not 9.6), so the physics' margin, the walls and the rim follow it.
Overrides = {3: (10.0, [8, 14, 18, 20, 20, 20, 20, 18, 14, 8], 20)}


def draw_radius(size):
	if size in Overrides:
		return Overrides[size][0]
	if size >= CriticalSize:
		return CriticalRadius
	return SmallRadius + (size - 1) * Step


def physics_radius(size):
	"""The radius balls collide at: a little more than the drawn one, so a squashed pile overlaps less."""
	return draw_radius(size) + Margin


@dataclass
class Shape:
	size: int
	radius: float						# the drawn radius, units
	width: int							# pixels
	height: int							# lines
	spans: list							# lines set in each pixel column, centred
	runs: dict = field(default_factory=dict)	# parity -> [(lead, single, full, smask, fmask)]

	def pixels(self):
		"""The set pixels as (i, j), from the top left."""
		out = []
		for i, span in enumerate(self.spans):
			top = (self.height - span) // 2
			out.extend((i, j) for j in range(top, top + span))
		return out


def raster(radius, width, height):
	"""Each pixel column's span for a circle centred in a width x height box."""
	spans = []
	for i in range(width):
		xu = 2 * i + 1 - width
		span = 0
		for j in range(height):
			yu = j + 0.5 - height / 2
			if xu * xu + yu * yu <= radius * radius:
				span += 1
		spans.append(span)
	return spans


def trim(spans, height):
	"""Drop empty columns from both sides alike, and empty lines from top and bottom alike."""
	while spans and spans[0] == 0 and spans[-1] == 0:
		spans = spans[1:-1]
	tallest = max(spans)
	height = tallest + (height - tallest) % 2		# keep the parity: spans are centred
	return spans, height


def error(radius, width, height, spans):
	"""Area of the symmetric difference with the true circle, sampled 4 x 4 a pixel."""
	bad = 0
	for i in range(width):
		top = (height - spans[i]) // 2
		for j in range(height):
			inside = top <= j < top + spans[i]
			for sx in range(4):
				for sy in range(4):
					xu = 2 * (i + (sx + 0.5) / 4) - width
					yu = j + (sy + 0.5) / 4 - height / 2
					if (xu * xu + yu * yu <= radius * radius) != inside:
						bad += 1
	return bad / 16


def best_shape(size, radius):
	"""The width and height parities that best fit the circle."""
	best = None
	n = 2 * math.ceil(radius) + 4
	for wp in (0, 1):
		for hp in (0, 1):
			w, h = n + wp, n + hp
			spans, h2 = trim(raster(radius, w, h), h)
			w2 = len(spans)
			e = error(radius, w2, h2, spans)
			if best is None or e < best[0]:
				best = (e, w2, h2, spans)
	_, w, h, spans = best
	return shape_from(size, radius, spans, h)


def shape_from(size, radius, spans, height):
	shape = Shape(size, radius, len(spans), height, list(spans))
	for p in (0, 1):
		shape.runs[p] = column_runs(spans, height, p)
	return shape


def column_runs(spans, height, p):
	cols = []
	w = len(spans)
	for k in range((w + p + 1) // 2):
		il, ir = 2 * k - p, 2 * k + 1 - p
		sl = spans[il] if 0 <= il < w else 0
		sr = spans[ir] if 0 <= ir < w else 0
		hi, lo = max(sl, sr), min(sl, sr)
		longer = 0xAA if sl > sr else 0x55
		assert (height - hi) % 2 == 0
		if lo == 0:
			cols.append(((height - hi) // 2, 0, hi, 0xFF, longer))
		else:
			assert (hi - lo) % 2 == 0
			cols.append(((height - hi) // 2, (hi - lo) // 2, lo, longer, 0xFF))
	return cols


def column_pixels(col, height):
	"""A column's runs back as (line, mask) pairs: a check that they cover the shape."""
	lead, single, full, smask, fmask = col
	out = []
	for j in range(single):
		out.append((lead + j, smask))
		out.append((height - 1 - lead - j, smask))
	for j in range(full):
		out.append((lead + single + j, fmask))
	return sorted(out)


def make_shapes(radius_fn=None):
	"""Each size's shape: the best raster of its radius, or the hand-drawn one (Overrides, for the drawn
	radius only)."""
	overrides = Overrides if radius_fn is None else {}
	radius_fn = radius_fn or draw_radius
	return {s: shape_from(s, *overrides[s]) if s in overrides else best_shape(s, radius_fn(s))
			for s in range(1, MaxSize + 1)}


if __name__ == "__main__":
	for s, sh in make_shapes().items():
		print(f"size {s:2d}: r {sh.radius:5.2f}  {sh.width:2d} x {sh.height:2d}  "
			  f"cols p0 {len(sh.runs[0])} p1 {len(sh.runs[1])}  spans {sh.spans}")
