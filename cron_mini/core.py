"""cron 表达式解析与调度计算（5 字段标准 cron + @别名）。

字段：分钟 小时 日 月 星期（0=周日，7 也视为周日）。
支持：``*``、列表、区间、步进（含区间步进 ``a-b/n``）、月份与星期英文名（jan..dec / sun..sat）。

语义：vixie cron —— 若「日」与「星期」**都被显式限制**（均非 ``*``），则按 OR 匹配；
只限制其一或都未限制时按 AND 匹配。
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta

_FIELD_NAMES = {
    "minute": (0, 59, {}),
    "hour": (0, 23, {}),
    "day": (1, 31, {}),
    "month": (1, 12, {name: i + 1 for i, name in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun",
         "jul", "aug", "sep", "oct", "nov", "dec"])}),
    "weekday": (0, 7, {name: i for i, name in enumerate(
        ["sun", "mon", "tue", "wed", "thu", "fri", "sat"])}),
}

_ALIASES = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}


class CronError(ValueError):
    """cron 表达式不合法。"""


@dataclass(frozen=True)
class CronExpr:
    """解析后的表达式：各字段为允许值集合；``raw`` 保留原文。"""

    minutes: frozenset[int]
    hours: frozenset[int]
    days: frozenset[int]
    months: frozenset[int]
    weekdays: frozenset[int]
    raw: str

    @property
    def day_restricted(self) -> bool:
        return self.days != frozenset(range(1, 32))

    @property
    def weekday_restricted(self) -> bool:
        return self.weekdays != frozenset(range(7))


def _parse_field(spec: str, field: str) -> frozenset[int]:
    low, high, names = _FIELD_NAMES[field]
    allowed = frozenset(range(low, high + 1))
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip().lower()
        if not part:
            raise CronError(f"{field} 字段存在空子项: {spec!r}")
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            if not step_s.isdigit() or int(step_s) < 1:
                raise CronError(f"{field} 字段步进非法: {spec!r}")
            step = int(step_s)
            if "/" in step_s:
                raise CronError(f"{field} 字段含多个 '/': {spec!r}")
        if part == "*":
            values = allowed
        elif "-" in part and not part.startswith("-"):
            a, b = part.split("-", 1)
            lo, hi = _value_of(a, names, field), _value_of(b, names, field)
            if lo is None or hi is None or lo > hi or lo < low or hi > high:
                raise CronError(f"{field} 字段区间越界: {spec!r}")
            values = frozenset(range(lo, hi + 1))
        else:
            v = _value_of(part, names, field)
            if v is None or v < low or v > high:
                raise CronError(f"{field} 字段取值越界: {spec!r}")
            values = frozenset([v])
        if step > 1:
            seq = sorted(values)
            out.update(seq[::step])
        else:
            out.update(values)
    if not out:
        raise CronError(f"{field} 字段为空: {spec!r}")
    invalid = out - allowed
    if invalid:
        raise CronError(f"{field} 字段取值越界: {sorted(invalid)}")
    return frozenset(out)


def _value_of(text: str, names: dict[str, int], field: str) -> int | None:
    if text in names:
        return names[text]
    if text.isdigit():
        return int(text)
    raise CronError(f"{field} 字段含非法记号: {text!r}")


def parse(expr: str) -> CronExpr:
    """解析 5 字段 cron 或 @别名；失败抛 CronError。"""
    if not isinstance(expr, str) or not expr.strip():
        raise CronError("表达式为空")
    s = expr.strip()
    s = _ALIASES.get(s.lower(), s)
    fields = s.split()
    if len(fields) != 5:
        raise CronError(f"需要 5 个字段（分钟 小时 日 月 星期），收到 {len(fields)} 个: {expr!r}")
    minutes = _parse_field(fields[0], "minute")
    hours = _parse_field(fields[1], "hour")
    days = _parse_field(fields[2], "day")
    months = _parse_field(fields[3], "month")
    weekdays = _parse_field(fields[4], "weekday")
    weekdays = frozenset(0 if w == 7 else w for w in weekdays)  # 7 也是周日
    return CronExpr(minutes, hours, days, months, weekdays, raw=expr.strip())


def _day_ok(expr: CronExpr, t: datetime) -> bool:
    dom_ok = t.day in expr.days
    cron_wd = (t.weekday() + 1) % 7  # 周一=1 ... 周日=0
    dow_ok = cron_wd in expr.weekdays
    if expr.day_restricted and expr.weekday_restricted:
        return dom_ok or dow_ok  # vixie 规则：两者都受限 → OR
    if expr.day_restricted:
        return dom_ok
    if expr.weekday_restricted:
        return dow_ok
    return True


def next_after(expr: CronExpr | str, after: datetime) -> datetime:
    """下一次执行时刻（严格晚于 ``after``，按本地朴素时间，分钟级精度）。

    采用跳跃式推进：月不符 → 直接跳到下月 1 日；日不符 → 跳到次日 0 点；
    时/分不符 → 逐级跳进，远快于逐分钟扫描。
    """
    if isinstance(expr, str):
        expr = parse(expr)
    t = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    limit = t.replace(year=t.year + 5)  # 兜底：最多向前找 5 年
    while t < limit:
        if t.month not in expr.months:
            m = t.month + 1
            year = t.year + (m > 12)
            m = m if m <= 12 else 1
            t = datetime(year, m, 1)
            continue
        if not _day_ok(expr, t):
            t = (t + timedelta(days=1)).replace(hour=0, minute=0)
            continue
        if t.hour not in expr.hours:
            t = t.replace(minute=0) + timedelta(hours=1)
            continue
        if t.minute not in expr.minutes:
            t += timedelta(minutes=1)
            continue
        return t
    raise CronError("5 年内未找到匹配时刻（请检查表达式）")


def iter_between(expr: CronExpr | str, start: datetime, end: datetime):
    """按时间顺序产出 (start, end] 内的全部执行时刻。"""
    if isinstance(expr, str):
        expr = parse(expr)
    t = next_after(expr, start)
    while t <= end:
        yield t
        t = next_after(expr, t)


def _describe_count(spec: str, low: int, high: int) -> str:
    full = set(range(low, high + 1))
    vals = set(int(x) for x in spec.replace("*", str(low)).split(",")) if spec else full
    if set(vals) == set(full):
        return "每"
    if spec.startswith("*/"):
        return f"每 {spec[2:]} "
    return ""


def explain(expr: CronExpr | str) -> dict:
    """人类可读解释：各字段中文描述 + 汇总一句。"""
    if isinstance(expr, str):
        expr = parse(expr)
    raw_fields = expr.raw.split()
    spec = raw_fields if len(raw_fields) == 5 else ["*", "*", "*", "*", "*"]

    def desc(unit: str, vals: frozenset[int], full_size: int, field_idx: int) -> str:
        if len(vals) == full_size:
            return f"每{unit}"
        if spec[field_idx].startswith("*/"):
            return f"每 {spec[field_idx][2:]} {unit}"
        if len(vals) == 1:
            return f"第 {sorted(vals)[0]} {unit}"
        return "第 " + "、".join(str(v) for v in sorted(vals)) + f" {unit}"

    minute_d = desc("分钟", expr.minutes, 60, 0)
    hour_d = desc("小时", expr.hours, 24, 1)
    day_d = "每天" if not expr.day_restricted else f"{len(expr.days)} 个日号"
    month_d = "每月" if len(expr.months) == 12 else f"{len(expr.months)} 个月份"
    if not expr.weekday_restricted:
        wd_d = "不限星期"
    else:
        names = "日一二三四五六"  # cron 星期 0=周日
        wd_d = "星期" + "".join(names[w] for w in sorted(expr.weekdays))

    full_minutes = len(expr.minutes) == 60
    full_hours = len(expr.hours) == 24
    full_month = len(expr.months) == 12
    if full_month and not expr.day_restricted and not expr.weekday_restricted:
        if full_minutes and full_hours:
            summary = "每分钟执行一次"
        elif full_hours and spec[0].startswith("*/"):
            summary = f"每 {spec[0][2:]} 分钟执行一次"
        elif full_hours:
            summary = f"每小时第 {spec[0]} 分执行一次"
        elif full_minutes and len(expr.hours) == 1:
            summary = f"每天 {sorted(expr.hours)[0]} 点内每分钟执行一次"
        elif not full_hours and not full_minutes:
            summary = f"每天 {', '.join(str(h) for h in sorted(expr.hours))} 点 " \
                      f"{', '.join(str(m) for m in sorted(expr.minutes))} 分执行一次"
        else:
            summary = "组合调度"
    else:
        summary = (f"在 {minute_d}、{hour_d}、{day_d}、{month_d}、{wd_d} "
                   "的组合时刻执行")
    parts = {"minute": minute_d, "hour": hour_d, "day": day_d,
             "month": month_d, "weekday": wd_d}
    return {"summary": summary, "fields": parts, "raw": expr.raw}
