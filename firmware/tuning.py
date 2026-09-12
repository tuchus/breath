"""Live tuning of the breath mapping over MIDI.

The bench page (tools/bench.html) sends control changes on TUNE_CHANNEL;
the firmware applies them to the running BreathMapper and echoes the
current settings back on the same channel so the page's sliders stay in
sync. Pure Python, shared between CircuitPython and the desktop tests.
"""

TUNE_CHANNEL = 15  # 0-based, i.e. MIDI channel 16

CC_THRESHOLD = 20
CC_FULL_SCALE = 21
CC_CURVE = 22
CC_SMOOTHING = 23
CC_REZERO = 24
CC_REPORT = 25

# Slider value (0..127) <-> parameter, chosen so each CC step is a usable
# increment and the default constants land on a whole number.
_RANGES = {
    CC_THRESHOLD: (0.0, 6.35),     # 0.05 hPa per step
    CC_FULL_SCALE: (5.0, 68.5),    # 0.5 hPa per step
    CC_CURVE: (0.3, 2.0),
    CC_SMOOTHING: (0.05, 1.0),
}


def cc_to_param(cc, value):
    lo, hi = _RANGES[cc]
    return lo + (hi - lo) * (value & 0x7F) / 127.0


def param_to_cc(cc, param):
    lo, hi = _RANGES[cc]
    v = int((param - lo) / (hi - lo) * 127.0 + 0.5)
    return 0 if v < 0 else (127 if v > 127 else v)


def apply(mapper, cc, value):
    """Apply one tuning CC to the mapper.

    Returns "rezero" if the caller should re-measure ambient, "report" if
    it should send the current settings, a string naming the changed
    parameter, or None if the CC is not a tuning message.
    """
    if cc == CC_THRESHOLD:
        t = cc_to_param(cc, value)
        if t < mapper.full_scale:
            mapper.threshold = t
        return "threshold"
    if cc == CC_FULL_SCALE:
        fs = cc_to_param(cc, value)
        if fs > mapper.threshold:
            mapper.full_scale = fs
        return "full_scale"
    if cc == CC_CURVE:
        mapper.curve = cc_to_param(cc, value)
        return "curve"
    if cc == CC_SMOOTHING:
        mapper.smoothing = cc_to_param(cc, value)
        return "smoothing"
    if cc == CC_REZERO:
        return "rezero"
    if cc == CC_REPORT:
        return "report"
    return None


def report(mapper):
    """(cc, value) pairs describing the mapper's current settings."""
    return (
        (CC_THRESHOLD, param_to_cc(CC_THRESHOLD, mapper.threshold)),
        (CC_FULL_SCALE, param_to_cc(CC_FULL_SCALE, mapper.full_scale)),
        (CC_CURVE, param_to_cc(CC_CURVE, mapper.curve)),
        (CC_SMOOTHING, param_to_cc(CC_SMOOTHING, mapper.smoothing)),
    )


def settings_text(mapper):
    """The TUNING lines for code.py matching the mapper's current state."""
    return (
        "THRESHOLD_HPA = %.2f\nFULL_SCALE_HPA = %.1f\nCURVE = %.2f\nSMOOTHING = %.2f"
        % (mapper.threshold, mapper.full_scale, mapper.curve, mapper.smoothing)
    )


class ControlChangeParser:
    """Minimal MIDI byte-stream parser that yields (channel, cc, value).

    Handles running status and ignores everything that is not a control
    change, including system real-time bytes interleaved in a message.
    """

    def __init__(self):
        self._status = 0
        self._data = []

    def feed(self, data):
        out = []
        for b in data:
            if b >= 0xF8:          # real-time: ignore, does not affect status
                continue
            if b >= 0xF0:          # system common: cancels running status
                self._status = 0
                self._data = []
                continue
            if b & 0x80:           # new channel status
                self._status = b
                self._data = []
                continue
            if not self._status:
                continue
            self._data.append(b)
            kind = self._status & 0xF0
            need = 1 if kind in (0xC0, 0xD0) else 2
            if len(self._data) == need:
                if kind == 0xB0:
                    out.append((self._status & 0x0F, self._data[0], self._data[1]))
                self._data = []
        return out
