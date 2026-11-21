# cron-mini

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-17%20passing-success)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

零依赖的 cron 表达式解析与调度计算库 —— 下次执行时间、区间迭代、中文解释，5 字段标准语法。

- **完整 5 字段语法**：`*`、列表、区间、步进（含区间步进 `a-b/n`）、月份与星期英文名（`jan` / `mon-fri`）
- **@别名**：`@yearly` `@monthly` `@weekly` `@daily` `@midnight` `@hourly`
- **vixie 语义**：「日」与「星期」同时显式受限时按 **OR** 匹配（与 Linux cron 一致），否则按 AND
- **星期兼容**：0 与 7 都表示周日
- **跳跃式推进**：月不符跳月、日不符跳天，远快于逐分钟扫描；5 年兜底防死循环
- **中文解释**：`explain()` 输出各字段中文描述与汇总语句

零第三方依赖，Python ≥ 3.8。时间按本地朴素时间（naive datetime）处理，不做时区换算。

## 安装

```bash
pip install .
```

## 真实运行示例

```console
$ python -m cron_mini next "*/5 * * * *" --now 2026-03-04T10:07 --count 3
1: 2026-03-04 10:10:00 (Wednesday)
2: 2026-03-04 10:15:00 (Wednesday)
3: 2026-03-04 10:20:00 (Wednesday)

$ python -m cron_mini next "0 9 * * 1-5" --now 2026-03-06T12:00     # 周五中午 → 下周一
1: 2026-03-09 09:00:00 (Monday)

$ python -m cron_mini explain "30 9 * * 1-5"
在 第 30 分钟、第 9 小时、每天、每月、星期一二三四五 的组合时刻执行
  minute  第 30 分钟
  hour    第 9 小时
  day     每天
  month   每月
  weekday 星期一二三四五

$ python -m cron_mini validate "0 0 29 2 *"     # 闰年 2 月 29 日，合法
表达式合法
$ python -m cron_mini validate "* 24 * * *"
错误：hour 字段取值越界: '24'
```

## 作为库使用

```python
from datetime import datetime
from cron_mini import explain, iter_between, next_after, parse

next_after("0 9 * * 1-5", datetime(2026, 3, 6, 12, 0))
# datetime(2026, 3, 9, 9, 0)   周五之后 → 下周一

next_after("0 0 29 2 *", datetime(2026, 1, 1))
# datetime(2028, 2, 29, 0, 0)  闰年 2 月 29 日

for t in iter_between("@hourly", datetime(2026, 3, 4, 10, 7), datetime(2026, 3, 4, 14, 7)):
    print(t)   # 11:00, 12:00, 13:00, 14:00

explain("*/10 * * * *")["summary"]   # '每 10 分钟执行一次'
```

## 设计取舍

- **跳跃推进而非逐分钟扫描**：月不在集合 → 直接跳下月 1 日；日不匹配 → 跳次日 0 点；这样 `0 0 29 2 *` 这类稀疏表达式也能瞬间算完
- **严格晚于**：`next_after` 永远返回严格晚于基准时刻的下一跳，方便连续迭代不重复
- **vixie 日/星期规则**：两者都受限时取并集，是标准 cron 的历史行为，实现与文档一致并配有专项测试
- **秒被丢弃**：cron 粒度是分钟，输入秒一律截断

## 运行测试

```bash
python -m unittest discover -s tests
# Ran 17 tests ... OK
```


## 📁 项目结构

```
cron-mini/
├── LICENSE
├── cron_mini/
├── pyproject.toml
├── tests/
└── README.md
```

## License

MIT
