# MuJoCo · 源码导读

Newton 1.7.0，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。

## 构造到 step 的数据流

1. 注册 `mujoco.*` 自定义属性；构造参数覆盖模型属性，未覆盖部分继续走注册默认/后端默认。
2. 把 Newton bodies/joints/shapes/equalities 转成 MuJoCo spec，编译模型，创建 CPU 或 Warp 数据与索引映射。
3. 每次 step 先提交 control 和外力；仅 Newton state → 后端 data 的同步受 update_data_interval 门控。interval=0 也会接受新的控制输入。
4. native CPU 始终用原生碰撞，不消费传入的 Newton contacts；MuJoCo Warp 才按 use_mujoco_contacts 选择内建检测或外部 contacts 转换，然后执行后端步进。
5. 写回 Newton 输出状态及已请求的观测量；模型属性变更需走 `notify_model_changed` 支持的路径。

## 需要特别检查的转换边界

DISTANCE/ROD 不能视为已受支持的原生约束。MuJoCo 碰撞 mesh 使用凸几何；非凸任务应检查编译后实际模型。Newton 的标量关节坐标相对 authored pose，MuJoCo qpos 还可能含 `ref`；导入、范围与 position control 的偏移要一致。`update_data_interval=0` 会改变输入同步语义，不能仅当作性能开关。

## 默认值冲突

`separate_worlds` 的 docstring 简写为 `not use_mujoco_cpu`，实际构造分支还要求 `model.world_count > 1`，本库以执行分支为准。`integrator=None` 也不能解释为原生 MuJoCo Euler；Newton 注册默认值是 implicitfast。


## 模型转换概念导航

| 概念 | Newton → MuJoCo 的主要语义与边界 |
|---|---|
| joint | FREE/BALL/REVOLUTE/PRISMATIC 分别映射 free/ball/hinge/slide；D6 按活动轴展开至最多 3 slide + 3 hinge；FIXED 合入层级或世界根 mocap。DISTANCE 被丢弃（保留自由体记账），ROD 不转发，不能据此宣称支持。 |
| geometry | sphere/capsule/cylinder/box/ellipsoid 直接转换；plane 必须挂 world 且碰撞为无限平面；heightfield 归一化并修正基准高度。mesh 的凸包由 MuJoCo compiler 处理；cone 是离散网格近似，改变尺寸需重建；Gaussian 不支持。SITE 是引用标记而非碰撞形状。非凸/SDF/hydroelastic 需 Newton 碰撞管线和 Warp 外部接触路径。 |
| equality / mimic | CONNECT、WELD、JOINT equality 经 builder.add_custom_values 的 mujoco:equality_constraint_* 命名空间提供，不能假设有通用 add_equality API；set_joint_mimic 生成含 offset/multiplier 的 JOINT equality，覆盖 revolute/prismatic/D6 标量轴。闭环 FIXED/REVOLUTE/BALL 转为相应等式；闭环的驱动、限位等不会新增广义坐标，部分其他 joint 类型警告跳过。 |
| tendon / general actuator | tendon 通过 mujoco 自定义命名空间与 MJCF/USD 导入；空间 tendon 的 site/geom/pulley 路径受支持性检查，不支持或退化路径警告跳过。general actuator 可表达增益/偏置/动态/传动及范围，不能由简单 joint target 参数概括。 |
| kinematic root | 只支持运动学根，子体可动态；非 fixed 根用普通关节与大 armature 处理，fixed 世界根和全锁 D6 用 mocap。输入 joint_q/qd 写回时保留，施加其上的 body wrench/joint force 忽略，接触仍存在。 |
| dof_ref | Newton 标量 joint_q、limit、position target 相对 authored pose；后端 qpos/range/位置控制加回 ref，qd 不变。native dof_springref / actuator_ctrlrange 保持绝对语义。改变 ref 后通知 JOINT_REFERENCE_POSE_PROPERTIES。 |
| limit gains / passive dynamics | force-space joint_limit_ke/joint_limit_kd 经 dof_invweight0*(1-dmax) 缩放后转换 solreflimit；raw authored 值与隐式 MJCF 默认分开。正值 solref 可被 refsafe 时间步保护钳制。joint_damping、frictionloss、armature 与 PD target gains 含义不同。tendon limit gains 有独立 mode 和 TENDON_PROPERTIES 通知，不等于被动 tendon_damping。 |
| collision filtering | 保留单一导入域的 contype/conaffinity 原生掩码时，掩码仍是权威；collision_mask_domain 是导入来源标签，本身不是过滤器。混合域/原生 Newton 形状/新增排除对时编译允许对。32 位表达能力有限，大图可能走近似回退；显式 pair 可绕过 mask，仍须核对其他过滤。不要假设任意 Newton 排除图都无损映射。 |

固定入口：[newton/_src/solvers/mujoco/solver_mujoco.py:6023](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L6023)；[newton/_src/solvers/mujoco/solver_mujoco.py:3394](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L3394)；[newton/_src/solvers/mujoco/solver_mujoco.py:3713](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L3713)；[newton/_src/solvers/mujoco/solver_mujoco.py:3180](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L3180)；[newton/_src/solvers/mujoco/solver_mujoco.py:9557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L9557)。

完整转换规则按固定版本官方文档继续索引：[docs/solvers/mujoco.rst:36](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L36)。

## 关节、摩擦与接触的新增实测

已新增 12 组 native CPU 配对实验，48 次独立运行；8 组通过各自事前物理门槛。原两组迭代预算/ke-kd 接触响应实验继续保留。新增结果同时检查 Newton 输入、编译后的 MuJoCo 模型字段和实际响应，每设置独立进程重复两次。详见 [关节与碰撞实验](experiments.md)。


## 固定来源

- [newton/_src/solvers/mujoco/solver_mujoco.py:470](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L470)
- [docs/solvers/mujoco.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L5)
- [newton/_src/solvers/mujoco/solver_mujoco.py:4557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)
