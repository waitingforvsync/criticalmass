"""Test the screen the loader leaves (the packed screen unpacked: the checker, the walls, the floor, the
panel's boxes and labels) against the model's, byte for byte; and a new game's screen (new_screen, after
GAME OVER) the same.

	.venv/bin/python tools/test_background.py
"""

import sys

from font import draw_text
from layout import (FloorLine, FloorRow, OverBox, OverBoxCol, OverCol, OverLine, WallRightCol, WellCol,
					background, black_box, draw_limit, wipe_row)
from machine import Machine
from mode2 import ScreenBase, ScreenSize, Screen


def compare(m, want, what):
	got = bytes(m.mpu.memory[ScreenBase:ScreenBase + ScreenSize])
	bad = [i for i in range(ScreenSize) if got[i] != want.mem[i]]
	if bad:
		print(f"FAIL: {what}: {len(bad)} bytes differ, first at &{ScreenBase + bad[0]:04X}")
		sys.exit(1)


def main():
	m = Machine()
	want = Screen()
	background(want)
	compare(m, want, "the loader's screen")
	print(f"the loader's screen matches the model byte for byte ({m.load_cycles} cycles to load)")

	# the game over's wipe (scribble on the well first), GAME OVER's box, then a new game's screen: back to
	# the start's, the well cleared, and the limit's line
	mem = m.mpu.memory
	over = Screen()
	background(over)

	def scribble():
		for col in range(WellCol, WallRightCol):
			for line in range(FloorLine):
				mem[ScreenBase + (line >> 3) * 512 + col * 8 + (line & 7)] = 0xFF
				over.put(col, line, 0xFF)

	scribble()
	m.poke(m["Wipe"], FloorRow)
	for row in reversed(range(FloorRow)):
		m.call("wipe_row")
		wipe_row(over, row)
	assert m.peek(m["Wipe"]) == 0
	compare(m, over, "the game over's wipe")
	m.call("draw_game_over")
	black_box(over, OverBox, OverBoxCol)
	draw_text(over, "GAME OVER", OverCol, OverLine)
	compare(m, over, "GAME OVER")
	scribble()
	m.call("new_screen")
	draw_limit(want)								# the game's own, on screen.png's
	compare(m, want, "a new game's screen")
	print("the game over's wipe, GAME OVER's box, and a new game's screen match too")


if __name__ == "__main__":
	main()
