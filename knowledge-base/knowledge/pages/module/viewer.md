# 查看 记录与导出

ViewerGL / ViewerUSD / ViewerNull 与结果导出。

## 职责、输入与输出

Viewer 接收 model、时间步和 state，支持交互显示、USD 记录或无窗口执行。渲染、接触显示和离线导出共用物理输出，但不改变 solver 的数值结果。

## 失败模式与限制

观测接触力需传入已分配的 observables；帧率与仿真子步区分，结果应同时保存数值指标、配置和原始状态，不仅保存视频。

## 模块公开导出索引

- [Layer](#/record/symbol%3Anewton.viewer.Layer)
- [ViewerBase](#/record/symbol%3Anewton.viewer.ViewerBase)
- [ViewerFile](#/record/symbol%3Anewton.viewer.ViewerFile)
- [ViewerGL](#/record/symbol%3Anewton.viewer.ViewerGL)
- [ViewerNull](#/record/symbol%3Anewton.viewer.ViewerNull)
- [ViewerRTX](#/record/symbol%3Anewton.viewer.ViewerRTX)
- [ViewerRerun](#/record/symbol%3Anewton.viewer.ViewerRerun)
- [ViewerUSD](#/record/symbol%3Anewton.viewer.ViewerUSD)
- [ViewerViser](#/record/symbol%3Anewton.viewer.ViewerViser)

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.viewer.ViewerGL](#/record/symbol%3Anewton.viewer.ViewerGL)
- [newton.viewer.ViewerUSD](#/record/symbol%3Anewton.viewer.ViewerUSD)
- [newton.viewer.ViewerNull](#/record/symbol%3Anewton.viewer.ViewerNull)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/guide/visualization.html)。

## 固定版本原始出处

- [newton/viewer.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/viewer.py#L1)
- [docs/guide/visualization.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/visualization.rst#L1)
- [docs/api/newton_viewer.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_viewer.rst#L1)
- [newton/_src/viewer/viewer_gl.py:198](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/viewer/viewer_gl.py#L198)
- [newton/_src/viewer/viewer_usd.py:72](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/viewer/viewer_usd.py#L72)
- [newton/_src/viewer/viewer_null.py:18](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/viewer/viewer_null.py#L18)
