#!/usr/bin/env python3
"""Replay a synthetic breath phrase through BreathMapper and print the CC
output as an ASCII plot. Use it to get a feel for CURVE / SMOOTHING before
the hardware is on the bench:

    python3 tools/simulate.py --curve 0.7 --smoothing 0.35
    python3 tools/simulate.py --trace my_capture.txt   # lines from monitor.py

A trace file is any text whose lines contain "delta=<number>"; the monitor
tool prints exactly that, so you can paste a serial capture straight in.
"""

import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "firmware"))
from breath import BreathMapper  # noqa: E402

RATE = 140  # samples per second, same as the sensor ODR in code.py


def synthetic_phrase():
    """Attack, sustain with vibrato, decay, then a hard accent. In hPa."""
    out = []
    for i in range(int(RATE * 4.0)):
        t = i / RATE
        if t < 0.25:
            d = 0.0
        elif t < 0.6:
            d = 18.0 * (t - 0.25) / 0.35
        elif t < 2.0:
            d = 18.0 + 2.0 * math.sin(2 * math.pi * 5.5 * t)
        elif t < 2.5:
            d = 18.0 * (1 - (t - 2.0) / 0.5)
        elif t < 3.0:
            d = 0.0
        elif t < 3.1:
            d = 45.0 * (t - 3.0) / 0.1
        elif t < 3.5:
            d = 45.0 * (1 - (t - 3.1) / 0.4)
        else:
            d = 0.0
        d += 0.03 * math.sin(i * 1.7)  # sensor noise
        out.append(d)
    return out


def load_trace(path):
    pat = re.compile(r"delta=\s*(-?\d+(?:\.\d+)?)")
    deltas = []
    for line in Path(path).read_text().splitlines():
        m = pat.search(line)
        if m:
            deltas.append(float(m.group(1)))
    if not deltas:
        sys.exit("no 'delta=' values found in %s" % path)
    return deltas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--full-scale", type=float, default=25.0)
    ap.add_argument("--curve", type=float, default=0.7)
    ap.add_argument("--smoothing", type=float, default=0.35)
    ap.add_argument("--trace", help="text file with delta=... lines (from monitor.py)")
    ap.add_argument("--width", type=int, default=64, help="plot width in columns")
    args = ap.parse_args()

    deltas = load_trace(args.trace) if args.trace else synthetic_phrase()
    m = BreathMapper(args.threshold, args.full_scale, args.curve, args.smoothing)
    m.set_baseline(1013.25)

    sends = 0
    step = max(1, len(deltas) // 60)
    print("   t(s)  delta   cc  |" + "-" * args.width + "|")
    for i, d in enumerate(deltas):
        if m.update(1013.25 + d) is not None:
            sends += 1
        if i % step == 0:
            bar = "#" * (m.value * args.width // 127)
            print("%6.2f %6.1f  %3d  |%-*s|" % (i / RATE, d, m.value, args.width, bar))
    print("\n%d samples, %d CC messages sent (%.0f%% of samples)" % (len(deltas), sends, 100.0 * sends / len(deltas)))


if __name__ == "__main__":
    main()
