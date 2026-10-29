# Finite effort-limit switching results

Physical acceptance: **passed**; 113 checks passed, 0 failed. Four independent processes.

已按公开通知契约完成正反力限切换，全部预设物理门槛通过。物理门槛与严格 PADMM 收敛诊断分开记录。 最大力矩参考误差 2.66e-06 N·m；A 每次切换在同一步采用新限值，状态在通知前后不跳变；A/B 收敛标记比例 100%/100%，仅适用于本小驱动场景，不覆盖旧高增益场景。

- A repeat 1: effort max error 2.659218e-06 N m; angle 1.4049535e-07 rad; speed 9.9319481e-07 rad/s; stale-limit steps 0; convergence 100.0%, max iterations 20.
- A repeat 2: effort max error 2.659218e-06 N m; angle 1.4049535e-07 rad; speed 9.9319481e-07 rad/s; stale-limit steps 0; convergence 100.0%, max iterations 20.
- B repeat 1: effort max error 0 N m; angle 7.3927641e-08 rad; speed 2.4284236e-07 rad/s; stale-limit steps 0; convergence 100.0%, max iterations 9.
- B repeat 2: effort max error 0 N m; angle 7.3927641e-08 rad; speed 2.4284236e-07 rad/s; stale-limit steps 0; convergence 100.0%, max iterations 9.

Convergence is reported separately; physical acceptance is not a claim that strict stopping diagnostics pass.

One finite-positive limit update contract on one CPU Y hinge, no route topology change, no zero/inf/sentinel, no unnotified update, no gain/mode change, contacts, GPU, graph capture, multiworld or general convergence claim.
