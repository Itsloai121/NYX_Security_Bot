from services.detection import RateDetector, SlidingWindow


def test_sliding_window_counts_within_window():
    window = SlidingWindow(10)
    assert window.hit("k", now=100.0) == 1
    assert window.hit("k", now=105.0) == 2
    assert window.count("k", now=109.0) == 2


def test_sliding_window_expires_old_events():
    window = SlidingWindow(10)
    window.hit("k", now=100.0)
    window.hit("k", now=105.0)
    assert window.count("k", now=120.0) == 0


def test_rate_detector_triggers_at_threshold():
    detector = RateDetector(cooldown_seconds=30)
    assert detector.record(1, "channel_delete", 2, 10, now=100.0) is False
    assert detector.record(1, "channel_delete", 2, 10, now=101.0) is True


def test_rate_detector_ignores_slow_activity():
    detector = RateDetector(cooldown_seconds=30)
    assert detector.record(1, "ban", 3, 10, now=100.0) is False
    assert detector.record(1, "ban", 3, 10, now=115.0) is False
    assert detector.record(1, "ban", 3, 10, now=130.0) is False


def test_rate_detector_cooldown_blocks_repeat_trigger():
    detector = RateDetector(cooldown_seconds=30)
    detector.record(1, "role_delete", 2, 10, now=100.0)
    assert detector.record(1, "role_delete", 2, 10, now=101.0) is True
    assert detector.record(1, "role_delete", 2, 10, now=102.0) is False
    assert detector.record(1, "role_delete", 2, 10, now=140.0) is True