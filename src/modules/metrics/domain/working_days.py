from calendar import monthrange
from datetime import date, timedelta


def _easter(year: int) -> date:
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month = (h + m - 7 * n + 114) // 31
    day = ((h + m - 7 * n + 114) % 31) + 1
    return date(year, month, day)


class WorkingDays:
    def _holidays(self, year: int) -> set[str]:
        easter = _easter(year)
        fixed = [
            f"{year}-01-01", f"{year}-04-21", f"{year}-05-01", f"{year}-09-07",
            f"{year}-10-12", f"{year}-11-02", f"{year}-11-15", f"{year}-11-20", f"{year}-12-25",
        ]
        movable = [(easter + timedelta(days=n)).isoformat() for n in (-48, -47, -2, 60)]
        return set(fixed) | set(movable)

    def is_holiday(self, d: date) -> bool:
        return d.isoformat() in self._holidays(d.year)

    def is_working_day(self, d: date) -> bool:
        return d.weekday() != 6 and not self.is_holiday(d)

    def count_working_days(self, start: date, end: date) -> int:
        count, cur = 0, start
        while cur <= end:
            if self.is_working_day(cur):
                count += 1
            cur += timedelta(days=1)
        return count

    def working_days_in_month(self, year: int, month: int) -> int:
        return self.count_working_days(date(year, month, 1), date(year, month, monthrange(year, month)[1]))

    def remaining_working_days(self, year: int, month: int, current_day: int) -> int:
        return self.count_working_days(date(year, month, current_day), date(year, month, monthrange(year, month)[1]))
