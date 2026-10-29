# Kamino 机制实验与适用边界

固定 Newton 1.7.0，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。先冻结场景、指标与门槛，再运行；所有原始尝试均保留。

本轮 8 个机制案例、32 个正式独立进程运行。catalog 的 passed 仅表示证据完整性通过；物理失败案例仍显示 failed_criteria，不会因被收录而变成已验证。

| 案例 | 物理验收 | 观察 |
|---|---|---|
| [kamino_fourbar_fk](kamino_fourbar_fk.svg) | passed | 6 个非奇异主动角目标下，两种 FK 初值策略均通过；A/B 最大解析位置误差 5.314e-08/1.893e-07 m。被动关节与闭环锚点重建符合事前门槛。该数据是有序姿态查询，不是动力学跟踪。 |
| [kamino_fourbar_loop_dynamics](kamino_fourbar_loop_dynamics.svg) | failed_criteria | 开链 A/闭环 B 保留关节最大间隙 7.3148/0.1192 mm；虚拟/真实闭环最大间隙 325.4276/0.1186 mm。本步长的完整拓扑对照未通过，保留失败。alpha 和积分器固定，仅改变拓扑；跨组 dt 细化不能覆盖原失败或证明收敛阶。 |
| [kamino_fourbar_loop_dt960](kamino_fourbar_loop_dt960.svg) | failed_criteria | 开链 A/闭环 B 保留关节最大间隙 0.9173/0.0093 mm；虚拟/真实闭环最大间隙 338.4540/0.0093 mm。本步长的完整拓扑对照未通过，保留失败。alpha 和积分器固定，仅改变拓扑；跨组 dt 细化不能覆盖原失败或证明收敛阶。 |
| [kamino_fourbar_loop_dt3840](kamino_fourbar_loop_dt3840.svg) | passed | 开链 A/闭环 B 保留关节最大间隙 0.0658/0.0015 mm；虚拟/真实闭环最大间隙 331.6746/0.0015 mm。本步长的完整拓扑对照通过。alpha 和积分器固定，仅改变拓扑；跨组 dt 细化不能覆盖原失败或证明收敛阶。 |
| [kamino_backend_guided_contact](kamino_backend_guided_contact.svg) | passed | 同一倾斜导轨单接触中，两配置组通过物理门槛；尾段位置最大差 2.684e-07 m。PADMM/DVI 收敛标记比例 22.92%/99.31%，但定义和停止准则不同，不能用来排名物理准确性或性能。 |
| [kamino_drive_effort_paths](kamino_drive_effort_paths.svg) | passed | 显式 effort 与有界隐式 PD 的正反饱和响应均符合 1 N·m 力限；速度解析参考最大误差 A/B 为 2.722e-07/2.356e-07 rad/s。实际路由不同，均通过事前门槛；未测试非饱和跟踪或力限切换。 |
| [kamino_reset_default_replay](kamino_reset_default_replay.svg) | passed | 有非零历史的求解器默认 reset 后，与新求解器同初态重放通过；body/joint 各位置或速度字段的配对最大绝对差至多 0（按各字段单位）。力、加速度、内部时间/步数按协议清除，外部 Control 保持不变。 |
| [kamino_reset_preserve_replay](kamino_reset_preserve_replay.svg) | passed | preserve reset 保持输入 body 姿态/速度并清除历史量后，老求解器与只接收 body 状态的新求解器重放通过；各字段配对最大绝对差至多 0（按各字段单位）。只测试一致状态、单 world 和 internal 暖启动。 |

## 证据与复现

[机器可读目录](catalog.json)、[完整回放/门槛报告](report-data.json)。原始 NPZ 包括每个保存时刻的 body/joint 状态；交互回放仅画 X-Z 投影中的 body 坐标系和轨迹，不伪造模型外观。FK 的横轴是有序目标查询编号，不能解读为物理时间。

```powershell
.\experiments\.venv_multisolver\Scripts\python.exe -B -X utf8 experiments/kamino_mechanism_lab/analyze_experiments.py
```

此聚合命令只重新分析已保存证据，不运行物理。各正式 run 包含冻结 protocol.json 与 runner.py，result.json 保存设置与程序指纹；重复原实验需遵循各子目录 DESIGN/REPRODUCE 及归档程序的 CLI。重跑应创建新 run 目录，不能覆盖已有原始结果。

## 失败与排除账本

原开链 dt=1/240 的关节漂移和后续步长下仍失败的标准保留为物理负结果。另有安装路径假设、源验证/懒分配观测列等 harness 修正；其较早尝试没有计入 32 个正式运行，见 [loop 修正记录](loop_fk/harness-revisions.json) 和 [drive/reset 修正记录](drive_reset/harness-revisions.json)。逐次排除理由在 report-data.json 中，所有旧 run 与哈希继续保存。

## 未覆盖范围

GPU、多 world、masked reset、接触历史匹配、复杂接触/闭环组合、非饱和 PD 跟踪、力限切换、多 DoF 混合驱动、奇异/多分支 FK 和长期稳定性仍未验证。PADMM/DVI 的残差同名但定义不同，不用收敛标记或迭代次数排名性能/准确性。关联参数表示 measures_behavior_of，固定的 alpha/integrator 等不计为新增单参数 A/B 覆盖。
