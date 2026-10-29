# 关节与机械系统

广义坐标和最大坐标的双重表示。

## 机制与数据流

joint_q/joint_qd 表示广义坐标；body_q/body_qd 表示刚体位姿和质心 twist。eval_fk 从关节坐标更新刚体表示，eval_ik 做反向表示转换；MuJoCo/Featherstone 主要使用广义坐标。

## 诊断与边界

碰撞前保证最大坐标更新；FREE/BALL 的坐标数与 DOF 数不同，不能统一按 qd offset 索引目标。



## 树、闭环与耦合关系

| 概念 | 如何表达 | 关键边界 |
|---|---|---|
| articulation tree | `add_joint_*` 建关节，树关节列表交给 `add_articulation` | 每个body至多一个树父关节；FK、IK和ArticulationView沿树遍历 |
| loop-closing joint | 另建连接两个已由树可达body的关节，但不把它加入articulation的joint_list | 它不是orphan joint，正常通过finalize；不额外出现在树的FK/IK坐标中。maximal solver按所支持关节类型求约束；MuJoCo编译为受限双边耦合；Featherstone不执行该闭环约束 |
| joint-owned mimic | `set_joint_mimic(follower, reference, coeffs=(offset, multiplier))` | 两端位置/速度维度相同，限PRISMATIC/REVOLUTE/D6；不能建立mimic链。四元数关节不能逐分量做这类仿射关系 |
| equality | MuJoCo专属约束通过注册的`mujoco:equality_constraint_*`自定义属性构建 | 不是所有solver共享的独立核心构件；不能因能写入字段就推断VBD等会消费 |
| tendon | fixed/spatial tendon通过MuJoCo命名空间的自定义属性与MJCF/USD导入保留 | core没有通用`add_tendon` API；转换和所支持的wrap表示见MuJoCo专区 |

独立设定初始或复位关节状态后，需要body姿态体现mimic时，先`eval_mimic(model,state)`，再`eval_fk(model,state.joint_q,state.joint_qd,state)`。支持mimic的solver在step内自行执行其约束；不要每步再投影一次。若maximal solver只更新body状态，要读求解后的关节坐标，应先`eval_ik`，不能对陈旧joint数组直接eval_mimic。

入口：[mimic维度、顺序和solver差异](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/articulations.rst#L141-L237)；[闭环、orphan和各后端处理](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/articulations.rst#L1085-L1193)；[MuJoCo equality与tendon authoring](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L411-L550)。

## 谁负责写状态

| 身份 | 状态更新责任 | 接触与建模限制 |
|---|---|---|
| static | 世界附着shape或固定世界根，位置不积分 | 可以作为障碍或支撑 |
| kinematic | 用户规定位置和一致的速度；外力不驱动自身运动 | `is_kinematic=True`只允许root link/body；非root会在articulation构造时报错。可以推动dynamic物体 |
| dynamic | solver由力、关节和接触推进 | 必须建立适当质量/惯量，不能把零质量当作通用kinematic开关 |

广义坐标路径写`joint_q/joint_qd`，再用FK更新碰撞需要的body状态；最大坐标路径写`body_q/body_qd`。速度要与规定轨迹一致，FREE/BALL的四元数用流形一致的积分，不能直接把qd加到q。MuJoCo/Featherstone与XPBD/VBD/SemiImplicit的内部处理不同；例如SemiImplicit保留规定状态，但接触内没有同样清零逆质量/惯量，接触可能更软。Kamino专属FK与驱动约束见其专区，不从这张概念表推导所有后端支持。

依据：[static/kinematic/dynamic与状态写入](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/articulations.rst#L292-L420)。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/articulations.html)。

## 固定版本原始出处

- [docs/concepts/articulations.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/articulations.rst#L1)
- [docs/concepts/articulations.rst:141](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/articulations.rst#L141-L237)
- [docs/concepts/articulations.rst:292](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/articulations.rst#L292-L420)
- [docs/concepts/articulations.rst:1085](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/articulations.rst#L1085-L1193)
- [docs/solvers/mujoco.rst:411](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L411-L550)
