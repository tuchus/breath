"""Pressure-to-MIDI mapping for the breath controller.

Pure Python with no board dependencies, so the same file runs on the
microcontroller (CircuitPython) and on a desktop (CPython) for tests and
simulation.
"""


def clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


class BreathMapper:
    """Turn absolute pressure samples (hPa) into a MIDI controller value.

    :param threshold: hPa above ambient before the output starts to rise
    :param full_scale: hPa above ambient that gives the maximum value
    :param curve: exponent applied to the normalised 0..1 signal; < 1 makes
        the quiet end more sensitive, 1 is linear, > 1 compresses the low end
    :param smoothing: 0..1 weight of the newest sample in an exponential
        moving average; 1 means no smoothing
    :param baseline_track: per-sample rate at which the ambient baseline
        follows slow drift while the player is not blowing; 0 disables
    :param bits: 7 for a single CC (0..127), 14 for CC + LSB (0..16383)
    """

    def __init__(
        self,
        threshold,
        full_scale,
        curve=1.0,
        smoothing=1.0,
        baseline_track=0.0,
        bits=7,
    ):
        if full_scale <= threshold:
            raise ValueError("full_scale must be greater than threshold")
        if bits not in (7, 14):
            raise ValueError("bits must be 7 or 14")
        self.threshold = threshold
        self.full_scale = full_scale
        self.curve = curve
        self.smoothing = smoothing
        self.baseline_track = baseline_track
        self.max_value = (1 << bits) - 1

        self.baseline = None
        self.delta = 0.0
        self.smoothed = 0.0
        self.value = 0

    def set_baseline(self, pressure_hpa):
        """Set ambient pressure. Call once after averaging a quiet second."""
        self.baseline = float(pressure_hpa)
        self.smoothed = 0.0

    def update(self, pressure_hpa):
        """Feed one sample. Returns the new value if it changed, else None."""
        if self.baseline is None:
            self.set_baseline(pressure_hpa)

        self.delta = pressure_hpa - self.baseline

        if self.baseline_track and self.delta < self.threshold:
            self.baseline += self.baseline_track * self.delta

        self.smoothed += self.smoothing * (self.delta - self.smoothed)

        norm = clamp01((self.smoothed - self.threshold) / (self.full_scale - self.threshold))
        shaped = norm ** self.curve if norm > 0.0 else 0.0
        value = int(shaped * self.max_value + 0.5)

        if value == self.value:
            return None
        self.value = value
        return value

    @property
    def msb(self):
        return self.value >> 7 if self.max_value > 127 else self.value

    @property
    def lsb(self):
        return self.value & 0x7F
