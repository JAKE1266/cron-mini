"""命令行入口：

    python -m cron_mini next "*/5 * * * *" --now 2026-03-04T10:07 --count 3
    python -m cron_mini explain "0 9 * * 1-5"
    python -m cron_mini validate "0 0 29 2 *"
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from . import __version__
from .core import CronError, explain, iter_between, parse


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cron-mini", description="cron 表达式解析与下次执行时间")
    ap.add_argument("--version", action="version", version=f"cron-mini {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("next", help="计算之后的执行时刻")
    sp.add_argument("expr")
    sp.add_argument("--now", help="基准时刻（ISO，缺省当前时间）")
    sp.add_argument("--count", type=int, default=1, help="列出接下来 N 次（默认 1）")

    sp = sub.add_parser("explain", help="中文解释表达式")
    sp.add_argument("expr")

    sp = sub.add_parser("validate", help="校验表达式合法性")
    sp.add_argument("expr")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "next":
            base = datetime.fromisoformat(args.now) if args.now else datetime.now()
            expr = parse(args.expr)
            for i, t in zip(range(args.count), iter_between(expr, base, base.replace(year=base.year + 5))):
                print(f"{i + 1}: {t:%Y-%m-%d %H:%M:%S} ({t:%A})")
        elif args.cmd == "explain":
            info = explain(args.expr)
            print(info["summary"])
            for k, v in info["fields"].items():
                print(f"  {k:<8}{v}")
        else:
            parse(args.expr)
            print("表达式合法")
        return 0
    except CronError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"参数错误：{e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
