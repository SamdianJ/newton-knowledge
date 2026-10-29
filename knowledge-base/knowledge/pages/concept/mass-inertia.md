# 质量 惯量与质心

质量、质心与惯量决定动力学尺度。

## 机制与数据流

构建时由形状密度或显式质量/惯量建立 body 质量属性；区分 body frame、中心惯量和 world frame，检查单位、正定性及 kinematic/static 身份。

## 诊断与边界

错误密度、薄片惯量或质量比会表现为接触抖动；不能仅靠接触刚度弥补。最终以 Model 的实际数组与后端转换为准。



## 质量来源不是简单的二选一

| 构建方式 | 实际规则 | 检查点 |
|---|---|---|
| 程序化`add_link(mass,inertia,com)` | 给出body初始质量属性；之后添加正密度shape会继续累加 | 显式mass默认不阻止shape贡献；避免不知情地重复计质量 |
| `lock_inertia=True` | 后续shape不再修改该body的mass、COM或inertia | 用于保护手工质量属性；不是只锁一个惯量矩阵字段 |
| shape密度推断 | 质量相加、COM按质量加权，原惯量和shape惯量平移到新COM后相加 | plane/heightfield不贡献质量；site强制density=0 |
| 文件导入 | 显式inertial通常优先，缺失时由几何推断；URDF/MJCF可用ignore_inertial_definitions改策略 | 仍须服从格式特有compiler/属性规则；视觉shape默认不贡献，但被提升为collider后可能贡献 |

例如先设body质量2kg，再添加正密度球形状，未锁定时最终质量是2kg加球的质量，而非仍为2kg。`com`是相对body origin的偏移，`inertia`是关于COM的张量；不要把模型惯量当world-frame张量。规则与例子见[质量指定、累加与lock](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/mass_inertia.rst#L44-L160)，执行入口见[shape质量累加](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L11704-L11728)。

## finalize会检查，也可能修改

`balance_inertia=True`默认修正主惯量三角不等式；可选`bound_mass`和`bound_inertia`设置下界。验证还处理负质量、零质量与非零惯量、对称性和负特征值。开发时设`builder.validate_inertia_detailed=True`获得每body警告，并比较finalize前后的实际质量/惯量。`collapse_fixed_joints`的质量合并发生在这些验证之前。

因此应保存导入/密度/lock/验证配置与最终`Model.body_mass/body_com/body_inertia`，再核对solver转换。不要以“没有异常”推断数值未变，也不要用零质量替代`is_kinematic=True`。依据：[验证与修正设置](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/mass_inertia.rst#L163-L218)；[finalize实际处理](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L14309-L14367)。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/mass_inertia.html)。

## 固定版本原始出处

- [docs/concepts/mass_inertia.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/mass_inertia.rst#L1)
- [docs/concepts/mass_inertia.rst:44](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/mass_inertia.rst#L44-L160)
- [newton/_src/sim/builder.py:11704](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L11704-L11728)
- [docs/concepts/mass_inertia.rst:163](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/mass_inertia.rst#L163-L218)
- [newton/_src/sim/builder.py:14309](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L14309-L14367)
