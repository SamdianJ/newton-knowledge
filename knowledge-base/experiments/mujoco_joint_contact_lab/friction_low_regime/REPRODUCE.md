# 重现低摩擦/低速区域

```powershell
& experiments/.venv_multisolver/Scripts/python.exe -B experiments/mujoco_joint_contact_lab/friction_low_regime/runner.py --protocol experiments/mujoco_joint_contact_lab/friction_low_regime/protocol.json --expected-protocol-sha 7136df96193e18891909fbface417912db6bc724121f092cf328be9958dc272a --case mujoco_sliding_friction_mu_low_regime --variant A --repeat 1
```

另一个case为`mujoco_torsional_friction_condim_low_regime`，每case A/B、repeat1/2各自独立进程。唯一新目录保存原始状态、contact与efc观测、程序/协议副本、源和native库hash、配置与日志。现有分析器要求每case恰好4个正式run；新重现数据需独立选择清单，不能静默挑选。

只读重新评分为本目录`analyze.py`，出版为`publish.py`。t/body/joint状态含初态；step观测在公开solver.step之后立即复制，不调用额外mj_forward。ncon和native_nefc分别限定16接触槽和64约束槽，填充0不是活跃力。每步native_timestep=.001已直接记录。

初态独立QP参考及其hash由冻结protocol的design_reference绑定。supplemental-observations.json是在run前登记的早期饱和统计，既不替代也不更改主物理门槛。重复与结果负/正均完整保留。
