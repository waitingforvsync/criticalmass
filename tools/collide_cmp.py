"""Compare collision-distance methods: the sketch's trig chain, exact squares, and log tables.

Units: 1 = one scanline (x is in half Mode 2 pixels, so space is square). Ball radii follow the
original scaled to a 64-pixel well: r(s) = 1.28 + 3.2*s units.
"""
import math
import random

# --- the sketch's tables, verbatim ---
k = math.pi / 512
atan = [round(math.atan(x / 256) / k) for x in range(256)]
cos = [round(math.cos(x * k) * 256) & 0xFF for x in range(256)]
cos_valid = math.ceil(math.acos(255.5 / 256) / k)
multab = [x * x // 4 for x in range(512)]
mulnegtab = [(x - 255) * (x - 255) // 4 for x in range(512)]
reciplo = [min(round(65536 / max(1, x)), 0xFFFF) & 0xFF for x in range(256)]
reciphi = [min(round(65536 / max(1, x)), 0xFFFF) >> 8 for x in range(256)]


def mul_int_int(a, b):
    return multab[a + b] - mulnegtab[a + (b ^ 0xFF)]


def mul_int_frac(a, b):
    return (multab[a + b] - mulnegtab[a + (b ^ 0xFF)] + 128) >> 8


def div_int_frac(a, b):
    return mul_int_int(a, reciphi[b]) + mul_int_frac(a, reciplo[b])


def sketch_overlap(absdx, absdy, radii):
    """The sketch's overlap and push, from whole-unit |dx|, |dy| (as it stores them)."""
    if absdx < absdy:
        lo, hi, swap = absdx, absdy, False
    else:
        lo, hi, swap = absdy, absdx, True
    if lo == hi:
        dist = div_int_frac(hi, cos[128])
        ov = radii - dist
        a = mul_int_frac(ov, cos[128]) if ov > 0 else 0
        return ov, a, a
    ang = atan[div_int_frac(lo, hi)]
    if ang >= cos_valid:
        dist = div_int_frac(hi, cos[ang])
        ov = radii - dist
        if ov <= 0:
            return ov, 0, 0
        along = mul_int_frac(ov, cos[ang])
    else:
        ov = radii - hi
        if ov <= 0:
            return ov, 0, 0
        along = ov
    across = mul_int_frac(ov, cos[(256 - ang) & 0xFF])
    return (ov, along, across) if not swap else (ov, along, across)


# --- squares: exact from the same quarter-square table, inputs in 1/q units ---
def squares_overlap(dx, dy, radii, q):
    ix, iy, ir = round(abs(dx) * q), round(abs(dy) * q), round(radii * q)
    assert ix < 256 and iy < 256 and ir < 256
    d2 = multab[2 * ix] + multab[2 * iy]      # x^2 = multab[2x], exact
    r2 = multab[2 * ir]
    diff = r2 - d2
    if diff <= 0:
        return 0.0
    return diff / (2 * ir) / q                # linearised: (R^2 - d^2) / 2R


# --- logs: 8-bit log/exp tables (log2 * 32, Elite-style) for the distance itself ---
LOG = [0] + [round(math.log2(x) * 32) for x in range(1, 256)]


def logs_overlap(dx, dy, radii, q):
    ix, iy = round(abs(dx) * q), round(abs(dy) * q)
    hi, lo = max(ix, iy), min(ix, iy)
    if lo == 0:
        d = hi
    else:
        u = LOG[hi] - LOG[lo]                  # log2(hi/lo) * 32
        h = round(0.5 * math.log2(1 + 2 ** (-2 * u / 32)) * 32)   # an 8-bit table on u
        d = 2 ** ((LOG[hi] + h) / 32)
    return radii - d / q


def radius(s):
    return 1.28 + 3.2 * s


def trial(n=20000, seed=1):
    rnd = random.Random(seed)
    errs = {"sketch (whole units)": [], "sketch, 1/2 unit": [], "squares, 1/2 unit": [], "squares, 1/4 unit": [],
            "logs, 1/2 unit": []}
    for _ in range(n):
        s0, s1 = rnd.randint(1, 9), rnd.randint(1, 9)
        R = radius(s0) + radius(s1)
        ov = rnd.uniform(0.0, 3.0)                # the overlaps that matter: resting contacts
        th = rnd.uniform(0, math.pi / 2)
        d = R - ov
        dx, dy = d * math.cos(th), d * math.sin(th)
        # the sketch stores whole-unit positions and radii: truncate as the 6502 would
        so, _, _ = sketch_overlap(int(abs(dx)), int(abs(dy)), int(R))
        errs["sketch (whole units)"].append(so - ov)
        so, _, _ = sketch_overlap(round(abs(dx) * 2), round(abs(dy) * 2), round(R * 2))
        errs["sketch, 1/2 unit"].append(so / 2 - ov)
        if R * 4 < 256:
            errs["squares, 1/4 unit"].append(squares_overlap(dx, dy, R, 4) - ov * (1 - ov / (2 * R)))
        errs["squares, 1/2 unit"].append(squares_overlap(dx, dy, R, 2) - ov * (1 - ov / (2 * R)))
        errs["logs, 1/2 unit"].append(logs_overlap(dx, dy, R, 2) - ov)
    for name, e in errs.items():
        e.sort()
        rms = math.sqrt(sum(x * x for x in e) / len(e))
        print(f"{name:24s} rms {rms:5.2f}  worst {max(abs(e[0]), abs(e[-1])):5.2f}  "
              f"(units, n={len(e)})")


trial()
