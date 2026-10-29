# 版本迁移与外部集成

迁移时核对字段、布局和外部集成。

逐条检查 migration 文档中的 removed/deprecated 属性、坐标布局、Control targets、sensor/observable API 和 importer 变化。use_coord_layout_targets 应在建模前设置；joint_target_q 可能按坐标而 joint_target_qd 按 DOF。Actuator 的 controller 旧别名迁移到 drive 命名。

MuJoCo 转换、USD schema 与 viewer 输出分别有集成边界。固定旧版本记录与新版本记录独立保存，不能把 latest 文档或其他版本实验默认继承到 Newton 1.7.0。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.Control](#/record/symbol%3Anewton.Control)

## 相关知识

- [topic:environment](#/record/topic%3Aenvironment)
- [module:usd](#/record/module%3Ausd)
- [solver:mujoco](#/record/solver%3Amujoco)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/migration.html)。

## 固定版本原始出处

- [docs/migration.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/migration.rst#L1)
- [docs/guide/compatibility.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/compatibility.rst#L1)
- [docs/concepts/actuators.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/actuators.rst#L1)
- [docs/concepts/usd_parsing.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/usd_parsing.rst#L1)
- [newton/_src/sim/control.py:16](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/control.py#L16)
