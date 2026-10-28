"""Write the model's data as Baron source, so the 6502 and the model share one source of truth.

	.venv/bin/python tools/gendata.py build/gen

Writes two files:
- data.6502: constants (Gen...): the critical size, the palette, the layout's numbers, where the tables
  start, and the like.
- tables.6502: the tables MASS holds, from GenBakedOrg up to the screen (D18); made.6502: the places of
  the ones the loader makes, from GenMadeOrg up to &8000. This file places them: the full-page ones on
  the top pages, the big ones (more than a page) under those, and every other one packed into the pages
  below without crossing a page, so no indexed read of one pays for a crossing. Baron checks each
  address. tables.json has every table's bytes; screen.bin and title.bin are the screens.
"""

import math
import os
import sys
from dataclasses import dataclass

import layout
from colours import Palette, colour_bytes
from mode2 import Lines, ScreenBase, palette_bytes, pixel_byte
from physics import WellLeft, WellRight
from shapes import CriticalSize, make_shapes
from tables import C, EXP, H, L8, RQ, SQ, WQ, pair_r


PixPad = 4								# empty pixel columns between shapes' (shared by neighbours)
FastShapes = CriticalSize - 1			# shapes the two-band and vertical paths draw: not the critical ball's,
										# which moves for a few frames only (its columns would need a second page)


# The wide EXP table (physics.6502's pair reads it at a ball's log plus log |dx| or |dy|): it must cover every
# index a contact can make, which exp_range works out over every size pair and every |dx|, |dy| that touch
ExpWLo, ExpWHi = -350, 295


def exp_range():
	from tables import log16, log_d
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


def lo(v):
	return v & 0xFF


def hi(v):
	return (v >> 8) & 0xFF


def signed(v):
	return v - 256 if v >= 128 else v


@dataclass
class Part:
	"""A table's part: its label, its bytes (a list; a Baron expression for EQUB, a string; or, made by the
	loader, a function of the tables' addresses giving them), its size and a comment."""
	label: str
	body: object
	size: int
	comment: str

	@property
	def made(self):
		return callable(self.body)


@dataclass
class Table:
	"""A table: its parts, back to back."""
	parts: list
	align: str = "in"					# "page": starts a page; "in": inside one page; "any": anywhere

	@property
	def size(self):
		return sum(p.size for p in self.parts)


def part(label, values, comment):
	return Part(label, [v & 0xFF for v in values], len(values), comment)


def table(label, values, comment, align="in"):
	return Table([part(label, values, comment)], align)


def expr(label, text, size, comment, align="in"):
	return Table([Part(label, text, size, comment)], align)


def made_part(label, values, comment, size=None):
	"""A table the loader makes (entry.6502's make_tables): not in MASS. values: its bytes, or a
	function of the tables' addresses giving them (then size)."""
	comment += " (the loader makes it)" if comment else ""
	if callable(values):
		return Part(label, values, size, comment)
	v = [x & 0xFF for x in values]
	return Part(label, lambda addr: v, len(v), comment)


def made(label, values, comment, align="in", size=None):
	return Table([made_part(label, values, comment, size)], align)


def place(tables, top):
	"""Addresses for the tables, ending at top: the page-aligned ones on the top pages (under the part
	page below top, if it's not a page), the big ones under them, then the rest first-fit (largest first)
	into the space left, none crossing a page. Returns {id(table): address} and the lowest address."""
	where = {}
	bins = []							# [base, capacity, used, down]: down packs from the top end
	cur = top
	if cur & 0xFF:
		bins.append([cur & ~0xFF, cur & 0xFF, 0, True])
		cur &= ~0xFF
	for t in [t for t in tables if t.align == "page"]:
		pages = -(-t.size // 256)
		cur -= pages * 256
		where[id(t)] = cur
		if t.size < pages * 256:
			bins.append([cur + t.size, pages * 256 - t.size, 0, False])
	for t in [t for t in tables if t.align == "any"]:
		assert t.size > 256, "a table of a page or less belongs inside a page"
		cur -= t.size
		where[id(t)] = cur
	if cur & 0xFF:
		bins.append([cur & ~0xFF, cur & 0xFF, 0, True])
	cur &= ~0xFF
	for t in sorted([t for t in tables if t.align == "in"], key=lambda t: -t.size):
		assert t.size <= 256
		for b in bins:
			if b[1] - b[2] >= t.size:
				break
		else:
			cur -= 256
			b = [cur, 256, 0, True]
			bins.append(b)
		b[2] += t.size
		where[id(t)] = b[0] + b[1] - b[2] if b[3] else b[0] + b[2] - t.size
	return where, min(where.values())


def emit_values(values):
	out = []
	for i in range(0, len(values), 16):
		out.append("\tEQUB " + ", ".join(str(v) for v in values[i:i + 16]))
	return out


def main():
	out = sys.argv[1] if len(sys.argv) > 1 else "build/gen"
	lo_, hi_ = exp_range()
	assert ExpWLo <= lo_ and hi_ <= ExpWHi, f"ExpW covers {ExpWLo}..{ExpWHi}, but a contact reaches {lo_}..{hi_}"
	os.makedirs(out, exist_ok=True)
	shapes = make_shapes()
	sizes = range(CriticalSize + 1)		# by size, 0 (no ball) first
	tables = []

	# --- data.6502: the constants ---

	lines = ["\\\\ data.6502 - made by tools/gendata.py from the model: don't edit.", ""]
	lines.append(f"GenCriticalSize = {CriticalSize}")
	lines.append(f"GenFastShapes = {FastShapes}\t; shapes the two-band and vertical paths draw (not critical)")
	lines.append(f"GenPalette = {lst(palette_bytes(Palette))}\t; &FE21's 16 writes")
	lines.append(f"GenPixPad = {PixPad}")
	from game import DropSizes
	lines.append(f"GenDropSizes = {len(DropSizes)}\t; drops are sizes 1 to this")
	lines.append(f"GenExpWLo = {ExpWLo}")
	lines.append("")
	lines.append("\\\\ The layout (layout.py): byte columns, lines and rows")
	for name in ("WallLeftCol", "WellCol", "WellCols", "WallRightCol", "FloorRow", "FloorLine", "RimLine",
				 "BoxCol", "BoxCols", "LabelCol", "ScoreLine", "BestLine", "OverBoxCol", "OverCol", "OverLine"):
		lines.append(f"Gen{name} = {getattr(layout, name)}")
	lines.append(f"GenNextX = {layout.NextX}:GenNextY = {layout.NextY}\t; the next ball's centre, units")
	for name in ("NextBox", "OverBox"):
		row, rows = getattr(layout, name)
		lines.append(f"Gen{name}Row = {row}:Gen{name}Rows = {rows}")
	from colours import W as White, Y as Yellow
	lines.append(f"GenTextColour = {pixel_byte(White, White)}\t; the labels' and numbers' colour")
	import font
	lines.append(f"GenSpaceGlyph = {font.glyph_number(' ')}")

	# --- the tables ---

	# the shapes (shapes.py): each byte column's runs, 5 bytes {lead, single, full, smask, fmask}, every
	# shape's in one list, shape by shape, parity 0 then 1; by 2 * shape + parity, where its columns start
	# and how many
	runs, offsets, counts = [], [0, 0], [0, 0]
	for s, sh in shapes.items():
		for p in (0, 1):
			offsets.append(len(runs))
			counts.append(len(sh.runs[p]))
			for c in sh.runs[p]:
				runs.extend(c)
	tables.append(table("Runs", runs, "each byte column's runs: lead, single, full, smask, fmask", "any"))
	tables.append(expr("RunsLo", f"LO(Runs + {lst(offsets)})", len(offsets),
					   "by 2 * shape + parity: where its columns' runs start"))
	tables.append(expr("RunsHi", f"HI(Runs + {lst(offsets)})", len(offsets), ""))
	tables.append(table("RunsCols", counts, "and how many columns"))
	tables.append(table("Heights", [0] + [sh.height for sh in shapes.values()], "by shape: its height in lines"))
	tables.append(table("Widths", [0] + [sh.width for sh in shapes.values()], "and its width in pixels"))
	tables.append(table("HalfHeights", [0] + [sh.height // 2 for sh in shapes.values()], "and half its height"))
	even = [colour_bytes(s)[0] for s in range(1, CriticalSize + 1)]
	odd = [colour_bytes(s)[1] for s in range(1, CriticalSize + 1)]
	tables.append(table("ColourEven", [0] + even, "by colour (a size): both pixels set, on even lines"))
	tables.append(table("ColourOdd", [0] + odd, "and on odd ones"))

	# each fast shape's pixel columns: the first line set and the line after the last, from its top, every
	# shape's in one list with PixPad empty ones either side (top = bottom = its middle), so the plotter can
	# read a column a few pixels off either edge as an empty span; by shape, where its first is
	tops, bots, poff = [], [], [0]
	items = [(s, sh) for s, sh in shapes.items() if s <= FastShapes]
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
		# the padding after a shape is the next one's before: half each's middle (an empty span anywhere is
		# right by EOR; at the ball's middle it's cheapest)
		nmid = items[k + 1][1].height // 2 if k + 1 < len(items) else mid
		half = PixPad // 2
		tops += [mid] * half + [nmid] * (PixPad - half)
		bots += [mid] * half + [nmid] * (PixPad - half)
	assert len(tops) <= 256, f"the fast shapes' pixel columns take {len(tops)} bytes: more than a page"
	poff += [0] * (CriticalSize - FastShapes)
	tables.append(table("PixOffset", poff, "by fast shape: where its pixel columns start in PixTop and PixBot"))
	tables.append(table("PixTop", tops, "the fast shapes' pixel columns: the first line set", "page"))
	tables.append(table("PixBot", bots, "and the line after the last", "page"))

	# the vertical path's boundaries (plot_vertical), fast shapes only: for each shape and parity, each byte
	# column's run boundaries from the top, offset and kind (&80 left pixel, &01 right, 0 both); &FF ends a
	# column
	offs, kinds, start, count = [], [], [0, 0], [0, 0]
	kind = {0xFF: 0x00, 0xAA: 0x80, 0x55: 0x01}
	for s, sh in shapes.items():
		for p in (0, 1):
			start.append(len(offs))
			n0 = len(offs)
			if s > FastShapes:
				count.append(0)
				continue
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
	tables.append(table("BndOff", offs, "the vertical path's boundaries: offsets from the top (&FF: next column)",
						"any"))
	tables.append(table("BndKind", kinds, "and kinds: &80 the left pixel, &01 the right, 0 both", "any"))
	tables.append(expr("BndStartLo", f"LO(BndOff + {lst(start)})", len(start),
					   "by 2 * shape + parity: where its boundaries start"))
	tables.append(expr("BndStartHi", f"HI(BndOff + {lst(start)})", len(start), ""))
	tables.append(table("BndCount", count, "and how many"))
	tables.append(made("RowHi", [hi(layout.WellAddr) + (line >> 3) * 2 for line in range(Lines)],
					   "by line: the high byte of its row's start in the well (a row is two pages)"))

	# the balls (balls.6502): by size, the radius in quarter units, in units rounded up (sweep's quick
	# test) and in 8.8; where its centre may go (the walls and floor: the drawn radius)
	tables.append(table("RadiusQ", RQ, "by size: the physics radius, quarter units"))
	tables.append(table("RadiusU", [(q + 3) // 4 for q in RQ], "in units, rounded up"))
	tables.append(table("RadiusLo", [lo(q * 64) for q in RQ], "in 8.8"))
	tables.append(table("RadiusHi", [hi(q * 64) for q in RQ], ""))
	for name, f, comment in (("Left", lambda w: WellLeft * 256 + w * 64, "the walls and floor: the centre's limits"),
							 ("Right", lambda w: WellRight * 256 - w * 64, ""),
							 ("Floor", lambda w: layout.FloorLine * 256 - w * 64, ""),
							 ("DropLo", lambda w: WellLeft * 256 + w * 64 + 256, "the dropper's limits"),
							 ("DropHi", lambda w: WellRight * 256 - w * 64 - 256, ""),
							 ("HeldY", lambda w: layout.RimLine * 256 - w * 64, "the held ball's centre: on the rim"),
							 ("Rim", lambda w: layout.RimLine * 256 + w * 64, "a centre above this pokes above the rim"),
							 ("RimTwo", lambda w: (layout.RimLine + 2) * 256 + w * 64,
							  "the held ball waits till the drop's below this")):
		v = [f(w) for w in WQ]
		tables.append(table(name + "Lo", [lo(x) for x in v], comment))
		tables.append(table(name + "Hi", [hi(x) for x in v], ""))

	# the pairs, by 16 * size a + size b: the push's log constant on a ball of size a from one of size b
	# (tables.py), as pointers into ExpW (a log l is at ExpW - Lo + l), and the other way round; R; R^2
	def by_pair(f):
		return [f(a, b) if 1 <= a <= CriticalSize and 1 <= b <= CriticalSize else 0
				for a in sizes for b in range(16)]
	ctab = by_pair(lambda a, b: C[a][b])
	cbtab = by_pair(lambda a, b: C[b][a])
	n = len(ctab)
	none = [a == 0 or b == 0 or b > CriticalSize for a in sizes for b in range(16)]
	def pointers(tab, f):
		return lambda addr: [0 if z else f(addr["ExpW"] - ExpWLo + c) for z, c in zip(none, tab)]
	tables.append(made("PairCLo", pointers(ctab, lo),
					   "by 16 * size a + size b: the push's log constant on a from b, as a pointer into ExpW",
					   size=n))
	tables.append(made("PairCHi", pointers(ctab, hi), "", size=n))
	tables.append(made("PairCbLo", pointers(cbtab, lo), "and on b from a", size=n))
	tables.append(made("PairCbHi", pointers(cbtab, hi), "", size=n))
	pr = by_pair(lambda a, b: 0 if a >= CriticalSize and b >= CriticalSize else pair_r(a, b))
	assert max(pr) < 256
	tables.append(made("PairR", pr, "R, quarter units (0: no pair): RadiusQ's sum, at most 255"))
	tables.append(made("PairR2Lo", [lo(r * r) for r in pr], "R^2: from the squares"))
	tables.append(made("PairR2Hi", [hi(r * r) for r in pr], ""))
	# the loader's: C for each pair, less the least (so a byte), by 12 * (a - 1) + b - 1
	cmin = min(C[a][b] for a in range(1, CriticalSize + 1) for b in range(1, CriticalSize + 1))
	cmat = [C[a][b] - cmin for a in range(1, CriticalSize + 1) for b in range(1, CriticalSize + 1)]
	assert max(cmat) < 256
	lines.append(f"GenPairCMin = {cmin}")
	lines.append(f"GenPairC = {lst(cmat)}\t; C[a][b] - GenPairCMin, by {CriticalSize} * (a - 1) + b - 1 (the loader's)")
	tables.append(table("Times16", [v * 16 for v in range(16)], "a size * 16: the pair tables' row"))

	# the physics' full-page tables, each read indexed by a byte, back to back from a page:
	# - RoundP, RoundN: a low byte's share of |d|'s rounding to quarter units, positive d and negative (~d + 33)
	# - L8: round(32 log2 v), clamped to 255
	# - H: log d = log max + H[log max - log min]
	# - BitLen: the bits in a byte (log16's shifts)
	# - Times6Lo/Hi, Times11Lo/Hi: a push that fits a signed byte, t * 6 and (t * 11) >> 1 (apply's kv, kp)
	bitlen = [v.bit_length() for v in range(256)]
	t6 = [signed(v) * 6 for v in range(256)]
	t11 = [math.floor(signed(v) * 11 / 2) for v in range(256)]
	tables.append(Table([
		part("RoundP", [(v + 32) // 64 for v in range(256)], "the physics' full pages, back to back: rounding, d > 0"),
		part("RoundN", [(288 - v) // 64 for v in range(256)], "and d < 0"),
		part("L8", L8, "round(32 log2 v), clamped to 255"),
		part("H", H, "log d = log max + H[log max - log min]"),
		part("BitLen", bitlen, "the bits in a byte (log16's shifts)")], "page"))
	tables.append(Table([
		made_part("Times6Lo", [lo(v) for v in t6], "a signed byte t * 6 (apply's kv)"),
		made_part("Times6Hi", [hi(v) for v in t6], ""),
		made_part("Times11Lo", [lo(v) for v in t11], "(t * 11) >> 1 (apply's kp)"),
		made_part("Times11Hi", [hi(v) for v in t11], "")], "page"))
	tables.append(table("ExpW", [0 if L < 0 else EXP[min(L, 255)] for L in range(ExpWLo, ExpWHi + 1)],
						f"EXP clamped, by log from {ExpWLo}: read through each ball's log as a pointer", "any"))
	tables.append(table("Times32Lo", [lo(v * 32) for v in range(9)], "32 n, for log16"))
	tables.append(table("Times32Hi", [hi(v * 32) for v in range(9)], ""))
	tables.append(expr("ChainEntry", "0, LO(log16.chain + 3 * (8 - (1..8)))", 9, "log16's entries into its chain"))
	tables.append(made("SqLo", [lo(v) for v in SQ], "v * v for v in 0..255 (the squares of |dx|, |dy|)", "page"))
	tables.append(made("SqHi", [hi(v) for v in SQ], "", "page"))

	# the explosion patterns (game.py): pieces' sizes (0 ends one), offsets in half units and velocities in
	# eighths of a unit a step, signed bytes
	from game import make_patterns
	psize, dx, dy, vx, vy, starts = [], [], [], [], [], []
	for pat in make_patterns():
		starts.append(len(psize))
		for p in pat:
			assert p.dx % 128 == 0 and p.dy % 128 == 0 and p.vx % 32 == 0 and p.vy % 32 == 0
			psize.append(p.size)
			dx.append(p.dx // 128); dy.append(p.dy // 128); vx.append(p.vx // 32); vy.append(p.vy // 32)
		psize.append(0)
		dx.append(0); dy.append(0); vx.append(0); vy.append(0)
	assert len(psize) <= 256 and all(-128 <= v < 128 for v in dx + dy + vx + vy)
	tables.append(table("PatternStart", starts, "the explosion patterns: where each starts"))
	tables.append(table("PieceSize", psize, "its pieces' sizes (0 ends one)"))
	tables.append(table("PieceDX", dx, "offsets from the critical ball's centre, half units"))
	tables.append(table("PieceDY", dy, ""))
	tables.append(table("PieceVX", vx, "velocities, eighths of a unit a step"))
	tables.append(table("PieceVY", vy, ""))

	# the panel's font (font.py) as masks, by glyph * 5 + row (each row drawn twice); the text as glyphs
	gl, gr = [], []
	for ch in font.Order:
		cell = font.glyph_bytes(ch, 15)		# masks: every bit of a pixel that's set (ANDed with a colour)
		gl += cell[0][0::2]
		gr += cell[1][0::2]
	tables.append(table("GlyphL", gl, "the font, by glyph * 5 + row: the left byte column's masks"))
	tables.append(table("GlyphR", gr, "and the right's"))
	tables.append(table("OverText", [font.glyph_number(c) for c in "GAME OVER"] + [255],
						"GAME OVER, as glyphs (255 ends it)"))

	# the palette, and the sound's (sound.6502): each channel's bits in a command byte, and the effects, by
	# request (from 1): channel, period lo and hi, slide, attenuation, decay, and 2 spare
	tables.append(table("Palette", palette_bytes(Palette), "&FE21's writes: logical on top, physical EOR 7 below"))
	tables.append(table("ChanBits", [0x00, 0x20, 0x40, 0x60], "the sound: each channel's bits in a command byte"))
	effects = [(1, 500, 8, 2, 1),			# drop: a low thud, falling
			   (0, 120, 2, 0, 2),			# merge: a plink, lower for bigger balls
			   (3, 0, 0, 0, 4),				# explode: noise, dying away
			   (2, 300, 6, 0, 6)]			# game over: a long falling tone
	tables.append(table("Effects", [b for ch, per, sl, att, dec in effects
									for b in (ch, lo(per), hi(per), sl, att, dec, 0, 0)],
						"the effects: channel, period lo and hi, slide, attenuation, decay, 2 spare"))

	# the sparks (sparks.py, P21), by direction: each speed's code, and the life (their slots are in zero
	# page: memory.6502)
	import sparks
	lines.append(f"GenSparkSlots = {sparks.Slots}")
	most = max(sh.height // 2 for sh in shapes.values())
	assert 2 * most + 3 <= 127, "a spark's speed (2r quarters) and its quarters add without overflow (sparks.6502)"
	assert sparks.Gravity in (0, 1), "sparks.6502 adds gravity with an INC, or not at all"
	lines.append(f"GenSparkGravity = {sparks.Gravity}")
	tables.append(table("SparkDirX", sparks.DirX, "the sparks, by direction: the speed across's code"))
	tables.append(table("SparkDirY", sparks.DirY, "and down's"))
	tables.append(table("SparkDirLife", sparks.DirLife, "and the life, frames"))

	# --- the screens: the game's as it starts (assets/screen.png), and the loading title's ---

	from mode2 import Screen, ScreenSize
	import screenpng
	scr = Screen()
	layout.background(scr)
	with open(os.path.join(out, "screen.bin"), "wb") as f:
		f.write(bytes(scr.mem))
	with open(os.path.join(out, "title.bin"), "wb") as f:
		f.write(screenpng.title_bytes())
	lines.append("")
	lines.append("\\\\ The screens (D18): the game's, and the loading title's (!BOOT's)")
	lines.append(f"GenScreenAddr = &{ScreenBase:04X}\t; so the well's first byte is on a page, an even one")
	lines.append(f"GenScreenEnd = &{ScreenBase + ScreenSize:04X}")
	lines.append(f"GenWellAddr = &{layout.WellAddr:04X}")
	lines.append(f"GenTitleChars = {screenpng.TitleWidth // 2}:GenTitleRows = {screenpng.TitleLines // 8}")
	lines.append(f"GenTitlePalette = {lst([(l << 4) | ((l & 7) ^ 7) for l in range(16)])}\t; logical = physical")

	# the well is clear in screen.png (the balls are EORed there); the limit's line across it is the game's
	# to draw (layout.py, limit.6502)
	assert not any(scr.get(col, line) for line in range(layout.FloorLine)
				   for col in range(layout.WellCol, layout.WallRightCol)), "screen.png's well is clear"
	lines.append(f"GenLimitLine = {layout.LimitLine}:GenLimitByte = {layout.LimitByte}\t; the limit's line (layout.py)")

	# --- place the tables: MASS's under the screen, the loader's at the top of memory ---

	baked = [t for t in tables if not any(p.made for p in t.parts)]
	loaders = [t for t in tables if all(p.made for p in t.parts)]
	assert len(baked) + len(loaders) == len(tables), "a table is all MASS's or all the loader's"
	where, org = place(baked, ScreenBase)
	mwhere, morg = place(loaders, 0x8000)
	where.update(mwhere)
	lines.append("")
	lines.append(f"GenBakedOrg = &{org:04X}\t; MASS's tables (tables.6502), up to the screen")
	lines.append(f"GenMadeOrg = &{morg:04X}\t; the loader's (made.6502), up to &8000")
	with open(os.path.join(out, "data.6502"), "w") as f:
		f.write("\n".join(lines) + "\n")

	addr = {}

	def emit(region, start, end, head):
		tl = list(head)
		pc = start
		for t in sorted(region, key=lambda t: where[id(t)]):
			a = where[id(t)]
			assert a >= pc
			if a > pc:
				tl.append(f"\tSKIPTO &{a:04X}\t\t\t\t\t\t; ({a - pc} bytes spare)")
			if t.align == "in":
				assert a >> 8 == (a + t.size - 1) >> 8, "a table crosses a page"
			for p in t.parts:
				if p.comment:
					tl.append(f"\\\\ {p.comment}")
				tl.append(f"\tASSERT P% == &{a:04X}")
				tl.append(f".{p.label}")
				addr[p.label] = a
				if p.made:
					tl.append(f"\tSKIP {p.size}")
				elif isinstance(p.body, str):
					tl.append(f"\tEQUB {p.body}")
				else:
					assert len(p.body) == p.size
					tl += emit_values(p.body)
				a += p.size
			pc = a
		assert pc <= end
		if pc < end:
			tl.append(f"\tSKIPTO &{end:04X}\t\t\t\t\t\t; ({end - pc} bytes spare)")
		return tl

	tl = emit(baked, org, ScreenBase, [
		"\\\\ tables.6502 - made by tools/gendata.py from the model: don't edit. The tables MASS holds, from",
		"\\\\ GenBakedOrg up to the screen, placed by gendata.py (none of a page or less crosses one).", ""])
	tl.append(f"\tASSERT P% == &{ScreenBase:04X}, \"the tables end at the screen\"")
	with open(os.path.join(out, "tables.6502"), "w") as f:
		f.write("\n".join(tl) + "\n")
	ml = emit(loaders, morg, 0x8000, [
		"\\\\ made.6502 - made by tools/gendata.py from the model: don't edit. The tables the loader makes",
		"\\\\ (entry.6502's make_tables), from GenMadeOrg up to &8000: their places only.", "",
		"SECTION MadeTables, org = GenMadeOrg, guard = &8000, virtual = TRUE"])
	ml.append("ENDSECTION")
	with open(os.path.join(out, "made.6502"), "w") as f:
		f.write("\n".join(ml) + "\n")

	# every table's address and bytes, for tools/test_tables.py (a Baron expression's: none, but RunsLo/Hi's
	# and BndStartLo/Hi's, worked out here)
	import json
	want = {}
	for t in tables:
		for p in t.parts:
			if p.made:
				body = p.body(addr)
				assert len(body) == p.size
			elif isinstance(p.body, str):
				body = None
			else:
				body = p.body
			want[p.label] = [addr[p.label], body]
	want["RunsLo"][1] = [lo(addr["Runs"] + o) for o in offsets]
	want["RunsHi"][1] = [hi(addr["Runs"] + o) for o in offsets]
	want["BndStartLo"][1] = [lo(addr["BndOff"] + o) for o in start]
	want["BndStartHi"][1] = [hi(addr["BndOff"] + o) for o in start]
	with open(os.path.join(out, "tables.json"), "w") as f:
		json.dump(want, f)
	bsize = sum(t.size for t in baked)
	msize = sum(t.size for t in loaders)
	print(f"wrote {out}/: MASS's tables {bsize} bytes from &{org:04X} ({ScreenBase - org - bsize} spare), "
		  f"the loader's {msize} from &{morg:04X} ({0x8000 - morg - msize} spare)")


if __name__ == "__main__":
	main()
