# 环境与兼容

依赖、设备与兼容条件。

Python、Warp、Newton 和可选后端依赖共同决定运行条件；以该 release 的 pyproject.toml、uv.lock 和兼容文档为准。MuJoCo native CPU 与 MuJoCo Warp 区别于计算设备 cpu/cuda；Warp 版本与驱动兼容单独核查。无 GPU 不意味着所有 solver 都不能运行。

安装工作流可用 uv sync --extra dev 或独立 venv；本库固定源码快照不应为试验安装而被修改。记录 Python、OS、Newton/Warp/backend 版本与设备。网页/MCP 是只读索引服务，读取不执行 solver。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 相关知识

- [topic:development-testing](#/record/topic%3Adevelopment-testing)
- [topic:migration-integrations](#/record/topic%3Amigration-integrations)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/guide/compatibility.html)。

## 固定版本原始出处

- [docs/guide/compatibility.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/compatibility.rst#L1)
- [pyproject.toml:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/pyproject.toml#L1)
- [docs/guide/installation.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/installation.rst#L1)
- [docs/guide/development.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/development.rst#L1)
