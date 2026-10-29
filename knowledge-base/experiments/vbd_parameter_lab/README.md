# VBD 参数实验表 · Newton 1.7.0

打开 [index.html](index.html)。主体是 **17 行 example–参数效果表**，每行包含 A/B 两次真实 Newton 运行的同步回放、完整时间曲线、量化结果、说明对照和固定版本源码链接。双击 HTML 即可离线查看；初始显示终态，点击行内“回放”或拖动进度条查看过程。

**交互三维版：[index-3d.html](index-3d.html)**（2026-10-28 更新）。顶部可在两版之间切换；表格、曲线和实验数据相同。三维版使用完整 XYZ 轨迹和真实网格拓扑，通过共享 WebGL 渲染器绘制深度遮挡及光照，HTML 内已包含全部绘图代码，不依赖在线资源。

- 拖动画面旋转、滚轮缩放、Shift + 拖动平移；每行 A/B 共用相机，操作任一侧会联动另一侧。
- 可切换透视三维、正视 XZ、俯视 XY、侧视 YZ。双击或“复位”恢复初始三维视角。
- “放大 A/B”打开双画面对照窗口，时间轴与主表同步；Esc 关闭。键盘聚焦画面后，方向键旋转、加减号缩放、R 复位。
- 坐标轴显示观察方向，网格标注真实单位间距。辅助网格不是额外碰撞面；微小粒子/固定点可能放大显示，关节实验中的球是刚体位置示意。原本一维或平面内的运动保持原样，没有添加侧向运动。

三维版无需重跑物理。修改 `viewer-3d.js` / `viewer-3d.css` 后运行 `build_report.py`，再运行 `validate_3d.py`。交互及两版数据一致性检查保存在 [validation-3d.json](validation-3d.json)，页面截图位于 `screenshots-3d/`。

## 固定了什么

- Newton 官方 `v1.7.0`，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。源码位于 `../../sources/newton-v1.7.0`。已核对实际加载的 VBD 文件与快照哈希一致。
- Windows / Python 3.12.14 / Warp 1.18.0 / NumPy 2.5.4，全部使用 **CPU、`particle_enable_tile_solve=False`**。当前 Warp 的 CUDA 版本与本机驱动不匹配，未运行 GPU 测试，也未更改驱动。
- A/B 使用相同几何、质量、初始位姿、物理时长及固定设置，只改变每行声明的参数或参数组；子步实验的单步 dt 随子步数变化。完整设置可在每行展开，场景构造以 `run_lab.py` 为准。
- 这不是 47 个可选构造参数的穷举：其中 **9 个**完成了直接 A/B；其余行测试材料、碰撞管线、时间步等相关输入。HTML 底部逐项标明构造参数覆盖情况。尚未覆盖的四面体材料、复杂网格、历史/容量/耦合选项不从这些最小场景推断。

## 实验清单

| ID | 改变项（A → B） | 场景与主要观测 |
|---|---|---|
| full_surface | `enable_rigid_soft_full_surface_contact`: False → True | 固定粗三角形托球；顶点均不接触球。开启后生成面接触，球被托住，仍有约 0.245 mm penalty 压入。该开关属于 **CollisionPipeline**。 |
| iterations | `iterations`: 1 → 30 | 竖直弹簧链；相同 dt 下与全局线性隐式解比较，末端轨迹 RMSE 约 70.6 → 0.00287 mm。 |
| substeps | 子步数 1 → 8，帧 dt = 1/30 s | 无阻尼振子；细分时间步减少隐式 Euler 数值耗散。 |
| stiffness | 弹簧 k: 50 → 500 N/m | 1 kg 重物静态伸长约 196.2 → 19.62 mm，与 mg/k 相符。 |
| damping | 弹簧 kd: 0 → 8 | 同一振子；比较机械能衰减，区分材料阻尼与数值耗散。 |
| self_contact | `particle_enable_self_contact`: False → True | 上下两片三角网格；开启后上片留在下片上方，关闭后穿过。 |
| self_margin | `particle_self_contact_margin`: 0.005 → 0.04 m | 显式固定 gap = 0.08 m；平衡间距随交互距离变化。 |
| contact_stiffness | 接触 ke: 500 → 50000 | 1 kg 质点落在平面；末段压入约 19.62 → 0.1962 mm。同时设置模型与形状接触材料，避免混合规则改变干预。 |
| friction | 接触 mu: 0.05 → 0.8 | 相同初速度滑动；1 s 水平位移约 754.5 → 63.0 mm。 |
| friction_epsilon | `friction_epsilon`: 0.001 → 0.2 m/s | 相同 mu、小恒力推质点；1 s 蠕滑约 0.108 → 21.1 mm。 |
| dat | `rigid_soft_enable_dat`: False → True | 零半径高速质点冲向薄板，弱 penalty；观察位移截断和穿板。圆点仅用于显示。 |
| dat_relaxation | `dat_conservative_bound_relaxation`: 0.25 → 0.85 | DAT 开启；观察保守系数改变接近接触面的过程。 |
| rigid_mode | `rigid_compliant_alm`: False → True | 同一固定关节，有限 ke；模式改变约束的物理解释，误差较小不自动代表更真实。 |
| joint_stiffness | `rigid_joint_linear_ke`: 200 → 2000 | compliant 模式下的结构刚度；关节平衡误差约 49.05 → 4.905 mm。 |
| membrane | `tri_ke` 与 `tri_ka`: 100 → 10000 | 相同薄膜及载荷；同时缩放两项，观察顶点下移，不能单独归因于某一项。 |
| bending | `edge_ke`: 0.01 → 10 | 两个三角形组成的折页；保持面内材料不变，比较弯曲变形。 |
| stabilization | `rigid_avbd_alpha`: 0 → 0.95 | 无重力、同一初始关节误差；比较纠错速度、过冲和剩余误差。 |

这些值刻意拉开差异以显示机制，**不是通用推荐范围**。每个实验仅一个 A/B 对照对；当前没有进行全范围扫描或独立重复统计。

## 如何与官方指南对照

每行将三类证据分开保留：

1. `expectation`：指南/源码机制所导出的可观测预期；其中 mg/k 等是具有明确假设的物理参考，不冒充官方原文。
2. `observation`：从本次轨迹测得的结果；`comparison_status` 只表示在本最小场景观察到此效应。
3. `source`：Newton 1.7.0 固定 commit 的实际源码路径与行号；`guide_url` 指向在线官方指南。

从用户指定的 [solver 总览](https://newton-physics.github.io/newton/latest/solvers/index.html) 继续引用官方碰撞和调参详细页。`latest` 会变化，因此另保存了 **6 页原始 HTML 快照**，其 URL、读取时间和 SHA-256 见 [official-sources.json](official-sources.json)。快照未改写，页面依赖资源未打包；它们用于证据存档，实验 HTML 本身可以离线使用。

特别注意：在线 latest 现在描述 compliant ALM 默认开启；1.7.0 中省略参数仍解析为 legacy。本轮显式指定模式，除模式对照的 A 外统一使用 compliant。不能用最新文档默认值反推旧版本实际配置。刚柔 full surface、软体自接触、DAT 和 penalty 刚度也分别测试，避免把候选覆盖、位移截断与有限压入当作同一问题。

## 数据与复现

| 文件 | 内容 |
|---|---|
| `run_lab.py` / `cases.json` | 可运行场景及 A/B 干预定义 |
| `data/<id>/A.npz`, `B.npz` | 每一步 time、粒子位置/速度、刚体位姿、接触记录数、指标和步耗时 |
| `data/<id>/A.json`, `B.json` | 配置、拓扑、指标、完整曲线、降采样回放帧、runner SHA-256 |
| `analyze_lab.py` / `plots/` | 分析与可独立使用的 SVG/PNG 科学曲线 |
| `report-data.json` | 17 条结构化实验记录，含出处和条件，可后续导入 RAG/图谱；本轮未改变既有检索索引 |
| `metrics.csv` | 34 行基本数值指标；轨迹参考 RMSE、能量比例等扩展指标见 `report-data.json` |
| `report.template.html` / `build_report.py` | HTML 模板及离线打包脚本 |
| `environment.json` / `run.log` | 运行环境、源码一致性、最终全部运行日志 |
| `PILOT_NOTES.md` | 探索期间的失败与场景修订，避免将筛选过程隐藏为一次成功 |
| `validate_lab.py` / `validation.json` | 数据一致性、有限状态、物理 sanity checks、浏览器交互与布局检查 |
| `screenshots/` | 桌面、手机和筛选页面的实际浏览器截图 |

在 PowerShell 中重跑全部实验（会更新本目录实验结果）：

```powershell
Set-Location 'D:\RAG\Newton knowledge'
.\.venv\Scripts\python.exe -X utf8 experiments\vbd_parameter_lab\run_lab.py
.\.venv\Scripts\python.exe -X utf8 experiments\vbd_parameter_lab\analyze_lab.py
.\.venv\Scripts\python.exe -X utf8 experiments\vbd_parameter_lab\build_report.py
.\.venv\Scripts\python.exe -X utf8 experiments\vbd_parameter_lab\validate_lab.py
```

单独重跑可加 `--case full_surface`（参数可重复）；若修改 runner，正式归档前需重跑全部案例，校验会拒绝混用不同脚本哈希。修改网页排版只需重建 HTML 并重新执行验证，无需重跑物理。文档快照不随常规重建更新；只有主动运行 `snapshot_guides.py` 才刷新证据日期。

独立环境的补充依赖见 [requirements-lab.txt](requirements-lab.txt)，Newton 从本地固定源码安装。浏览器验证通过 Playwright 使用已安装的 Microsoft Edge，新建隔离配置；不访问个人浏览器会话。只检查数据时可加 `validate_lab.py --skip-browser`。

## 读数边界

动画来自保存的真实状态，仅在采样帧间做显示插值；曲线使用完整逐步数据。A/B 的相机和比例相同，数值始终显示终态或指定汇总指标，不随回放时刻变化。迭代实验的参考是**同 dt 的线性 backward Euler 离散解**；子步实验的参考是**连续无阻尼谐振子**，两者的含义不同。

CPU 中位步耗时去掉前 5 步，包含 solver 拥有的碰撞管线调用，不含状态读回和绘图。子步数不同意味着总步数不同，不能只拿“每步更快”评价整段性能。单次运行及这些最小模型不构成 GPU 基准、复杂网格鲁棒性证明或真实材料标定结果。
