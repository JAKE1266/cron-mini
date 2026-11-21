import unittest
from datetime import datetime

from cron_mini.core import CronError, explain, iter_between, next_after, parse

DT = datetime(2026, 3, 4, 10, 7, 30)  # 周三 10:07:30，秒应被丢弃且严格晚于


def nxt(expr, after=DT):
    return next_after(expr, after)


class TestParse(unittest.TestCase):
    def test_basic_sets(self):
        e = parse("*/10 0-8 1,15 JAN-MAR MON-FRI")
        self.assertEqual(e.minutes, frozenset(range(0, 60, 10)))
        self.assertEqual(e.hours, frozenset(range(0, 9)))
        self.assertEqual(e.days, frozenset({1, 15}))
        self.assertEqual(e.months, frozenset({1, 2, 3}))
        self.assertEqual(e.weekdays, frozenset({1, 2, 3, 4, 5}))

    def test_aliases(self):
        self.assertEqual(parse("@daily").minutes, frozenset({0}))
        self.assertEqual(parse("@HOURLY").hours, frozenset(range(24)))
        self.assertEqual(parse("@weekly").weekdays, frozenset({0}))
        self.assertEqual(parse("@monthly").days, frozenset({1}))

    def test_dow_7_is_sunday(self):
        self.assertEqual(parse("0 0 * * 7").weekdays, frozenset({0}))
        self.assertEqual(parse("0 0 * * sun").weekdays, frozenset({0}))

    def test_invalid(self):
        bad = ["", "* * * *", "* * * * * *", "60 * * * *", "* 24 * * *",
               "* * 0 * *", "* * * 13 *", "* * * * 8", "*/0 * * * *",
               "5-1 * * * *", "abc * * * *", "* * * * fri-mon", "1,,2 * * * *"]
        for expr in bad:
            with self.assertRaises(CronError, msg=expr):
                parse(expr)


class TestNextAfter(unittest.TestCase):
    def test_every_5_minutes(self):
        self.assertEqual(nxt("*/5 * * * *"), datetime(2026, 3, 4, 10, 10))
        self.assertEqual(nxt("*/5 * * * *", datetime(2026, 3, 4, 10, 10)),
                         datetime(2026, 3, 4, 10, 15))  # 严格晚于

    def test_daily_at_9(self):
        self.assertEqual(nxt("0 9 * * *"), datetime(2026, 3, 5, 9, 0))  # 10:07 → 次日

    def test_weekday_jump(self):
        # 周三 10:07 之后，下一个工作日 9 点 = 周四
        self.assertEqual(nxt("0 9 * * 1-5"), datetime(2026, 3, 5, 9, 0))
        # 周五 10 点之后 → 下周一
        self.assertEqual(nxt("0 9 * * 1-5", datetime(2026, 3, 6, 12, 0)),
                         datetime(2026, 3, 9, 9, 0))

    def test_month_boundary(self):
        self.assertEqual(nxt("0 0 1 * *", datetime(2026, 3, 10, 0, 0)),
                         datetime(2026, 4, 1, 0, 0))
        self.assertEqual(nxt("0 0 1 1 *", datetime(2026, 5, 1, 0, 0)),
                         datetime(2027, 1, 1, 0, 0))  # 跨年

    def test_feb_29(self):
        self.assertEqual(nxt("0 0 29 2 *", datetime(2026, 1, 1, 0, 0)),
                         datetime(2028, 2, 29, 0, 0))  # 2028 是闰年

    def test_late_night(self):
        self.assertEqual(nxt("59 23 * * *", datetime(2026, 3, 4, 23, 59)),
                         datetime(2026, 3, 5, 23, 59))

    def test_dow_sunday_zero_and_seven(self):
        # 2026-03-08 是周日
        self.assertEqual(nxt("0 0 * * 0", datetime(2026, 3, 4, 0, 0)),
                         datetime(2026, 3, 8, 0, 0))
        self.assertEqual(nxt("0 0 * * 7", datetime(2026, 3, 4, 0, 0)),
                         datetime(2026, 3, 8, 0, 0))


class TestVixieDayOrWeekday(unittest.TestCase):
    def test_both_restricted_is_or(self):
        # 日 1,15 与 星期五 都受限 → 任一满足即触发
        e = parse("0 12 1,15 * 5")
        self.assertEqual(next_after(e, datetime(2026, 3, 4, 0, 0)),
                         datetime(2026, 3, 6, 12, 0))   # 周五先到
        self.assertEqual(next_after(e, datetime(2026, 3, 6, 13, 0)),
                         datetime(2026, 3, 13, 12, 0))  # 3/13 也是周五
        self.assertEqual(next_after(e, datetime(2026, 3, 13, 13, 0)),
                         datetime(2026, 3, 15, 12, 0))  # 之后才是 15 号

    def test_one_restricted_is_and(self):
        # 仅限制日 → 忽略星期字段
        e = parse("0 12 1,15 * *")
        self.assertEqual(next_after(e, datetime(2026, 3, 4, 0, 0)),
                         datetime(2026, 3, 15, 12, 0))  # 3/6 周五不触发
        # 仅限制星期
        e2 = parse("0 12 * * 5")
        self.assertEqual(next_after(e2, datetime(2026, 3, 4, 0, 0)),
                         datetime(2026, 3, 6, 12, 0))


class TestIterBetween(unittest.TestCase):
    def test_daily_between(self):
        e = parse("0 9 * * *")
        got = list(iter_between(e, datetime(2026, 3, 4, 0, 0), datetime(2026, 3, 8, 0, 0)))
        self.assertEqual([t.day for t in got], [4, 5, 6, 7])  # 8 日 9 点不在区间内

    def test_hourly_count(self):
        e = parse("@hourly")
        got = list(iter_between(e, datetime(2026, 3, 4, 10, 7), datetime(2026, 3, 4, 14, 7)))
        self.assertEqual([t.hour for t in got], [11, 12, 13, 14])


class TestExplain(unittest.TestCase):
    def test_summary(self):
        self.assertEqual(explain("*/10 * * * *")["summary"], "每 10 分钟执行一次")
        self.assertEqual(explain("* * * * *")["summary"], "每分钟执行一次")
        self.assertEqual(explain("30 9 * * *")["summary"], "每天 9 点 30 分执行一次")
        info = explain("0 9 * * 1-5")
        self.assertEqual(info["fields"]["weekday"], "星期一二三四五")
        self.assertEqual(info["fields"]["day"], "每天")
        self.assertIn("组合时刻", info["summary"])

    def test_raw_preserved(self):
        self.assertEqual(explain("30 4 * * *")["raw"], "30 4 * * *")


if __name__ == "__main__":
    unittest.main()
