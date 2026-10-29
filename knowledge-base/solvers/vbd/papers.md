# 论文阅读卡与实现边界

论文全文、逐页提取文本位于 `sources/papers`，哈希与原始 URL 见 [papers.json](../../manifests/papers.json)。页码为 PDF 页码，从 1 开始；文本提取可能丢失公式布局。已经视觉核对 VBD p.3、AVBD p.6、DAT p.4。

## VBD 2024：为什么能逐顶点解隐式系统

Anka He Chen、Ziheng Liu、Yin Yang、Cem Yuksel；TOG 43(4), Article 116；DOI `10.1145/3658179`。[Vertex Block Descent](https://graphics.cs.utah.edu/research/projects/vbd/vbd-siggraph2024.pdf)；[本地 PDF](../../sources/papers/vbd2024.pdf)。

**问题与核心思路：**全局隐式系统的大规模求解开销高；把未知量分成顶点坐标块，以相邻力元构建 3×3 局部系统。颜色调度保留块 Gauss–Seidel 的信息传播并提供并行性。

**阅读路径：**p.3 Eqs.(2)–(5) 定义全局和局部目标；p.4 Eqs.(7)–(9) 定义局部 Newton 系统；Sec.3.3–3.9 讨论阻尼、接触、摩擦、初始化与并行。实验考察弹性形变、困难初始构形和计算预算。本文报告的稳定现象不能替代目标场景的误差测量。

**与 Newton 对应：**[`solve_elasticity`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2720-L2857) 和 [`SolverVBD._solve_particle_iteration`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L3747-L3982) 是主入口。膜/tet 当前客观阻尼不直接等于论文 Sec.3.3 的简化 Rayleigh；tile 特化、DAT 和 rigid compliant ALM 是额外实现。复现先用单弹簧解析步，再用固定网格静态载荷与动态衰减分别识别材料/阻尼。

**图示建议：**证据页用 p.3 的全局/局部目标；解释图用“一个顶点与相邻三角形/tet”的局部系统，勿把整页论文当架构图。

## AVBD 2025：硬约束与刚度差异

Chris Giles、Elie Diaz、Cem Yuksel；TOG 44(4), Article 90；DOI `10.1145/3731195`。[Augmented Vertex Block Descent](https://graphics.cs.utah.edu/research/projects/avbd/Augmented_VBD-SIGGRAPH25.pdf)；[本地 PDF](../../sources/papers/avbd2025.pdf)。

**问题与核心思路：**单纯提高 penalty 处理硬约束会使收敛困难；引入 dual，交替做局部 primal 更新与约束乘子/罚参数更新。接触需要处理不等式与摩擦边界。

**阅读路径：**p.3 Eq.(8) 约束能量、Eq.(11) dual、Eq.(12) stiffness；p.6 Eq.(19) warm start 与 Algorithm 1 总流程。实验覆盖刚体接触、堆叠与关节等困难约束场景。

**与 Newton 对应：**[`solve_rigid_body`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L6219-L6493)、[`update_duals_joint`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L6497-L7093)、[`_ramp_penalty_k`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L1151-L1158) 对应 legacy 机制。论文示例 alpha=0.95、gamma=0.99，不等于 Newton 全部默认（源码 gamma=0.999、beta=0，compliant 默认 alpha=0）。有限材料 K 与 rho 分离的 compliant ALM 依据当前源码单独建卡，不能偷换成原论文公式。

**图示建议：**证据页 p.6 Algorithm 1；解释图画 primal→dual 的反馈，并把物理 K 和数值 rho 分开。

## DAT 2026：把几何合法性从优化步骤分离

Anka He Chen、Jerry Hsu、Youssef Ayman、Miles Macklin；arXiv `2604.15513v1`，已下载版本为 2026-04-16 的 v1；正式发表 DOI `10.1145/3799902.3811143`。归档的 arXiv 标题使用 Systems，Newton 引用的发表标题使用 System，未声称两版正文逐字相同。[Divide and Truncate: A Penetration and Inversion Free Framework for Coupled Multi-physics Systems](https://arxiv.org/pdf/2604.15513v1)；[本地 PDF](../../sources/papers/dat2026.pdf)。

**问题与核心思路：**不同物理系统在耦合中可能穿插；为接触双方构造互斥区域，限制每次更新。Planar-DAT 按趋近运动分配分隔平面，减少对切向运动的过度限制。

**阅读路径：**Sec.3、p.4 Eqs.(11)–(12) 平面分配、Eqs.(13)–(15) 顶点条件、Eq.(16) 截断；Fig.3 展示相向、远离和切向运动。实验包含多类物理对象耦合，具体保证依赖候选覆盖与合法初态等前提。

**与 Newton 对应：**[`apply_planar_truncation_parallel_by_collision`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2054-L2188)、[`rigid_trajectory_truncation_t`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L7944-L8058)。启用 `rigid_soft_enable_dat` 有 pipeline/半径/外部 solver 限制。本文更广的方法（如 Divide and Project）不因被论文讨论就自动视为此 release 已完整实现。

**图示建议：**证据图为 p.4 Fig.3；解释图叠加候选范围、原始位移和截断后位移，分别展示漏候选与截断。

## 相关文献的收录原则

固定版本 `docs/solvers/vbd.rst` 还引用 OGC（Offset Geometric Contact, DOI `10.1145/3731205`），同时明确 OGC coverage 待 Newton 可用后补充。本样板把它保留为背景线索，不建“1.7.0 已完整支持 OGC”的图关系。后续材料模型论文也应先由具体 kernel 引用或实现差异触发收录，不凭术语相似就建立等价关系。
