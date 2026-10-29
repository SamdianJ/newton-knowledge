# Reproduce contact evidence

Run from `D:\RAG\Newton knowledge`. The frozen protocol SHA-256 is `8acf6051cc232801a4414bbb7aea41b429f50c36ee621f408be368cf517ff7dc`. Do not edit it or DESIGN. The runner rejects a mismatch and verifies all 809 installed Newton source files, pinned source references, official source-material hashes, and Newton/MuJoCo versions.

```powershell
foreach ($caseId in @('native_solref_rebound','native_gap_activation')) {
  foreach ($variantId in @('A','B')) {
    foreach ($repeatId in @(1,2)) {
      & 'experiments/.venv_multisolver/Scripts/python.exe' 'experiments/mujoco_joint_contact_lab/contact/runner.py' --case $caseId --variant $variantId --repeat $repeatId --protocol 'experiments/mujoco_joint_contact_lab/contact/protocol.json' --expected-protocol-sha 8acf6051cc232801a4414bbb7aea41b429f50c36ee621f408be368cf517ff7dc
      if ($LASTEXITCODE -ne 0) { throw 'Preserved failed attempt; inspect before proceeding' }
    }
  }
}
```

Each command is an independent process and creates a timestamped directory. Runner, protocol, XML input, environment, installed-source validation, resolved configuration, logs, raw trajectory, result and hashes are retained. Earlier eight complete attempts are explicitly excluded only for a pre-step timestep snapshot ambiguity; `harness-revisions.json` identifies every run and both code hashes. No raw data or thresholds were changed.

To reproduce the published analysis without running physics:

```powershell
& '.venv/Scripts/python.exe' 'experiments/mujoco_joint_contact_lab/contact/analyze.py'
```

The analyzer requires exactly the eight formal archived runs after the named exclusions. Additional reproduction runs need a separate explicit run selection; never silently choose a favorable repeat. It imports NumPy/matplotlib, not Newton or MuJoCo. It recomputes geometric event times, impulse, energy, intervention and repeat gates from raw NPZ. Figures, analysis.json, publication.json and RESULTS.md are derived files.

Contact step arrays describe collision/force evaluation at input t[n], while body/joint output is t[n+1]. Native options captured before the first step have timestep .002; `step_native_timestep` proves every actual step uses .0005. This constructor default is not a changed experiment timestep. CPU is explicit; the preserved CUDA driver warning does not switch the experiment onto a GPU.
