"""A py65 machine with MASS loaded as the loader leaves it, for testing the 6502 against the model.

MASS is loaded at its load address, and main RAM's code unpacked to where it runs by the loader's own
unpacker (zx.unpack). Nothing else of the loader runs (it calls the OS), so a test sets up what it needs
itself.

	m = Machine()
	m.call("plot_ball", **{"plot_ball.shapea": 3, ...})

py65's memory is a list: only ever slice it, never copy it whole.
"""

import json
import os

from py65.devices.mpu6502 import MPU

Root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Sentinel = 0xFFF0						# the return address a call stops at


class Machine:
	def __init__(self, build=os.path.join(Root, "build")):
		self.sym = self.symbols(os.path.join(build, "mass.json"))
		self.mpu = MPU()
		mem = self.mpu.memory
		image = open(os.path.join(build, "bin", "MASS"), "rb").read()
		load = self.sym["maincode_image"]
		mem[load:load + len(image)] = list(image)
		org = self.sym["CodeOrg"]
		self.call("zx.unpack", **{"zx.src": load & 0xFF, "zx.src+1": load >> 8,
								   "zx.dst": org & 0xFF, "zx.dst+1": org >> 8})

	@staticmethod
	def symbols(path):
		d = json.load(open(path))
		out = {}
		for asm in d["assemblies"]:
			for sec in asm["sections"]:
				for kind in ("labels", "assignments", "za_autos"):
					for name, v in sec.get(kind, {}).items():
						if isinstance(v.get("value"), int):
							out.setdefault(name, v["value"])
		return out

	def __getitem__(self, name):
		return self.sym[name]

	def poke(self, addr, value):
		self.mpu.memory[addr] = value & 0xFF

	def peek(self, addr):
		return self.mpu.memory[addr]

	def call(self, routine, max_cycles=2_000_000, **inputs):
		"""JSR to a routine with its inputs poked by name; returns the cycles it took."""
		mpu = self.mpu
		for name, value in inputs.items():
			if name.endswith("+1"):
				self.poke(self.sym[name[:-2]] + 1, value)
			else:
				self.poke(self.sym[name], value)
		ret = Sentinel - 1
		mpu.sp = 0xFF
		mpu.memory[0x1FF] = ret >> 8
		mpu.memory[0x1FE] = ret & 0xFF
		mpu.sp = 0xFD
		mpu.pc = self.sym[routine] if isinstance(routine, str) else routine
		start = mpu.processorCycles
		while mpu.pc != Sentinel:
			mpu.step()
			if mpu.processorCycles - start > max_cycles:
				raise RuntimeError(f"{routine}: still running after {max_cycles} cycles, pc &{mpu.pc:04X}")
		return mpu.processorCycles - start
