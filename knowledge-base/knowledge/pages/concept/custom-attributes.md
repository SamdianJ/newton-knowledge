# 自定义属性与注册

frequency、assignment、namespace 与注册。

## 机制与数据流

add_custom_attribute 在构建前声明 dtype、frequency、assignment、default、namespace 等，决定数组分配到 Model、State、Control 或 Contacts。solver 注册的字段需在构建/finalize 前准备好。

## 诊断与边界

None 占位声明不是物理默认。namespace 与 frequency 不是任意键值标签：world 合并、引用重映射和接触容量均影响分配。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/custom_attributes.html)。

## 固定版本原始出处

- [docs/concepts/custom_attributes.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/custom_attributes.rst#L1)
