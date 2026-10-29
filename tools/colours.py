"""The balls' colours: a checkerboard of two logical colours for each size, and the palette (D4, D10).

The checkerboard is anchored to the screen: pixel (px, line) shows colour A where px + line is even and B
where it's odd. So a byte's left pixel is A on even lines and B on odd ones, and its right pixel the
other way round. Moving a ball never changes its inside, only its edges.

Balls use only the 8 odd-parity logical colours. Two overlapping balls EOR to an even colour, and every
even colour is black. The physical colour a code shows is set here once for the whole game.
"""

from mode2 import Black, Red, Green, Yellow, Blue, Magenta, Cyan, White, pixel_byte, parity

# Logical colour codes (odd parity), by the physical colour each shows
R, G, B, Y, M, C, W, P = 1, 2, 4, 7, 8, 11, 13, 14
# P, the pulse, is a second white used only by the size one merge from critical mass: the IRQ can change
# its physical colour, and only those balls change

Palette = [Black] * 16
for code, physical in ((R, Red), (G, Green), (B, Blue), (Y, Yellow), (M, Magenta), (C, Cyan),
					   (W, White), (P, White)):
	Palette[code] = physical
assert all(parity(c) for c in (R, G, B, Y, M, C, W, P))

# Size -> (A, B). Solid where A == B. Neighbouring sizes differ in hue, so a pair to merge is easy to see.
SizeColours = {
	1: (R, R),							# red
	2: (Y, Y),							# yellow
	3: (B, M),							# violet
	4: (G, Y),							# lime
	5: (B, C),							# azure
	6: (R, Y),							# orange
	7: (M, W),							# pink
	8: (G, G),							# green (gone with D27's size, back with D32's)
	9: (M, M),							# magenta
	10: (G, C),							# sea green
	11: (C, P),							# ice, pulsing: one merge from critical mass
	12: (W, W),							# critical: white, then it explodes
}


def colour_bytes(size):
	"""(even line byte, odd line byte) for a size: both pixels set, before masking."""
	a, b = SizeColours[size]
	return pixel_byte(a, b), pixel_byte(b, a)
