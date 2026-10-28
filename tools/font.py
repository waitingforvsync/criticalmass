"""The panel's font: 3 x 5 pixel glyphs, each row doubled to two lines, in a 2-byte cell (4 pixels: the
glyph and a gap). Where it's drawn is layout.py's. Shared by the model (drawn into its screen) and the
6502 (gendata.py's tables), so the screens match.
"""

from colours import W
from mode2 import pixel_byte

Glyphs = {
	"0": ("111", "101", "101", "101", "111"),
	"1": ("010", "110", "010", "010", "111"),
	"2": ("111", "001", "111", "100", "111"),
	"3": ("111", "001", "111", "001", "111"),
	"4": ("101", "101", "111", "001", "001"),
	"5": ("111", "100", "111", "001", "111"),
	"6": ("111", "100", "111", "101", "111"),
	"7": ("111", "001", "001", "001", "001"),
	"8": ("111", "101", "111", "101", "111"),
	"9": ("111", "101", "111", "001", "111"),
	"S": ("111", "100", "111", "001", "111"),
	"C": ("111", "100", "100", "100", "111"),
	"O": ("111", "101", "101", "101", "111"),
	"R": ("110", "101", "110", "101", "101"),
	"E": ("111", "100", "110", "100", "111"),
	"N": ("110", "101", "101", "101", "101"),
	"X": ("101", "101", "010", "101", "101"),
	"T": ("111", "010", "010", "010", "010"),
	"B": ("110", "101", "110", "101", "110"),
	" ": ("000", "000", "000", "000", "000"),
	"G": ("111", "100", "101", "101", "111"),
	"A": ("111", "101", "111", "101", "101"),
	"M": ("101", "111", "111", "101", "101"),
	"V": ("101", "101", "101", "101", "010"),
	"P": ("111", "101", "111", "100", "100"),
	"U": ("101", "101", "101", "101", "111"),
	"I": ("111", "010", "010", "010", "111"),
	"L": ("100", "100", "100", "100", "111"),
}
GlyphLines = 10							# 5 rows, each two lines
# The 6502's glyphs, by number: only what it draws itself, the score's digits and GAME OVER (the labels are
# in the screen the loader unpacks). O is drawn as 0 and S as 5: the same glyphs.
Order = "0123456789 GAMEVR"
Same = {"O": "0", "S": "5"}


def glyph_number(ch):
	return Order.index(Same.get(ch, ch))


def glyph_bytes(ch, colour=W):
	"""A glyph as its cell's bytes: two byte columns, GlyphLines lines each (left column first)."""
	rows = Glyphs[ch]
	out = [[], []]
	for r in rows:
		bits = [int(c) for c in r] + [0]
		for col in range(2):
			b = pixel_byte(colour if bits[2 * col] else 0, colour if bits[2 * col + 1] else 0)
			out[col] += [b, b]
	return out


def draw_text(screen, text, col, line, colour=W):
	"""Plain stores: the panel is never EORed."""
	for i, ch in enumerate(text):
		cell = glyph_bytes(ch, colour)
		for c in range(2):
			for j in range(GlyphLines):
				screen.put(col + 2 * i + c, line + j, cell[c][j])


def score_text(score):
	return f"{score:6d}"


# The panel's labels (NEXT, SCORE, BEST): only ever in assets/screen.png, so free to be anything. 4 x 5
# pixels, each row two lines; a white top row over cyan, and a blue shadow a pixel right and two lines down,
# as the logo's CRITICAL. Centred in their boxes.
LabelGlyphs = {
	"N": ("1001", "1101", "1011", "1001", "1001"),
	"E": ("1111", "1000", "1110", "1000", "1111"),
	"X": ("1001", "1001", "0110", "1001", "1001"),
	"T": ("1111", "0110", "0110", "0110", "0110"),
	"S": ("0111", "1000", "0110", "0001", "1110"),
	"C": ("0111", "1000", "1000", "1000", "0111"),
	"O": ("0110", "1001", "1001", "1001", "0110"),
	"R": ("1110", "1001", "1110", "1010", "1001"),
	"B": ("1110", "1001", "1110", "1001", "1110"),
}


def set_pixel(screen, px, line, code):
	from mode2 import left_bits, right_bits
	col = px >> 1
	b = screen.get(col, line)
	b = (b & 0xAA) | right_bits(code) if px & 1 else (b & 0x55) | left_bits(code)
	screen.put(col, line, b)


def draw_label(screen, text, centre_px, line):
	"""A label in the labels' font, centred on a pixel column, its top at a line."""
	from colours import B, C, W
	width = 5 * len(text)						# the letters and their gaps, the shadow in the last
	x0 = centre_px - width // 2
	lit = [(x0 + 5 * i + c, r) for i, ch in enumerate(text) for r, row in enumerate(LabelGlyphs[ch])
		   for c, bit in enumerate(row) if bit == "1"]
	for x, r in lit:
		for d in (0, 1):
			set_pixel(screen, x + 1, line + 2 * r + d + 2, B)
	for x, r in lit:
		for d in (0, 1):
			set_pixel(screen, x, line + 2 * r + d, W if r == 0 else C)
