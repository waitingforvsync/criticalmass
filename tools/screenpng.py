"""Screens as PNGs (D18): the game's starting screen (assets/screen.png) and the loading title
(assets/title.png). Each is drawn in MODE 2's pixels, a pixel a block of image pixels at any whole scale
(found from the image's size: Rich's previews are 8 x 4 a pixel), in the BBC's eight physical colours.

	.venv/bin/python tools/screenpng.py --compose

writes assets/screen.png once, from layout.py's parts and the logo (assets/logo.png); after that the PNG is
the source, to retouch by hand. gendata.py converts both PNGs to screen bytes.
"""

import os
import sys

from PIL import Image

from mode2 import Columns, Lines, PhysicalRGB, pixel_byte

Root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ScreenPng = os.path.join(Root, "assets", "screen.png")
TitlePng = os.path.join(Root, "assets", "title.png")
LogoPng = os.path.join(Root, "assets", "logo.png")
TitleWidth, TitleLines = 128, 64		# the title: MODE 2 pixels, lines
LogoWidth, LogoLines = 48, 32


def read_pixels(path, width, height):
	"""The PNG's MODE 2 pixels as physical colours (0-7), a list of rows. It must be a whole scale of
	width x height, each block one colour, every colour one of the BBC's."""
	im = Image.open(path).convert("RGB")
	w, h = im.size
	if w % width or h % height:
		sys.exit(f"{path}: {w} x {h} isn't a whole scale of {width} x {height} MODE 2 pixels")
	sx, sy = w // width, h // height
	data = im.tobytes()
	physical = {bytes(c): i for i, c in enumerate(PhysicalRGB)}
	rows = []
	for y in range(height):
		row = []
		for x in range(width):
			at = ((y * sy) * w + x * sx) * 3
			c = data[at:at + 3]
			for dy in range(sy):
				line = ((y * sy + dy) * w + x * sx) * 3
				if data[line:line + 3 * sx] != c * sx:
					sys.exit(f"{path}: MODE 2 pixel ({x}, {y}) isn't one colour")
			if c not in physical:
				sys.exit(f"{path}: MODE 2 pixel ({x}, {y}) is {tuple(c)}, not a BBC colour")
			row.append(physical[c])
		rows.append(row)
	return rows


def screen_bytes(rows, codes, chars):
	"""MODE 2 bytes in the CRTC's order (a character row's 8 lines a byte column at a time), from physical
	colours mapped to logical codes."""
	out = bytearray(len(rows) * chars)
	for y, row in enumerate(rows):
		for col in range(chars):
			out[(y >> 3) * chars * 8 + col * 8 + (y & 7)] = pixel_byte(codes[row[2 * col]], codes[row[2 * col + 1]])
	return bytes(out)


def game_codes():
	"""Physical colour -> the game's logical code for it (D10: the odd-parity codes, white as W)."""
	from colours import B, C, G, M, R, W, Y
	from mode2 import Black, Blue, Cyan, Green, Magenta, Red, White, Yellow
	codes = {Black: 0, Red: R, Green: G, Yellow: Y, Blue: B, Magenta: M, Cyan: C, White: W}
	return [codes[p] for p in range(8)]


def title_bytes():
	"""The title's screen: logical = physical."""
	return screen_bytes(read_pixels(TitlePng, TitleWidth, TitleLines), list(range(8)), TitleWidth // 2)


def main():
	if "--compose" not in sys.argv:
		sys.exit(__doc__)
	from colours import Palette
	from layout import compose
	from mode2 import Screen
	screen = Screen()
	compose(screen)
	screen.image(Palette, 4).save(ScreenPng)
	print("wrote", ScreenPng)


if __name__ == "__main__":
	main()
