import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "firmware"))

from breath import BreathMapper  # noqa: E402

AMBIENT = 1013.25


def make(**kw):
    args = dict(threshold=0.5, full_scale=25.0, curve=1.0, smoothing=1.0)
    args.update(kw)
    m = BreathMapper(**args)
    m.set_baseline(AMBIENT)
    return m


def run(m, deltas):
    """Feed a list of deltas above ambient, return the final value."""
    for d in deltas:
        m.update(AMBIENT + d)
    return m.value


def test_silent_at_ambient():
    m = make()
    assert run(m, [0.0] * 50) == 0


def test_noise_below_threshold_stays_zero():
    m = make(threshold=0.5)
    noise = [0.02 * math.sin(i) for i in range(200)]
    assert run(m, noise) == 0


def test_suction_clamps_to_zero():
    m = make()
    assert run(m, [-5.0, -20.0]) == 0


def test_full_scale_hits_127():
    m = make(full_scale=25.0)
    assert run(m, [25.0]) == 127
    assert run(m, [60.0]) == 127


def test_linear_midpoint():
    m = make(threshold=0.0, full_scale=20.0, curve=1.0)
    assert run(m, [10.0]) == 64  # round(0.5 * 127)


def test_monotonic():
    m = make(smoothing=1.0)
    values = [run(m, [d]) for d in [x * 0.5 for x in range(0, 60)]]
    assert values == sorted(values)
    assert values[0] == 0 and values[-1] == 127


def test_curve_below_one_boosts_quiet_end():
    linear = make(threshold=0.0, full_scale=20.0, curve=1.0)
    soft = make(threshold=0.0, full_scale=20.0, curve=0.5)
    assert run(soft, [5.0]) > run(linear, [5.0])
    # Ends are unchanged.
    assert run(soft, [0.0]) == run(linear, [0.0]) == 0
    assert run(soft, [20.0]) == run(linear, [20.0]) == 127


def test_update_returns_none_when_unchanged():
    m = make()
    assert m.update(AMBIENT + 10.0) is not None
    assert m.update(AMBIENT + 10.0) is None
    assert m.update(AMBIENT + 10.0001) is None


def test_smoothing_lags_then_converges():
    m = make(smoothing=0.2)
    first = m.update(AMBIENT + 25.0)
    assert 0 < first < 127
    run(m, [25.0] * 100)
    assert m.value == 127


def test_baseline_tracks_drift_when_idle():
    m = make(threshold=0.5, baseline_track=0.05)
    # Ambient creeps up by 0.3 hPa, below threshold; baseline should follow.
    run(m, [0.3] * 500)
    assert abs(m.baseline - (AMBIENT + 0.3)) < 0.01
    assert m.value == 0


def test_baseline_does_not_track_while_blowing():
    m = make(threshold=0.5, baseline_track=0.05)
    run(m, [15.0] * 500)
    assert m.baseline == AMBIENT
    assert m.value > 0


def test_14bit_output_and_msb_lsb():
    m = make(threshold=0.0, full_scale=20.0, bits=14)
    assert run(m, [20.0]) == 16383
    assert m.msb == 127 and m.lsb == 127
    run(m, [10.0])
    assert m.value == 8192  # round(0.5 * 16383)
    assert (m.msb << 7) | m.lsb == m.value


def test_7bit_msb_is_value():
    m = make()
    run(m, [12.0])
    assert m.msb == m.value
    assert 0 <= m.msb <= 127


def test_invalid_config():
    with pytest.raises(ValueError):
        BreathMapper(threshold=5.0, full_scale=5.0)
    with pytest.raises(ValueError):
        BreathMapper(threshold=0.0, full_scale=5.0, bits=8)
