"""The panel's font: 3 x 5 pixel glyphs, each row doubled to two lines, in a 2-byte cell (4 pixels: the
glyph and a gap). Shared by the model (drawn into its screen) and the 6502 (gendata.py's tables), so the
screens match.
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
Order = "0123456789SCORENXTB GAMVPUIL"	# the 6502's glyph numbers

# The panel: where the labels and numbers go (byte column, top line)
LabelCol = 44
ScoreLabel, ScoreLine = 96, 110
BestLabel, BestLine = 140, 154
TitleLine, MassLine = 2, 14				# the name, at the panel's top
NextLabel = 30
OverLine = 190							# GAME OVER, and RETURN, at the game's end
ReturnLine = 204


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
