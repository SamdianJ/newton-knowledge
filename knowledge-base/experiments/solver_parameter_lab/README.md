# MuJoCo / Kamino 参数实验与复现

Newton **1.7.0**，固定 commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。这些是本机实测，不是示意动画。

网站中的每个 solver 有独立实验室，也可以打开 [三维 A/B 总表](http://127.0.0.1:18448/files/experiments/solver_parameter_lab/index.html)。每行使用相同初始状态、时间轴和相机；位姿来自 NPZ，方块按 XYZW 四元数旋转。几何计算和显示都将四元数归一化，保留原始数组。

| Solver | 参数组 A / B | 场景 | 主要量测 |
|---|---|---|---|
| MuJoCo native CPU | iterations = 5 / 50 | 五方块堆叠 | 接触瞬态地面穿透、能量、最高表面 |
| MuJoCo native CPU | 两接触形状 ke = 2000 / 200000；kd = 2√ke | 1 kg 球下落 | 穿透与沉降，实际 geom_solref |
| Kamino PADMM CPU | max_iterations = 20 / 60 | 五方块堆叠 | r_p / r_d / r_c、收敛比例、穿透 |
| Kamino PADMM CPU | constraints.gamma = 0 / 0.2 | 球初始重叠 15 mm | 重叠恢复、速度、约束收敛 |

协议 [1.2](../../planning/p4/protocol.json) 在正式重复运行前冻结。每个设置用独立进程运行两次，共 **8 个主运行 + 8 个复现运行**。位姿绝对容差 1e-5、速度 1e-4、相对容差 1e-5；计时不纳入轨迹复现判定。每个 run 文件夹保存程序副本、协议、场景、配置、依赖、日志、结果和 NPZ 及哈希。`result.json` 的 completed 仅表示运行结束；是否纳入有效 A/B 由协议哈希、原始数组复核、响应边界与复现共同判断。

初版压力测试中 MuJoCo 1 次迭代失稳，Kamino 2 次预算产生严重接触误差；保留对应原始 run 与 [初版协议](../../planning/p4/protocol-1.1-initial-stress.json)，**不计入有效 A/B**。5/20 次的探索探针带 `probe_completed_not_ab` 标记，也不计。分析器只选当前协议下通过门槛且有独立复现的完整运行。

`analyze_experiments.py` 使用独立的八顶点几何算法复算方块地面穿透，以四元数向量运算复算转动能；与运行器的矩阵公式比较。Matplotlib 输出完整时间曲线，JSON 提供同步回放。配置 diff 验证只有预声明的干预项改变，且改变到达实际后端配置。

复现命令（PowerShell）：

```powershell
$kb = 'D:\RAG\Newton knowledge'
uv venv "$kb\experiments\.venv_multisolver" --python 3.12
uv pip install --python "$kb\experiments\.venv_multisolver\Scripts\python.exe" -r "$kb\experiments\solver_parameter_lab\requirements.lock.txt"
# 锁中的 Newton 本地来源应指向本机固定快照；安装后检查 source_verification。
foreach ($repeat in @(1,2)) {
  foreach ($case in @('mujoco_iterations_stack','mujoco_contact_response','kamino_padmm_budget','kamino_contact_stabilization')) {
    foreach ($variant in @('A','B')) {
      & "$kb\experiments\.venv_multisolver\Scripts\python.exe" "$kb\experiments\solver_parameter_lab\run_experiments.py" --case $case --variant $variant
    }
  }
}
& "$kb\experiments\.venv_multisolver\Scripts\python.exe" "$kb\experiments\solver_parameter_lab\analyze_experiments.py"
```

依赖补充：当前 Warp 1.18.0 在本机仅 CPU 可用，CUDA 驱动不满足该构建要求。本实验没有改驱动，也没有运行 GPU 路径。Kamino 显式启用内部碰撞，关闭 graph conditionals；native MuJoCo 使用内部碰撞。没有在 native MuJoCo CPU 读取 CONTACT_F。

观察只解释保存的场景与参数组。ke/kd 为共同干预，`kd=2√ke` 是这里采用的 legacy 数值比例，不是普适临界阻尼规律；positive solref 的 time constant 受 refsafe 的 `2dt` 下限约束。Kamino γ 属于接触 Baumgarte；α 属于双边关节、β 属于关节限位。速度约束收敛不保证位置重叠消退。耗时仅为单进程单场景观测，不用于不同 solver 的性能排名。
