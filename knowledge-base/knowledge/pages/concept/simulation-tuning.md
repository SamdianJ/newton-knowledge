# 仿真调参与诊断

先诊断、再调物理参数和数值预算。

## 机制与数据流

先构造最小复现，再检查几何/初态、control、质量与驱动、容量，最后调整接触模型和 solver 预算。一次 step 的 iterations 与每帧 substeps 对应不同误差来源。

## 诊断与边界

更硬未必更稳定；把 penetration、轨迹、能量、接触力与成本一起量测。默认值以固定源码为准，实验取值不自动成为通用建议区间。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/simulation_tuning.html)。

## 固定版本原始出处

- [docs/concepts/simulation_tuning.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/simulation_tuning.rst#L1)
