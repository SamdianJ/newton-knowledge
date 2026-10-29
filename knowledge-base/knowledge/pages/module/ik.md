# 逆运动学

逆运动学目标与迭代求解。

## 职责、输入与输出

IKSolver 将位置、旋转、关节限制等 IKObjective 组合到运动学优化问题，求解满足任务目标的关节配置。它与 newton.eval_ik 的表示转换、以及 controllers 的微分控制职责不同。

## 失败模式与限制

运动学目标不保证动力学可行或接触安全；之后要映射 Control 布局、选择驱动并经 solver 检验。

## 模块公开导出索引

- [IKJacobianType](#/record/symbol%3Anewton.ik.IKJacobianType)
- [IKObjective](#/record/symbol%3Anewton.ik.IKObjective)
- [IKObjectiveJointLimit](#/record/symbol%3Anewton.ik.IKObjectiveJointLimit)
- [IKObjectivePosition](#/record/symbol%3Anewton.ik.IKObjectivePosition)
- [IKObjectiveRotation](#/record/symbol%3Anewton.ik.IKObjectiveRotation)
- [IKOptimizer](#/record/symbol%3Anewton.ik.IKOptimizer)
- [IKOptimizerLBFGS](#/record/symbol%3Anewton.ik.IKOptimizerLBFGS)
- [IKOptimizerLM](#/record/symbol%3Anewton.ik.IKOptimizerLM)
- [IKSampler](#/record/symbol%3Anewton.ik.IKSampler)
- [IKSolver](#/record/symbol%3Anewton.ik.IKSolver)

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.ik.IKSolver](#/record/symbol%3Anewton.ik.IKSolver)
- [newton.ik.IKObjectivePosition](#/record/symbol%3Anewton.ik.IKObjectivePosition)
- [newton.ik.IKObjectiveRotation](#/record/symbol%3Anewton.ik.IKObjectiveRotation)

## 相关知识

- [topic:robot-control](#/record/topic%3Arobot-control)
- [recipe:ik-mujoco-contact](#/record/recipe%3Aik-mujoco-contact)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/api/newton_ik.html)。

## 固定版本原始出处

- [newton/ik.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/ik.py#L1)
- [docs/api/newton_ik.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_ik.rst#L1)
- [newton/_src/sim/ik/ik_solver.py:196](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/ik/ik_solver.py#L196)
- [newton/_src/sim/ik/ik_objectives.py:257](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/ik/ik_objectives.py#L257)
- [newton/_src/sim/ik/ik_objectives.py:875](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/ik/ik_objectives.py#L875)
