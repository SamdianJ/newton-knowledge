# MuJoCo · 完整参数与配置

构造参数、嵌套配置和 reset 字段分层列出。声明默认不一定是给定 Model/后端的最终值。


## solver_constructor

### `model`

要转换为 MuJoCo 模型的 Newton Model。

- 类型：`Model`；声明默认：`必填`。
- 最终默认策略：直接声明值；仍需核对适用后端。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The model to be simulated.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4070](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4070)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `separate_worlds`

是否拆分 Newton worlds；None 时实际分支为 not use_mujoco_cpu 且 world_count > 1。

- 类型：`bool | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：If True, each Newton world is mapped to a separate MuJoCo world. Defaults to `not use_mujoco_cpu`.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4072](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4072)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `njmax`

每 world 的约束容量；自动估算或检查初始约束并告警扩容，不是迭代预算。

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Maximum number of constraints per world. If None, a default
        value is estimated automatically. An explicit value is preserved
        unless it cannot hold the initial MuJoCo constraints; in that case,
        it is increased with a warning.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4073](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4073)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `njmax_nnz`

稀疏约束 Jacobian 的非零元素容量。

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Sparse constraint Jacobian nonzero capacity per world. If provided, must be non-negative and large enough for the initial sparse Jacobian. If None, derived from the model's constraint counts and njmax.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4074](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4074)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `nconmax`

每 world 接触点容量；不足与物理解算未收敛是不同问题。

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Number of contact points per world. If None, a default value
        is estimated automatically. An explicit value is preserved unless
        it cannot hold the initial MuJoCo contacts; in that case, it is
        increased with a warning.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4075](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4075)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `iterations`

约束优化最大迭代预算；None 继续走模型属性/后端默认解析。

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Number of solver iterations. If None, uses model custom attribute or MuJoCo's default (100).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4076](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4076)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`mujoco_iterations_stack`；见 [实验与边界](../../experiments/solver_parameter_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `ls_iterations`

每轮优化的线搜索预算。

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Number of line search iterations for the solver. If None, uses model custom attribute or MuJoCo's default (50).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4077](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4077)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `ccd_iterations`

碰撞检测 CCD 迭代预算。

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Maximum CCD iterations. If None, uses model custom attribute or MuJoCo's default (35).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4078](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4078)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `sdf_iterations`

SDF 碰撞搜索迭代预算。

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Maximum SDF iterations. If None, uses model custom attribute or MuJoCo's default (10).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4079](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4079)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `sdf_initpoints`

SDF 搜索初始点数量。

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Number of SDF initialization points. If None, uses model custom attribute or MuJoCo's default (40).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4080](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4080)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `solver`

选择 CG/Newton 约束求解方法。

- 类型：`int | str | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Solver type. Can be "cg" or "newton", or their corresponding MuJoCo integer constants. If None, uses model custom attribute or Newton's default ("newton").
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4081](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4081)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `integrator`

时间积分方法；Newton 注册默认 implicitfast，与原生 MuJoCo 默认不同。

- 类型：`int | str | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Integrator type. Can be "euler", "rk4", or "implicitfast", or their corresponding MuJoCo integer constants. If None, uses model custom attribute or Newton's default ("implicitfast").
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4082](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4082)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `cone`

摩擦锥近似：pyramidal 或 elliptic。

- 类型：`int | str | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The type of contact friction cone. Can be "pyramidal", "elliptic", or their corresponding MuJoCo integer constants. If None, uses model custom attribute or Newton's default ("pyramidal").
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4083](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4083)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `jacobian`

约束 Jacobian 的 dense/sparse/auto 表示。

- 类型：`int | str | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Jacobian computation method. Can be "dense", "sparse", or "auto", or their corresponding MuJoCo integer constants. If None, uses model custom attribute or MuJoCo's default ("auto").
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4084](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4084)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `impratio`

切向与法向约束阻抗的比值，不能当作摩擦系数。

- 类型：`float | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Frictional-to-normal constraint impedance ratio. If None, uses model custom attribute or MuJoCo's default (1.0).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4085](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4085)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `tolerance`

约束优化提前终止容差。

- 类型：`float | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Solver tolerance for early termination. If None, uses model custom attribute or MuJoCo's default (1e-8).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4086](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4086)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `ls_tolerance`

线搜索提前终止容差。

- 类型：`float | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Line search tolerance for early termination. If None, uses model custom attribute or MuJoCo's default (0.01).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4087](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4087)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `ccd_tolerance`

CCD 收敛容差。

- 类型：`float | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Continuous collision detection tolerance. If None, uses model custom attribute or MuJoCo's default (1e-6).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4088](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4088)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `density`

流体介质密度，影响阻力与升力。

- 类型：`float | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Medium density for lift and drag forces. If None, uses model custom attribute or MuJoCo's default (0.0).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4089](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4089)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `viscosity`

介质黏度。

- 类型：`float | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Medium viscosity for lift and drag forces. If None, uses model custom attribute or MuJoCo's default (0.0).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4090](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4090)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `wind`

介质风速向量。

- 类型：`tuple | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Wind velocity vector (x, y, z) for lift and drag forces. If None, uses model custom attribute or MuJoCo's default (0, 0, 0).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4091](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4091)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `magnetic`

磁场向量。

- 类型：`tuple | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Global magnetic flux vector (x, y, z). If None, uses model custom attribute or MuJoCo's default (0, -0.5, 0).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4092](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4092)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `use_mujoco_cpu`

切换 MuJoCo-C native CPU 后端；此分支始终由原生 MuJoCo 生成接触，不消费传入的 Newton contacts。MuJoCo Warp 的 CPU 设备与本选项不是一回事。

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：直接声明值；仍需核对适用后端。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：If True, use the MuJoCo-C CPU backend instead of `mujoco_warp`.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4093](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4093)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `enable_multiccd`

多点碰撞接触生成；效果受几何和 margin 路径限制。

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：直接声明值；仍需核对适用后端。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：If True, enable multi-CCD contact generation (up to 4 contact points per geom pair instead of 1). Note: geom pairs where either geom has ``margin > 0`` always produce a single contact regardless of this flag.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4094](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4094)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `enable_sleeping`

GPU sleeping 优化，受 solver、积分器和碰撞路径组合约束。

- 类型：`bool | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Whether to enable MuJoCo Warp's sleeping optimization. If None, uses the model custom attribute or defaults to False. Sleeping requires the GPU backend, the Newton solver, MuJoCo contact handling, and a non-RK4 integrator.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4095](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4095)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `nvmax`

sleeping 路径的活跃自由度容量。

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Maximum number of active degrees of freedom per world when sleeping is enabled. Must accommodate every initially awake degree of freedom. If None, allocates space for every degree of freedom, which is safe but provides no compact-solver memory savings.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4096](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4096)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `sleep_tolerance`

休眠速度阈值。

- 类型：`float | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Sleep velocity tolerance. If None, uses model custom attribute or MuJoCo default (0.001).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4097](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4097)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `disable_contacts`

禁用接触计算；用于诊断时会改变物理场景。

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：直接声明值；仍需核对适用后端。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：If True, disable contact computation in MuJoCo.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4098](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4098)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `disable_sensors`

禁用常规传感器计算；部分请求的观测量仍按源码路径更新。

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：直接声明值；仍需核对适用后端。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：If True, disable sensor computation in MuJoCo. ``body_qdd`` and ``body_parent_f`` are still computed on the MuJoCo Warp backend when requested through solver observables or legacy output-state fields.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4099](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4099)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `update_data_interval`

Newton state 向 MuJoCo data 同步的步间隔；0 关闭 step 内的 state 同步。control 和外力仍每步提交，reset 的显式状态同步另行处理。

- 类型：`int`；声明默认：`1`。
- 最终默认策略：直接声明值；仍需核对适用后端。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Frequency (in simulation steps) at which to update the MuJoCo Data object from the Newton state. If 0, Data is never updated after initialization.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4100](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4100)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `save_to_mjcf`

导出编译前模型以排查转换；这是 solver 参数，MCP 只读工具不会执行导出。

- 类型：`str | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Optional path to save the generated MJCF model file.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4101](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4101)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `use_mujoco_contacts`

仅 MuJoCo Warp 分支用此开关选择内建检测或导入 Newton contacts；use_mujoco_cpu=True 的 native CPU 分支即使设 False 也不消费传入 contacts。响应仍由 MuJoCo 约束体系求解。

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：直接声明值；仍需核对适用后端。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：If True, use the MuJoCo contact solver. If False, use the Newton contact solver (newton contacts must be passed in through the step function in that case).
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4102](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4102)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `include_sites`

是否导出 SITE 参考点；SITE 不参与碰撞。

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：直接声明值；仍需核对适用后端。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：If ``True`` (default), Newton shapes marked with ``ShapeFlags.SITE`` are exported as MuJoCo sites. Sites are non-colliding reference points used for sensor attachment, debugging, or as frames of reference. If ``False``, sites are skipped during export. Defaults to ``True``.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4103](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4103)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `skip_visual_only_geoms`

是否从导出模型排除仅可视几何。

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：直接声明值；仍需核对适用后端。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：If ``True`` (default), geometries used only for visualization (i.e. not involved in collision) are excluded from the exported MuJoCo spec. This avoids mismatches with models that use explicit ``<contact>`` definitions for collision geometry.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4104](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4104)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `deterministic`

MuJoCo Warp 核确定性设置；None 继承 Warp 配置。

- 类型：`wp.DeterministicMode | None`；声明默认：`None`。
- 最终默认策略：优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Deterministic mode for MuJoCo Warp solver kernels. Pass a
        :class:`warp.DeterministicMode`, or ``None`` to inherit
        ``wp.config.deterministic``.
- 源码：[newton/_src/solvers/mujoco/solver_mujoco.py:4105](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4105)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。



## 固定来源

- [newton/_src/solvers/mujoco/solver_mujoco.py:470](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L470)
- [docs/solvers/mujoco.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L5)
- [newton/_src/solvers/mujoco/solver_mujoco.py:4557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)
