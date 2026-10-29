# 原生 MuJoCo 摩擦实验设计（待冻结）

固定 Newton 1.7.0 / `7e75abe28b8d69522bc0b34837aaed2c303dff5a` 和 native MuJoCo 3.15.0，CPU单world。只写本新目录，旧数据和源码不改；尚未运行仿真。

## 两个可判别场景

1. 薄宽盒在水平面以2 m/s滑动：质量1 kg、半尺寸(.2,.15,.025)m，使用解析均匀盒惯量；只改变盒滑动摩擦μ=.1/.4。持续.3 s、dt=.001 s，condim=3固定。低COM、宽底面和无翻滚门槛避免把滚动/倾倒当作摩擦变化；持续滑动速度必须>.5m/s。
2. 半径.1m球体以10 rad/s绕接触法线自旋：质量1kg、惯量.004 kg m²；滑动μ=.3、扭转系数.002m固定，仅改球condim=3/4。持续.5s。球与平面只有一个接触点，纯法线自旋不产生多点滑动摩擦矩，故可区分condim启用的扭转力矩；同时限制横向速度和非轴向角速度。

每case A/B各2个独立进程，共8次。地面三种摩擦输入均0、priority相同；两geom的raw solref=(.01,1)、solimp=(.95,.95,.001,.5,2)、solmix=1相同。初始只压入1e-5m，不做筛选性预跑；保留全部启动过程。简单恒定法向载荷解析参考从固定t=.05s开始，其余接触、冲量平衡、有限性始终检查全程。

## 实际映射与混合

Newton `ShapeConfig.mu/mu_torsional/mu_rolling` 分别映射 `shape_material_mu/..._torsional/..._rolling` 和原生 `geom_friction=[slide,torsion,rolling]`。滑动系数无量纲，扭转/滚动系数单位为m，不能统一称无量纲摩擦系数。

同priority时，原生condim取最大，三个摩擦分量逐项取最大，再展开为 `[slide,slide,torsion,rolling,rolling]`。MuJoCo会将接触系数最小裁为1e-5，即使对应维度未启用；condim3中“保存了非零torsion”不表示已产生扭矩。高priority覆盖规则和显式pair不在本次干预范围。固定3.15.0源已保存在native-source并有URL/hash，特别核对 collision_driver.c、core_constraint.c、core_util.c；不使用GPU实现推断native行为。

## 力和参考

仅用原生 `mujoco.mj_contactForce` 诊断接触坐标中的 `[force,torque]`，分别为N和Nm；这不是Newton `CONTACT_F` 支持声明。每次Newton solver.step后立即读出该步求解用的contact，不调用会重新求解/覆盖数据的mj_forward。接触frame的转置将局部向量转到世界；正向施加于geom2，对动态物体位于geom1时取反。力矩再加接触点相对步前COM的力臂叉积。该符号约定由独立动量平衡强制验证，不能看结果后择符号。

滑动对照检查解析 `Δv=-μgΔt`、切向/法向冲量比例、完整线动量平衡及最终速度分离≥.6m/s。自旋检查condim3角速度近似不变/无法向接触矩，condim4满足 `Δω=-μ_t*m*g/I*Δt`、扭矩/法向力比例、独立角动量平衡，最终角速度分离≥1.5rad/s。有效接触、正法向力、实际contact dim/friction、无倾倒/无侧向运动是必要条件，不以“看起来减速”替代接触证据。

## 接受门槛与边界

所有阈值、对照差异和重复容差在protocol-draft.json列出。预计速度差.883m/s、角速度差2.4525rad/s，阈值低于预期但远高于数值噪声；动量平衡是独立于库配置的物理交叉核验。将记录实际geom/接触字段、native solver设置、全部809个Newton安装源hash、native库hash和所有失败。

仅证明native CPU、两个简单持续滑动/自旋机制。未测试静摩擦启滑、滚动condim6、非等priority、显式pair、各向异性、多接触复杂堆叠、GPU或Newton外部碰撞路径。不得据此覆盖所有摩擦参数组合。root冻结协议并通知SHA后才可运行。
