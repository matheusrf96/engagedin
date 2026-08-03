from __future__ import annotations

from datetime import datetime


def _parse_hour_range(spec: str) -> tuple[int, int] | None:
    try:
        start_s, end_s = spec.split("-", 1)
        start = int(start_s.strip())
        end = int(end_s.strip())
    except ValueError:
        return None
    if not (0 <= start <= 23 and 0 <= end <= 23):
        return None
    return start, end


def is_best_time(now: datetime, best_times: list[str]) -> bool:
    """Return True if `now` falls within any best posting hour range.

    Ranges use inclusive hours in the format "7-9". Ranges that wrap
    around midnight (e.g. "22-2") are supported.
    """
    hour = now.hour
    for spec in best_times:
        parsed = _parse_hour_range(spec)
        if parsed is None:
            continue
        start, end = parsed
        if start <= end:
            if start <= hour <= end:
                return True
        elif hour >= start or hour <= end:
            return True
    return False
