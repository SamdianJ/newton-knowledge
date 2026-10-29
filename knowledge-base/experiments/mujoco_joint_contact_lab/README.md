# MuJoCo 关节、摩擦与接触实验

固定 Newton 1.7.0 / native MuJoCo 3.15.0 / CPU / 单 world；协议先冻结，逐设置独立进程重复两次。

12 组配对案例，48 次唯一正式运行。证据完整性 passed 不等于每种场景的物理门槛全部通过。

| 案例 | 物理门槛 | 结果 |
|---|---|---|
| [被动关节阻尼：无驱动自由转子的能量衰减](joints/mujoco_joint_passive_damping.svg) | passed | 初速1rad/s、无驱动时，被动damping从0变2，2s末速度从1降至0.0184623rad/s，动能剩0.03409%；无阻尼对照能量不变。符合含隐式被动阻尼的Euler独立参考。 |
| [Armature：同力矩下的有效惯量与加速度](joints/mujoco_joint_armature_inertia.svg) | passed | armature从0增至3，在相同1N·m力矩下原生有效惯量约从1增至4kg·m²，速度和加速度降为约1/4；物理body质量及惯量没有增加。它改变惯量，不是耗散阻尼。 |
| [驱动阻尼：同位置增益下振荡与收敛](joints/mujoco_joint_pd_damping.svg) | passed | 固定kp25、目标0.1rad，target_kd从0变10，过冲从0.100001rad降为0，末误差5.50e-5rad。两者驱动力矩和轨迹均吻合独立离散参考；此处只扫描kd，不代表已经扫描kp。 |
| [关节上限：到达时刻、软约束反力与停止位置](joints/mujoco_joint_upper_limit.svg) | passed | 上限从0.1移至0.2rad，首次限位反力由0.448s延后至0.632s，末位置随范围平移约0.1rad。最大软穿越0.00607/0.00805rad，末残差约1.10e-4rad；末反力抵消1N·m外力矩，不是硬裁剪到限位。 |
| [原始高速度/较高摩擦边界：滑动μ单因素](friction/mujoco_sliding_friction_mu.svg) | failed_criteria | μ=0.1/0.4，末vx=1.706430/0.811475m/s，速度分离0.894956m/s；实际积分切向/法向比=0.1/0.4，完整线冲量误差≤4.87e-07Ns。t≥.05有效承载比例18.80%/30.40%；完整物理验收failed_criteria。未通过：settled_contact_present_fraction=0.188未达>=0.99；settled_positive_normal_force_fraction=0.188未达>=0.99；settled_contact_present_fraction=0.304未达>=0.99；settled_positive_normal_force_fraction=0.304未达>=0.99；analytic_sliding_velocity_max_error_m_s=0.0866295未达<=0.08。 |
| [原始高速度/较高摩擦边界：condim3/4扭转机制](friction/mujoco_torsional_friction_condim.svg) | failed_criteria | 固定扭转系数0.002m，仅改condim3/4，末ωz=10.000015/7.553361rad/s；A扭矩0，B积分扭矩/法向比=0.002m、角冲量误差2.5e-07Nms。t≥.05有效承载比例100.00%/75.11%；完整物理验收failed_criteria。未通过：settled_contact_present_fraction=0.751111未达>=0.99；settled_positive_normal_force_fraction=0.751111未达>=0.99；kinetic_energy_max_positive_step_J=0.000136617未达<=0.0001。 |
| [原生 solref 阻尼比与回弹](contact/native_solref_rebound.svg) | passed | 固定 timeconst .02 s，阻尼比 .2 / 1 的实测回弹速度比为 0.583149 / 0.136499；该正值 solref 干预同时改变有效刚度。 |
| [gap 提前检测但不提前激活接触力](contact/native_gap_activation.svg) | passed | gap 0 / .04 m 的首次检测为 0.0905 / 0.0505 s；首次激活均为 0.0905 s。较大 gap 提供 80 个提前检测但无力样本，A/B 轨迹等价。 |
| [提高impratio假设对照：滑动μ单因素](friction_stable/mujoco_sliding_friction_mu_stable.svg) | failed_criteria | 公共impratio仅由1改为1000，组内对照不变。μ=0.1/0.4，末vx=1.703840/0.823855m/s，速度分离0.879984m/s；实际积分切向/法向比=0.1/0.4，完整线冲量误差≤4.61e-07Ns。t≥.05有效承载比例53.20%/30.00%；完整物理验收failed_criteria。未通过：settled_contact_present_fraction=0.532未达>=0.99；settled_positive_normal_force_fraction=0.532未达>=0.99；settled_contact_present_fraction=0.3未达>=0.99；settled_positive_normal_force_fraction=0.3未达>=0.99。 提高该值未消除间歇承载；目录stable只是设计时名称，不表示稳定效果。 |
| [提高impratio假设对照：condim3/4扭转机制](friction_stable/mujoco_torsional_friction_condim_stable.svg) | failed_criteria | 公共impratio仅由1改为1000，组内对照不变。固定扭转系数0.002m，仅改condim3/4，末ωz=10.000015/7.554088rad/s；A扭矩0，B积分扭矩/法向比=0.002m、角冲量误差2.54e-07Nms。t≥.05有效承载比例100.00%/74.67%；完整物理验收failed_criteria。未通过：settled_contact_present_fraction=0.746667未达>=0.99；settled_positive_normal_force_fraction=0.746667未达>=0.99。 提高该值未消除间歇承载；目录stable只是设计时名称，不表示稳定效果。 |
| [低摩擦/低速区域：滑动μ单因素](friction_low_regime/mujoco_sliding_friction_mu_low_regime.svg) | passed | 新低量级场景，不能推论原高速/较高摩擦条件已解决。μ=0.001/0.004，末vx=0.017057/0.008228m/s，速度分离0.008829m/s；实际积分切向/法向比=0.001/0.004，完整线冲量误差≤1.27e-07Ns。t≥.05有效承载比例100.00%/100.00%；完整物理验收passed。各冻结物理门槛通过。 |
| [低摩擦/低速区域：condim3/4扭转机制](friction_low_regime/mujoco_torsional_friction_condim_low_regime.svg) | passed | 新低量级场景，不能推论原高速/较高摩擦条件已解决。固定扭转系数2e-05m，仅改condim3/4，末ωz=0.999999/0.975477rad/s；A扭矩0，B积分扭矩/法向比=2e-05m、角冲量误差1.15e-08Nms。t≥.05有效承载比例100.00%/100.00%；完整物理验收passed。各冻结物理门槛通过。 |

## 原始数据、独立参考与复现

[目录](catalog.json)、[完整结果](report-data.json)、[交互曲线与回放](index.html)。仅从保存数组绘制 body 坐标系，不表示碰撞几何。

- [joints 的场景与标准](joints/protocol.json)、[结果](joints/RESULTS.md)、[复现](joints/REPRODUCE.md)。
- [friction 的场景与标准](friction/protocol.json)、[结果](friction/RESULTS.md)、[复现](friction/REPRODUCE.md)。
- [contact 的场景与标准](contact/protocol.json)、[结果](contact/RESULTS.md)、[复现](contact/REPRODUCE.md)。
- [friction_stable 的场景与标准](friction_stable/protocol.json)、[结果](friction_stable/RESULTS.md)、[复现](friction_stable/REPRODUCE.md)。
- [friction_low_regime 的场景与标准](friction_low_regime/protocol.json)、[结果](friction_low_regime/RESULTS.md)、[复现](friction_low_regime/REPRODUCE.md)。

重新运行本目录 analyze_experiments.py 仅检查并聚合保存数据，不运行物理。新仿真必须创建新 run 目录，不覆盖原结果。

## 适用边界

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
