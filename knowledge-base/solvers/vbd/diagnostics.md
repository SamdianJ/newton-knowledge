# 面向任务的诊断方案

下面是源码驱动的待验证计划，不是已经积累的成功经验。执行时把 scene、reference、commit、dt、控制轨迹和完整参数写入 [实验模板](../../experience/experiment-template.json)。

## 薄布穿透/自接触遗漏

编号：`diag:penetration`；关联结论：c:margin, c:capacity, c:dat。

1. 先确认接触类别与 initial intersection；检查候选覆盖、尺度、margin/gap、primitive filters 与容量
2. 固定材料，比较更密检测/更小 dt；观察穿透深度和候选数量，再单独增加迭代

记录指标：max penetration, candidate counts/capacity, dt, iterations。

不能只靠加大 ke 或 iterations。

## 抓取滑落

编号：`diag:slip`；关联结论：c:friction, c:observable, c:attachment。

1. 核对真实夹紧位移/控制、两侧接触法向和接触几何
2. 分开扫描材料 mu、摩擦平滑阈值和法向刚度；保持执行轨迹相同

记录指标：slip displacement, contact wrench, object pose error。

不能以 attachment 或人为位置锁定宣称恢复真实摩擦抓取。

## 材料太软/关节漂移

编号：`diag:soft`；关联结论：c:alm_math, c:legacy, c:cache。

1. 先分离物理材料、结构刚度、drive 参数与数值收敛
2. 固定物理参数增加预算检查解是否收敛，再改变材料并比较静态形变

记录指标：static deflection, joint residual, runtime。

外观变硬不等于已识别真实刚度。

## 抖动或过度阻尼

编号：`diag:oscillation`；关联结论：c:damping, c:friction, c:implicit。

1. 核对阻尼量纲和模型尺度；不要套用旧版 tri_kd 经验
2. 固定物理参数分别扫 dt 和 iterations，再扫材料 damping；记录相位、幅度和静态形变

记录指标：amplitude decay, phase error, kinetic energy。

数值耗散与物理阻尼可能混淆。

## 刚体未受软体反力影响

编号：`diag:coupling`；关联结论：c:external。

1. 确认是否启用 external rigid 单向模式
2. 需要双向时选统一 VBD 或审查专门 coupled solver 数据交换与力反馈

记录指标：two-side momentum change, contact force, coupling schedule。

单个 True 选项不会自动创建反力闭环。

## 复位后突然跳动

编号：`diag:reset`；关联结论：c:reset, c:history。

1. 同时核对模型默认位姿与 episode 位姿
2. reset 后重做 FK/碰撞并清除 pipeline matching 历史，再进入固定步长

记录指标：first-step displacement, history validity。

状态重置不能保留过期接触对应关系。

## 迭代慢/显存或容量不足

编号：`diag:performance`；关联结论：c:capacity, c:tile, c:schedule。

1. 把 JIT 编译排除出稳态计时，记录设备和 Warp 版本
2. 记录 mesh/颜色数、候选数、buffer 与检测频率；比较 tile 路径但保持物理配置

记录指标：steady step ms, memory, contact overflow, color count。

不要靠默默漏检获得速度。

## 刚柔 DAT 构造失败

编号：`diag:dat_config`；关联结论：c:rigid_dat_requires。

1. 检查 solver-owned pipeline、external-rigid 开关与正的最小查询半径
2. 按报错修正配置后运行密集接触用例；不是放宽所有校验

记录指标：constructor error, query radius, contact schedule。

参数通过校验不等于几何鲁棒性已验证。

## 经验晋级条件

一次看起来成功的视频只能算候选经验。至少保存基线、单项干预、固定评价指标、失败条件和完整产物；跨对象或跨网格复测后再扩大适用范围。所有结论都应能回溯到 run_id，而不是只留下“某值比较好”。
