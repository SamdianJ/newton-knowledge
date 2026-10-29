# 复现

从知识库根目录运行。固定Newton 1.7.0安装树逐文件核验，不混装版本。原始数据不覆盖。

```powershell
experiments/.venv_multisolver/Scripts/python.exe -B -X utf8 experiments/kamino_pd_lab/convergence/runner.py --variant baseline --repeat 1 --protocol experiments/kamino_pd_lab/convergence/protocol.json --expected-protocol-sha 79614e42dc3f2f954ce04fa54b03e828265f03ddc45e35ed0741ea70aa3da50a
```

variant可为 `baseline`、`budget1000`、`compl1e6`、`noaccel`、`noprecondition`，repeat为1或2。每次自动创建新的UTC唯一run目录。若再次重跑，分析器会因超过10个唯一正式记录拒绝将新数据静默替代旧数据；应在独立副本中复现或明确登记新一轮分析集合。

只重新分析已有数据及生成配对发布内容：

```powershell
experiments/.venv_multisolver/Scripts/python.exe -B -X utf8 experiments/kamino_pd_lab/convergence/analyze.py
experiments/.venv_multisolver/Scripts/python.exe -B -X utf8 experiments/kamino_pd_lab/convergence/build_publication.py
```

原始 `trajectory.npz` 保存t/time及全部物理状态，初始status有defined mask；`iterations.npz` 保存每个有效内迭代的前后变量和终态。`derived/*-residuals.npz` 是独立分析派生数据，不覆盖原始数组。

首个run因CPU NumPy共享结构化标量视图导致前值断言失败，未形成完整物理轨迹，保留为harness失败。修复为`.copy()`后，baseline r1记录了3006列预分配容量；后续仅记录6个活跃行并保存原容量，跨版本比较先按dim/vio归一，不以相同程序hash推定等价。归档runner各自hash验证，详情见`harness-revisions.json`。这两处修正不改变协议、物理设置或原计算调用。
