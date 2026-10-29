# Kamino 优先机制实验：结果、复核与剩余缺口

本轮由 3 个实验 agent 分别负责闭环/FK、PADMM/DVI、驱动/reset，主 agent 负责协议冻结、发布集成和旧功能回归。已经实际运行 **8 组案例、32 次正式独立进程实验**：6 组通过事前物理门槛，2 组未通过并保留负结果。所有设置均重复两次；15 次较早的测试程序失败或观测不完整尝试单列保留，没有计入正式运行。

最终知识库 build：`37213b4b24552935be27464a`，101 篇文档、2714 条记录。固定 Newton 1.7.0，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。结论限于本机 CPU、单 world 和已保存的场景；本轮没有修改 Newton 实现。

入口：[知识库实验页](http://127.0.0.1:18448/#/solvers/kamino/experiments)、[生成后的结果与边界](../../solvers/kamino/experiments.md)、[原始证据与复现](../../experiments/kamino_mechanism_lab/README.md)、[机器可读交付账本](resolution.json)。

## 先定义，再执行

最初 6 组、24 次正式运行的场景、指标、验收门槛于 2026-10-29 05:09:35 UTC 冻结，见 [freeze.json](../../planning/kamino-mechanisms/freeze.json)。发现粗时间步开链对照的关节漂移超限后，另于 05:15:54 UTC 冻结 2 组、8 次步长细化运行，见 [refinement-freeze.json](../../planning/kamino-mechanisms/refinement-freeze.json)。细化保持同一场景、初态、外力、求解器预算、0.5 s 总时长及全部物理门槛，只改变时间步；没有用细步长成功替换粗步长失败，也没有拟合或宣称收敛阶。

| 场景 | 主要事前门槛 | 独立参考或对照 |
|---|---|---|
| 112 mm 四杆闭环 FK，6 个主动角目标 | 位置/闭环锚点误差 ≤10 µm，主动/被动角及转角误差 ≤0.1 mrad，reset 全部成功 | 平行四边形解析几何；比较 `fk.reset_state` 两种初始猜测策略，二者均写入状态 |
| 同四杆的开链/闭环动力学 | 两侧保留关节间隙 ≤0.5 mm；闭环间隙 ≤0.5 mm；非平凡角运动 ≥0.01 rad；开链虚拟闭合边 ≥1 mm 且至少为闭环的 5 倍 | 相同 body/树关节，只移除或保留闭合 hinge；从 body pose 和 joint frame 独立重建锚点 |
| 1 kg 球、倾斜导轨与地面接触，PADMM/DVI | 自由段位置误差 ≤4 mm、速度误差 ≤5 mm/s；离轴误差 ≤0.2 mm；穿透 ≤15 mm；尾段位置/速度、能量等分别设门槛 | 自由段解析加速度与 Euler 截断界；接触尾段对照。比较默认与强制条件形成的配置组 |
| 单 revolute 转子，显式 effort/有界隐式 PD | 正反实际力矩误差 ≤0.002 N·m，绝对力矩 ≤1.001 N·m；速度误差 ≤0.002 rad/s、Euler 角位移误差 ≤0.001 rad | 有效惯量 1.25 kg·m²、±1 N·m 的独立积分参考；同时验证实际驱动路由 |
| default/preserve reset，各自 fresh/aged 对照 | 先证明历史非零；reset 状态门槛 1e-6 或 1e-7；重放位置/速度 atol 1e-5/1e-4、rtol 1e-5；外部 Control 保持一致 | 先运行 60 步形成状态与乘子，再与新建求解器在相同 body 初态下重放 |

完整标准及阈值理由见各 [FK/闭环协议](../../experiments/kamino_mechanism_lab/loop_fk/protocol.json)、[后端协议](../../experiments/kamino_mechanism_lab/backends/protocol.json)、[驱动/reset 协议](../../experiments/kamino_mechanism_lab/drive_reset/protocol.json)。求解器终止状态在协议中是诊断项，与物理门槛分别报告。

## 实际结果

| 案例 | 关键结果 | 物理验收 |
|---|---|---|
| `kamino_fourbar_fk` | 最大解析位置误差 1.893e-7 m；最大被动角误差约 2.623e-7 rad；两种初始猜测均成功 | 通过 |
| `kamino_fourbar_loop_dynamics`，dt=1/240 s | 开链/闭环保留关节最大间隙 7.3148/0.1192 mm | **未通过**：开链超过 0.5 mm |
| `kamino_fourbar_loop_dt960`，dt=1/960 s | 对应间隙 0.9173/0.0093 mm | **未通过**：开链仍超限 |
| `kamino_fourbar_loop_dt3840`，dt=1/3840 s | 对应间隙 0.0658/0.0015 mm；开链虚拟闭合间隙约 331.675 mm | 通过原门槛 |
| `kamino_backend_guided_contact` | 两后端通过各自物理门槛；尾段位置最大差 2.684e-7 m | 通过 |
| `kamino_drive_effort_paths` | 正反实际力矩均为 ±1 N·m；最大速度参考误差约 2.73e-7 rad/s | 通过 |
| `kamino_reset_default_replay` | 有历史求解器恢复默认初态后，与 fresh 的重放状态数组差为零 | 通过 |
| `kamino_reset_preserve_replay` | 保留一致 body 状态、清除历史后，与 fresh 重放状态数组差为零 | 通过 |

有界隐式 PD 的收敛标记比例为 **0%**，达到 **200 次迭代**；在冻结的严格 1e-7 容差下，末互补残差约 4.4–4.7e-7 J。两种 reset 使用同一有界驱动，其运行也存在相同诊断边界。通过的是实际力矩、运动参考和生命周期门槛，不能写成求解器全部收敛。显式驱动的标记为 100%。

PADMM/DVI 的收敛标记比例分别为 22.92%/99.31%。两者残差定义和停止准则不同，配置还涉及 `sparse_jacobian`、预条件、线性求解器选择；这些比例不能用于准确性或性能排名。本实验不是只改变一个 backend 字段的单因素扫描。

两种 reset 均验证了外部 Control 保持不变，重放前由调用方显式重新下发。`preserve` 输入来自已运行的一致状态，不证明能修复任意不一致姿态。FK 是有序姿态查询，不是动态目标跟踪。

## 生成源与发布变化

- 聚合源 [analyze_experiments.py](../../experiments/kamino_mechanism_lab/analyze_experiments.py) 生成目录、轨迹报告及 8 组曲线；记录 455 项证据文件哈希。原始 run 保存协议、程序、环境、配置与 NPZ。
- [kamino_experiment_content.py](../../scripts/kamino_experiment_content.py) 与 [extend_solvers.py](../../scripts/extend_solvers.py) 从实测目录生成结果正文、implementation/version-notes 摘要及两项受限论文机制映射。论文映射保持 `partial_local_evidence`，不标成论文基准已复现。
- [build_platform.py](../../scripts/build_platform.py) 发布 8 条新实验和两篇结果文档，校验证据哈希。两条物理失败记录的 `experiment_validated` 保持 false；固定字段的关联不冒充单参数干预。
- [knowledge_store.py](../../scripts/knowledge_store.py) 支持新实验目录、归档 runner 与曲线读取。明确比较多个 solver 时保留各 owner 的最佳候选；耦合类问题仍按原词法相关性排序。
- 网站增加真实保存轨迹的 X-Z 回放、曲线、门槛及原始数据链接；区分 FK 目标序号和物理时间。修正参数页实验按钮的 solver 归属。回放展示 body 坐标系与轨迹，不把示意图当作碰撞几何。

## 复核与兼容性

新实验聚合通过 843 项证据检查；驱动/reset 另经 147 项独立复核，发布正文经 10 项独立检查。复核发现的 PD 诊断遗漏、默认选择与强制条件混称已在生成源修复。见 [review-drive-reset.json](review-drive-reset.json)、[review-loop-fk.json](review-loop-fk.json)、[review-publication.json](review-publication.json)。

| 最终发布检查 | 结果 |
|---|---|
| 新实验真实 stdio MCP | 375/375，57 次调用 |
| 新实验来源、HTTP、桌面/移动端 UI | 308/308，含全部 8 组回放、负结果及参数入口 |
| 旧 MCP P2 / P3 / P4 / P5 | 1574 / 349 / 111 / 82 项全部通过 |
| 旧页面综合 P2 / P3 / P4 | 全部通过，精确数量见交付账本 |
| 快照维护 P5 | 184/184 |
| 原 VBD 检索及额外 solver 结构 | 24/24 查询；291/291 结构检查 |
| 全量重建幂等 | 同 build ID，reused=true |

检查数不是独立实验数或知识正确率。P2 原冻结集 Recall@5 为 0.7196969697，与基线一致，所有必需证据完成读取；P3 Recall@5 为 1.0。没有修改冻结问题或放宽物理门槛。新数据暴露的旧测试假设已调整：实验视窗按目录定位，Kamino 总数为 2 旧+8 新，MCP 关系按较小页面及原 cursor 继续完整读取。早期验收失败和修正保留在日志/历史报告中。

原 323 个历史实验文件、固定源代码锁、旧 build 均检查未变。初始未求解 status 的未定义占位只在原始记录中保留，未被当成有效收敛样本；所有物理数组及后续有效 status 按协议验证。

## 剩余实验缺口

本轮补上了 KAM-03 中四个优先机制的局部实测证据，但不将整个实验充分性问题标记为已完全关闭。

| 方向 | 仍需验证 |
|---|---|
| 闭环/FK | 奇异位形、多分支选择、不可达目标和失败恢复；多闭环/混合关节；闭环与接触组合；更长时间的漂移及约束稳定化干预 |
| PADMM/DVI | 多接触、摩擦滑移、关节限位、复杂闭环；分别消融稀疏 Jacobian/动态、预条件与线性求解器；停止准则和残差参考，不能只比较收敛率 |
| 驱动 | 严格容差下未收敛的原因及影响；非饱和跟踪、力限切换、多 DoF/混合驱动、负载变化；增益和力限独立扫描 |
| reset | 多 world、mask/flags/callback 部分 reset；接触历史匹配、FK/碰撞缓存；不一致 preserve 输入；不同 warmstart 模式及模型变更通知 |
| 后端与论文 | Moreau、GPU/graph、长期稳定性与跨硬件重复性；公式级参考和论文基准复现 |
| 其他知识库领域 | 资产 URDF/MJCF/USD fixture 矩阵、碰撞容量/过滤/复杂自接触、VBD tet/rod/阻尼及 MuJoCo 容差/材料/控制同步等，仍沿用上一轮缺口清单，本轮未新增运行 |

原完整审核和修复报告保留不变；本报告是本轮实验增量的结果，不覆盖或改写历史结论。
