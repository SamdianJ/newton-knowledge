# Kamino · 有界 PD 收敛、跟踪与力限切换

Newton 1.7.0；CPU、单 world。

## 有界 PD 后续诊断与跟踪实测

新增 7 组配对案例、22 次唯一正式运行，7 组达到事前物理门槛。诊断配对复用同一严格基线，运行数不重复计数。实验分别检查观测一致性、配置停止条件、原始严格停止条件和实际运动误差。详见 [PD 收敛、非饱和跟踪与力限切换](pd-experiments.md)。原饱和驱动 0% 收敛记录保持不变；后续实验不能将旧结果追认成收敛。

## 场景与保存结果

| 场景 | 物理门槛 | 实测结果 |
|---|---|---|
| [有界 PD：200 与 1000 次迭代预算](#/record/lab%3Akamino_pd_iteration_budget) | 通过 | 两设置均通过冻结的物理门槛；200→1000 次迭代后，原严格三容差 1e-7 下收敛比例仍为 0%；终止残差及 body/joint 轨迹逐元素相同，r_c 中位数 4.25416e-07 J。预定六个时间步的尾20次有界行 x/y/z 均不再变化，支持持续停滞而非仅200次预算不足。 |
| [有界 PD：仅改变互补停止容差](#/record/lab%3Akamino_pd_complementarity_gate) | 通过 | 两设置均通过冻结的物理门槛；仅将互补容差从 1e-7 改为 1e-6 J，配置收敛比例由 0% 到 100%，最多 16 次；按原严格三容差重算仍为 0%。r_c 中位数仍为 4.25639e-07 J。这识别了停止门槛，不是严格收敛问题已经解决。 |
| [有界 PD：仅关闭加速](#/record/lab%3Akamino_pd_acceleration) | 通过 | 两设置均通过冻结的物理门槛；仅关闭加速，严格收敛比例仍为 0%，用满200次；r_c 中位数 4.25532e-07 J，最大值 6.52368e-07 J。该对照未消除停滞，不能把失败归结为仅加速分支。 |
| [有界 PD：仅关闭对角预条件](#/record/lab%3Akamino_pd_preconditioning) | 通过 | 两设置均通过冻结的物理门槛；仅关闭对角预条件，严格收敛比例仍为 0%，r_c 中位数从 4.25416e-07 升至 0.000460158 J；200次下数值残差更大。物理力矩/轨迹仍通过事前门槛，不能据此推荐关闭预条件或声称收敛修复。 |
| [非饱和隐式PD：正负位置目标与中途反向](#/record/lab%3Akamino_pd_unsaturated_step_reversal) | 通过 | 正负目标在2s反向，四次运行最大离散参考角误差 1.62892e-07 rad；物理验收 passed。收敛比例范围 100.000%–100.000%，不能从物理吻合推断逐步求解收敛。 |
| [动态目标与速度参考语义：POSITION_VELOCITY 对 POSITION](#/record/lab%3Akamino_pd_unsaturated_sine_modes) | 通过 | 同传位置/速度正弦参考，POSITION_VELOCITY 与 POSITION 末周期 RMS 为 0.0193778/0.0664529 rad，前者改善 70.84%；物理验收 passed。POSITION 按实现忽略速度参考而保留阻尼。收敛比例范围 100.000%–100.000%。 |
| [有界隐式 PD：有限正力限切换、释放与重新饱和](#/record/lab%3Akamino_pd_finite_limit_switch) | 通过 | 已按公开通知契约完成正反力限切换，全部预设物理门槛通过。物理门槛与严格 PADMM 收敛诊断分开记录。 最大力矩参考误差 2.66e-06 N·m；A 每次切换在同一步采用新限值，状态在通知前后不跳变；A/B 收敛标记比例 100%/100%，仅适用于本小驱动场景，不覆盖旧高增益场景。 |

## 本轮对 0% 标记的解释

baseline与1000的预定六步尾20次有界x/y/z不变；第0步x距上界26ULP，gap约9.68575e-8乘|z|4.39956生成rc4.26130e-7J，非零对偶增量小于z半ULP2.38419e-7并在float32加法中丢失。支持当前算术与缩放下量化停滞，未证明普适floor；仅放宽互补容差不算严格收敛修复。

旧有效步中只有互补残差未达标；新基线与旧轨迹和有效终止 status 一致，独立重算也匹配源停止规则。因此旧 0% 结果不是初始占位或统计读取错误。当前证据支持这个饱和场景的有限精度停滞；严格要求本身未被修复。互补容差对照的唯一配置改动是停止容差，提前停止产生细小轨迹变化，实际运动仍满足物理门槛，不能称为原严格要求已经通过。

## 观测、容差与求解器行为如何区分

1. 观测检查只读原始数组，排除首次 step 前未定义 status；将保存的内迭代变量独立重算为残差与停止布尔值，且新基线与旧基线比较。CPU `.numpy()` 可能返回共享视图，跨迭代快照必须复制；测试程序修正及被排除尝试单列留档。
2. 严格基线的 primal/dual/complementarity 容差均为 `1e-7`、预算为 200。只将互补容差改为 `1e-6` 的案例仍同时按原 `1e-7` 重新评分；配置停止通过不能当作原精度要求已解决。
3. 增加预算、关闭加速、关闭预条件分别是独立干预。内迭代停滞、ULP 与残差乘积可支持有限精度敏感性的解释；没有同等 float64 求解实现，不证明通用精度下限或所有场景的算法缺陷。

有界行互补残差按 `abs((x-lower)*max(z,0)+(upper-x)*max(-z,0))` 计算，使用未投影 `x` 和更新后的 `z`；预条件缩放在乘积中相消，单位为 J。实际投影力矩达到限值，并不保证该残差通过。停止还要求迭代数大于 1，且三类残差分别低于各自阈值。

## 非饱和跟踪的独立参考

对 COM 位于转轴的单轴转子，惯量 `I=1 kg·m²`，无外力时使用双精度标量递推：

```text
v_next = (I*v + h*(kp*(qref-q) + kd*vref_used)) / (I + h*kd + h*h*kp)
q_next = q + h*v_next
tau = I*(v_next-v)/h
```

POSITION 模式仍含阻尼，但 `vref_used=0`；POSITION_VELOCITY 使用给定速度目标。非饱和参考不裁剪力矩，实际与参考都必须保持冻结的限值裕量。阶跃反向检查全瞬态、终值、镜像与能量；正弦检查指定频率下的跟踪和模式语义。这不是任意带宽、增益或步长的调参结论。

## 力限切换的公开契约

仅测试已有有界 PD 行的有限正值力限修改：更新 `Model.joint_effort_limit` 后，在下一步前调用 `notify_model_changed(JOINT_DOF_FORCE_PROPERTIES)`。新一步组装的冲量界应为 `dt*limit`；通知本身不得跳变姿态或速度。实验分别核对正/负饱和、释放、重新饱和及第一次使用新力限的步。零、无穷、增删约束行或模式/增益变化不在这个合同内。

## 每组适用边界

- **有界 PD：200 与 1000 次迭代预算**：仅固定的CPU单转子饱和场景，物理门槛通过不代表严格收敛通过；未证明普适float32精度下限，没有改求解器实现；每迭代观测同步开销不支持性能排名。
- **有界 PD：仅改变互补停止容差**：仅固定的CPU单转子饱和场景，物理门槛通过不代表严格收敛通过；未证明普适float32精度下限，没有改求解器实现；每迭代观测同步开销不支持性能排名。
- **有界 PD：仅关闭加速**：仅固定的CPU单转子饱和场景，物理门槛通过不代表严格收敛通过；未证明普适float32精度下限，没有改求解器实现；每迭代观测同步开销不支持性能排名。
- **有界 PD：仅关闭对角预条件**：仅固定的CPU单转子饱和场景，物理门槛通过不代表严格收敛通过；未证明普适float32精度下限，没有改求解器实现；每迭代观测同步开销不支持性能排名。
- **非饱和隐式PD：正负位置目标与中途反向**：Newton1.7.0 pinned commit only, CPU singleworld dense PADMM; No contacts/gravity/armature/friction or translation eccentricity; Only bounded implicit PD interior; saturation and runtime limit changes belong to separate experiments; Private state/config reads are observational instrumentation, not supported user API; Single critically damped gain setting and fixed dt, not universal PD tuning; Mirror comparison is symmetry evidence; scalar recurrence supplies independent correctness evidence; Strict solver termination is diagnosed separately; physical pass does not imply every step converged.
- **动态目标与速度参考语义：POSITION_VELOCITY 对 POSITION**：Newton1.7.0 pinned commit only, CPU singleworld dense PADMM; No contacts/gravity/armature/friction or translation eccentricity; Only bounded implicit PD interior; saturation and runtime limit changes belong to separate experiments; Private state/config reads are observational instrumentation, not supported user API; One smooth frequency/amplitude only; no claim of arbitrary-bandwidth tracking; Comparison tests target-mode semantics, not solver backend ranking; Strict solver termination is diagnosed separately; physical pass does not imply every step converged.
- **有界隐式 PD：有限正力限切换、释放与重新饱和**：One finite-positive limit update contract on one CPU Y hinge, no route topology change, no zero/inf/sentinel, no unnotified update, no gain/mode change, contacts, GPU, graph capture, multiworld or general convergence claim. Strict convergence statistics are diagnostics and may fail even if physical gates pass.

## 仍未覆盖

多关节与复杂接触、GPU/graph、多 world、不同幅值/频率/增益/时间步扫描、结构性力限变化、长时间稳定性和论文基准复现。当前结果不直接建议修改 Newton 默认配置。

[原始证据、冻结协议与复现](../../experiments/kamino_pd_lab/README.md)。


## 实体轮廓回放

当前 MuJoCo / Kamino 参数实验已统一为三维实体轮廓展示，可同步旋转、缩放、切换正侧俯视和放大 A/B。原始几何按冻结尺寸绘制；无 shape 的转子以标注的示意转盘显示保存转角，不改变动力学或碰撞模型。归档数据、曲线与验收结果保持原样。历史实验 README 中的坐标轴展示描述对应原版视图；当前展示机制见 [新版回放说明](../../experiments/solid_replay/README.md)。
