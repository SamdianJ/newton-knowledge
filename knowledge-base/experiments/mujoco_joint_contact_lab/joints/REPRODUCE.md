# 复现

工作目录 `D:\RAG\Newton knowledge`，环境 `experiments/.venv_multisolver`。固定Newton1.7.0 commit7e75、native MuJoCo3.15.0、CPU。每次进程核验809个已安装Newton Python源码hash。

```powershell
& 'experiments/.venv_multisolver/Scripts/python.exe' 'experiments/mujoco_joint_contact_lab/joints/runner.py' --protocol 'experiments/mujoco_joint_contact_lab/joints/protocol.json' --expected-protocol-sha 36ffb87df53457e8cefd36324a8d95fdf4bd49d915d495a28639b6372f90b77c --case mujoco_joint_passive_damping --variant A --repeat 1
```

其他case为 `mujoco_joint_armature_inertia`、`mujoco_joint_pd_damping`、`mujoco_joint_upper_limit`。每个case的A/B各repeat1/2，独立进程。每次新目录，保留失败，不覆盖或择优。现有分析器要求同一冻结协议与runner指纹每设置恰好两个完整重复；另行复现应明确另建cohort，不能删除原结果让新结果替代。

```powershell
& 'experiments/.venv_multisolver/Scripts/python.exe' 'experiments/mujoco_joint_contact_lab/joints/analyze.py'
& 'experiments/.venv_multisolver/Scripts/python.exe' 'experiments/mujoco_joint_contact_lab/joints/publish.py'
```

分析器只使用NumPy与保存的原始数组，不导入Newton或MuJoCo。`t`为1001状态时刻；`force_t`为1000个本步积分前力计算时刻。Euler的force[n]和state[n]对齐，native qpos/qvel在mj_step返回后已经是state[n+1]。`update_data_interval=0`使native MuJoCo持有积分状态；本实验没有中途编辑State。

协议称native qM表示广义质量矩阵的语义，安装的MuJoCo3.15使用`MjData.M`和`mj_fullM(model,data,dst)`；仅此观测接口映射经root批准修正，动力学配置不变。最初旧字段qM访问失败发生在任何step之前，保留于runs与harness-revisions.json；不能把该失败当物理反例。

正式runner SHA256 `a1d1bc3bdcedc290549f9b2a503bbb55299498ef5f1884378a818182b1f65c43`。所有run保存原始轨迹、actual native字段、source/environment、runner/protocol副本和文件hash。场景和阈值以冻结protocol为准。
