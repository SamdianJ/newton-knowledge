# 版本差异、冲突和缺口

## 固定版本的意义

以正式 tag `v1.7.0` 的完整 commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a` 为基线。正式发布并不改变 SolverVBD 在源码中标记为 experimental 的事实。线上 `latest` 和 GitHub `main` 都不是本知识库默认事实源。

| 容易误读的内容 | 1.7.0 的结论 |
|---|---|
| 省略 rigid_compliant_alm | 实际 False legacy；推荐显式 True 是另一件事 |
| alpha 的 None | 依据模式解析：legacy .95、compliant 0 |
| AVBD 论文 gamma | 论文示例 .99；源码默认 .999 |
| beta | 默认 0；不能照搬论文递增流程认定默认每步都 ramp |
| self-contact margin | 单独给 margin 仍为旧 query radius；新式必须显式给 gap |
| 原 particle conservative relaxation | 弃用别名仍覆盖新的共享 DAT 参数 |
| rigid_contact_stick_* | 弃用且忽略，不应纳入搜索空间 |
| 普通 rigid 与 rigid-soft DAT | AUTO 检测节奏不同，DAT 必须 owned pipeline |
| VBD 2024 阻尼公式 | 当前膜/tet 客观阻尼不是论文简化 Rayleigh 的逐式复刻 |
| OGC | pinned guide 说待可用后补充，不能宣称已完整支持 |
| docs 的调参章节 | 很多是 in-development outline，不是经验证参数表 |

见 [结论记录](claims.json)、[`SolverVBD.__init__`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L353-L1000)、[`SolverVBD._default_collision_frequency_type`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L4690-L4712) 与仓库固定版本 `docs/concepts/simulation_tuning_vbd.rst`。

## 已保留的不确定性

1. 薄膜/弯曲参数的官方单位标签与离散能量缩放，需要材料标定适配；见 [模型输入](model-inputs.md)。
2. 复杂自接触、刚柔 DAT、转动轨迹、密集堆叠与 GPU tile 没有在本样板全面复现。
3. 本次 `.venv` 安装 Warp 1.18.0 的 CUDA 13 构建，本机驱动报告 12.8；CPU 探针正常通过。没有修改驱动，也没有把 GPU 不可用写成算法缺陷。
4. 源码里的测试是“有测试覆盖的证据入口”，不等于这些上游测试本次全部通过。
5. 旧版调参经验尚未导入；经验表仅有模板。历史 1.4 等版本记录应保留原版本和场景，重跑后才推广为 1.7.0 经验。

## 下一批物理实验（proposed / not_run）

以下是尚未执行的验证计划，不因本轮修正文档或缓存通知探针而变成已验证：

| 主要缺口 | 建议的最小场景与量测 | 不能借用的现有证据 |
|---|---|---|
| tet 与客观阻尼 | 固定体网格载荷与自由衰减，比较体积/形变/能量；叠加刚体旋转检查响应一致性 | 单三角膜和折页不验证体积材料或阻尼客观性 |
| rod 与刚体接触 | 简单弯扭 rod、修改静止构形后的恢复力；单刚体摩擦/接触，记录位姿和约束误差 | 缓存刷新探针只检查缓存值；固定关节和粒子摩擦不替代rod/刚体动力学 |
| history / matching / reset | 相同初态的全新solver与运行后reset对照，加入局部world复位，检查状态和接触历史 | 单次A/B不验证复位后的历史一致性 |
| 容量与耦合 | 稠密候选压力和刚柔接口场景，分别记录VT/EE容量溢出、各方轨迹/力及接口所有权 | 简单质点撞板不证明密集覆盖或双向耦合 |
| GPU / tile / graph | 在可用设备上固定场景/预算比较scalar与tile、eager与capture的轨迹误差和开销 | 当前CPU实验不构成GPU、跨设备逐位确定性或性能排名证据 |

每组先冻结干预、误差指标、初态和验收阈值，再保存原始数据并独立复算；不以“每个参数都有一行”替代主要机制覆盖。

## 更新到下一个版本

保留本目录版本基线；新版本建立独立 source manifest。先比较构造签名和默认解析，再比较相关函数、材料约定、缓存生命周期、碰撞调度。重跑本样板探针与检索问题集，补充目标场景回归；只有通过证据审查的关系才获得新 version scope，不能全库替换版本字符串。
