"""MODE 2 as Critical Mass sets it up: 64 characters by 28 rows, the screen at &33E8 (D18).

The screen model is the real memory layout. Byte column c, line l is at
ScreenBase + (l >> 3) * RowBytes + c * 8 + (l & 7). A byte holds two pixels: the left pixel's colour bits
3..0 are in bits 7, 5, 3, 1 and the right pixel's in bits 6, 4, 2, 0.
"""

from PIL import Image

ScreenBase = 0x33E8						# so the well's first byte (column 3) is on a page, an even one (D18)
Columns = 64							# byte columns (characters) across
Rows = 28
RowBytes = Columns * 8					# 512
Lines = Rows * 8						# 224
ScreenSize = RowBytes * Rows			# &3800

# Physical colours, in the ULA's numbering
Black, Red, Green, Yellow, Blue, Magenta, Cyan, White = range(8)
PhysicalRGB = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (255, 255, 0),
			   (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]


def parity(code):
	return bin(code).count("1") & 1


# The ball codes: the logical colours of odd parity (D10). Any two of them EOR to an even code, which the
# palette shows as black.
BallCodes = [c for c in range(16) if parity(c)]		# 1, 2, 4, 7, 8, 11, 13, 14


def left_bits(code):
	"""A logical colour as the left pixel's bits of a byte."""
	return ((code & 8) << 4) | ((code & 4) << 3) | ((code & 2) << 2) | ((code & 1) << 1)


def right_bits(code):
	return left_bits(code) >> 1


def pixel_byte(left, right):
	return left_bits(left) | right_bits(right)


def byte_pixels(b):
	"""A screen byte -> (left code, right code)."""
	def get(b):
		return ((b >> 4) & 8) | ((b >> 3) & 4) | ((b >> 2) & 2) | ((b >> 1) & 1)
	return get(b), get(b << 1)


def address(col, line):
	return ScreenBase + (line >> 3) * RowBytes + col * 8 + (line & 7)


class Screen:
	"""The screen's memory, &33E8 to &6BE7."""

	def __init__(self):
		self.mem = bytearray(ScreenSize)

	def offset(self, col, line):
		return (line >> 3) * RowBytes + col * 8 + (line & 7)

	def get(self, col, line):
		return self.mem[self.offset(col, line)]

	def put(self, col, line, value):
		self.mem[self.offset(col, line)] = value

	def eor(self, col, line, value):
		self.mem[self.offset(col, line)] ^= value

	def image(self, palette, scale=2):
		"""As the TV shows it: each MODE 2 pixel 2 wide and 1 tall, then scaled."""
		im = Image.new("RGB", (Columns * 2 * 2, Lines))
		px = im.load()
		for line in range(Lines):
			for col in range(Columns):
				left, right = byte_pixels(self.get(col, line))
				for i, code in enumerate((left, right)):
					rgb = PhysicalRGB[palette[code]]
					x = (col * 2 + i) * 2
					px[x, line] = rgb
					px[x + 1, line] = rgb
		if scale != 1:
			im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
		return im


def palette_bytes(palette):
	"""The 16 bytes to write to &FE21: logical in the top nybble, physical EOR 7 in the bottom."""
	return [(logical << 4) | (palette[logical] ^ 7) for logical in range(16)]
