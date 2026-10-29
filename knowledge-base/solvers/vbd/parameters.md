# SolverVBD 构造参数全集

基线为 1.7.0 固定签名：48 个输入含必填 model，47 个可选项。原始类型、英文参数说明、所有文本引用位置在 [parameters.json](parameters.json)；“文本出现”并不等于实际运行时依赖。

## 阅读规则

- 声明 `None` 不代表无效或值为零；下表单列实际解析。
- 官方默认值是接口事实，推荐范围/经验证成功区间是另一种证据；本库没有伪造统一调参区间。
- 默认把 constructor 参数看作构造期配置；调度有公开 setter，Model 变更需遵守 notify/cache 规则。
- 数值预算、物理材料、几何检测和历史参数分开记录；dt 与 substeps 不是此 constructor 的两个缺失参数。

## 完整清单

### `model`

类别：模型；声明默认：`必填`；单位：对象。

ModelBuilder.finalize 产生的模型，需完成粒子和由 VBD 积分的刚体着色；不是调参旋钮。

解析：`required; no default`。状态：`active`。

证据：[签名 L355](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L355)；[完整记录](parameters.json)。

### `iterations`

类别：数值预算；声明默认：`10`；单位：次/step。

每个 step 的 VBD 外迭代次数；每次先刚体再粒子，各自按颜色更新。更多迭代不能修复漏检或错误物理模型。

解析：`10`。状态：`active`。

证据：[签名 L358](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L358)；[完整记录](parameters.json)。

### `friction_epsilon`

类别：摩擦正则；声明默认：`0.01`；单位：长度/时间（SI: m/s）。

低相对速度的摩擦平滑阈值；内核以 epsilon*dt 转为滑移距离阈值，不是摩擦系数 mu。

解析：`0.01`。状态：`active`。

证据：[签名 L359](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L359)；[完整记录](parameters.json)。

### `dat_conservative_bound_relaxation`

类别：DAT；声明默认：`0.85`；单位：无量纲。

DAT 保守截断系数；源码强制 0<值<1；共享于粒子与启用的刚柔 DAT。

解析：`0.85`。状态：`active`。

证据：[签名 L360](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L360)；[完整记录](parameters.json)。

### `integrate_with_external_rigid_solver`

类别：耦合模式；声明默认：`False`；单位：布尔。

True 时由外部 solver 积分刚体，state_in/out 必须分别提供上一/当前刚体状态；这个选项本身不构成双向耦合。

解析：`False`。状态：`active`。

证据：[签名 L361](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L361)；[完整记录](parameters.json)。

### `particle_enable_self_contact`

类别：自接触；声明默认：`False`；单位：布尔。

启用软体顶点-三角形和边-边自接触；检测调度不得为 NONE。

解析：`False`。状态：`active`。

证据：[签名 L363](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L363)；[完整记录](parameters.json)。

### `particle_self_contact_radius`

类别：弃用兼容；声明默认：`None`；单位：长度。

旧交互半径。设置它时 margin 仍表示旧检测半径；不可同时指定 gap。新配置应迁移至 margin+gap。

解析：`None`。状态：`deprecated`。

证据：[签名 L364](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L364)；[完整记录](parameters.json)。

### `particle_self_contact_margin`

类别：自接触；声明默认：`None`；单位：长度。

显式指定 gap 才采用新语义：相互作用距离。单独给 margin 且不传 radius/gap 时仍采用旧检测半径语义。

解析：`all omitted -> interaction 0.2; explicit gap -> margin (or 0.2); margin-only -> legacy query radius`。状态：`active`。

证据：[签名 L365](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L365)；[完整记录](parameters.json)。

### `particle_self_contact_gap`

类别：自接触；声明默认：`None`；单位：长度。

新语义的额外检测距离，query_radius=margin+gap；新配置即使 gap=0 也应显式填写。

解析：`None -> 0 only in default/new convention; legacy radius/margin computes query minus interaction`。状态：`active`。

证据：[签名 L366](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L366)；[完整记录](parameters.json)。

### `particle_conservative_bound_relaxation`

类别：弃用兼容；声明默认：`None`；单位：无量纲。

弃用别名；非 None 时覆盖 dat_conservative_bound_relaxation 并警告。

解析：`None`。状态：`deprecated`。

证据：[签名 L367](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L367)；[完整记录](parameters.json)。

### `particle_vertex_contact_buffer_size`

类别：容量；声明默认：`32`；单位：候选对/顶点。

每顶点的顶点-三角形候选容量；超出容量的对会在检测时被静默丢弃。

解析：`32`。状态：`active`。

证据：[签名 L368](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L368)；[完整记录](parameters.json)。

### `particle_edge_contact_buffer_size`

类别：容量；声明默认：`64`；单位：候选对/边。

每边的边-边候选容量；超出容量的对会在检测时被静默丢弃。

解析：`64`。状态：`active`。

证据：[签名 L369](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L369)；[完整记录](parameters.json)。

### `particle_collision_detection_interval`

类别：弃用兼容；声明默认：`None`；单位：迭代间隔。

旧调度：负数 PRE_INIT，0 PRE_POST_INIT，正 n ITERATIONS；新配置用 collision_frequency_type/frequency。

解析：`None`。状态：`deprecated`。

证据：[签名 L370](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L370)；[完整记录](parameters.json)。

### `particle_edge_parallel_epsilon`

类别：几何数值；声明默认：`1e-05`；单位：内核近乎平行判据阈值。

边-边接触中识别近乎平行边的阈值；不要当作接触厚度。

解析：`1e-05`。状态：`active`。

证据：[签名 L371](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L371)；[完整记录](parameters.json)。

### `particle_enable_tile_solve`

类别：执行策略；声明默认：`True`；单位：布尔。

CUDA 上使用 tiled 粒子弹性核，CPU 自动停用；构造时按材料特化，改变三角形/边刚度后重建 solver。

解析：`True`。状态：`active`。

证据：[签名 L372](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L372)；[完整记录](parameters.json)。

### `particle_topological_contact_filter_threshold`

类别：自接触过滤；声明默认：`2`；单位：拓扑环数。

丢弃拓扑距离过近的候选；增大可能滤掉真实折叠接触，文档提示超过 3 环代价明显。

解析：`2`。状态：`active`。

证据：[签名 L373](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L373)；[完整记录](parameters.json)。

### `particle_rest_shape_contact_exclusion_radius`

类别：自接触过滤；声明默认：`0.0`；单位：长度。

根据 model.particle_q 的静止构形间距额外排除近邻候选；不是当前帧接触半径。

解析：`0.0`。状态：`active`。

证据：[签名 L374](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L374)；[完整记录](parameters.json)。

### `particle_external_vertex_contact_filtering_map`

类别：自接触过滤；声明默认：`None`；单位：primitive ID 映射。

额外排除的 vertex→triangle ID 集合/列表；仅自接触启用时使用。

解析：`None`。状态：`active`。

证据：[签名 L375](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L375)；[完整记录](parameters.json)。

### `particle_external_edge_contact_filtering_map`

类别：自接触过滤；声明默认：`None`；单位：primitive ID 映射。

额外排除的 edge→edge ID 集合/列表；避免拿场景对象 ID 代替 primitive ID。

解析：`None`。状态：`active`。

证据：[签名 L376](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L376)；[完整记录](parameters.json)。

### `rigid_compliant_alm`

类别：刚体模式；声明默认：`None`；单位：布尔或 None。

True 为推荐的 compliant ALM；1.7.0 省略时实际为 False legacy，并在积分刚体时警告。须显式固定。

解析：`None -> False in 1.7.0; explicit True selects compliant ALM`。状态：`active`。

证据：[签名 L378](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L378)；[完整记录](parameters.json)。

### `rigid_avbd_alpha`

类别：约束稳定化；声明默认：`None`；单位：无量纲。

既存约束误差稳定化，作用于 C-alpha*C0；None 在 compliant 为 0、legacy 为 0.95。不是刚度。

解析：`None -> 0.0 (compliant) or 0.95 (legacy)`。状态：`active`。

证据：[签名 L379](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L379)；[完整记录](parameters.json)。

### `rigid_avbd_joint_alpha`

类别：约束稳定化；声明默认：`None`；单位：无量纲。

关节行 alpha 覆盖；None 继承已解析的全局 alpha。

解析：`None -> resolved rigid_avbd_alpha`。状态：`active`。

证据：[签名 L380](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L380)；[完整记录](parameters.json)。

### `rigid_avbd_contact_alpha`

类别：约束稳定化；声明默认：`None`；单位：无量纲。

接触行 alpha 覆盖；None 继承已解析的全局 alpha。

解析：`None -> resolved rigid_avbd_alpha`。状态：`active`。

证据：[签名 L381](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L381)；[完整记录](parameters.json)。

### `rigid_avbd_beta`

类别：legacy 罚参数；声明默认：`0.0`；单位：依约束残差量纲。

legacy penalty ramp 的全局速率，0 表示不增长；不能把它当物理刚度。body-particle penalty 路径也使用该设置。

解析：`0.0`。状态：`active`。

证据：[签名 L382](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L382)；[完整记录](parameters.json)。

### `rigid_avbd_linear_beta`

类别：legacy 罚参数；声明默认：`None`；单位：线性行的刚度/残差。

None 继承 beta；线性约束和 body-particle 接触增长速率。

解析：`None -> rigid_avbd_beta`。状态：`active`。

证据：[签名 L383](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L383)；[完整记录](parameters.json)。

### `rigid_avbd_angular_beta`

类别：legacy 罚参数；声明默认：`None`；单位：角度行的刚度/残差。

None 继承 beta；角约束增长速率；线性和角度参数不可直接等量替换。

解析：`None -> rigid_avbd_beta`。状态：`active`。

证据：[签名 L384](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L384)；[完整记录](parameters.json)。

### `rigid_avbd_gamma`

类别：历史状态；声明默认：`0.999`；单位：无量纲。

历史罚参数/乘子衰减。legacy 乘子保留 alpha*gamma，compliant 保留 gamma；论文示例 gamma 不等于源码默认。

解析：`0.999`。状态：`active`。

证据：[签名 L385](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L385)；[完整记录](parameters.json)。

### `rigid_contact_hard`

类别：legacy 模式；声明默认：`True`；单位：布尔。

控制 legacy 刚体接触硬约束乘子行为；compliant ALM 中无该硬/软切换效应。

解析：`True`。状态：`active`。

证据：[签名 L387](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L387)；[完整记录](parameters.json)。

### `rigid_contact_history`

类别：历史状态；声明默认：`False`；单位：布尔。

跨帧恢复刚体接触状态；要求接触匹配可用，owned pipeline 的 matching=disabled 会被拒绝。

解析：`False`。状态：`active`。

证据：[签名 L388](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L388)；[完整记录](parameters.json)。

### `rigid_contact_stick_motion_eps`

类别：已忽略；声明默认：`None`；单位：旧接口。

已弃用且忽略；传数值不产生 deadzone 效果。几何持久化应在 CollisionPipeline 配置 sticky matching。

解析：`None`。状态：`ignored_deprecated`。

证据：[签名 L389](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L389)；[完整记录](parameters.json)。

### `rigid_contact_stick_freeze_translation_eps`

类别：已忽略；声明默认：`None`；单位：旧接口。

已弃用且忽略，不应纳入调参搜索空间。

解析：`None`。状态：`ignored_deprecated`。

证据：[签名 L390](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L390)；[完整记录](parameters.json)。

### `rigid_contact_stick_freeze_angular_eps`

类别：已忽略；声明默认：`None`；单位：旧接口。

已弃用且忽略，不应纳入调参搜索空间。

解析：`None`。状态：`ignored_deprecated`。

证据：[签名 L391](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L391)；[完整记录](parameters.json)。

### `rigid_contact_k_start`

类别：legacy 罚参数；声明默认：`100.0`；单位：接触刚度量纲。

legacy 接触罚参数起点；beta=0 时不起渐增作用，compliant 的刚体行由内部 rho 策略决定。

解析：`100.0`。状态：`active`。

证据：[签名 L392](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L392)；[完整记录](parameters.json)。

### `rigid_body_contact_buffer_size`

类别：容量；声明默认：`64`；单位：接触/刚体。

每刚体接触邻接表容量；不同于 CollisionPipeline 的全局 rigid_contact_max。

解析：`64`。状态：`active`。

证据：[签名 L393](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L393)；[完整记录](parameters.json)。

### `rigid_body_particle_contact_buffer_size`

类别：容量；声明默认：`256`；单位：接触/刚体。

每刚体刚柔接触邻接表容量；不同于全局 soft_contact_max，需考虑接触密度。

解析：`256`。状态：`active`。

证据：[签名 L394](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L394)；[完整记录](parameters.json)。

### `rigid_soft_contact_use_log_barrier`

类别：刚柔接触；声明默认：`False`；单位：布尔。

False 为默认二次 penalty；True 使用与软体自接触同类的 C2 log barrier。不是 DAT 开关。

解析：`False`。状态：`active`。

证据：[签名 L395](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L395)；[完整记录](parameters.json)。

### `rigid_joint_linear_ke`

类别：物理/结构行；声明默认：`100000.0`；单位：N/m。

非 ROD 关节结构线性刚度；compliant 中是有限材料刚度，legacy 中还承担相应罚参数边界语义。

解析：`100000.0`。状态：`active`。

证据：[签名 L397](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L397)；[完整记录](parameters.json)。

### `rigid_joint_angular_ke`

类别：物理/结构行；声明默认：`100000.0`；单位：N·m/rad。

非 ROD 关节结构角刚度；不可与线性 ke 混为同一量纲。

解析：`100000.0`。状态：`active`。

证据：[签名 L398](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L398)；[完整记录](parameters.json)。

### `rigid_joint_linear_k_start`

类别：legacy 罚参数；声明默认：`100.0`；单位：N/m。

legacy 结构线性行罚参数起点；是否生效与 beta/模式有关。

解析：`100.0`。状态：`active`。

证据：[签名 L399](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L399)；[完整记录](parameters.json)。

### `rigid_joint_angular_k_start`

类别：legacy 罚参数；声明默认：`10.0`；单位：N·m/rad。

legacy 结构角行罚参数起点；不是 ROD 的材料参数。

解析：`10.0`。状态：`active`。

证据：[签名 L400](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L400)；[完整记录](parameters.json)。

### `rigid_joint_linear_kd`

类别：物理/结构行；声明默认：`0.0`；单位：N·s/m。

非 ROD 结构线性阻尼，绝对物理阻尼系数，负值按源码夹为 0。

解析：`0.0`。状态：`active`。

证据：[签名 L401](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L401)；[完整记录](parameters.json)。

### `rigid_joint_angular_kd`

类别：物理/结构行；声明默认：`0.0`；单位：N·m·s/rad。

非 ROD 结构角阻尼，绝对物理阻尼系数，负值按源码夹为 0。

解析：`0.0`。状态：`active`。

证据：[签名 L402](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L402)；[完整记录](parameters.json)。

### `rigid_soft_enable_dat`

类别：DAT；声明默认：`False`；单位：布尔。

为刚柔接触启用刚体与粒子运动截断；要求 solver-owned pipeline，禁止 external rigid，实际查询存在时最小查询半径须为正。不能推广为全场景无穿透保证。

解析：`False`。状态：`active`。

证据：[签名 L404](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L404)；[完整记录](parameters.json)。

### `rigid_soft_dat_use_interval_arithmetic`

类别：DAT；声明默认：`False`；单位：布尔。

刚柔 DAT 刚体轨迹截断的区间算术求界选项；仅对应路径启用时有意义。

解析：`False`。状态：`active`。

证据：[签名 L405](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L405)；[完整记录](parameters.json)。

### `deterministic`

类别：执行策略；声明默认：`None`；单位：Warp 枚举或 None。

None 继承 wp.config.deterministic；非 NOT_GUARANTEED 模式采用无原子 per-particle gather 等路径，不代表跨所有设备逐位相同。

解析：`None -> wp.config.deterministic`。状态：`active`。

证据：[签名 L406](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L406)；[完整记录](parameters.json)。

### `collision_pipeline`

类别：碰撞所有权；声明默认：`None`；单位：对象或 None。

传入后 solver 持有 pipeline/contacts 并按调度执行检测；step 必须传 contacts=None。未传时由调用者外部检测。

解析：`None`。状态：`active`。

证据：[签名 L407](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L407)；[完整记录](parameters.json)。

### `collision_frequency`

类别：碰撞调度；声明默认：`None`；单位：迭代间隔映射。

按 CollisionSlot 配置 ITERATIONS 模式的 k；与 frequency_type 合用，可经 set_collision_frequency 更新。刚柔 DAT 与自接触同时启用时，RIGID/SOFT_SELF_CONTACT 的 ITERATIONS 频率必须相同。

解析：`None`。状态：`active`。

证据：[签名 L408](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L408)；[完整记录](parameters.json)。

### `collision_frequency_type`

类别：碰撞调度；声明默认：`None`；单位：枚举映射。

AUTO 默认：启用软自接触为 PRE_POST_INIT；owned rigid 默认 PRE_INIT，开启 rigid_soft DAT 时为 PRE_POST_INIT。双 DAT 同时启用时两个 slot 的解析类型须一致，ITERATIONS 还须同频率。

解析：`AUTO resolved per slot and active DAT family`。状态：`active`。

证据：[签名 L409](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L409)；[完整记录](parameters.json)。

## 新式自接触配置示意

```python
particle_enable_self_contact=True,
particle_self_contact_margin=0.005,
particle_self_contact_gap=0.005,
```

这里的 5 mm + 5 mm 仅是兼容语义探针配置，已验证 query radius=10 mm；不是布料抓取的通用推荐值。若仅填 margin=0.005 而不填 gap，启用自接触且有粒子时会因保留旧语义而报错。

## 代码强制约束与建议的区别

| 类别 | 本版本已核查规则 |
|---|---|
| 强制约束 | DAT relaxation 严格在 (0,1)；全局 beta>=0；旧 radius 不可和新 gap 并用 |
| 强制依赖 | rigid-soft DAT 需 owned pipeline、不可 external rigid、存在查询时需正查询半径 |
| 模式依赖 | legacy hard/soft 控制在 compliant rigid 路径不产生同样模式作用；body-particle 仍需单独分析 |
| 已忽略 | 三个 stick/deadzone 参数被忽略，即使优化器给它们采样也不会达到预期效果 |
| 待实测建议 | iterations、dt、网格精度、buffer、摩擦和刚度的搜索区间由任务标定决定 |

不要把本表当作完整参数有效性验证器；精确异常还受场景结构、运行模式和设备影响。
