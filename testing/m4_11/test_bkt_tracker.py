import pytest
from m4_11_zpd_pipeline.bkt_tracker import BKTTracker


def test_bkt_initialization():
    tracker = BKTTracker()
    assert tracker.p_l0 == 0.30
    assert tracker.p_t == 0.15
    assert tracker.p_g == 0.10
    assert tracker.p_s == 0.10

    lower, upper = tracker.calculate_zpd_boundaries(0.30)
    assert lower == pytest.approx(0.10, rel=1e-2)
    assert upper == pytest.approx(0.55, rel=1e-2)


def test_bkt_update_on_success():
    tracker = BKTTracker()
    p_prev = 0.30
    p_next = tracker.update_mastery(p_prev=p_prev, is_success=True)

    # Calculation:
    # num = 0.30 * (1 - 0.10) = 0.27
    # den = 0.27 + (1 - 0.30) * 0.10 = 0.27 + 0.07 = 0.34
    # p_post = 0.27 / 0.34 = 0.7941
    # p_next = 0.7941 + (1 - 0.7941) * 0.15 = 0.825
    assert p_next > p_prev
    assert pytest.approx(p_next, rel=1e-2) == 0.825


def test_bkt_update_on_failure():
    tracker = BKTTracker()
    p_prev = 0.80
    p_next = tracker.update_mastery(p_prev=p_prev, is_success=False)

    # Calculation:
    # num = 0.80 * 0.10 = 0.08
    # den = 0.08 + (1 - 0.80) * (1 - 0.10) = 0.08 + 0.18 = 0.26
    # p_post = 0.08 / 0.26 = 0.3077
    # p_next = 0.3077 + (1 - 0.3077) * 0.15 = 0.4115
    assert p_next < p_prev
    assert pytest.approx(p_next, rel=1e-2) == 0.4115
