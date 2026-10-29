# Native MuJoCo contact results

Frozen checks: 270/270; 8 independent formal runs.

固定 timeconst .02 s，阻尼比 .2 / 1 的实测回弹速度比为 0.583149 / 0.136499；该正值 solref 干预同时改变有效刚度。

gap 0 / .04 m 的首次检测为 0.0905 / 0.0505 s；首次激活均为 0.0905 s。较大 gap 提供 80 个提前检测但无力样本，A/B 轨迹等价。

Eight earlier completed attempts are retained as instrumentation-incomplete because their configuration snapshot preceded the first step and lacked the actual per-step timestep. No physical outcome was used to exclude them. New formal runs record actual .0005 s at every step. CUDA driver warning is retained; actual backend is CPU.

- native CPU frictionless sphere-plane only
- constant solimp and fixed timestep
- positive solref ratio changes effective stiffness as well as damping ratio
- no pair override, mesh, multiccd, runtime margin changes or MuJoCo Warp claim
- MuJoCo 3.15 modern gap semantics only
