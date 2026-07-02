from datetime import date
from src.modules.metrics.domain.working_days import WorkingDays

w = WorkingDays()


def test_sunday_excluded_saturday_counts() -> None:
    assert w.is_working_day(date(2026, 1, 4)) is False
    assert w.is_working_day(date(2026, 1, 3)) is True


def test_fixed_holiday() -> None:
    assert w.is_working_day(date(2026, 12, 25)) is False


def test_movable_holiday_good_friday_2026() -> None:
    assert w.is_working_day(date(2026, 4, 3)) is False


def test_working_days_in_month_positive() -> None:
    assert w.working_days_in_month(2026, 2) > 20
