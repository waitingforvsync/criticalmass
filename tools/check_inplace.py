"""Check MASS's in-place unpacking (D18): the payload unpacks forward from &140 to the screen's end, out of
MASS, which ends PayloadSlack bytes past that. ZX02's runs are at most 256, so a tail that packs badly
needs more slack than one that packs well: this runs the loader's own decoder in py65 and, at every write
into the output, checks that the reading is still ahead of it. Part of `make`.

	.venv/bin/python tools/check_inplace.py
"""

import os
import sys

from py65.devices.mpu6502 import MPU

from machine import Machine, Root, Sentinel, StackTop


def main():
	sym = Machine.symbols(os.path.join(Root, "build", "mass.json"))
	image = open(os.path.join(Root, "build", "bin", "MASS"), "rb").read()
	load, end = sym["payload_image"], sym["payload_end"]
	out0, out1 = sym["CodeOrg"], sym["ScreenEnd"]
	src = sym["zx.src"]
	least = [1 << 30]						# the least the reading was ahead of a write, bytes

	class Memory(list):
		def __setitem__(self, k, v):
			if type(k) is int and out0 <= k < out1:
				read = list.__getitem__(self, src) | list.__getitem__(self, src + 1) << 8
				least[0] = min(least[0], read - k)
			list.__setitem__(self, k, v)

	mem = Memory([0] * 65536)
	mem[load:load + len(image)] = list(image)
	for name, v in (("zx.src", load), ("zx.dst", out0)):
		list.__setitem__(mem, sym[name], v & 0xFF)
		list.__setitem__(mem, sym[name] + 1, v >> 8)
	ret = Sentinel - 1
	list.__setitem__(mem, StackTop, ret >> 8)
	list.__setitem__(mem, StackTop - 1, ret & 0xFF)
	mpu = MPU(memory=mem)
	mpu.sp = (StackTop - 2) & 0xFF
	mpu.pc = sym["zx.unpack"]
	while mpu.pc != Sentinel:
		mpu.step()
	slack = end - out1
	need = slack - least[0] + 1
	if least[0] < 1:
		print(f"FAIL: unpacking in place overtakes its reading: the payload needs {need} bytes of slack past "
			  f"the screen's end, PayloadSlack (memory.6502) is {slack}")
		sys.exit(1)
	print(f"unpacking in place: the reading stays ahead (it needs {need} bytes of slack; it has {slack})")


if __name__ == "__main__":
	main()
