"""Tune the physics: drop the same balls under different settings and measure the settled pile, as it's
seen (the drawn circles, not the physics ones).

	.venv/bin/python tools/tune.py [label=margin,kp16,kv16[,passes[,gravity]] ...]

With no settings it compares the original's constants with the game's. Each setting is averaged over six
seeds; each run drops 30 balls (sizes 1 to 6) one every 0.6 s at random places, runs on for 6 s, then
measures over 2 s more. Units are units (scanlines). Over the pairs touching at the end:
- deep, p90: the deepest drawn overlap, and the 90th percentile
- mean: the mean drawn overlap where there is one
- p10: the 10th percentile: negative is a gap between drawn circles that touch physically
- gap: the share of touching pairs whose drawn circles are more than a unit apart
And:
- impact: the deepest drawn overlap while the balls land
- wobble: how far balls move over the 2 s (rms of each ball's range of y)
- moves: how often a ball crosses a 2-unit cell a step (what the hysteresis has to hide)
- top: the pile's top, in lines from the screen's top (smaller is a taller pile)
"""

import math
import random
import sys

import shapes
import tables
from physics import Ball, One, Params, World, WellLeft, WellRight


def set_margin(m):
	shapes.Margin = m
	tables.build()


def drops(seed, count=30):
	rnd = random.Random(seed)
	out = []
	for _ in range(count):
		s = rnd.choice((1, 2, 2, 3, 3, 4, 4, 5, 6))
		r = shapes.draw_radius(s)
		out.append((s, rnd.uniform(WellLeft + r, WellRight - r)))
	return out


def drawn_overlaps(w):
	"""(drawn overlap, touching physically) for each pair near enough to matter."""
	out = []
	o = w.order
	for i, a in enumerate(o):
		for b in o[i + 1:]:
			d = math.hypot((a.x - b.x) / One, (a.y - b.y) / One)
			rd = shapes.draw_radius(a.size) + shapes.draw_radius(b.size)
			rp = tables.pair_r(a.size, b.size) / 4
			if d < rp + 2:
				out.append((rd - d, d < rp))
	return out


def pct(v, q):
	v = sorted(v)
	return v[min(len(v) - 1, int(q * len(v)))] if v else 0


def run(params, seed):
	w = World(params)
	rate = params.rate
	every = round(0.6 * rate)
	impact = 0.0
	for s, x in drops(seed):
		r = shapes.draw_radius(s)
		w.add(Ball(s, round(x * One), round((32 - r) * One), age=0))
		for _ in range(every):
			w.step()
			impact = max([impact] + [ov for ov, _ in drawn_overlaps(w)])
	for _ in range(6 * rate):
		w.step()
	ys = {id(b): [] for b in w.order}
	moves = 0
	last = {id(b): (b.x >> 9, b.y >> 9) for b in w.order}
	steps = 2 * rate
	for _ in range(steps):
		w.step()
		for b in w.order:
			ys[id(b)].append(b.y / One)
			pos = (b.x >> 9, b.y >> 9)
			moves += pos != last[id(b)]
			last[id(b)] = pos
	touching = [o for o, t in drawn_overlaps(w) if t]
	vis = [o for o in touching if o > 0]
	return dict(deep=max(touching, default=0), p90=pct(touching, 0.9), mean=sum(vis) / max(1, len(vis)),
				p10=pct(touching, 0.1), gap=sum(o < -1 for o in touching) / max(1, len(touching)),
				impact=impact, wobble=math.sqrt(sum((max(v) - min(v)) ** 2 for v in ys.values()) / len(ys)),
				moves=moves / (steps * len(w.order)),
				top=min(b.y / One - shapes.draw_radius(b.size) for b in w.order))


def main():
	configs = []
	for arg in sys.argv[1:]:
		label, spec = arg.split("=")
		configs.append((label, [float(x) for x in spec.split(",")]))
	if not configs:
		now = Params()
		configs = [("before (margin 0, kv 6)", [0, 11, 6]),
				   ("now", [shapes.Margin, round(now.kp * 16), round(now.kv * 16), now.passes])]
	margin = shapes.Margin
	print(f"{'':24s} {'deep':>5s} {'p90':>5s} {'mean':>5s} {'p10':>5s} {'gap':>5s} {'impact':>6s} "
		  f"{'wobble':>6s} {'moves':>6s} {'top':>5s}")
	for label, v in configs:
		set_margin(v[0])
		p = Params(kp=v[1] / 16, kv=v[2] / 16, passes=int(v[3]) if len(v) > 3 else 2,
				   gravity=v[4] if len(v) > 4 else Params.gravity, merge_age=999)
		rs = [run(p, s) for s in range(1, 7)]
		a = {k: sum(r[k] for r in rs) / len(rs) for k in rs[0]}
		print(f"{label:24s} {a['deep']:5.1f} {a['p90']:5.1f} {a['mean']:5.2f} {a['p10']:5.1f} {a['gap']:5.2f} "
			  f"{a['impact']:6.1f} {a['wobble']:6.2f} {a['moves']:6.3f} {a['top']:5.1f}")
		sys.stdout.flush()
	set_margin(margin)


if __name__ == "__main__":
	main()
