import os
import subprocess
import sys
from datetime import datetime
from importlib.metadata import distribution
from pathlib import Path

import cron_mini

ROOT = Path(__file__).resolve().parents[1]


def run_cli(console, *args, cwd):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    env.pop("PYTHONUTF8", None)
    result = subprocess.run([str(console), *args], cwd=cwd, capture_output=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout.decode("utf-8")


def main():
    module_path = Path(cron_mini.__file__).resolve()
    if module_path == (ROOT / "cron_mini" / "__init__.py").resolve():
        raise RuntimeError(f"cron_mini 仍从源码目录导入：{module_path}")

    package = distribution("cron-mini")
    if package.version != "0.1.1":
        raise RuntimeError(f"版本不符：{package.version}")

    scripts_dir = Path(sys.executable).parent
    console = scripts_dir / ("cron-mini.exe" if os.name == "nt" else "cron-mini")
    if not console.exists():
        raise RuntimeError(f"控制台脚本不存在：{console}")

    version = run_cli(console, "--version", cwd=ROOT)
    if "cron-mini 0.1.1" not in version:
        raise RuntimeError(f"控制台脚本版本检查失败：{version!r}")

    output = run_cli(console, "next", "0 12 1 * 0-6", "--now", "2026-03-02T00:00", cwd=ROOT)
    if "2026-03-02 12:00:00" not in output:
        raise RuntimeError(f"显式星期范围语义不正确：{output!r}")

    output = run_cli(console, "next", "* * * * *", "--now", "2024-02-29T10:00", cwd=ROOT)
    if "2024-02-29 10:01:00" not in output:
        raise RuntimeError(f"闰年起始日期不正确：{output!r}")

    output = run_cli(console, "explain", "0 9 * * 1-5", cwd=ROOT)
    if "星期一二三四五" not in output:
        raise RuntimeError(f"中文输出不是 UTF-8：{output!r}")

    result = cron_mini.next_after("0 12 1-31 * 0", datetime(2026, 3, 2, 0, 0))
    if result != datetime(2026, 3, 2, 12, 0):
        raise RuntimeError(f"库调用结果不正确：{result}")

    print("Installed wheel smoke test passed")


if __name__ == "__main__":
    main()
