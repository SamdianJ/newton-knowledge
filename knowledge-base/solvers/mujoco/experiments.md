# MuJoCo · 关节、摩擦与接触参数实验

固定 Newton 1.7.0 / native MuJoCo 3.15.0 / CPU、单 world。

## 关节、摩擦与接触的新增实测

已新增 12 组 native CPU 配对实验，48 次独立运行；8 组通过各自事前物理门槛。原两组迭代预算/ke-kd 接触响应实验继续保留。新增结果同时检查 Newton 输入、编译后的 MuJoCo 模型字段和实际响应，每设置独立进程重复两次。详见 [关节与碰撞实验](experiments.md)。

## 场景与效果

| 参数机制 | 物理验收 | 保存结果 |
|---|---|---|
| [被动关节阻尼：无驱动自由转子的能量衰减](#/record/lab%3Amujoco_joint_passive_damping) | 通过 | 初速1rad/s、无驱动时，被动damping从0变2，2s末速度从1降至0.0184623rad/s，动能剩0.03409%；无阻尼对照能量不变。符合含隐式被动阻尼的Euler独立参考。 |
| [Armature：同力矩下的有效惯量与加速度](#/record/lab%3Amujoco_joint_armature_inertia) | 通过 | armature从0增至3，在相同1N·m力矩下原生有效惯量约从1增至4kg·m²，速度和加速度降为约1/4；物理body质量及惯量没有增加。它改变惯量，不是耗散阻尼。 |
| [驱动阻尼：同位置增益下振荡与收敛](#/record/lab%3Amujoco_joint_pd_damping) | 通过 | 固定kp25、目标0.1rad，target_kd从0变10，过冲从0.100001rad降为0，末误差5.50e-5rad。两者驱动力矩和轨迹均吻合独立离散参考；此处只扫描kd，不代表已经扫描kp。 |
| [关节上限：到达时刻、软约束反力与停止位置](#/record/lab%3Amujoco_joint_upper_limit) | 通过 | 上限从0.1移至0.2rad，首次限位反力由0.448s延后至0.632s，末位置随范围平移约0.1rad。最大软穿越0.00607/0.00805rad，末残差约1.10e-4rad；末反力抵消1N·m外力矩，不是硬裁剪到限位。 |
| [原始高速度/较高摩擦边界：滑动μ单因素](#/record/lab%3Amujoco_sliding_friction_mu) | 未通过，保留负结果 | μ=0.1/0.4，末vx=1.706430/0.811475m/s，速度分离0.894956m/s；实际积分切向/法向比=0.1/0.4，完整线冲量误差≤4.87e-07Ns。t≥.05有效承载比例18.80%/30.40%；完整物理验收failed_criteria。未通过：settled_contact_present_fraction=0.188未达>=0.99；settled_positive_normal_force_fraction=0.188未达>=0.99；settled_contact_present_fraction=0.304未达>=0.99；settled_positive_normal_force_fraction=0.304未达>=0.99；analytic_sliding_velocity_max_error_m_s=0.0866295未达<=0.08。 |
| [原始高速度/较高摩擦边界：condim3/4扭转机制](#/record/lab%3Amujoco_torsional_friction_condim) | 未通过，保留负结果 | 固定扭转系数0.002m，仅改condim3/4，末ωz=10.000015/7.553361rad/s；A扭矩0，B积分扭矩/法向比=0.002m、角冲量误差2.5e-07Nms。t≥.05有效承载比例100.00%/75.11%；完整物理验收failed_criteria。未通过：settled_contact_present_fraction=0.751111未达>=0.99；settled_positive_normal_force_fraction=0.751111未达>=0.99；kinetic_energy_max_positive_step_J=0.000136617未达<=0.0001。 |
| [原生 solref 阻尼比与回弹](#/record/lab%3Anative_solref_rebound) | 通过 | 固定 timeconst .02 s，阻尼比 .2 / 1 的实测回弹速度比为 0.583149 / 0.136499；该正值 solref 干预同时改变有效刚度。 |
| [gap 提前检测但不提前激活接触力](#/record/lab%3Anative_gap_activation) | 通过 | gap 0 / .04 m 的首次检测为 0.0905 / 0.0505 s；首次激活均为 0.0905 s。较大 gap 提供 80 个提前检测但无力样本，A/B 轨迹等价。 |
| [提高impratio假设对照：滑动μ单因素](#/record/lab%3Amujoco_sliding_friction_mu_stable) | 未通过，保留负结果 | 公共impratio仅由1改为1000，组内对照不变。μ=0.1/0.4，末vx=1.703840/0.823855m/s，速度分离0.879984m/s；实际积分切向/法向比=0.1/0.4，完整线冲量误差≤4.61e-07Ns。t≥.05有效承载比例53.20%/30.00%；完整物理验收failed_criteria。未通过：settled_contact_present_fraction=0.532未达>=0.99；settled_positive_normal_force_fraction=0.532未达>=0.99；settled_contact_present_fraction=0.3未达>=0.99；settled_positive_normal_force_fraction=0.3未达>=0.99。 提高该值未消除间歇承载；目录stable只是设计时名称，不表示稳定效果。 |
| [提高impratio假设对照：condim3/4扭转机制](#/record/lab%3Amujoco_torsional_friction_condim_stable) | 未通过，保留负结果 | 公共impratio仅由1改为1000，组内对照不变。固定扭转系数0.002m，仅改condim3/4，末ωz=10.000015/7.554088rad/s；A扭矩0，B积分扭矩/法向比=0.002m、角冲量误差2.54e-07Nms。t≥.05有效承载比例100.00%/74.67%；完整物理验收failed_criteria。未通过：settled_contact_present_fraction=0.746667未达>=0.99；settled_positive_normal_force_fraction=0.746667未达>=0.99。 提高该值未消除间歇承载；目录stable只是设计时名称，不表示稳定效果。 |
| [低摩擦/低速区域：滑动μ单因素](#/record/lab%3Amujoco_sliding_friction_mu_low_regime) | 通过 | 新低量级场景，不能推论原高速/较高摩擦条件已解决。μ=0.001/0.004，末vx=0.017057/0.008228m/s，速度分离0.008829m/s；实际积分切向/法向比=0.001/0.004，完整线冲量误差≤1.27e-07Ns。t≥.05有效承载比例100.00%/100.00%；完整物理验收passed。各冻结物理门槛通过。 |
| [低摩擦/低速区域：condim3/4扭转机制](#/record/lab%3Amujoco_torsional_friction_condim_low_regime) | 通过 | 新低量级场景，不能推论原高速/较高摩擦条件已解决。固定扭转系数2e-05m，仅改condim3/4，末ωz=0.999999/0.975477rad/s；A扭矩0，B积分扭矩/法向比=2e-05m、角冲量误差1.15e-08Nms。t≥.05有效承载比例100.00%/100.00%；完整物理验收passed。各冻结物理门槛通过。 |

## 关节参数应怎样区分

- `joint_damping` 是被动黏性阻尼，直接导出到 `dof_damping`；它不需要 PD 驱动。本组 Euler 参考将被动阻尼隐式积分，同时验证实际被动力与能量衰减。
- `joint_armature` 增加广义惯量，保持 body 质量及惯量不变；同一力矩下加速度变化有独立惯量参考。它不是耗散项。
- `joint_target_kd` 在位置驱动中改变速度反馈。实验固定 kp、只改变 kd，核对 actuator gain/bias；不能把该结果称为 kp 扫描。明确选择 Euler 后，驱动阻尼按本组离散公式验收，不能套用 Kamino 的全隐式 PD 公式。
- `joint_limit_upper` 改变运动范围和到达时刻；MuJoCo 限位是软约束。实验检查实际范围、约束反力、有限超限与末态平衡，不假设硬裁剪或零穿透。

## 摩擦需要同时检查什么

滑动摩擦不仅取决于单个 shape 的 `mu`，还要核对两侧材质混合后的实际 contact friction、接触维度和法向力。每个滑动案例分别检查独立冲量平衡、持续承载和恒载荷运动参考；摩擦减速方向正确，不等于整组物理验收通过。

`condim=3` 含法向和两方向切向响应；`condim=4` 还允许法线轴上的扭转摩擦。扭转案例固定扭转系数，只改变接触维度，检查自旋制动及实际接触力矩。`mu_torsional` 和 `mu_rolling` 的尺度单位是 m，不能与无量纲滑动 mu 混用。本轮扭转实验不构成 `condim=6` 滚动摩擦验证。

原始较高摩擦/速度场景出现间歇承载，仍作为正式负结果保留；仅提高 `impratio` 的假设也单列检验，不能凭其名称或参数值认定接触已稳定。较低摩擦/速度区域是另行冻结的场景，不覆盖或修复原失败条件。是否通过以各案例的事前门槛为准；动能上升还需结合势能和外力判断，不能直接等同于能量注入。

原生 MuJoCo 的 contact force 读取属于本实验的后端诊断，不能由此宣称 Newton 的 native CPU `CONTACT_F` 接口已受支持。

## 接触响应与碰撞检测的边界

正值 `solref` 的时间常数和阻尼比共同决定接触响应；固定时间常数只改阻尼比也会影响等效刚度，因此这类回弹对照不是独立 penalty 阻尼系数扫描。需同时记录实际 solref/solimp、refsafe 和时间步。

接触候选生成、活动约束和实际接触力是不同事件。margin/gap 案例依据固定后端版本的语义，分别记录候选出现和约束激活时刻，并检查 Newton 导出后的实际参数及 CCD 标志；不能把检测到候选直接当作已经产生力。

## 每组适用边界

- **被动关节阻尼：无驱动自由转子的能量衰减**：Native CPU MuJoCo3.15.0 with Newton1.7.0 only; no MuJoCo Warp claim; One scalar joint, diagonal constant inertia, no gravity/contact or coupled joints; Euler selected for auditable discrete references; not a recommendation over default implicitfast; Joint limit is soft and transient waveform is not claimed analytically reproduced; No kp sweep, effort/velocity-limit sweep or runtime property update tested; Model export/native diagnostic arrays are observational instrumentation
- **Armature：同力矩下的有效惯量与加速度**：Native CPU MuJoCo3.15.0 with Newton1.7.0 only; no MuJoCo Warp claim; One scalar joint, diagonal constant inertia, no gravity/contact or coupled joints; Euler selected for auditable discrete references; not a recommendation over default implicitfast; Joint limit is soft and transient waveform is not claimed analytically reproduced; No kp sweep, effort/velocity-limit sweep or runtime property update tested; Model export/native diagnostic arrays are observational instrumentation
- **驱动阻尼：同位置增益下振荡与收敛**：Native CPU MuJoCo3.15.0 with Newton1.7.0 only; no MuJoCo Warp claim; One scalar joint, diagonal constant inertia, no gravity/contact or coupled joints; Euler selected for auditable discrete references; not a recommendation over default implicitfast; Joint limit is soft and transient waveform is not claimed analytically reproduced; No kp sweep, effort/velocity-limit sweep or runtime property update tested; Model export/native diagnostic arrays are observational instrumentation
- **关节上限：到达时刻、软约束反力与停止位置**：Native CPU MuJoCo3.15.0 with Newton1.7.0 only; no MuJoCo Warp claim; One scalar joint, diagonal constant inertia, no gravity/contact or coupled joints; Euler selected for auditable discrete references; not a recommendation over default implicitfast; Joint limit is soft and transient waveform is not claimed analytically reproduced; No kp sweep, effort/velocity-limit sweep or runtime property update tested; Model export/native diagnostic arrays are observational instrumentation
- **原始高速度/较高摩擦边界：滑动μ单因素**：仅固定Newton1.7.0 / native MuJoCo3.15.0 CPU单world；GPU、Newton外部contact路径未测。; 两组均未通过完整事前物理验收，不能将可观测的摩擦作用标为持续接触机制已验证。; 滑动无量纲；扭转系数单位m，输出摩擦力N、扭矩Nm。mj_contactForce为原生诊断，不代表Newton CONTACT_F受支持。; 未测静摩擦启滑、滚动condim6、非等priority、显式pair、各向异性、复杂堆叠。; 默认geom_gap约.1m使ncon包含分离候选；active efc_address和正法向力必须单独检查。; 构造前步长快照为.002s；逐步native_timestep原始记录与正式dt均为.001s。; t≥.05解析参考以测得速度作锚点；全程独立动量平衡不依赖该锚点。
- **原始高速度/较高摩擦边界：condim3/4扭转机制**：仅固定Newton1.7.0 / native MuJoCo3.15.0 CPU单world；GPU、Newton外部contact路径未测。; 两组均未通过完整事前物理验收，不能将可观测的摩擦作用标为持续接触机制已验证。; 滑动无量纲；扭转系数单位m，输出摩擦力N、扭矩Nm。mj_contactForce为原生诊断，不代表Newton CONTACT_F受支持。; 未测静摩擦启滑、滚动condim6、非等priority、显式pair、各向异性、复杂堆叠。; 默认geom_gap约.1m使ncon包含分离候选；active efc_address和正法向力必须单独检查。; 构造前步长快照为.002s；逐步native_timestep原始记录与正式dt均为.001s。; t≥.05解析参考以测得速度作锚点；全程独立动量平衡不依赖该锚点。
- **原生 solref 阻尼比与回弹**：native CPU frictionless sphere-plane only; constant solimp and fixed timestep; positive solref ratio changes effective stiffness as well as damping ratio; no pair override, mesh, multiccd, runtime margin changes or MuJoCo Warp claim; MuJoCo 3.15 modern gap semantics only
- **gap 提前检测但不提前激活接触力**：native CPU frictionless sphere-plane only; constant solimp and fixed timestep; positive solref ratio changes effective stiffness as well as damping ratio; no pair override, mesh, multiccd, runtime margin changes or MuJoCo Warp claim; MuJoCo 3.15 modern gap semantics only
- **提高impratio假设对照：滑动μ单因素**：仅固定Newton1.7.0 / native MuJoCo3.15.0 CPU单world；GPU、Newton外部contact路径未测。; 两组均未通过完整事前物理验收，不能将可观测的摩擦作用标为持续接触机制已验证。; 滑动无量纲；扭转系数单位m，输出摩擦力N、扭矩Nm。mj_contactForce为原生诊断，不代表Newton CONTACT_F受支持。; 未测静摩擦启滑、滚动condim6、非等priority、显式pair、各向异性、复杂堆叠。; 默认geom_gap约.1m使ncon包含分离候选；active efc_address和正法向力必须单独检查。; 构造前步长快照为.002s；逐步native_timestep原始记录与正式dt均为.001s。; t≥.05解析参考以测得速度作锚点；全程独立动量平衡不依赖该锚点。
- **提高impratio假设对照：condim3/4扭转机制**：仅固定Newton1.7.0 / native MuJoCo3.15.0 CPU单world；GPU、Newton外部contact路径未测。; 两组均未通过完整事前物理验收，不能将可观测的摩擦作用标为持续接触机制已验证。; 滑动无量纲；扭转系数单位m，输出摩擦力N、扭矩Nm。mj_contactForce为原生诊断，不代表Newton CONTACT_F受支持。; 未测静摩擦启滑、滚动condim6、非等priority、显式pair、各向异性、复杂堆叠。; 默认geom_gap约.1m使ncon包含分离候选；active efc_address和正法向力必须单独检查。; 构造前步长快照为.002s；逐步native_timestep原始记录与正式dt均为.001s。; t≥.05解析参考以测得速度作锚点；全程独立动量平衡不依赖该锚点。
- **低摩擦/低速区域：滑动μ单因素**：仅固定Newton1.7.0 / native MuJoCo3.15.0 CPU单world；GPU、Newton外部contact路径未测。; 滑动无量纲；扭转系数单位m，输出摩擦力N、扭矩Nm。mj_contactForce为原生诊断，不代表Newton CONTACT_F受支持。; 未测静摩擦启滑、滚动condim6、非等priority、显式pair、各向异性、复杂堆叠。; 默认geom_gap约.1m使ncon包含分离候选；active efc_address和正法向力必须单独检查。; 构造前步长快照为.002s；逐步native_timestep原始记录与正式dt均为.001s。; t≥.05解析参考以测得速度作锚点；全程独立动量平衡不依赖该锚点。
- **低摩擦/低速区域：condim3/4扭转机制**：仅固定Newton1.7.0 / native MuJoCo3.15.0 CPU单world；GPU、Newton外部contact路径未测。; 滑动无量纲；扭转系数单位m，输出摩擦力N、扭矩Nm。mj_contactForce为原生诊断，不代表Newton CONTACT_F受支持。; 未测静摩擦启滑、滚动condim6、非等priority、显式pair、各向异性、复杂堆叠。; 默认geom_gap约.1m使ncon包含分离候选；active efc_address和正法向力必须单独检查。; 构造前步长快照为.002s；逐步native_timestep原始记录与正式dt均为.001s。; t≥.05解析参考以测得速度作锚点；全程独立动量平衡不依赖该锚点。

## 仍未覆盖

MuJoCo Warp/GPU、复杂多关节耦合、多 world、滚动摩擦参数扫描、各向异性/复杂接触、所有增益/步长/容差组合、长时间稳定性和论文基准。案例演示的效果只在已保存场景成立，不直接生成通用推荐参数。

[原始证据、冻结协议与复现](../../experiments/mujoco_joint_contact_lab/README.md)。


## 实体轮廓回放

当前 MuJoCo / Kamino 参数实验已统一为三维实体轮廓展示，可同步旋转、缩放、切换正侧俯视和放大 A/B。原始几何按冻结尺寸绘制；无 shape 的转子以标注的示意转盘显示保存转角，不改变动力学或碰撞模型。归档数据、曲线与验收结果保持原样。历史实验 README 中的坐标轴展示描述对应原版视图；当前展示机制见 [新版回放说明](../../experiments/solid_replay/README.md)。
