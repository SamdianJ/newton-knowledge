# MuJoCo 接触转换与刚度解释边界

## 机制与输入输出

ke/kd 的数值与 MuJoCo 实际约束参数要连同接触来源、solref_mode 和 backend 判断。相同字段名不是跨路径等效的保证。

## 配置与诊断步骤

1. 先区分 backend：Newton 1.7.0 中 use_mujoco_cpu=True 的 native CPU 分支直接调用 mj_step，不消费传入的 Newton contacts；即使 use_mujoco_contacts=False 仍使用原生碰撞。MuJoCo Warp 分支才按 use_mujoco_contacts 选择原生检测或 False 时的 Newton 接触导入，后者需要调用方先计算 contacts。Warp 的 cpu/cuda 设备与 native CPU backend 不是同一个开关。
2. 正数 ke/kd 的旧数值映射为 timeconst=2/kd、dampratio=kd/(2*sqrt(ke))。这个 unit-mass 数值映射不是任意有效质量下的物理临界阻尼公式。
3. Newton contacts 的 force-space 修正使用两刚体 translational body_invweight0 的和与 solimp，这不是任意铰接/偏心接触的完整 (J M^-1 J^T)^-1。固定文档明确 native contacts/CPU 不采用该逐接触因子，不能把它们解释为同一物理刚度转换。
4. RAW、MJCF_DEFAULT、Newton force-space 模式与导入属性分别核查。SOLREF_MODE_* 是实现标记，不是公开选择 API，不从 _src 导入常量改变模式。正格式 solref 的 refsafe 使用 max(timeconst,2*dt) 作为活动约束下界，不改写存储值；负数 direct 格式绕过此规则。
5. 记录真正的 solver/model/backend 配置及转换值，再对压入、振动和轨迹做对照。不要从相同 ke 给出严格相同响应的承诺。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.solvers.SolverMuJoCo](#/record/symbol%3Anewton.solvers.SolverMuJoCo)

## 相关知识

- [solver:mujoco](#/record/solver%3Amujoco)
- [concept:simulation-tuning](#/record/concept%3Asimulation-tuning)
- [concept:collisions](#/record/concept%3Acollisions)

## 固定出处

- [newton/_src/solvers/mujoco/solver_mujoco.py:470](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L470)
- [docs/solvers/mujoco.rst:272](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L272)
- [newton/_src/solvers/mujoco/kernels.py:189](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/kernels.py#L189)
- [newton/_src/solvers/mujoco/solver_mujoco.py:4568](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4568)
