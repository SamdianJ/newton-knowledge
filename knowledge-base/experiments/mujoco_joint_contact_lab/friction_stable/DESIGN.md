# 稳定承载摩擦对照：新协议待冻结

原friction两个正式case均保持负结果。原始首步滑动A/B法向力50.84/151.74N远高于mg9.81N，产生正vz与离地；sphere condim4首步13.35N后也出现正distance和efc_address=-1，非活跃步qacc_z=-g。ncon保留来自默认gap候选，不证明承载。

新协议不调整阈值、不筛选预跑。只将跨协议公共impratio从1改为1000：源码R_t=R_n/impratio、正则化锥mu=mu_slide/sqrt(impratio)提供减弱法向/切向正则耦合的机制假设。几何、初态、solref/solimp、dt、时长、单因素A/B差异、所有原物理验收门槛不变。各A/B重复2次，共8正式；新ID加_stable，但ID只是场景名称，实际通过与否仍由冻结门槛决定。

额外只读记录efc R/KBIP/aref/force/vel/b/J/pos/margin及contact.mu、native_timestep，完整nefc长度和零填充mask留档，用于核验原生优化器机制。禁止仅从高impratio后改善宣称solver修复；此值只是本场景实验选择，不是通用推荐。正负结果一并报告。
