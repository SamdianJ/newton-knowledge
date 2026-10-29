# Kamino 有界 PD 诊断与跟踪实验

固定 Newton 1.7.0 / CPU / 单 world；协议先冻结，逐设置独立进程重复两次。

7 组配对案例，22 次唯一正式运行；收敛诊断组复用同一严格基线，不重复计数。证据完整性 passed 不等于物理或终止条件全部通过。

| 案例 | 物理门槛 | 结果 |
|---|---|---|
| [有界 PD：200 与 1000 次迭代预算](convergence/kamino_pd_iteration_budget.svg) | passed | 两设置均通过冻结的物理门槛；200→1000 次迭代后，原严格三容差 1e-7 下收敛比例仍为 0%；终止残差及 body/joint 轨迹逐元素相同，r_c 中位数 4.25416e-07 J。预定六个时间步的尾20次有界行 x/y/z 均不再变化，支持持续停滞而非仅200次预算不足。 |
| [有界 PD：仅改变互补停止容差](convergence/kamino_pd_complementarity_gate.svg) | passed | 两设置均通过冻结的物理门槛；仅将互补容差从 1e-7 改为 1e-6 J，配置收敛比例由 0% 到 100%，最多 16 次；按原严格三容差重算仍为 0%。r_c 中位数仍为 4.25639e-07 J。这识别了停止门槛，不是严格收敛问题已经解决。 |
| [有界 PD：仅关闭加速](convergence/kamino_pd_acceleration.svg) | passed | 两设置均通过冻结的物理门槛；仅关闭加速，严格收敛比例仍为 0%，用满200次；r_c 中位数 4.25532e-07 J，最大值 6.52368e-07 J。该对照未消除停滞，不能把失败归结为仅加速分支。 |
| [有界 PD：仅关闭对角预条件](convergence/kamino_pd_preconditioning.svg) | passed | 两设置均通过冻结的物理门槛；仅关闭对角预条件，严格收敛比例仍为 0%，r_c 中位数从 4.25416e-07 升至 0.000460158 J；200次下数值残差更大。物理力矩/轨迹仍通过事前门槛，不能据此推荐关闭预条件或声称收敛修复。 |
| [非饱和隐式PD：正负位置目标与中途反向](tracking/kamino_pd_unsaturated_step_reversal.svg) | passed | 正负目标在2s反向，四次运行最大离散参考角误差 1.62892e-07 rad；物理验收 passed。收敛比例范围 100.000%–100.000%，不能从物理吻合推断逐步求解收敛。 |
| [动态目标与速度参考语义：POSITION_VELOCITY 对 POSITION](tracking/kamino_pd_unsaturated_sine_modes.svg) | passed | 同传位置/速度正弦参考，POSITION_VELOCITY 与 POSITION 末周期 RMS 为 0.0193778/0.0664529 rad，前者改善 70.84%；物理验收 passed。POSITION 按实现忽略速度参考而保留阻尼。收敛比例范围 100.000%–100.000%。 |
| [有界隐式 PD：有限正力限切换、释放与重新饱和](limit_switch/limit-switch.svg) | passed | 已按公开通知契约完成正反力限切换，全部预设物理门槛通过。物理门槛与严格 PADMM 收敛诊断分开记录。 最大力矩参考误差 2.66e-06 N·m；A 每次切换在同一步采用新限值，状态在通知前后不跳变；A/B 收敛标记比例 100%/100%，仅适用于本小驱动场景，不覆盖旧高增益场景。 |

## 原始数据、独立参考与复现

[目录](catalog.json)、[完整结果](report-data.json)、[交互曲线与回放](index.html)。仅从保存数组绘制 body 坐标系，不表示碰撞几何。

- [convergence 的场景与标准](convergence/protocol.json)、[结果](convergence/RESULTS.md)、[复现](convergence/REPRODUCE.md)。
- [tracking 的场景与标准](tracking/protocol.json)、[结果](tracking/RESULTS.md)、[复现](tracking/REPRODUCE.md)。
- [limit_switch 的场景与标准](limit_switch/protocol.json)、[结果](limit_switch/RESULTS.md)、[复现](limit_switch/REPRODUCE.md)。

重新运行本目录 analyze_experiments.py 仅检查并聚合保存数据，不运行物理。新仿真必须创建新 run 目录，不覆盖原结果。

## 适用边界

- **有界 PD：200 与 1000 次迭代预算**：仅固定的CPU单转子饱和场景，物理门槛通过不代表严格收敛通过；未证明普适float32精度下限，没有改求解器实现；每迭代观测同步开销不支持性能排名。
- **有界 PD：仅改变互补停止容差**：仅固定的CPU单转子饱和场景，物理门槛通过不代表严格收敛通过；未证明普适float32精度下限，没有改求解器实现；每迭代观测同步开销不支持性能排名。
- **有界 PD：仅关闭加速**：仅固定的CPU单转子饱和场景，物理门槛通过不代表严格收敛通过；未证明普适float32精度下限，没有改求解器实现；每迭代观测同步开销不支持性能排名。
- **有界 PD：仅关闭对角预条件**：仅固定的CPU单转子饱和场景，物理门槛通过不代表严格收敛通过；未证明普适float32精度下限，没有改求解器实现；每迭代观测同步开销不支持性能排名。
- **非饱和隐式PD：正负位置目标与中途反向**：Newton1.7.0 pinned commit only, CPU singleworld dense PADMM; No contacts/gravity/armature/friction or translation eccentricity; Only bounded implicit PD interior; saturation and runtime limit changes belong to separate experiments; Private state/config reads are observational instrumentation, not supported user API; Single critically damped gain setting and fixed dt, not universal PD tuning; Mirror comparison is symmetry evidence; scalar recurrence supplies independent correctness evidence; Strict solver termination is diagnosed separately; physical pass does not imply every step converged.
- **动态目标与速度参考语义：POSITION_VELOCITY 对 POSITION**：Newton1.7.0 pinned commit only, CPU singleworld dense PADMM; No contacts/gravity/armature/friction or translation eccentricity; Only bounded implicit PD interior; saturation and runtime limit changes belong to separate experiments; Private state/config reads are observational instrumentation, not supported user API; One smooth frequency/amplitude only; no claim of arbitrary-bandwidth tracking; Comparison tests target-mode semantics, not solver backend ranking; Strict solver termination is diagnosed separately; physical pass does not imply every step converged.
- **有界隐式 PD：有限正力限切换、释放与重新饱和**：One finite-positive limit update contract on one CPU Y hinge, no route topology change, no zero/inf/sentinel, no unnotified update, no gain/mode change, contacts, GPU, graph capture, multiworld or general convergence claim. Strict convergence statistics are diagnostics and may fail even if physical gates pass.
