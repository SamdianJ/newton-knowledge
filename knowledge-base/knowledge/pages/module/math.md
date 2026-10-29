# 空间数学与坐标

空间数学与坐标变换索引。

## 职责、输入与输出

空间向量、惯量与变换运算服务于控制、关节和动力学。先确定向量的参考点和参考系，再选择公开 math 导出；签名与实现可从下方源码入口读取。

## 失败模式与限制

本模块首版为 I 级索引，不给全部数学函数另写推导。不要把线性/角度分量顺序或 body-origin twist 与质心 twist 混用。

## 模块公开导出索引

- [boltzmann](#/record/symbol%3Anewton.math.boltzmann)
- [leaky_max](#/record/symbol%3Anewton.math.leaky_max)
- [leaky_min](#/record/symbol%3Anewton.math.leaky_min)
- [normalize_with_norm](#/record/symbol%3Anewton.math.normalize_with_norm)
- [orthonormal_basis](#/record/symbol%3Anewton.math.orthonormal_basis)
- [quat_between_axes](#/record/symbol%3Anewton.math.quat_between_axes)
- [quat_between_vectors_robust](#/record/symbol%3Anewton.math.quat_between_vectors_robust)
- [quat_decompose](#/record/symbol%3Anewton.math.quat_decompose)
- [quat_velocity](#/record/symbol%3Anewton.math.quat_velocity)
- [safe_div](#/record/symbol%3Anewton.math.safe_div)
- [smooth_max](#/record/symbol%3Anewton.math.smooth_max)
- [smooth_min](#/record/symbol%3Anewton.math.smooth_min)
- [transform_twist](#/record/symbol%3Anewton.math.transform_twist)
- [transform_wrench](#/record/symbol%3Anewton.math.transform_wrench)
- [vec_abs](#/record/symbol%3Anewton.math.vec_abs)
- [vec_allclose](#/record/symbol%3Anewton.math.vec_allclose)
- [vec_inside_limits](#/record/symbol%3Anewton.math.vec_inside_limits)
- [vec_leaky_max](#/record/symbol%3Anewton.math.vec_leaky_max)
- [vec_leaky_min](#/record/symbol%3Anewton.math.vec_leaky_min)
- [vec_max](#/record/symbol%3Anewton.math.vec_max)
- [vec_min](#/record/symbol%3Anewton.math.vec_min)
- [velocity_at_point](#/record/symbol%3Anewton.math.velocity_at_point)

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/conventions.html)。

## 固定版本原始出处

- [newton/math.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/math.py#L1)
- [docs/concepts/conventions.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/conventions.rst#L1)
- [docs/api/newton_math.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_math.rst#L1)
