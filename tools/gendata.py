"""Write the model's data as Baron source, so the 6502 and the model share one source of truth.

	.venv/bin/python tools/gendata.py build/gen

Writes build/gen/data.6502: the palette, the colours, the shapes' run tables, the radii, and the log
tables. Assignments only, plus the tables as FUNCTION-free lists, so a section can place them where it
likes (`EQUB GenX`).
"""

import os
import sys

from colours import Palette, SizeColours, colour_bytes
from mode2 import palette_bytes, pixel_byte
from shapes import CriticalSize, make_shapes
from tables import C, EXP, H, L8, RQ, WQ, pair_r


PixPad = 4								# empty pixel columns between shapes' (shared by neighbours)


# The wide EXP table (physics.6502's pair reads it at a ball's log plus log |dx| or |dy|): it must cover every
# index a contact can make, which exp_range works out over every size pair and every |dx|, |dy| that touch
ExpWLo, ExpWHi = -300, 291


def exp_range():
	from tables import L8, SQ, log16, log_d
	lo, hi = 0, 0
	for a in range(1, CriticalSize + 1):
		for b in range(a, CriticalSize + 1):
			if a >= CriticalSize and b >= CriticalSize:
				continue
			R = pair_r(a, b)
			for qx in range(R):
				for qy in range(R):
					qy1 = 1 if qx == 0 and qy == 0 else qy
					d2 = qx * qx + qy1 * qy1
					if d2 >= R * R:
						break
					lx = L8[qx] if qx else None
					ly = L8[qy1]
					ld = log16(R * R - d2) - log_d(lx, ly)
					for c in (C[a][b], C[b][a]):
						for l in (lx, ly):
							if l is not None:
								lo, hi = min(lo, ld + c + l), max(hi, ld + c + l)
	return lo, hi


def lst(values):
	return "{" + ", ".join(str(v) for v in values) + "}"


def main():
	out = sys.argv[1] if len(sys.argv) > 1 else "build/gen"
	lo, hi = exp_range()
	assert ExpWLo <= lo and hi <= ExpWHi, f"ExpW covers {ExpWLo}..{ExpWHi}, but a contact reaches {lo}..{hi}"
	os.makedirs(out, exist_ok=True)
	shapes = make_shapes()
	lines = ["\\\\ data.6502 - made by tools/gendata.py from the model: don't edit.", ""]
	lines.append(f"GenCriticalSize = {CriticalSize}")
	lines.append(f"GenPalette = {lst(palette_bytes(Palette))}\t; &FE21's 16 writes")
	even = [colour_bytes(s)[0] for s in range(1, CriticalSize + 1)]
	odd = [colour_bytes(s)[1] for s in range(1, CriticalSize + 1)]
	lines.append(f"GenColourEven = {lst([0] + even)}\t; by size: both pixels, even lines")
	lines.append(f"GenColourOdd = {lst([0] + odd)}\t; and odd")
	lines.append(f"GenRadiusQ = {lst(RQ)}\t; by size: physics radius, quarter units")
	lines.append(f"GenWallQ = {lst(WQ)}\t; and the drawn one: the walls and the floor")
	lines.append("")
	lines.append("\\\\ Shapes, by size: width (pixels), height (lines), and for each parity the byte columns as")
	lines.append("\\\\ {lead, single, full, smask, fmask}")
	lines.append("")
	for s, sh in shapes.items():
		lines.append(f"GenShape{s}Width = {sh.width}")
		lines.append(f"GenShape{s}Height = {sh.height}")
		for p in (0, 1):
			cols = ", ".join(lst(c) for c in sh.runs[p])
			lines.append(f"GenShape{s}Runs{p} = {{{cols}}}")
	lines.append("")
	lines.append("\\\\ The same, combined for the plotter: every shape's columns in one list, 5 bytes each, shape by")
	lines.append("\\\\ shape, parity 0 then 1; and by 2 * shape + parity, where its columns start (bytes) and how many")
	lines.append("")
	runs, offsets, counts = [], [0, 0], [0, 0]
	for s, sh in shapes.items():
		for p in (0, 1):
			offsets.append(len(runs))
			counts.append(len(sh.runs[p]))
			for c in sh.runs[p]:
				runs.extend(c)
	lines.append(f"GenRuns = {lst(runs)}")
	lines.append(f"GenRunsOffset = {lst(offsets)}")
	lines.append(f"GenRunsCols = {lst(counts)}")
	lines.append(f"GenHeights = {lst([0] + [sh.height for sh in shapes.values()])}")
	lines.append(f"GenWidths = {lst([0] + [sh.width for sh in shapes.values()])}")
	lines.append("")
	lines.append("\\\\ Each shape's pixel columns: the first line set and the line after the last, from its top, every")
	lines.append("\\\\ shape's in one list with GenPixPad empty ones either side; and by shape, where its first is")
	lines.append("")
	# each shape's columns padded with PixPad empty spans either side (top = bottom = its middle), so the
	# plotter can read a column a few pixels off either edge as an empty span
	tops, bots, poff = [], [], [0]
	items = list(shapes.items())
	for k, (s, sh) in enumerate(items):
		mid = sh.height // 2
		if k == 0:
			tops += [mid] * PixPad
			bots += [mid] * PixPad
		poff.append(len(tops))
		for span in sh.spans:
			top = (sh.height - span) // 2
			assert (sh.height - span) % 2 == 0, "a column's span is centred"
			tops.append(top)
			bots.append(top + span)
		# the padding after a shape is the next one's before: half each's middle (an empty span
		# anywhere is right by EOR; at the ball's middle it's cheapest)
		nmid = items[k + 1][1].height // 2 if k + 1 < len(items) else mid
		half = PixPad // 2
		tops += [mid] * half + [nmid] * (PixPad - half)
		bots += [mid] * half + [nmid] * (PixPad - half)
	assert len(tops) <= 256
	lines.append(f"GenPixPad = {PixPad}")
	lines.append(f"GenPixTop = {lst(tops)}")
	lines.append(f"GenPixBot = {lst(bots)}")
	lines.append(f"GenPixOffset = {lst(poff)}")
	lines.append("")
	lines.append(f"GenL8 = {lst(L8)}\t; round(32 log2 v), clamped to 255")
	lines.append(f"GenExp = {lst(EXP)}\t; round(2^(L/32))")
	lines.append(f"GenExpW = {lst([0 if L < 0 else EXP[min(L, 255)] for L in range(ExpWLo, ExpWHi + 1)])}"
				 f"\t; EXP clamped, L {ExpWLo}..{ExpWHi}")
	lines.append(f"GenExpWLo = {ExpWLo}")
	lines.append(f"GenH = {lst(H)}\t; log d = log max + H[log max - log min]")
	pairs = [C[a][b] for a in range(1, CriticalSize + 1) for b in range(1, CriticalSize + 1)]
	lines.append(f"GenPairC = {lst(pairs)}\t; [a-1][b-1]: the push's log constant on size a from b")
	table = [C[a][b] if 1 <= a <= CriticalSize and 1 <= b <= CriticalSize else 0
			 for a in range(CriticalSize + 1) for b in range(16)]
	lines.append(f"GenPairCTable = {lst(table)}\t; [16 a + b]: the same, laid out for the 6502")
	# by the same index: R (0: no pair: two critical balls, or no ball), R^2, and C the other way round
	pr = [pair_r(a, b) if 1 <= a <= CriticalSize and 1 <= b <= CriticalSize
		  and not (a >= CriticalSize and b >= CriticalSize) else 0
		  for a in range(CriticalSize + 1) for b in range(16)]
	assert max(pr) < 256
	lines.append(f"GenPairR = {lst(pr)}")
	lines.append(f"GenPairR2 = {lst([r * r for r in pr])}")
	tableb = [C[b][a] if 1 <= a <= CriticalSize and 1 <= b <= CriticalSize else 0
			  for a in range(CriticalSize + 1) for b in range(16)]
	lines.append(f"GenPairCbTable = {lst(tableb)}\t; [16 a + b]: C[b][a]")
	# the vertical path's boundaries (plot_vertical): for each shape and parity, each byte column's run
	# boundaries from the top, offset and kind (&80 left pixel, &01 right, 0 both); &FF ends a column
	offs, kinds, start, count = [], [], [0, 0], [0, 0]
	kind = {0xFF: 0x00, 0xAA: 0x80, 0x55: 0x01}
	for s, sh in shapes.items():
		for p in (0, 1):
			start.append(len(offs))
			n0 = len(offs)
			for ci, (lead, single, full, smask, fmask) in enumerate(sh.runs[p]):
				if ci:
					offs.append(0xFF)
					kinds.append(0)
				if single:
					bnd = [(lead, smask), (lead + single, smask ^ fmask), (lead + single + full, smask ^ fmask),
						   (lead + 2 * single + full, smask)]
				else:
					bnd = [(lead, fmask), (lead + full, fmask)]
				for o, mk in bnd:
					if mk:
						offs.append(o)
						kinds.append(kind[mk])
			count.append(len(offs) - n0)
	lines.append("")
	lines.append("\\\\ The vertical path's boundaries: offsets from the top (&FF: the next column) and kinds")
	lines.append(f"GenBndOff = {lst(offs)}")
	lines.append(f"GenBndKind = {lst(kinds)}")
	lines.append(f"GenBndStart = {lst(start)}")
	lines.append(f"GenBndCount = {lst(count)}")

	# the explosion patterns (game.py): each a list of pieces, size 0 ending it
	from game import make_patterns
	sizes, dx, dy, vx, vy, starts = [], [], [], [], [], []
	for pat in make_patterns():
		starts.append(len(sizes))
		for p in pat:
			sizes.append(p.size)
			dx.append(p.dx); dy.append(p.dy); vx.append(p.vx); vy.append(p.vy)
		sizes.append(0)
		dx.append(0); dy.append(0); vx.append(0); vy.append(0)
	assert len(sizes) <= 256
	lines.append("")
	lines.append("\\\\ The explosion patterns (game.py): pieces' sizes (0 ends one), offsets and velocities, 8.8")
	lines.append(f"GenPatternStart = {lst(starts)}")
	lines.append(f"GenPieceSize = {lst(sizes)}")
	lines.append(f"GenPieceDX = {lst(dx)}")
	lines.append(f"GenPieceDY = {lst(dy)}")
	lines.append(f"GenPieceVX = {lst(vx)}")
	lines.append(f"GenPieceVY = {lst(vy)}")
	# the panel's font (font.py): by glyph number, 10 lines of its left byte column and of its right
	import font
	gl, gr = [], []
	for ch in font.Order:
		cell = font.glyph_bytes(ch, 15)		# masks: every bit of a pixel that's set (ANDed with a colour)
		gl += cell[0][0::2]					# each row once: it's doubled as it's drawn
		gr += cell[1][0::2]
	assert len(gl) <= 256
	lines.append("")
	lines.append("\\\\ The panel's font (font.py) as masks, by glyph * 5 + row; its layout; the labels as glyphs")
	lines.append(f"GenGlyphL = {lst(gl)}")
	lines.append(f"GenGlyphR = {lst(gr)}")
	from colours import W as White, Y as Yellow
	lines.append(f"GenTextColour = {pixel_byte(White, White)}\t; the labels' and numbers' colour")
	lines.append(f"GenTitleColour = {pixel_byte(Yellow, Yellow)}\t; the name's")
	for name in ("LabelCol", "ScoreLabel", "ScoreLine", "BestLabel", "BestLine", "NextLabel", "OverLine",
				 "ReturnLine", "TitleLine", "MassLine"):
		lines.append(f"Gen{name} = {getattr(font, name)}")
	for name, text in (("Next", "NEXT"), ("Score", "SCORE"), ("Best", "BEST"), ("Over", "GAME OVER"),
					   ("Return", "RETURN"), ("Title", "CRITICAL"), ("Mass", "MASS")):
		lines.append(f"Gen{name}Text = {lst([font.Order.index(c) for c in text] + [255])}")
	lines.append(f"GenSpaceGlyph = {font.Order.index(' ')}")
	with open(os.path.join(out, "data.6502"), "w") as f:
		f.write("\n".join(lines) + "\n")
	print("wrote", os.path.join(out, "data.6502"))


if __name__ == "__main__":
	main()
