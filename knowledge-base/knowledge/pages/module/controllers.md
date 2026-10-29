# 机器人控制器

机器人控制器：DifferentialIK、JointImpedance、OperationalSpace。

## 职责、输入与输出

控制器从关节状态、末端目标与模型/外部运动学产生控制信号。ControllerDifferentialIK 每步 eval_fk / eval_jacobian，按 articulation/joint/site 选择机器人、列与工具点，再执行可选 Jacobian 解法。

## 失败模式与限制

该 model-based DifferentialIK 当前只控制一坐标一 DOF 的关节；每个受控机器人恰好匹配一个 tool site，且 model.requires_grad=True 不受支持。controller 输出需按端口和模型索引写回 Control，不可假定它已经推进物理。

## 模块公开导出索引

- [ControllerBase](#/record/symbol%3Anewton.controllers.ControllerBase)
- [ControllerDifferentialIK](#/record/symbol%3Anewton.controllers.ControllerDifferentialIK)
- [ControllerDifferentialIKModelFree](#/record/symbol%3Anewton.controllers.ControllerDifferentialIKModelFree)
- [ControllerJointImpedance](#/record/symbol%3Anewton.controllers.ControllerJointImpedance)
- [ControllerJointImpedanceModelFree](#/record/symbol%3Anewton.controllers.ControllerJointImpedanceModelFree)
- [ControllerOperationalSpace](#/record/symbol%3Anewton.controllers.ControllerOperationalSpace)
- [ControllerOperationalSpaceModelFree](#/record/symbol%3Anewton.controllers.ControllerOperationalSpaceModelFree)
- [DifferentialIKMethod](#/record/symbol%3Anewton.controllers.DifferentialIKMethod)

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.controllers.ControllerDifferentialIK](#/record/symbol%3Anewton.controllers.ControllerDifferentialIK)
- [newton.controllers.ControllerDifferentialIK.step](#/record/symbol%3Anewton.controllers.ControllerDifferentialIK.step)

## 相关知识

- [module:ik](#/record/module%3Aik)
- [topic:robot-control](#/record/topic%3Arobot-control)
- [recipe:ik-mujoco-contact](#/record/recipe%3Aik-mujoco-contact)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/api/newton_controllers.html)。

## 固定版本原始出处

- [newton/controllers.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/controllers.py#L1)
- [docs/api/newton_controllers.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_controllers.rst#L1)
- [newton/_src/controllers/impl/differential_ik/model_based.py:32](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/controllers/impl/differential_ik/model_based.py#L32)
- [newton/_src/controllers/impl/differential_ik/model_based.py:511](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/controllers/impl/differential_ik/model_based.py#L511)
