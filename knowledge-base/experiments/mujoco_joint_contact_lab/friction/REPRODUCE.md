# 重现

在项目根目录使用已固定环境；每次runner都会创建唯一新目录，不能覆盖已有run。原协议SHA为`50c8d2ac17f5ffd8c698e684712342f3f6712975e2903430f26930d510847f9b`。

```powershell
& experiments/.venv_multisolver/Scripts/python.exe -B experiments/mujoco_joint_contact_lab/friction/runner.py --protocol experiments/mujoco_joint_contact_lab/friction/protocol.json --expected-protocol-sha 50c8d2ac17f5ffd8c698e684712342f3f6712975e2903430f26930d510847f9b --case mujoco_sliding_friction_mu --variant A --repeat 1
```

case另一个取`mujoco_torsional_friction_condim`，variant为A/B，repeat为1/2；共8个独立进程。新增重现数据需要独立目录或明确新的分析选择清单；现有analyze.py有恰好4个合格run/case约束，不会静默挑一组重复数据。

现有只读重新评分与出版：

```powershell
& experiments/.venv_multisolver/Scripts/python.exe -B experiments/mujoco_joint_contact_lab/friction/analyze.py
& experiments/.venv_multisolver/Scripts/python.exe -B experiments/mujoco_joint_contact_lab/friction/publish.py
```

trajectory.npz的t/body_q/body_qd/joint_q/joint_qd包含初态和每个输出；contact/native诊断为每步n→n+1求解样本，直接在solver.step后读取，未重新mj_forward。最多16个接触槽由ncon界定，未用槽全0，efc_address=-1可表示候选未激活；原始contact.dim/friction/geom/dist/frame/6D wrench均保留。每run归档runner/protocol、模型XML、resolved-config、809源expected/actual hash和native二进制hash、日志、结果状态。原8次排除原因和新旧fingerprint在harness-revisions.json；不能删除它们或将物理负结果排除。
