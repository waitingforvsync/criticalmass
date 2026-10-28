"""A py65 machine with MASS loaded as the loader leaves it, for testing the 6502 against the model.

MASS is loaded at its load address, and the loader run from just after its OS calls (entry.take_over)
until it reaches main: the payload (the code, its tables and the screen) unpacked in place, and the
loader's tables made. The hardware it sets up is just memory here.

	m = Machine()
	m.call("plot_ball", **{"plot_ball.shapea": 3, ...})

py65's memory is a list: only ever slice it, never copy it whole.
"""

import json
import os

from py65.devices.mpu6502 import MPU

Root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Sentinel = 0xFFF0						# the return address a call stops at
StackTop = 0x13F						# the game's stack: &100-&13F (code from &140)
StackFill = 0xA5						# under the stack before a call: the lowest byte changed is its deepest


class Machine:
	def __init__(self, build=os.path.join(Root, "build")):
		self.sym = self.symbols(os.path.join(build, "mass.json"))
		self.mpu = MPU()
		mem = self.mpu.memory
		image = open(os.path.join(build, "bin", "MASS"), "rb").read()
		load = self.sym["payload_image"]
		# memory as MASS finds it, more or less: junk, and the title where !BOOT put it (so a read of
		# anything before it's written shows up)
		junk = bytes((i * 167 + 59) & 0xFF for i in range(0x8000))
		mem[0:0x8000] = list(junk)
		title = open(os.path.join(build, "gen", "title.bin"), "rb").read()
		mem[0x8000 - len(title):0x8000] = list(title)
		mem[load:load + len(image)] = list(image)
		mpu = self.mpu
		mpu.sp = StackTop & 0xFF
		mpu.pc = self.sym["entry.take_over"]
		while mpu.pc != self.sym["main"]:
			mpu.step()
			if mpu.processorCycles > 20_000_000:
				raise RuntimeError(f"the loader: still running, pc &{mpu.pc:04X}")
		self.load_cycles = mpu.processorCycles
		self.stack_depth = 0				# the most bytes of stack a call has used (the IRQ's not counted)

	@staticmethod
	def symbols(path):
		d = json.load(open(path))
		out = {}
		for asm in reversed(d["assemblies"]):	# MASS's (the last) first: !BOOT's zx.* are its own
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
		mpu.memory[0x100:StackTop - 1] = [StackFill] * (StackTop - 1 - 0x100)
		mpu.memory[StackTop] = ret >> 8
		mpu.memory[StackTop - 1] = ret & 0xFF
		mpu.sp = (StackTop - 2) & 0xFF
		mpu.pc = self.sym[routine] if isinstance(routine, str) else routine
		start = mpu.processorCycles
		while mpu.pc != Sentinel:
			mpu.step()
			if mpu.processorCycles - start > max_cycles:
				raise RuntimeError(f"{routine}: still running after {max_cycles} cycles, pc &{mpu.pc:04X}")
		low = next((a for a in range(0x100, StackTop - 1) if mpu.memory[a] != StackFill), StackTop - 1)
		self.stack_depth = max(self.stack_depth, StackTop + 1 - low)
		return mpu.processorCycles - start
