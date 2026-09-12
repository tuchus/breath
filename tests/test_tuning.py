import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "firmware"))

import tuning  # noqa: E402
from breath import BreathMapper  # noqa: E402


def make():
    return BreathMapper(threshold=0.5, full_scale=25.0, curve=0.7, smoothing=0.35)


def test_cc_param_round_trip():
    for cc in (tuning.CC_THRESHOLD, tuning.CC_FULL_SCALE, tuning.CC_CURVE, tuning.CC_SMOOTHING):
        for v in (0, 1, 63, 64, 126, 127):
            assert tuning.param_to_cc(cc, tuning.cc_to_param(cc, v)) == v


def test_defaults_representable():
    m = make()
    for cc, v in tuning.report(m):
        p = tuning.cc_to_param(cc, v)
        target = {
            tuning.CC_THRESHOLD: m.threshold,
            tuning.CC_FULL_SCALE: m.full_scale,
            tuning.CC_CURVE: m.curve,
            tuning.CC_SMOOTHING: m.smoothing,
        }[cc]
        assert abs(p - target) < 0.01


def test_apply_changes_parameters():
    m = make()
    assert tuning.apply(m, tuning.CC_FULL_SCALE, 127) == "full_scale"
    assert abs(m.full_scale - 68.5) < 1e-9
    assert tuning.apply(m, tuning.CC_CURVE, 0) == "curve"
    assert abs(m.curve - 0.3) < 1e-9
    assert tuning.apply(m, tuning.CC_SMOOTHING, 127) == "smoothing"
    assert abs(m.smoothing - 1.0) < 1e-9
    assert tuning.apply(m, tuning.CC_THRESHOLD, 20) == "threshold"
    assert abs(m.threshold - 1.0) < 1e-9


def test_apply_keeps_threshold_below_full_scale():
    m = make()
    tuning.apply(m, tuning.CC_FULL_SCALE, 0)      # full_scale = 5.0
    tuning.apply(m, tuning.CC_THRESHOLD, 127)     # 6.35 > 5.0, must be refused
    assert m.threshold == 0.5
    tuning.apply(m, tuning.CC_THRESHOLD, 80)      # 4.0 < 5.0, ok
    assert abs(m.threshold - 4.0) < 1e-9
    tuning.apply(m, tuning.CC_FULL_SCALE, 0)      # 5.0 > 4.0 still ok
    assert m.full_scale == 5.0
    m.threshold = 5.0
    tuning.apply(m, tuning.CC_FULL_SCALE, 0)      # 5.0 == threshold, refused
    assert m.full_scale == 5.0


def test_apply_actions_and_unknown():
    m = make()
    assert tuning.apply(m, tuning.CC_REZERO, 127) == "rezero"
    assert tuning.apply(m, tuning.CC_REPORT, 0) == "report"
    assert tuning.apply(m, 1, 64) is None
    assert tuning.apply(m, 2, 64) is None


def test_settings_text():
    m = make()
    assert tuning.settings_text(m) == (
        "THRESHOLD_HPA = 0.50\nFULL_SCALE_HPA = 25.0\nCURVE = 0.70\nSMOOTHING = 0.35"
    )


def test_parser_basic_cc():
    p = tuning.ControlChangeParser()
    assert p.feed(bytes([0xBF, 20, 100])) == [(15, 20, 100)]


def test_parser_running_status():
    p = tuning.ControlChangeParser()
    assert p.feed(bytes([0xB0, 2, 10, 2, 11, 2, 12])) == [(0, 2, 10), (0, 2, 11), (0, 2, 12)]


def test_parser_split_across_reads():
    p = tuning.ControlChangeParser()
    assert p.feed(bytes([0xBF, 21])) == []
    assert p.feed(bytes([64])) == [(15, 21, 64)]


def test_parser_ignores_other_messages_and_realtime():
    p = tuning.ControlChangeParser()
    stream = bytes([
        0x90, 60, 100,        # note on
        0xF8,                 # clock (real-time) mid-stream
        0xBF, 0xF8, 22, 0xFE, 50,  # CC with real-time bytes interleaved
        0xC0, 5,              # program change (1 data byte)
        0xD0, 7,              # channel pressure
        0xE0, 0, 64,          # pitch bend
        0xBF, 23, 1,
    ])
    assert p.feed(stream) == [(15, 22, 50), (15, 23, 1)]


def test_parser_sysex_cancels_running_status():
    p = tuning.ControlChangeParser()
    assert p.feed(bytes([0xBF, 20, 1, 0xF0, 0x7E, 0xF7, 20, 2])) == [(15, 20, 1)]


def test_parser_data_without_status_dropped():
    p = tuning.ControlChangeParser()
    assert p.feed(bytes([20, 1, 2, 3])) == []
