"""Test the 6502's background (walls, floor, rim marks, the panel's labels and name) against the model's,
byte for byte: draw_background on a black screen.

	.venv/bin/python tools/test_background.py
"""

import sys

from machine import Machine
from mode2 import ScreenBase, ScreenSize, Screen
from model import background


def main():
	m = Machine()
	m.call("make_tables")
	m.mpu.memory[ScreenBase:ScreenBase + ScreenSize] = [0] * ScreenSize
	m.call("draw_background")
	want = Screen()
	background(want)
	got = bytes(m.mpu.memory[ScreenBase:ScreenBase + ScreenSize])
	bad = [i for i in range(ScreenSize) if got[i] != want.mem[i]]
	if bad:
		print(f"FAIL: {len(bad)} bytes differ, first at &{ScreenBase + bad[0]:04X}")
		sys.exit(1)
	print("the background matches the model byte for byte")


if __name__ == "__main__":
	main()
