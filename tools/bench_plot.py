"""Cycles the plotter takes for the common moves, by size: the yardstick for its optimisation.

	.venv/bin/python tools/bench_plot.py

Each move is checked against the model too.
"""

from machine import Machine
from mode2 import ScreenBase, ScreenSize
from shapes import CriticalSize, make_shapes
from test_plot import expected

Moves = [("down 2", 0, 2), ("across 1", 1, 0), ("diagonal", 1, 2), ("down 6", 0, 6)]


def main():
	shapes = make_shapes()
	m = Machine()
	mem = m.mpu.memory
	names = [f"plot_ball.{k}{s}" for s in "ab" for k in ("shape", "colour", "px", "line")]
	print("size  " + "  ".join(f"{name:>9s}" for name, _, _ in Moves) + "       new")
	totals = [0] * (len(Moves) + 1)
	for s in range(1, CriticalSize):
		row = []
		for name, dx, dy in Moves + [("new", None, None)]:
			mem[ScreenBase:ScreenBase + ScreenSize] = [0] * ScreenSize
			old = (s, s, 21, 60)
			new = (s, s, 21 + (dx or 0), 60 + (dy or 0))
			if dx is None:
				old = None
			screen = bytes(ScreenSize)
			vals = list(old or (0, 0, 0, 0)) + list(new)
			cyc = m.call("plot_ball", **dict(zip(names, vals)))
			want = expected(screen, old, new, shapes)
			assert bytes(mem[ScreenBase:ScreenBase + ScreenSize]) == bytes(want), (s, name)
			row.append(cyc)
		for i, c in enumerate(row):
			totals[i] += c
		print(f"{s:4d}  " + "  ".join(f"{c:9d}" for c in row))
	print("all   " + "  ".join(f"{c:9d}" for c in totals))


if __name__ == "__main__":
	main()
