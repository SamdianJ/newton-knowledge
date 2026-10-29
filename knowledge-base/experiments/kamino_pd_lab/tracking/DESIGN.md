# 非饱和有界隐式 PD 跟踪协议

尚未运行 Newton 仿真。以 `protocol-draft.json` 供 root 审核；只有 root 写入冻结 `protocol.json` 并授权后才运行。

场景是质量 1 kg、COM 转动惯量单位矩阵、COM 与世界 Y 转轴重合的单转子。无重力、接触、限位、armature、摩擦。COM 与轴重合使标量惯量严格为 1 kg·m²，避免平移闭合漂移干扰控制律。采用 Euler 积分器、kp=25、kd=10、有限力矩限值 10 N·m，h=0.005 s，每次 800 步、4 s。

源实现先把有界 PD 写为 effort constraint。`kinematics/joints.py` 的 `compute_and_write_joint_effort_dynamics` 使用 m_a=h*kd+h²*kp，位置模式施加 kp*(qref-q)，位置速度模式额外使用 kd*vref。POSITION 保留 kd 阻尼，但忽略传入 target_qd。effort bound 是 h*limit，即冲量；输出 `lambda_tau_j` 又乘 inv_dt，单位回到 N·m。Euler 用更新后的角速度与 logmap 更新姿态。

独立双精度标量参考直接从角动量与隐式 PD 代数求解：

    v_next = (I*v + h*(kp*(qref-q)+kd*vref_used)) / (I+h*kd+h²*kp)
    q_next = q + h*v_next
    tau = I*(v_next-v)/h

参考不裁剪力矩；参考与实际全程均需离限值至少 4 N·m，否则本组“非饱和”假设判失败。连续时间 PD 仅用于预设合理幅值和门槛，不作为轨迹验收公式。

第一组包含正负镜像阶跃：前两秒 +0.1 rad，后两秒 -0.1 rad，以及相反顺序。要求全瞬态吻合离散参考、每段末误差 <=0.002 rad、速度 <=0.01 rad/s、常目标段能量不增、镜像和稳定性门槛通过。

第二组在两个模式下都输入 qref=0.1 sin(pi*t) 与 target_qd=0.1*pi*cos(pi*t)。A=POSITION_VELOCITY，B=POSITION。这同时验证动态跟踪与目标速度的模式语义。末周期 A/B 跟踪 RMS 分别 <=0.03/0.08 rad，A 相对改善至少30%，且两者各自匹配独立离散参考。

每设置两个独立进程，共8次正式运行；每次全量原始数据、配置、源809文件hash与代码/协议副本留档。所有负结果保留。初始 status 占位不作已求解结果，但完整保存；每一步末 status 均须有限。物理验收与收敛标志分开，严格维持 PADMM p/d/c=1e-7、200次预算，不因预期或实际结果调整门槛。

协议中逐项定义了误差、力矩单位、采样对齐、镜像、稳定性、重复性以及适用边界。该组不推断任意带宽、增益、步长或多关节性能。
