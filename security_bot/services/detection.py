"""Sliding-window rate tracking for anti-nuke and anti-raid triggers."""
from __future__ import annotations

import time
from collections import deque
from typing import Dict, Optional, Tuple


class SlidingWindow:
    def __init__(self, window_seconds: float) -> None:
        self.window = float(window_seconds)
        self._events: Dict[str, deque] = {}

    def hit(self, key: str, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        dq = self._events.setdefault(key, deque())
        dq.append(now)
        self._expire(key, now)
        return len(dq)

    def count(self, key: str, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        self._expire(key, now)
        return len(self._events.get(key, ()))

    def reset(self, key: str) -> None:
        self._events.pop(key, None)

    def _expire(self, key: str, now: float) -> None:
        dq = self._events.get(key)
        if not dq:
            return
        while dq and now - dq[0] > self.window:
            dq.popleft()


class RateDetector:
    """Per-(guild, metric) sliding window with a trigger cooldown.

    record() returns True exactly once when the threshold is crossed,
    then stays silent for cooldown_seconds to avoid punishment storms.
    """

    def __init__(self, cooldown_seconds: float = 30.0) -> None:
        self.cooldown = float(cooldown_seconds)
        self._windows: Dict[Tuple[int, str], SlidingWindow] = {}
        self._last_trigger: Dict[Tuple[int, str], float] = {}

    def record(
        self,
        guild_id: int,
        metric: str,
        threshold: int,
        window_seconds: float,
        now: Optional[float] = None,
    ) -> bool:
        now = time.time() if now is None else now
        key = (guild_id, metric)
        window = self._windows.get(key)
        if window is None or window.window != float(window_seconds):
            window = self._windows[key] = SlidingWindow(window_seconds)

        count = window.hit(metric, now)
        if count < threshold:
            return False

        last = self._last_trigger.get(key, 0.0)
        if now - last < self.cooldown:
            return False

        self._last_trigger[key] = now
        window.reset(metric)
        return True

    def count(self, guild_id: int, metric: str, now: Optional[float] = None) -> int:
        window = self._windows.get((guild_id, metric))
        if window is None:
            return 0
        return window.count(metric, now)

    def reset(self, guild_id: int, metric: str) -> None:
        key = (guild_id, metric)
        if key in self._windows:
            self._windows[key].reset(metric)
        self._last_trigger.pop(key, None)