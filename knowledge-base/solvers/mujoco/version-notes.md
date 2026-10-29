# MuJoCo · 版本与边界

Newton 1.7.0，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。

## 固定版本与依赖

事实基线是 Newton 1.7.0；其 `pyproject.toml` 对 `mujoco` 和 `mujoco-warp` 使用 `~=3.15.0`。这不是本机已经安装这两个包的声明。MCP 读取知识无需安装物理后端。

## 支持边界

native CPU 与 MuJoCo Warp 可用的 solver/integrator/contacts/sleeping 组合并不完全相同。sleeping 要求 GPU、Newton 优化方法、MuJoCo contacts 与非 RK4 积分。native CPU 不消费外部 Newton contacts，use_mujoco_contacts=False 不能改变这一点。逐接触 force-space 增益修正属于 MuJoCo Warp 的 Newton-contacts 路径；native CPU 或内建检测路径不使用该逐接触因子。

## 实验状态

静态入库阶段未运行 MuJoCo A/B；后续 P4 已增加两组 native CPU 参数实验，见 [多 solver 参数实验](../../experiments/solver_parameter_lab/README.md)。VBD 的 17 组实验不构成 MuJoCo 验证。未知后端能力及新版本行为保持未知。


## 审核后覆盖与实验缺口

本节补齐主要模型转换导航和三组具体论文机制映射；保留的旧包装层 mapping 标为 implementation_fact，不能按条数当作论文机制覆盖率。参数目录是字段/默认/分支静态解释，不等于所有参数已充分实验。现有归档只支持各 case 记录的场景与 interventions；backend × contact-source 组合、state-sync interval 与逐步 control 的隔离对照、ref/limit 转换、过滤回退、tendon/equality/kinematic、cone/solver/收敛容差跨场景仍需专项验证。此次修复未新增或重跑物理实验。

## 关节、摩擦与接触的新增实测

已新增 12 组 native CPU 配对实验，48 次独立运行；8 组通过各自事前物理门槛。原两组迭代预算/ke-kd 接触响应实验继续保留。新增结果同时检查 Newton 输入、编译后的 MuJoCo 模型字段和实际响应，每设置独立进程重复两次。详见 [关节与碰撞实验](experiments.md)。


## 固定来源

- [newton/_src/solvers/mujoco/solver_mujoco.py:470](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L470)
- [docs/solvers/mujoco.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L5)
- [newton/_src/solvers/mujoco/solver_mujoco.py:4557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)
