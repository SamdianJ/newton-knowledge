# Sites 与参考坐标

Site 是附着参考坐标，不是碰撞形状。

## 机制与数据流

Site 为末端控制、IMU 和其他传感器提供相对刚体的参考姿态；通过 label 匹配到机器人上的工具点或量测点。

## 诊断与边界

Site 位置与碰撞几何、COM 位置各有语义。控制器选 tool_sites 时每个受控机器人需匹配恰好一个。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.ModelBuilder.add_site](#/record/symbol%3Anewton.ModelBuilder.add_site)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/sites.html)。

## 固定版本原始出处

- [docs/concepts/sites.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/sites.rst#L1)
- [newton/_src/sim/builder.py:8655](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L8655)
