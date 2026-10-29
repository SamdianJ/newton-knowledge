# 复现非饱和隐式 PD 跟踪

从 `D:\RAG\Newton knowledge` 运行，使用现有 `experiments/.venv_multisolver/Scripts/python.exe`。固定 Newton 1.7.0 commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。每次进程核验 source-lock 中全部 809 个已安装 Python 文件。CPU 单 world；不要求 CUDA。

正式协议为 `protocol.json`，SHA256 `42406443ed54c3562b9f4af4bca1ec9cf3e1dc22f6027ca097507296032286db`。场景、门槛及采样定义见协议与 `DESIGN.md`。不改协议，不覆盖已有 run。

```powershell
& 'experiments/.venv_multisolver/Scripts/python.exe' 'experiments/kamino_pd_lab/tracking/runner.py' --protocol 'experiments/kamino_pd_lab/tracking/protocol.json' --expected-protocol-sha 42406443ed54c3562b9f4af4bca1ec9cf3e1dc22f6027ca097507296032286db --case kamino_pd_unsaturated_step_reversal --variant A --repeat 1
```

两个 case 为 `kamino_pd_unsaturated_step_reversal`、`kamino_pd_unsaturated_sine_modes`，各 A/B、repeat 1/2。每项单独进程。不要把额外尝试当成可供择优的新重复；现有分析器要求每一冻结协议/runner 指纹恰好两个完整重复。如果另行复现，需要明确建立独立分析 cohort，不能删掉原来的不利结果。

```powershell
& 'experiments/.venv_multisolver/Scripts/python.exe' 'experiments/kamino_pd_lab/tracking/analyze.py'
```

分析器只读取 NPZ、JSON 和代码 hash，不导入 Newton、不运行仿真。参考是独立 float64 隐式离散标量解，生成单独 reference NPZ，不改原始 run 数据。状态时刻 `t` 有 801 帧；命令有 800 行，命令 n 在 t[n] 写入并用于一步，输出状态位于 t[n+1]。比较时刻严格按冻结协议对齐。

原始 `joint_lambdas_tau` 和 `applied_body_wrench` 的角向分量均为 N·m。内部有界约束变量才是冲量，不能在输出力矩上再次除步长。初始 status 可能为构造占位，原样保存，统计只包含实际完成步；物理数组从初态开始全部检查有限。

即使物理验收通过，仍必须独立报告 `converged`、迭代数、r_p/r_d/r_c；不能称 strict tolerance 已通过，不能仅凭残差猜测 float32 floor。私有配置和内部 wrench 读取仅作观测，不是推荐应用 API。

冻结协议使用 `solver.constraints.preconditioning` 表示预条件意图，但实际 API 归属是 `SolverKamino.Config.dynamics.preconditioning`。runner 显式记录该映射并保持值为 true；不修改冻结协议。第一版 runner 因错把该字段放入 stabilization config，在 solver 创建前失败，保留于 runs；root 批准修正后使用新指纹重跑。详情见 `harness-revisions.json`，其记录不是物理反例。
