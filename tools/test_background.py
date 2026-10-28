"""Test the screen the loader leaves (the packed screen unpacked: the checker, the walls, the floor, the
panel's boxes and labels) against the model's, byte for byte; and a new game's screen (new_screen, after
GAME OVER) the same.

	.venv/bin/python tools/test_background.py
"""

import sys

from font import draw_text
from layout import (FloorLine, OverBox, OverBoxCol, OverCol, OverLine, WallRightCol, WellCol, background,
					black_box, draw_limit)
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

	# GAME OVER's box, then a new game's screen: back to the start's, the well cleared, and the limit's line
	# (scribble on all of the well first)
	m.call("draw_game_over")
	over = Screen()
	background(over)
	black_box(over, OverBox, OverBoxCol)
	draw_text(over, "GAME OVER", OverCol, OverLine)
	compare(m, over, "GAME OVER")
	mem = m.mpu.memory
	for col in range(WellCol, WallRightCol):			# the whole well, the limit's line too
		for line in range(FloorLine):
			mem[ScreenBase + (line >> 3) * 512 + col * 8 + (line & 7)] = 0xFF
	m.call("new_screen")
	draw_limit(want)								# the game's own, on screen.png's
	compare(m, want, "a new game's screen")
	print("GAME OVER's box, and a new game's screen, match too")


if __name__ == "__main__":
	main()
