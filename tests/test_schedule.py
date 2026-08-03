from __future__ import annotations

from datetime import datetime

from engagedin.core.schedule import is_best_time

BEST_TIMES = ["7-9", "12-13", "17-18"]


def test_in_range() -> None:
    assert is_best_time(datetime(2026, 6, 9, 8, 0), BEST_TIMES) is True


def test_boundaries_inclusive() -> None:
    assert is_best_time(datetime(2026, 6, 9, 7, 0), BEST_TIMES) is True
    assert is_best_time(datetime(2026, 6, 9, 9, 59), BEST_TIMES) is True


def test_out_of_range() -> None:
    assert is_best_time(datetime(2026, 6, 9, 10, 0), BEST_TIMES) is False
    assert is_best_time(datetime(2026, 6, 9, 15, 0), BEST_TIMES) is False


def test_empty_list() -> None:
    assert is_best_time(datetime(2026, 6, 9, 8, 0), []) is False


def test_wraps_midnight() -> None:
    wrapped = ["22-2"]
    assert is_best_time(datetime(2026, 6, 9, 23, 0), wrapped) is True
    assert is_best_time(datetime(2026, 6, 9, 0, 30), wrapped) is True
    assert is_best_time(datetime(2026, 6, 9, 12, 0), wrapped) is False


def test_invalid_ranges_ignored() -> None:
    invalid = ["abc", "24-25", "-1-5", "7", ""]
    assert is_best_time(datetime(2026, 6, 9, 8, 0), invalid) is False


def test_mixed_valid_and_invalid() -> None:
    mixed = ["garbage", "12-13"]
    assert is_best_time(datetime(2026, 6, 9, 13, 0), mixed) is True
    assert is_best_time(datetime(2026, 6, 9, 8, 0), mixed) is False
