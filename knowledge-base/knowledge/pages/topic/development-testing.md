# 开发规范与 Newton 测试

Newton coding style、公共 API 与测试入口。

__all__ 是公开导出的权威；通过 newton.* 公开路径导入，_src 是内部实现。命名采用 Solver*/Viewer*/IKObjective* 等共同前缀；保持可选 backend 懒加载，experimental 和弃用边界明确，避免不相关清理或破坏兼容。

Newton 上游测试入口：`uv run --extra dev -m newton.tests` 或 `python -m newton.tests`。默认最多 8 进程，资源不足用 `--jobs 4` 或 `--serial-fallback`。示例可 `python -m newton.tests.test_examples -k test_basic.example_basic_shapes`。代码检查用 `uvx pre-commit run -a`；覆盖率可 `--coverage --coverage-html htmlcov`。

这些是固定官方开发命令，本文没有执行上游完整测试。知识库自身的数据/网站/MCP/物理实验验收单独记录，不用 RoboSimStudio 的测试 tier 替代 Newton 测试。

## Examples 的校验钩子

每个 Newton example 必须实现 `test_final()`；可选 `test_post_step()` 在每仿真步后检查，`test_final()` 在示例结束时检查。失败要区分环境/设备/依赖、数值非有限、物理断言和性能问题；跳过或环境受限不能记为测试通过。类型/签名、单位、docstring 和 Warp 数组布局按 CODING_GUIDELINES.rst；本文只列命令和规定，没有伪造上游执行结果。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 相关知识

- [topic:environment](#/record/topic%3Aenvironment)
- [topic:migration-integrations](#/record/topic%3Amigration-integrations)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/guide/development.html)。

## 固定版本原始出处

- [docs/guide/development.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/development.rst#L1)
- [CODING_GUIDELINES.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/CODING_GUIDELINES.rst#L1)
- [docs/guide/source_code_guidelines.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/source_code_guidelines.rst#L1)
- [newton/tests/__main__.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/tests/__main__.py#L1)
