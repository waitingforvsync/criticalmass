"""Test every table in memory, after the loader, against the model's (build/gen/tables.json, gendata.py's):
the ones MASS holds, and the ones the loader makes (make_tables).

	.venv/bin/python tools/test_tables.py
"""

import json
import os
import sys

from machine import Machine, Root


def main():
	want = json.load(open(os.path.join(Root, "build", "gen", "tables.json")))
	m = Machine()
	mem = m.mpu.memory
	bad, checked = [], 0
	for name, (addr, body) in sorted(want.items(), key=lambda kv: kv[1][0]):
		if body is None:
			continue						# a Baron expression on the code's labels (ChainEntry)
		assert m[name] == addr, f"{name}: at &{m[name]:04X}, the model has &{addr:04X}"
		got = list(mem[addr:addr + len(body)])
		checked += 1
		if got != body:
			i = next(k for k in range(len(body)) if got[k] != body[k])
			bad.append(f"{name}[{i}]: got {got[i]} want {body[i]}")
	if bad:
		print(f"FAIL: {len(bad)} tables differ: " + "; ".join(bad[:8]))
		sys.exit(1)
	print(f"{checked} tables match the model, byte for byte (the loader's own included)")


if __name__ == "__main__":
	main()
