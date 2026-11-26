# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式,
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.1] - 2026-11-26

### 修复
- 显式写满值域的日/星期字段（如 `1-31`、`0-6`）现在按受限字段参与 vixie OR 语义
- 从闰年 2 月 29 日起计算执行时间不再触发日期越界
- CLI 的五年迭代上限同样兼容闰年起始日期
- Windows 旧编码环境下 CLI 中文输出统一为 UTF-8

### 变更
- Ubuntu CI 固定为 24.04，避免 Python 3.9 在滚动 runner 上缺失
- CI 构建并检查 wheel/sdist，三系统矩阵改为安装真实 wheel 后运行冒烟与测试
- 单元测试增至 24 个

## [0.1.0] - 2026-11-21

### 新增
- 核心功能实现(纯标准库,零第三方依赖)
- CLI 命令行入口
- 17 个单元测试
- GitHub Actions 三系统 × 多版本 CI
- 中文 README 与 MIT 许可证

### 变更
- 补齐徽章、项目结构与本日志,与其他仓库文档标准统一
