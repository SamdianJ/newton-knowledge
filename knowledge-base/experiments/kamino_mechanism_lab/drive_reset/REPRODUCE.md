# 驱动与 reset 实验复现

使用固定 Newton 1.7.0 和 `experiments/.venv_multisolver`。运行器必须接收已冻结协议及其 SHA256；每次创建新目录，不覆盖旧数据。

```powershell
Set-Location 'D:\RAG\Newton knowledge'
$protocol = 'experiments/kamino_mechanism_lab/drive_reset/protocol.json'
$expected = '9b4c235d475b1cb915714acebd078a4d0d5155736e8a300b0da52d02fa6dff74'
foreach ($case in @('kamino_drive_effort_paths','kamino_reset_default_replay','kamino_reset_preserve_replay')) {
  foreach ($variant in @('A','B')) {
    foreach ($repeat in @(1,2)) {
      & .\experiments\.venv_multisolver\Scripts\python.exe -B -X utf8 experiments/kamino_mechanism_lab/drive_reset/runner.py --case $case --variant $variant --repeat $repeat --protocol $protocol --expected-protocol-sha $expected
    }
  }
}
```

当前分析器要求每变体在当前 runner 哈希下恰有 repeat=1 和 repeat=2 两个完整 run；再次复现产生更多同哈希 run 时应明确新 cohort 选择，不能静默挑选最好结果。`result.json` 的 completed 只表示执行成功；`analysis.json` 才记录冻结标准的通过情况。

原始数据：每个 run 内包含 trajectory.npz、完整 resolved-config、scene、环境、809 个已安装源码文件的核验摘要、runner/协议副本、日志与各文件 SHA256。Reset 场景额外保存 warmup（适用时）和 reset-snapshots。NumPy 分析器不导入 Newton，以独立的惯量/脉冲积分公式和原始数组比较计算指标。

两个 harness 修正均未改变场景或门槛，详见 [harness-revisions.json](harness-revisions.json)：先修正 installed source 路径核验并全量检查 Python 文件，再修正 State 首次 step 时延迟创建的 effort-multiplier 采样列。原失败和不完整仪表 run 保留，不能计作物理失败或有效主运行。

`applied_body_wrench`、`dof_act_paths` 和内部时间是私有诊断读取。它们只用于固定 commit 下的机制验证，不作为通用应用 API 使用建议。
