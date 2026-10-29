# Kamino · 完整参数与配置

构造参数、嵌套配置和 reset 字段分层列出。声明默认不一定是给定 Model/后端的最终值。


## solver_constructor

### `model`

The Newton model for which to create the Kamino solver instance.

- 类型：`Model`；声明默认：`必填`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The Newton model for which to create the Kamino solver instance.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:736](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L736)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config`

Explicit user-provided configurations for the Kamino solver.

- 类型：`Config | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Explicit user-provided configurations for the Kamino solver.

        If `None`, configurations will be parsed from the Newton model's
        custom attributes using :meth:`SolverKamino.Config.from_model`,
        e.g. to be loaded from USD assets. If that also fails, then
        default configurations will be used.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:737](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L737)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。


## solver_configuration

### `config.sparse_jacobian`

None 时 DVI=True、PADMM=False；属于表示/后端组合设置。

- 类型：`bool | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Whether to use a sparse Jacobian representation. When unspecified, defaults to `True` for DVI and `False`
        for PADMM.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:191](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L191)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_backend_guided_contact`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.sparse_dynamics`

启用稀疏动力学；要求 sparse_jacobian=True。

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Flag to indicate whether the solver should use sparse data representations for the dynamics.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:197](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L197)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.use_collision_detector`

是否启用 Kamino 内部碰撞管线；默认 False 时由调用方提供 Newton contacts。

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Flag to indicate whether the Kamino-provided collision detector should be used.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:202](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L202)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.use_fk_solver`

config 配置：Flag to indicate whether the Kamino-provided FK solver should be enabled.

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Flag to indicate whether the Kamino-provided FK solver should be enabled.


        The FK solver is used for computing consistent initial states given input
        joint positions, joint velocities and optional base body poses and twists.

        It is specifically designed to handle the presence of:
        - kinematic loops
        - passive joints
        - over/under-actuation
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:207](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L207)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_fourbar_fk`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.collision_detector`

config 配置：Configurations for the collision detector.

- 类型：`CollisionDetectorConfig | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Configurations for the collision detector.

        See :class:`CollisionDetectorConfig` for more details.

        If `None`, the default configuration will be used.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:220](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L220)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.constraints`

config 配置：Configurations for the constraint stabilization parameters.

- 类型：`ConstraintStabilizationConfig | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Configurations for the constraint stabilization parameters.

        See :class:`ConstraintStabilizationConfig` for more details.

        If `None`, default values will be used.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:227](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L227)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dynamics`

config 配置：Configurations for the constrained dynamics problem.

- 类型：`ConstrainedDynamicsConfig | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Configurations for the constrained dynamics problem.

        See :class:`ConstrainedDynamicsConfig` for more details.

        If `None`, default values will be used.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:234](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L234)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm`

config 配置：Configurations for the PADMM dynamics solver.

- 类型：`PADMMSolverConfig | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Configurations for the PADMM dynamics solver.

        See :class:`PADMMSolverConfig` for more details.

        If `None`, default values will be used.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:241](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L241)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi`

config 配置：Configurations for the DVI dynamics solver.

- 类型：`DVISolverConfig | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Configurations for the DVI dynamics solver.

        See :class:`DVISolverConfig` for more details.

        If `None`, default values will be used.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:248](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L248)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk`

config 配置：Configurations for the forward kinematics solver.

- 类型：`ForwardKinematicsSolverConfig | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Configurations for the forward kinematics solver.

        See :class:`ForwardKinematicsSolverConfig` for more details.

        If `None`, default values will be used.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:255](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L255)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.materials`

config 配置：Configurations for the material manager and material property mixing.

- 类型：`MaterialManagerConfig | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Configurations for the material manager and material property mixing.
        See :class:`MaterialManagerConfig` for more details.
        If `None`, default values will be used.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:262](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L262)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.rotation_correction`

config 配置：The rotation correction mode to use for rotational DoFs.

- 类型：`Literal['twopi', 'continuous', 'none']`；声明默认：`'twopi'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The rotation correction mode to use for rotational DoFs.

        See :class:`JointCorrectionMode` for available options.
        Defaults to `twopi`.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:269](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L269)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.integrator`

Euler/Moreau；Moreau 要求内部碰撞检测，不应单独切换。

- 类型：`Literal['euler', 'moreau']`；声明默认：`'euler'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The time-integrator to use for state integration. The ``"moreau"`` option requires
        ``use_collision_detector=True``.


        See available options in the `integrators` module.

        Defaults to `"euler"`.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:276](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L276)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_fourbar_loop_dynamics`、`kamino_fourbar_loop_dt960`、`kamino_fourbar_loop_dt3840`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.dynamics_solver`

PADMM/DVI 后端选择；应在创建 Config 时指定，以一致解析依赖默认值。

- 类型：`Literal['padmm', 'dvi']`；声明默认：`'padmm'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The forward dynamics solver to use. Construct the config with this value
        so solver-dependent defaults are initialized consistently. Defaults to
        `"padmm"`.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:285](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L285)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_backend_guided_contact`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.angular_velocity_damping`

config 配置：A damping factor applied to the angular velocity of bodies during state integration.

- 类型：`float`；声明默认：`0.0`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：A damping factor applied to the angular velocity of bodies during state integration.

        This can help stabilize simulations with large time steps or high angular velocities.

        Defaults to `0.0` (i.e. no damping).
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:292](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L292)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.collect_solver_info`

收集额外诊断，有开销；status 在 False 时仍然存在。

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Enables additional collection of solver convergence and performance information.

        Per-world terminal status remains available through :attr:`SolverKamino.status`
        when this option is disabled. Enabling detailed collection adds runtime and memory
        overhead.

        Defaults to `False`.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:299](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L299)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.compute_solution_metrics`

config 配置：Enables/disables computation of solution metrics at each simulation step.

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Enables/disables computation of solution metrics at each simulation step.

        Enabling this option as it will significantly increase the runtime of the solver.

        Defaults to `False`.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:308](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L308)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.collision_detector.pipeline`

config.collision_detector 配置：The type of collision-detection pipeline to use, either `primitive` or `unified`.

- 类型：`Literal['primitive', 'unified']`；声明默认：`'unified'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The type of collision-detection pipeline to use, either `primitive` or `unified`.

    Defaults to `unified`.
- 源码：[newton/_src/solvers/kamino/config.py:83](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L83)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.collision_detector.broadphase`

config.collision_detector 配置：The broad-phase collision-detection to use (`nxn`, `sap`, or `explicit`).

- 类型：`Literal['nxn', 'sap', 'explicit']`；声明默认：`'explicit'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The broad-phase collision-detection to use (`nxn`, `sap`, or `explicit`).

    Defaults to `explicit`.
- 源码：[newton/_src/solvers/kamino/config.py:89](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L89)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.collision_detector.bvtype`

config.collision_detector 配置：The type of bounding volume to use in the broad-phase.

- 类型：`Literal['aabb', 'bs']`；声明默认：`'aabb'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The type of bounding volume to use in the broad-phase.

    Defaults to `aabb`.
- 源码：[newton/_src/solvers/kamino/config.py:95](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L95)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.collision_detector.max_contacts`

config.collision_detector 配置：Model-wide cap on contact buffer capacity during collision-detector

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Model-wide cap on contact buffer capacity during collision-detector
    initialization.

    When ``max_contacts_per_world`` is None, the geometry-based estimate is
    capped at this value; otherwise this field is ignored.

    Defaults to ``None``, leaving the geometry-based estimate uncapped.
- 源码：[newton/_src/solvers/kamino/config.py:101](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L101)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.collision_detector.max_contacts_per_world`

config.collision_detector 配置：Per-world contact buffer capacity override.

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Per-world contact buffer capacity override.

    When set, allocates ``max_contacts_per_world`` contacts for every world
    (``num_worlds * max_contacts_per_world`` total), bypassing the
    geometry-based estimate and ``max_contacts``.

    Defaults to ``None``.
- 源码：[newton/_src/solvers/kamino/config.py:110](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L110)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.collision_detector.max_contacts_per_pair`

config.collision_detector 配置：The maximum number of contacts to generate per candidate geom-pair.

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The maximum number of contacts to generate per candidate geom-pair.

    Used to compute the total maximum contacts allocated for the model,
    in conjunction with the total number of candidate geom-pairs.

    Defaults to `DEFAULT_GEOM_PAIR_MAX_CONTACTS` (`12`) if unspecified.
- 源码：[newton/_src/solvers/kamino/config.py:119](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L119)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.collision_detector.max_triangle_pairs`

config.collision_detector 配置：The maximum number of triangle-primitive shape pairs to consider in the narrow-phase.

- 类型：`int | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The maximum number of triangle-primitive shape pairs to consider in the narrow-phase.

    Used only when the model contains triangle meshes or heightfields.

    Defaults to `DEFAULT_TRIANGLE_MAX_PAIRS` (`1_000_000`) if unspecified.
- 源码：[newton/_src/solvers/kamino/config.py:127](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L127)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.collision_detector.default_gap`

config.collision_detector 配置：The default detection gap [m] applied as a floor to per-geometry gaps.

- 类型：`float | None`；声明默认：`None`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The default detection gap [m] applied as a floor to per-geometry gaps.

    Defaults to `DEFAULT_GEOM_PAIR_CONTACT_GAP` (`0.0`) if unspecified.
- 源码：[newton/_src/solvers/kamino/config.py:134](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L134)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.constraints.alpha`

双边关节 Baumgarte 稳定化比例，范围 [0,1]。

- 类型：`float`；声明默认：`0.01`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Global default Baumgarte stabilization parameter for bilateral joint constraints.

    Must be in range `[0, 1.0]`.

    Defaults to `0.01`.
- 源码：[newton/_src/solvers/kamino/config.py:234](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L234)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_fourbar_loop_dynamics`、`kamino_fourbar_loop_dt960`、`kamino_fourbar_loop_dt3840`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.constraints.beta`

单边关节限位 Baumgarte 稳定化比例，范围 [0,1]。

- 类型：`float`；声明默认：`0.01`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Global default Baumgarte stabilization parameter for unilateral joint-limit constraints.

    Must be in range `[0, 1.0]`.

    Defaults to `0.01`.
- 源码：[newton/_src/solvers/kamino/config.py:241](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L241)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.constraints.gamma`

单边接触 Baumgarte 稳定化比例，范围 [0,1]。

- 类型：`float`；声明默认：`0.01`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Global default Baumgarte stabilization parameter for unilateral contact constraints.

    Must be in range `[0, 1.0]`.

    Defaults to `0.01`.
- 源码：[newton/_src/solvers/kamino/config.py:248](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L248)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_contact_stabilization`；见 [实验与边界](../../experiments/solver_parameter_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.constraints.delta`

接触穿透容许 margin，非负，不能补偿碰撞漏检。

- 类型：`float`；声明默认：`1e-06`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Contact penetration margin used for unilateral contact constraints.

    Must be non-negative.

    Defaults to `1.0e-6`.
- 源码：[newton/_src/solvers/kamino/config.py:255](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L255)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dynamics.preconditioning`

对偶预条件；DVI 必须为 False，直接 dataclass 默认与 Config 组合解析不同。

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。 PADMM 默认 LLTB/预条件 True；DVI dense-dynamics 默认 LLTBRCM/False；DVI sparse-dynamics 默认 CR/False。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Set to `True` to enable preconditioning of the dual problem.

    Defaults to `True`.
- 源码：[newton/_src/solvers/kamino/config.py:366](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L366)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_backend_guided_contact`、`kamino_pd_preconditioning`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)、[实验与边界](../../experiments/kamino_pd_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.dynamics.linear_solver_type`

直接子配置默认 LLTB；默认 DVI 组合改为 LLTBRCM，稀疏 DVI 改为 CR。

- 类型：`Literal['LLTB', 'LLTBRCM', 'CR', 'CRF']`；声明默认：`'LLTB'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。 PADMM 默认 LLTB/预条件 True；DVI dense-dynamics 默认 LLTBRCM/False；DVI sparse-dynamics 默认 CR/False。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The type of linear solver to use for the dynamics problem.

    See :class:`LinearSolverType` for available options.

    Defaults to 'LLTB' (:class:`LLTBlockedSolver`, dense blocked LLT). The
    RCM-reordered semi-sparse variant is available as 'LLTBRCM'
    (:class:`LLTBlockedRCMSolver`) and is currently opt-in pending further
    performance optimization.
- 源码：[newton/_src/solvers/kamino/config.py:372](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L372)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_backend_guided_contact`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.dynamics.linear_solver_kwargs`

config.dynamics 配置：Additional keyword arguments to pass to the linear solver.

- 类型：`dict[str, Any]`；声明默认：`field(default_factory=dict)`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。 PADMM 默认 LLTB/预条件 True；DVI dense-dynamics 默认 LLTBRCM/False；DVI sparse-dynamics 默认 CR/False。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Additional keyword arguments to pass to the linear solver.

    Defaults to an empty dictionary.
- 源码：[newton/_src/solvers/kamino/config.py:382](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L382)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dynamics.cull_speculative_contacts`

config.dynamics 配置：Whether to cull speculative (= separated) contacts in the dynamics solve.

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。 PADMM 默认 LLTB/预条件 True；DVI dense-dynamics 默认 LLTBRCM/False；DVI sparse-dynamics 默认 CR/False。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Whether to cull speculative (= separated) contacts in the dynamics solve.
    These contacts have occasionally led to numerical instabilities, and
    can yield inaccurate restitutive impacts.
- 源码：[newton/_src/solvers/kamino/config.py:388](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L388)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.primal_tolerance`

config.padmm 配置：The target tolerance on the total primal residual `r_primal`.

- 类型：`float`；声明默认：`1e-06`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The target tolerance on the total primal residual `r_primal`.

    Must be greater than zero. Defaults to `1e-6`.
- 源码：[newton/_src/solvers/kamino/config.py:474](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L474)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.dual_tolerance`

config.padmm 配置：The target tolerance on the total dual residual `r_dual`.

- 类型：`float`；声明默认：`1e-06`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The target tolerance on the total dual residual `r_dual`.

    Must be greater than zero. Defaults to `1e-6`.
- 源码：[newton/_src/solvers/kamino/config.py:480](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L480)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.compl_tolerance`

config.padmm 配置：The target tolerance on the complementarity residual `r_compl`.

- 类型：`float`；声明默认：`1e-06`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The target tolerance on the complementarity residual `r_compl`.

    Must be greater than zero. Defaults to `1e-6`.
- 源码：[newton/_src/solvers/kamino/config.py:486](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L486)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_pd_complementarity_gate`；见 [实验与边界](../../experiments/kamino_pd_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.padmm.restart_tolerance`

config.padmm 配置：The tolerance on the total combined primal-dual residual `r_comb`,

- 类型：`float`；声明默认：`0.999`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The tolerance on the total combined primal-dual residual `r_comb`,
    for determining when gradient acceleration should be restarted.

    Must be greater than zero. Defaults to `0.999`.
- 源码：[newton/_src/solvers/kamino/config.py:492](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L492)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.eta`

近端正则化强度；影响子问题数值性质。

- 类型：`float`；声明默认：`1e-05`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The proximal regularization parameter.

    Must be greater than zero. Defaults to `1e-5`.
- 源码：[newton/_src/solvers/kamino/config.py:499](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L499)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.rho_0`

PADMM 初始增广罚参数；属于数值参数，不是接触材料刚度。

- 类型：`float`；声明默认：`1.0`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The initial value of the ALM penalty parameter.

    Must be greater than zero. Defaults to `1.0`.
- 源码：[newton/_src/solvers/kamino/config.py:505](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L505)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.rho_min`

config.padmm 配置：The lower-bound applied to the ALM penalty parameter.

- 类型：`float`；声明默认：`1e-05`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The lower-bound applied to the ALM penalty parameter.

    Used to ensure numerical stability when adaptive penalty updates are used.

    Must be greater than zero. Defaults to `1e-5`.
- 源码：[newton/_src/solvers/kamino/config.py:511](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L511)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.a_0`

config.padmm 配置：The initial value of the acceleration parameter.

- 类型：`float`；声明默认：`1.0`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The initial value of the acceleration parameter.

    Must be greater than zero. Defaults to `1.0`.
- 源码：[newton/_src/solvers/kamino/config.py:518](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L518)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.alpha`

config.padmm 配置：The primal-dual residual threshold used to determine when penalty updates are needed.

- 类型：`float`；声明默认：`10.0`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The primal-dual residual threshold used to determine when penalty updates are needed.
    Must be greater than one. Defaults to `10.0`.
- 源码：[newton/_src/solvers/kamino/config.py:524](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L524)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.tau`

config.padmm 配置：The factor by which the ALM penalty is increased/decreased when

- 类型：`float`；声明默认：`1.5`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The factor by which the ALM penalty is increased/decreased when
    the primal-dual residual ratios exceed the threshold `alpha`.

    Must be greater than `1.0`. Defaults to `1.5`.
- 源码：[newton/_src/solvers/kamino/config.py:530](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L530)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.max_iterations`

PADMM 最大迭代预算；同时核对三个残差和 converged。

- 类型：`int`；声明默认：`200`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The maximum number of solver iterations.

    Must be greater than zero. Defaults to `200`.
- 源码：[newton/_src/solvers/kamino/config.py:537](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L537)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_padmm_budget`、`kamino_pd_iteration_budget`；见 [实验与边界](../../experiments/kamino_pd_lab/README.md)、[实验与边界](../../experiments/solver_parameter_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.padmm.penalty_update_freq`

config.padmm 配置：The permitted frequency of penalty updates.

- 类型：`int`；声明默认：`1`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The permitted frequency of penalty updates.

    If zero, no updates are performed. Otherwise, updates are performed every
    `penalty_update_freq` iterations. Defaults to `1`.
- 源码：[newton/_src/solvers/kamino/config.py:543](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L543)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.penalty_update_method`

罚参数更新策略；非 fixed 需要 sparse_dynamics=True。

- 类型：`Literal['fixed', 'balanced']`；声明默认：`'fixed'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The penalty update method used to adapt the penalty parameter.

    Defaults to `fixed`. See :class:`PADMMPenaltyUpdate` for details.
- 源码：[newton/_src/solvers/kamino/config.py:550](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L550)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.linear_solver_tolerance`

config.padmm 配置：The default absolute tolerance for the iterative linear solver.

- 类型：`float`；声明默认：`0.0`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The default absolute tolerance for the iterative linear solver.

    When zero, the iterative solver's own tolerance is left unchanged.

    When positive, the iterative solver's atol is initialized
    to this value at the start of each ADMM solve.

    Must be non-negative. Defaults to `0.0`.
- 源码：[newton/_src/solvers/kamino/config.py:556](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L556)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.linear_solver_tolerance_ratio`

config.padmm 配置：The ratio used to adapt the iterative linear solver tolerance from the ADMM primal residual.

- 类型：`float`；声明默认：`0.0`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The ratio used to adapt the iterative linear solver tolerance from the ADMM primal residual.

    When zero, the linear solver tolerance is not adapted (fixed tolerance).

    When positive, the linear solver absolute tolerance is
    set to `ratio * ||r_primal||_2` at each ADMM iteration.

    Must be non-negative. Defaults to `0.0`.
- 源码：[newton/_src/solvers/kamino/config.py:565](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L565)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.use_acceleration`

config.padmm 配置：Enables Nesterov-type acceleration, i.e. use APADMM instead of standard PADMM.

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Enables Nesterov-type acceleration, i.e. use APADMM instead of standard PADMM.

    Defaults to `True`.
- 源码：[newton/_src/solvers/kamino/config.py:574](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L574)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_pd_acceleration`；见 [实验与边界](../../experiments/kamino_pd_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.padmm.use_graph_conditionals`

CUDA 条件图迭代控制；不适用的平台应选择固定上限循环路径。

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Enables use of CUDA graph conditional nodes in iterative solvers.

    If `False`, replaces `wp.capture_while` with unrolled for-loops over max iterations.

    Defaults to `True`.
- 源码：[newton/_src/solvers/kamino/config.py:580](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L580)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.warmstart_mode`

config.padmm 配置：Warmstart mode to be used for the dynamics solver.

- 类型：`Literal['none', 'internal', 'containers']`；声明默认：`'containers'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Warmstart mode to be used for the dynamics solver.

    See :class:`PADMMWarmStartMode` for the available options.

    Defaults to `containers` to warmstart from the solver data containers.
- 源码：[newton/_src/solvers/kamino/config.py:587](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L587)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_reset_default_replay`、`kamino_reset_preserve_replay`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.padmm.warmstart_scale`

缓存约束反力的 warmstart 缩放，不等同于材料耗散。

- 类型：`float`；声明默认：`0.9`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Scale applied to cached constraint forces during warm-starting.

    Must be in the range [0, 1]. Defaults to `0.9`.

    PADMM converges to a minimum-norm deviation from its initial guess. Scaling
    the warm-start forces makes null-space forces converge to the overall
    minimum-norm solution.
- 源码：[newton/_src/solvers/kamino/config.py:594](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L594)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.padmm.contact_warmstart_method`

config.padmm 配置：Method to be used for warm-starting contacts.

- 类型：`Literal['key_and_position', 'geom_pair_net_force', 'geom_pair_net_wrench', 'key_and_position_with_net_force_backup', 'key_and_position_with_net_wrench_backup']`；声明默认：`'key_and_position'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Method to be used for warm-starting contacts.

    See :class:`WarmstarterContacts.Method` for available options.

    Defaults to `key_and_position`.
- 源码：[newton/_src/solvers/kamino/config.py:604](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L604)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.tolerance`

config.dvi 配置：The convergence tolerance on the projected update size.

- 类型：`float`；声明默认：`1e-05`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The convergence tolerance on the projected update size.
    Must be non-negative. Defaults to `1e-5`.
- 源码：[newton/_src/solvers/kamino/config.py:802](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L802)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.regularization`

config.dvi 配置：Diagonal regularization added to each projected update denominator.

- 类型：`float`；声明默认：`1e-06`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Diagonal regularization added to each projected update denominator.
    Must be positive. Defaults to `1e-6`.
- 源码：[newton/_src/solvers/kamino/config.py:808](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L808)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.omega`

投影 Gauss-Seidel 松弛比例，范围 (0,2]。

- 类型：`float`；声明默认：`1.0`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Relaxation factor applied to projected Gauss-Seidel updates.
    Must be in the range `(0, 2]`. Defaults to `1.0`.
- 源码：[newton/_src/solvers/kamino/config.py:814](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L814)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.max_alternating_iterations`

DVI 外层双边直接解与单边投影交替预算。

- 类型：`int`；声明默认：`24`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Maximum number of outer DVI iterations alternating direct bilateral
    solves with projected inequality solves. Must be greater than zero.
    This schedule is also used when no bilateral constraints are present;
    in that case, the bilateral solve is skipped. Defaults to `24`.
- 源码：[newton/_src/solvers/kamino/config.py:820](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L820)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.inequality_sweeps_per_iteration`

每个 DVI 外层迭代中的单边投影扫描次数。

- 类型：`int`；声明默认：`2`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Number of projected Gauss-Seidel sweeps used for unilateral inequalities
    during each alternating DVI iteration. Contacts use graph-colored sweeps
    on CUDA. Must be greater than zero. Defaults to `2`.
- 源码：[newton/_src/solvers/kamino/config.py:828](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L828)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.use_schur_complement`

config.dvi 配置：Whether to eliminate bilateral rows from the unilateral solve through a Schur complement.

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Whether to eliminate bilateral rows from the unilateral solve through a Schur complement.

    .. experimental::

        The ``True`` mode may change without prior notice. It requires the same
        setting in every world and adds response-matrix setup and storage.

    Defaults to ``False``.
- 源码：[newton/_src/solvers/kamino/config.py:835](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L835)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.bilateral_solve_interval`

config.dvi 配置：Number of alternating DVI iterations between repeated direct bilateral solves.

- 类型：`int`；声明默认：`1`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Number of alternating DVI iterations between repeated direct bilateral solves.
    This controls coupling when :attr:`use_schur_complement` is ``False``.
    Larger values trade coupling accuracy for fewer direct solves. Must be greater
    than zero. Defaults to `1`.
- 源码：[newton/_src/solvers/kamino/config.py:847](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L847)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.tangential_warmstart_scale`

config.dvi 配置：Scale applied to cached tangential contact reactions before a DVI solve.

- 类型：`float`；声明默认：`0.97`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Scale applied to cached tangential contact reactions before a DVI solve.
    Normal reactions remain fully warm-started. Must be in the range `[0, 1]`.
    Defaults to `0.97`.
- 源码：[newton/_src/solvers/kamino/config.py:855](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L855)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.bilateral_solver_type`

config.dvi 配置：Direct linear solver used for the bilateral constraint block.

- 类型：`Literal['LLTB', 'LLTBRCM']`；声明默认：`'LLTB'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Direct linear solver used for the bilateral constraint block.
    ``LLTBRCM`` can accelerate large sparse articulated systems, while
    ``LLTB`` remains preferable for small or dense systems. Defaults to
    ``LLTB``.
- 源码：[newton/_src/solvers/kamino/config.py:862](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L862)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.bilateral_solver_kwargs`

config.dvi 配置：Additional keyword arguments passed to the bilateral linear solver.

- 类型：`dict[str, Any]`；声明默认：`field(default_factory=dict)`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Additional keyword arguments passed to the bilateral linear solver.
    Defaults to an empty dictionary.
- 源码：[newton/_src/solvers/kamino/config.py:870](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L870)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.warmstart_mode`

config.dvi 配置：Warmstart mode to be used for the DVI solver.

- 类型：`Literal['none', 'internal', 'containers']`；声明默认：`'containers'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Warmstart mode to be used for the DVI solver.
    Uses the same choices as the other dual dynamics solvers. Defaults to `containers`.
- 源码：[newton/_src/solvers/kamino/config.py:876](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L876)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.dvi.contact_warmstart_method`

config.dvi 配置：The contact warmstart method used when `warmstart_mode` is `containers`.

- 类型：`Literal['key_and_position', 'geom_pair_net_force', 'key_and_position_with_net_force_backup', 'key_and_position_with_tangential_net_force', 'key_and_position_with_net_force_backup_and_tangential_net_force']`；声明默认：`'key_and_position_with_tangential_net_force'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The contact warmstart method used when `warmstart_mode` is `containers`.
    See :class:`WarmstarterContacts.Method` for available options.
    Defaults to `key_and_position_with_tangential_net_force`.
- 源码：[newton/_src/solvers/kamino/config.py:882](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L882)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.tolerance`

config.fk 配置：Maximal absolute kinematic constraint value that is acceptable at the solution.

- 类型：`float`；声明默认：`1e-06`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Maximal absolute kinematic constraint value that is acceptable at the solution.
    This setting can be altered after the solver's construction (but will get baked in captured graphs).
    Defaults to `1e-6`.
- 源码：[newton/_src/solvers/kamino/config.py:983](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L983)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.max_newton_iterations`

config.fk 配置：Maximal number of Gauss-Newton iterations.

- 类型：`int`；声明默认：`30`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Maximal number of Gauss-Newton iterations.
    This setting can be altered after the solver's construction (but will get baked in captured graphs).
    Defaults to `30`.
- 源码：[newton/_src/solvers/kamino/config.py:990](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L990)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.max_line_search_iterations`

config.fk 配置：Maximal line search iterations in the inner loop.

- 类型：`int`；声明默认：`20`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Maximal line search iterations in the inner loop.
    This setting can be altered after the solver's construction (but will get baked in captured graphs).
    Defaults to `20`.
- 源码：[newton/_src/solvers/kamino/config.py:997](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L997)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.reset_state`

config.fk 配置：Whether to reset the state before the FK solve, using the reference state of the system as initial guess.

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Whether to reset the state before the FK solve, using the reference state of the system as initial guess.
    If False, the current body poses are used as initial guess, which often leads to faster convergence
    when solving forward kinematics along a trajectory (as opposed to isolated poses).
    This setting can be altered after the solver's construction (but will get baked in captured graphs).
    Defaults to `True`.
- 源码：[newton/_src/solvers/kamino/config.py:1004](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1004)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_fourbar_fk`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `config.fk.add_axis_joints`

config.fk 配置：Whether to automatically add axis joints to take out superfluous DoFs at tie rods (i.e. bodies

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Whether to automatically add axis joints to take out superfluous DoFs at tie rods (i.e. bodies
    between two passive spherical or gimbal joints, that may rotate freely about the connecting axis),
    that otherwise render the FK problem ill-posed.
    Defaults to `True`.
- 源码：[newton/_src/solvers/kamino/config.py:1013](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1013)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.use_incremental_solve`

config.fk 配置：Whether to automatically split large steps in actuator coordinates into smaller steps

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Whether to automatically split large steps in actuator coordinates into smaller steps
    in the FK solve, to improve the solver's robustness for a mild added cost.
    Defaults to `True`.
- 源码：[newton/_src/solvers/kamino/config.py:1021](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1021)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.max_linear_incremental_step`

config.fk 配置：If incremental solve is enabled, maximal allowed step in linear actuator coordinates

- 类型：`float`；声明默认：`0.05`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：If incremental solve is enabled, maximal allowed step in linear actuator coordinates
    per solver iteration, in meters. A lower value results in more incremental steps.
    Defaults to `0.05`.
- 源码：[newton/_src/solvers/kamino/config.py:1028](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1028)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.max_angular_incremental_step`

config.fk 配置：If incremental solve is enabled, maximal allowed step in angular actuator coordinates

- 类型：`float`；声明默认：`math.radians(10.0)`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：If incremental solve is enabled, maximal allowed step in angular actuator coordinates
    per solver iteration, in radians. A lower value results in more incremental steps.
    Defaults to `math.radians(10.0)`, i.e. 10 degrees.
- 源码：[newton/_src/solvers/kamino/config.py:1035](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1035)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.use_regularization`

config.fk 配置：Whether to regularize the FK problem by trying to preserve the rigid body poses with a small weight.

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Whether to regularize the FK problem by trying to preserve the rigid body poses with a small weight.
    This might result in constraint violations of the order of the regularization weight, but allows to
    tackle systems with solution sub-spaces, in particular underactuated systems.

    Important note: the default tolerance of 1e-6 may not be reachable if regularization is enabled,
    using 1e-5 instead is recommended in most cases.

    For systems that are only underactuated due to tie rods being free to rotate about their own axis,
    enabling `add_axis_joints` is recommended instead.

    Defaults to `False`.
- 源码：[newton/_src/solvers/kamino/config.py:1042](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1042)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.regularization_weight`

config.fk 配置：Weight applied to the rigid body pose least-squares regularizer, if regularization is enabled.

- 类型：`float`；声明默认：`1e-05`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Weight applied to the rigid body pose least-squares regularizer, if regularization is enabled.
    This setting can be altered after the solver's construction (but will get baked in captured graphs).
    Defaults to `1e-5`.
- 源码：[newton/_src/solvers/kamino/config.py:1057](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1057)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.use_sparsity`

config.fk 配置：Whether to use sparse Jacobian and solver; else dense versions are used (recommended for most systems).

- 类型：`bool`；声明默认：`False`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Whether to use sparse Jacobian and solver; else dense versions are used (recommended for most systems).
    Defaults to `False`.
- 源码：[newton/_src/solvers/kamino/config.py:1064](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1064)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.preconditioner`

config.fk 配置：Preconditioner to use for the Conjugate Gradient solver if sparsity is enabled.

- 类型：`Literal['none', 'jacobi_diagonal', 'jacobi_block_diagonal']`；声明默认：`'jacobi_block_diagonal'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Preconditioner to use for the Conjugate Gradient solver if sparsity is enabled.
    Defaults to `jacobi_block_diagonal`.
- 源码：[newton/_src/solvers/kamino/config.py:1070](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1070)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.fk.use_adaptive_cg_tolerance`

config.fk 配置：Whether to use an adaptive tolerance strategy for the Conjugate Gradient solver if sparsity

- 类型：`bool`；声明默认：`True`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Whether to use an adaptive tolerance strategy for the Conjugate Gradient solver if sparsity
    is enabled, which reduces the number of CG iterations in most cases.
    This setting can be altered after the solver's construction (but will get baked in captured graphs).
    Defaults to `True`.
- 源码：[newton/_src/solvers/kamino/config.py:1076](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1076)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.materials.friction_mix_mode`

config.materials 配置：The mixing mode to use for friction.

- 类型：`Literal['average', 'multiply', 'max', 'min']`；声明默认：`'average'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The mixing mode to use for friction.

    Defaults to `average`.
- 源码：[newton/_src/solvers/kamino/config.py:1155](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1155)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `config.materials.restitution_mix_mode`

config.materials 配置：The mixing mode to use for restitution.

- 类型：`Literal['average', 'multiply', 'max', 'min']`；声明默认：`'min'`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：The mixing mode to use for restitution.

    Defaults to `min`.
- 源码：[newton/_src/solvers/kamino/config.py:1161](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L1161)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。


## reset_configuration

### `reset.body_poses`

reset 配置：Reset option for body poses:

- 类型：`ToDefault | Preserve | FromJointQ | FromActuatorQ`；声明默认：`ToDefault()`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Reset option for body poses:

        - ToDefault: reset poses to their initial values.
        - Preserve: preserve poses in the state container, assuming they are consistent.
        - FromJointQ: extract actuator coordinates from joint coordinates, and compute consistent
          body poses with a position-level forward kinematics solve.
        - FromActuatorQ: compute consistent body poses for the prescribed actuator coordinates with
          a position-level forward kinematics solve.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:644](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L644)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_fourbar_fk`、`kamino_reset_default_replay`、`kamino_reset_preserve_replay`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `reset.body_velocities`

reset 配置：Reset option for body velocities:

- 类型：`ToDefault | Preserve | FromJointU | FromActuatorU`；声明默认：`ToDefault()`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Reset option for body velocities:

        - ToDefault: reset velocities to zero.
        - Preserve: if body poses are preserved, preserve velocities in the state container, assuming
          they are consistent. Otherwise, behaves like FromJointU, transferring current joint velocities
          in the state container, to the extent possible, to the new body poses.
        - FromJointU: extract actuator velocities from joint velocities, and compute consistent body
          velocities with a velocity-level forward kinematics solve.
        - FromActuatorU: compute consistent body velocities for the prescribed actuator velocities with
          a velocity-level forward kinematics solve.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:656](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L656)
- 实验证据：已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：`kamino_reset_default_replay`、`kamino_reset_preserve_replay`；见 [实验与边界](../../experiments/kamino_mechanism_lab/README.md)。结论仅限保存的场景、后端与参数组，不代表全范围验证。

### `reset.base_pose`

reset 配置：Reset option for the floating base pose:

- 类型：`ToDefault | Preserve | FromJointQ | FromBaseQ`；声明默认：`ToDefault()`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Reset option for the floating base pose:

        - ToDefault: reset the base pose to its initial value.
        - Preserve: preserve the current base pose, as read from current joint coordinates (if a base joint
          was set) or body poses (otherwise).
        - FromJointQ: read the base pose from joint coordinates, assuming a base joint was set. Behaves
          like ToDefault otherwise (as a fallback).
        - FromBaseQ: use the provided base pose.

        Body poses and velocities are transformed (if needed) to match the prescribed base pose, while
        preserving relative poses and velocities.
        All options are ignored for worlds for which no base body is set.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:670](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L670)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。

### `reset.base_velocity`

reset 配置：Reset option for the floating base velocity:

- 类型：`ToDefault | Preserve | FromJointU | FromBaseU`；声明默认：`ToDefault()`。
- 最终默认策略：声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。
- 原始说明（上游 docstring，执行边界以上述实现解读为准）：Reset option for the floating base velocity:

        - ToDefault: reset the base velocity to zero.
        - Preserve: preserve the current base velocity, as read from current joint velocities (if a base joint
          was set) or body velocities (otherwise), up to transformation due to the new base pose if applicable.
        - FromJointU: read the base velocity from joint velocities, assuming a base joint was set. Behaves
          like ToDefault otherwise (as a fallback).
        - FromBaseU: use the provided base velocity.

        Body velocities are updated to match the prescribed base velocity, while preserving relative velocities.
        All options are ignored for worlds for which no base body is set.
- 源码：[newton/_src/solvers/kamino/solver_kamino.py:686](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L686)
- 实验证据：当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。



## 固定来源

- [newton/_src/solvers/kamino/solver_kamino.py:111](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L111)
- [docs/solvers/kamino.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L5)
- [newton/_src/solvers/kamino/solver_kamino.py:1062](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L1062)
