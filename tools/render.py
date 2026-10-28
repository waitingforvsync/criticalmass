"""Drawing balls into the screen model as the 6502's plotter will: by EOR, from the run tables.

A ball is drawn at (px, line): its shape's top-left pixel, in screen pixels and lines. Drawing it again in
the same place takes it away. Moving it is drawing the old and the new once each; the plotter does both
in one pass and skips the bytes where they agree, which `delta_bytes` counts.
"""

from colours import colour_bytes
from mode2 import Columns, Lines


def ball_bytes(shape, px, line, size):
	"""{(col, line): byte} for a ball, built from its run table."""
	out = {}
	p = px & 1
	col0 = px >> 1
	even, odd = colour_bytes(size)
	h = shape.height
	for k, (lead, single, full, smask, fmask) in enumerate(shape.runs[p]):
		col = col0 + k
		rows = [(lead + j, smask) for j in range(single)]
		rows += [(h - 1 - lead - j, smask) for j in range(single)]
		rows += [(lead + single + j, fmask) for j in range(full)]
		for j, mask in rows:
			y = line + j
			out[(col, y)] = (even if y % 2 == 0 else odd) & mask
	return out


def ball_bytes_from_pixels(shape, px, line, size):
	"""The same from the bitmap, pixel by pixel: the check on the run tables."""
	from mode2 import left_bits, right_bits
	from colours import SizeColours
	a, b = SizeColours[size]
	out = {}
	for i, j in shape.pixels():
		x, y = px + i, line + j
		code = a if (x + y) % 2 == 0 else b
		bits = left_bits(code) if x % 2 == 0 else right_bits(code)
		key = (x >> 1, y)
		out[key] = out.get(key, 0) | bits
	return out


def eor_ball(screen, shape, px, line, size):
	for (col, y), value in ball_bytes(shape, px, line, size).items():
		assert 0 <= col < Columns and 0 <= y < Lines, (col, y)
		screen.eor(col, y, value)


def delta_bytes(old, new):
	"""The bytes a move changes: where the old and new balls' bytes differ. Each is (shape, px, line, size)
	or None."""
	a = ball_bytes(*old) if old else {}
	b = ball_bytes(*new) if new else {}
	return sum(1 for key in a.keys() | b.keys() if a.get(key, 0) != b.get(key, 0))
