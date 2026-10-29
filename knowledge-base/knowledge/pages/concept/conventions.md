# 单位 坐标与布局约定

SI 单位、XYZW 四元数与参考系。

## 机制与数据流

位置、质量、时间等采用官方约定；关节与刚体空间向量要同时注明线性/角度顺序、参考系和参考点。实际数组布局以 Control/State 字段文档为准。

## 诊断与边界

FREE/DISTANCE 的 joint_qd 与 joint_f 均以 child COM 为参考点，区别是表达参考系：joint_qd 在 joint parent frame，joint_f 在 world frame。body_qd=(v_COM, omega) 与 body_f=(force, torque_COM) 均为 world-frame、线性分量在前。不要把参考系旋转误作参考点平移。Control.clear(model) 可避免 coord layout 中四元数目标被零填坏。



## 最小布局速查

| 数组 | 分量顺序 | 表达参考系 / 参考点 |
|---|---|---|
| body_q | 位置XYZ + 四元数XYZW | body origin的world姿态 |
| body_qd | 线速度3 + 角速度3 | world / COM |
| body_f | 力3 + 力矩3 | world / COM |
| FREE/DISTANCE joint_qd | child线速度3 + 角速度3 | joint parent frame / child COM |
| FREE/DISTANCE joint_f | 力3 + 力矩3 | world / child COM |

旋转分量到另一个参考系和把twist/wrench平移到另一个参考点是不同变换。质心COM与body origin通常不同，但上表两种FREE/DISTANCE数组之间的区别是frame，不能重复施加COM平移。依据：[State的body与joint布局](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/state.py#L109-L165)；[Control wrench约定](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/control.py#L32-L42)。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/conventions.html)。

## 固定版本原始出处

- [docs/concepts/conventions.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/conventions.rst#L1)
- [newton/_src/sim/state.py:109](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/state.py#L109-L165)
- [newton/_src/sim/control.py:32](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/control.py#L32-L42)
