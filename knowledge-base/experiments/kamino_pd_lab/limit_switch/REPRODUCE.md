# Reproduce finite effort-limit switching

Protocol SHA256: `14094dfd45befa263e2fe7ac4e06d9437281ba0de1aeb6a97aa83d2d815bcb2e`.

Run from `D:\RAG\Newton knowledge` using `experiments/.venv_multisolver/Scripts/python.exe`. CPU only; the runner checks all 809 installed Newton Python files against the fixed source lock before constructing the scene. No packages or Newton sources are changed.

To rescore the saved immutable runs:

```powershell
.\experiments\.venv_multisolver\Scripts\python.exe experiments/kamino_pd_lab/limit_switch/analyze.py
```

To reproduce simulation in a fresh workspace copy, invoke the following once for each pair `(A,1)`, `(A,2)`, `(B,1)`, `(B,2)` (separate processes):

```powershell
.\experiments\.venv_multisolver\Scripts\python.exe experiments/kamino_pd_lab/limit_switch/runner.py --variant A --repeat 1 --protocol experiments/kamino_pd_lab/limit_switch/protocol.json --expected-protocol-sha 14094dfd45befa263e2fe7ac4e06d9437281ba0de1aeb6a97aa83d2d815bcb2e
```

The runner creates unique timestamped directories and never overwrites a run. The analyzer rejects duplicate current-runner repeat labels rather than silently selecting favorable attempts. Preserve and explicitly classify any harness failure before a new selection is authorized. Original protocol and DESIGN remain immutable.

Each directory contains the exact runner/protocol, source/environment validation, scene and resolved configuration, logs, result hashes, `events.json` and raw `trajectory.npz`. `t`, `body_q`, `body_qd`, `joint_q`, `joint_qd` contain 121 state samples including the initial state. `step_*` fields contain 120 actions/results aligned to the subsequent state sample. `events.json` stores before/after notification limits, impulse bounds, actuation routes and state-change deltas. Internal bound is assembled during the step; after-notify old bound is expected until that assembly. Initial solver status is not solved and is excluded from finite-status diagnostics; all physical arrays must be finite. The runner uses internal diagnostic reads, not internal mutation.

The NumPy reference is in `analyze.py:reference`; it imports no Newton solver. Physical acceptance checks and strict convergence statistics are separate. `analysis.json`, `publication.json`, `RESULTS.md` and `limit-switch.svg` are derived outputs. Timings are not a performance benchmark.
