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

# Drawn radius for each size, in units: the original's 0.8 + 2s at 1.6 units a PICO-8 pixel, so its
# 80-pixel board is our 128-unit well. Size CriticalSize explodes (D8, P4).
CriticalSize = 10
MaxSize = CriticalSize

Margin = 0.75							# units the physics circle is outside the drawn one (3 quarter units)


def draw_radius(size):
	return 1.6 * (0.8 + 2 * size)


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
	shape = Shape(size, radius, w, h, spans)
	for p in (0, 1):
		shape.runs[p] = column_runs(spans, h, p)
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
	radius_fn = radius_fn or draw_radius
	return {s: best_shape(s, radius_fn(s)) for s in range(1, MaxSize + 1)}


if __name__ == "__main__":
	for s, sh in make_shapes().items():
		print(f"size {s:2d}: r {sh.radius:5.2f}  {sh.width:2d} x {sh.height:2d}  "
			  f"cols p0 {len(sh.runs[0])} p1 {len(sh.runs[1])}  spans {sh.spans}")
