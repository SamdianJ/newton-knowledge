# MuJoCo 关节机制实验设计

当前只做静态设计，等待 root 冻结协议。四个案例各两个设置、每设置两独立进程，共16次正式运行。固定 Newton1.7.0 commit7e75，安装 native MuJoCo3.15.0，CPU单world。

所有案例用COM与世界Y转轴重合的1kg刚体，COM惯量单位矩阵，无接触几何、重力或dry friction。h=.002s、2s。明确选Euler以便独立检查离散公式，并记录这是相对默认implicitfast的场景限定。native state在初始化后由MuJoCo维护（update_data_interval=0），不做中途状态写入。

1. 被动阻尼：`damping=0/2`，初速度1rad/s，没有actuator。Newton的`joint_damping`直接导出到`mj_model.dof_damping`，不同于`joint_target_kd`。参考v乘I/(I+h*d)递推；检查能量、速度和被动力矩。
2. Armature：`armature=0/3`，相同1N·m外力矩，有效惯量1/4kg·m²。检查实际armature、native qM、加速度/速度四分之一比例及全轨迹解析解，物理body mass/inertia必须保持不变。
3. 驱动阻尼：POSITION、kp固定25，`target_kd=0/10`，目标.1rad。检查实际actuator gain/bias、过冲/末态、全部轨迹和驱动力矩；不同于把被动damping调大。只扫描kd，明确不冒充kp参数扫描。
4. 关节上限：upper=.1/.2rad，其余有限范围/力限响应相同。采用自由飞行独立参考预测到达时刻，再验证反力平衡、软限位的有限穿越与末位置平移。不会编造精确soft-limit瞬态解析解，也不硬裁剪状态来“通过”。

MuJoCo Euler对被动关节阻尼隐式、对actuator PD阻尼显式；本组参考为：

    I_eff = I_body_about_axis + armature
    tau_PD = kp*(qref-q_n)-kd*v_n
    v_next = (I_eff*v_n+h*(tau_external+tau_PD))/(I_eff+h*damping)
    q_next = q_n+h*v_next

不能套用上一组Kamino全隐式PD分母。Newton导出源码和[MuJoCo3.15.0积分文档](https://mujoco.readthedocs.io/en/3.15.0/computation/index.html#numerical-integration)共同支持这一参考。

采样必须区分时间：mj_step后的qpos/qvel是输出状态，而Euler的qfrc_*仍属于本步积分前计算的力；单独保存force_t并用force[n]对比state[n]。不插入初始未求解力，也不额外调用mj_forward改变正在运行的native数据。

每次保存 actual mj_model.dof_damping/dof_armature/body inertia、jnt range/solref/solimp、actuator gain/bias/force range与积分选项；这些字段作为生效检查，不只记录requested参数。所有物理验收阈值和边界在protocol-draft.json中明确；负结果保留，任何改线都需要新协议。
