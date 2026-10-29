# 源码导读与生命周期

官方版本：`7e75abe28b8d69522bc0b34837aaed2c303dff5a`。源码路径均在 `sources/newton-v1.7.0`。公开入口为 `newton.solvers.SolverVBD`；`_src` 只用于证据定位，业务代码使用公开入口。

## 模块地图

| 文件 | 职责 | 重点入口 |
|---|---|---|
| `solver_vbd.py` | 配置解析、内存、三阶段 step、历史、调度、导出 | [`SolverVBD.__init__`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L353-L1000)；[`SolverVBD.step`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L2513-L2609) |
| `particle_vbd_kernels.py` | 膜/tet/弯曲/弹簧力与 Hessian、摩擦、局部解、DAT | [`solve_elasticity`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2720-L2857)；[`compute_friction`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L1348-L1378) |
| `rigid_vbd_kernels.py` | 刚体局部系统、关节、ALM、接触材料/dual、刚体 DAT | [`solve_rigid_body`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L6219-L6493)；[`update_duals_joint`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L6497-L7093) |
| `vbd_coupling_kernels.py` | proxy 耦合相关接触力采集 | 见 [符号索引](../../indexes/source_symbols.json)，不等同 constructor 的单向耦合 |
| `geometry/tri_mesh_collision.py` | 网格自接触候选与拓扑过滤 | 见静态索引与调用方 |
| `sim/model.py`、`sim/builder.py` | 数据定义与模型装配 | [模型输入](model-inputs.md) |

## 构建顺序

1. 确定单位、坐标、材料、几何与控制；添加到 `ModelBuilder`。
2. `builder.color()`，覆盖粒子及 VBD 所积分的刚体；随后 `finalize`。
3. 建立 `CollisionPipeline`，明确是否由 solver 持有，配置全局容量与 matching。
4. 外部检测模式：pipeline → contacts → solver；owned 模式：把 pipeline 交给 solver 分配 contacts。
5. 分配 state/control；先完成一次普通运行或所需预分配，再考虑 CUDA graph capture。

不是所有数组都能在 graph capture 中临时增长。全局 contact storage 与每个刚体/顶点的邻接表容量也不是同一参数。相关保证与异常见 [`SolverVBD`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L167-L4866)。

## step 的真实顺序

依据 [`SolverVBD.step`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L2513-L2609)：

```text
解析 contacts 所有权与 observables
解析本步 rigid / soft-self-contact 检测调度并验证 DAT 条件
需要时执行初始化前检测
初始化刚体 → 初始化粒子
需要时执行初始化后检测
重复 iterations 次：
    需要时更新检测结果
    刚体迭代：颜色组 primal、相关 dual/penalty 等
    粒子迭代：颜色组接触/弹簧/材料力与 Hessian、位移及截断
可选：在最终迭代构形导出接触力
保存刚体接触历史 → 最终更新刚体 → 最终更新粒子速度
```

源码会使用 `state_in` 内的数组承载部分中间迭代，不应把其命名理解成函数式只读输入。需要保存上一帧观测时另行复制。外部刚体模式对 `state_in/out` 的旧/新刚体位姿语义有专门约定，见 [`SolverVBD._solve_particle_iteration`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L3747-L3982)。

### 碰撞所有权不能混用

- 外部：调用者 `pipeline.collide(state, contacts)`，再传 contacts 给 `solver.step`。
- owned：构造 `SolverVBD(..., collision_pipeline=pipeline)`，`step(..., contacts=None, dt=...)`，用 solver 的 contacts 读取结果。
- owned 模式 AUTO 的普通 rigid slot 为 PRE_INIT；soft self-contact 或 rigid-soft DAT 启用后相关 slot 为 PRE_POST_INIT。
- `rigid_soft_enable_dat=True` 要求 owned pipeline，而且不支持 external-rigid solver。参见 [`SolverVBD._default_collision_frequency_type`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L4690-L4712)、[`SolverVBD._init_rigid_penetration_free`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L2837-L2896)。
- 同时启用 `rigid_soft_enable_dat` 与 `particle_enable_self_contact` 时，两种 DAT 共用 motion reference：RIGID 与 SOFT_SELF_CONTACT 必须解析为同一种调度类型；若为 ITERATIONS，还必须使用相同 frequency。各自非 NONE 并不足够。显式修改检测频率时同步配置两个 slot；不匹配会在 step 中被拒绝。参见 [`SolverVBD._validate_dat_collision_schedules`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L4808-L4829)。

## 能力边界

支持 cloth 三角形/弯曲、tet、粒子弹簧、刚体、关节及相关混合。关节：BALL、FIXED、FREE、REVOLUTE、PRISMATIC、D6、ROD。DISTANCE 和若干模型字段不支持：armature、joint_friction、effort/velocity limits、target_mode、equality constraints；joint-owned mimic 与已弃用 sparse mimic 必须区分。完整机器记录在 [capabilities.json](capabilities.json)，证据为 [`SolverVBD`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L167-L4866)。

CONTACT_F 导出最终构形下的刚体接触和刚柔接触记录，不导出软自接触力。测量传感器的坐标系、作用点、符号和采样频率还需适配；不能直接将 contact wrench 与真实腕部六轴数据逐项相减。

## 修改与 reset

- 非 ROD 的结构材料、布局、静止角为构造缓存；重建 solver。
- ROD 的 `joint_target_ke/kd` 材料更新使用 `notify_model_changed(ModelFlags.JOINT_DOF_PROPERTIES)` 或较窄的 `ModelFlags.JOINT_DOF_FORCE_PROPERTIES`；这不会刷新静止弯扭角缓存。
- ROD 静止弯扭角由 `joint_X_p`、`joint_X_c` 和 `model.body_q` 派生。修改 joint rest frames 后通知 `ModelFlags.JOINT_PROPERTIES`，修改 body 的模型静止姿态后通知 `ModelFlags.BODY_PROPERTIES`；对应分支才调用 rest cache 刷新。仅改运行时 State 位姿不等于改变模型静止构形。参见 [`SolverVBD.notify_model_changed`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L1403-L1433)、[`SolverVBD._refresh_rod_rest_bend_twist_cache`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L1803-L1834)。
- `joint_enabled` 有 live 读取，但派生接触 conditioning 还需 `JOINT_PROPERTIES` 通知。
- CUDA tiled 材料类别特化在构造发生；改三角形/边刚度后重建。
- episode reset 需同时考虑 solver 历史、pipeline matching 历史、FK 和新接触。`JOINT_Q/QD` 不直接替代最大坐标 `body_q/qd`。

证据：[`SolverVBD`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L167-L4866)、[`SolverVBD.reset`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L2612-L2797)、[`SolverVBD._init_particle_system`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L1002-L1105)。不要把“某个数组可写”当作“所有缓存立即有效”。

## 本地可运行入口

[CPU 探针](../../experiments/run_cpu_probes.py) 使用公开 API 构造两个粒子和一根弹簧，运行真正的 SolverVBD 并与解析隐式步比较；另有配置语义检查。真实布料/软体案例优先参照固定快照的 `examples/vbd`、`examples/cloth`、`examples/softbody` 与 `examples/multiphysics/example_vbd_dat_rigid_soft.py`。这些上游例子已保留，但本样板没有声称全部运行通过。

密集接触与 DAT 后续回归入口列在 [upstream-tests.json](upstream-tests.json)，每条具有固定 commit 的函数定位和 `not_run_in_this_delivery` 标记，区分“上游存在测试”和“本机已运行”。
