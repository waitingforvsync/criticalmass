"""Profile a 6502 routine in py65: cycles by label, from the listing's labels.

	.venv/bin/python tools/profile.py physics [--scenes 6]

`physics` profiles physics_step over snapshots of a bot's game (test_physics.py's scenes).
"""

import argparse
import bisect
import collections

from machine import Machine, Sentinel
from test_physics import game_scenes, put


def labels(m):
	"""Every label in main RAM's code, by address: (address, name)."""
	out = []
	end = m.sym["CodeOrg"] + m.sym["maincode_end"] - m.sym["maincode_image"]
	for name, addr in m.sym.items():
		if m.sym["CodeOrg"] <= addr < end and not name[0].isupper():
			out.append((addr, name))
	out.sort()
	return out


def profile(m, routine, counts):
	lab = labels(m)
	addrs = [a for a, _ in lab]
	mpu = m.mpu
	mpu.sp = 0xFD
	ret = Sentinel - 1
	mpu.memory[0x1FF] = ret >> 8
	mpu.memory[0x1FE] = ret & 0xFF
	mpu.pc = m[routine]
	while mpu.pc != Sentinel:
		pc = mpu.pc
		before = mpu.processorCycles
		mpu.step()
		i = bisect.bisect_right(addrs, pc) - 1
		counts[lab[i][1] if i >= 0 else "?"] += mpu.processorCycles - before


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("what")
	ap.add_argument("--scenes", type=int, default=6)
	ap.add_argument("--seed", type=int, default=1)
	ap.add_argument("--skip", type=int, default=300)
	args = ap.parse_args()
	m = Machine()
	m.call("make_tables")
	counts = collections.Counter()
	for balls in game_scenes(args.scenes, args.seed, every=100, skip=args.skip):
		for slot, b in enumerate(balls):
			put(m, slot, b)
			m.poke(m["Order"] + slot, slot)
		m.poke(m["NumBalls"], len(balls))
		for _ in range(4):
			profile(m, "physics_step", counts)
	total = sum(counts.values())
	for name, c in counts.most_common(25):
		print(f"  {name:28s} {c:8d}  {100 * c / total:5.1f}%")


if __name__ == "__main__":
	main()
