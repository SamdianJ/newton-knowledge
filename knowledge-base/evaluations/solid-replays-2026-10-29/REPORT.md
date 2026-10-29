# MuJoCo / Kamino 实体轮廓回放交付

已将全部 **31组实验、62个A/B视图**统一为有物体轮廓的三维回放：MuJoCo14组、Kamino17组。当前构建`8a7a02fd821cc6b9eebd093f`。

- [MuJoCo实验室](http://127.0.0.1:18448/#/solvers/mujoco/experiments)
- [Kamino实验室](http://127.0.0.1:18448/#/solvers/kamino/experiments)
- [展示机制、来源与尺寸边界](../../experiments/solid_replay/README.md)

## 展示改动

采用VBD的共享WebGL方式绘制带填充和边线的方块、球体、四杆连杆，并提供同步旋转、缩放、平移、正侧俯视、初始/全轨迹范围，以及放大A/B。球面色带帮助观察自旋。两侧保持同相机和同尺度，时间滑杆直接选择保存帧；FK目标序列仍标目标序号，不伪装成连续物理仿真。

有真实shape的场景使用归档尺寸、局部变换和保存的body_q。没有shape的转子使用明确标注的转盘/指针示意轮廓；偏心臂采用已记录COM距离，示意宽度和盘半径不参与动力学。四杆box原先关闭碰撞的设置也保留在说明中。

原有曲线、原始数据下载、六个物理负结果以及Kamino PD的配置/严格收敛百分比全部保留，特别是原严格标准0%没有被物理通过标记掩盖。

## 生成与验证

几何生成源为`scripts/build_solid_replays.py`和`scripts/replay_geometry_kamino.py`；统一渲染位于`experiments/solid_replay/`。四个旧实验入口加载共享渲染器，原始report-data/catalog/NPZ/protocol不改。`scripts/rebuild.py`会重新生成几何来源清单；相关生成源、渲染资源和geometry.json纳入构建指纹。两次完整重建得到相同build ID与几何hash。

- 新增专项：**1799/1799通过**。独立核对全部31案例的初/中/末保存位姿、局部尺寸/四元数变换、mesh边界、实体像素、多视角、缩放、播放、移动端和负结果标记，零JS错误。
- Kamino几何独立复核：39/39通过，覆盖四杆锚点、偏心COM及Y轴转子。
- 既有回归：P4 MCP111、P5 MCP82、P5维护184、P4页面58项全部通过。
- 原1863个实验文件中，只有四个已授权HTML入口变更，其余**1859个文件逐项hash不变**，包括VBD全部文件与所有原始实验/分析数据。没有重新运行物理实验。

[完整专项验证](validation.json) · [机器可读交付清单](resolution.json) · [截图](screenshots/)
