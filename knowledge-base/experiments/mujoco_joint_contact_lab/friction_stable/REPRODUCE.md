# 重现提高 impratio 假设对照

```powershell
& experiments/.venv_multisolver/Scripts/python.exe -B experiments/mujoco_joint_contact_lab/friction_stable/runner.py --protocol experiments/mujoco_joint_contact_lab/friction_stable/protocol.json --expected-protocol-sha 0205504e415b5942cfc98a286841597ddd10b9d42c62fc06c0eb347b97865cfb --case mujoco_sliding_friction_mu_stable --variant A --repeat 1
```

第二case为`mujoco_torsional_friction_condim_stable`，每case A/B、repeat1/2独立进程。每次生成唯一目录。新增重复不能直接混入当前分析选择；分析器要求每case恰好4个正式run。

只读评分/出版使用本目录`analyze.py`和`publish.py`。trajectory状态包含初态，每步诊断按n→n+1排列。`native_nefc`限定64槽的有效efc行，`ncon`限定16接触槽；零填充不当作活跃约束。R/KBIP/aref等均在step后读取，没有额外mj_forward。保存完整809源hash、native库hash、程序与协议副本和日志。协议冻结门槛不可因失败改动。
