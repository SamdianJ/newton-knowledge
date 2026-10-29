# Native MuJoCo contact mechanisms: preregistration

This laboratory tests the supported public `ModelBuilder.add_mjcf` → Newton model → `SolverMuJoCo(use_mujoco_cpu=True)` path at Newton 1.7.0 / native MuJoCo 3.15.0. It does not mutate `mj_model` or `mj_data` to manufacture a response. Native arrays are read-only instrumentation. The exact input XML is saved and hashed in each run.

## Shared scene and controls

A free sphere of radius 0.05 m, mass 1 kg and diagonal inertia 0.001 kg m² starts at z=0.15 m above a plane z=0, with vertical velocity -1 m/s. Gravity, friction and external force are zero. The sphere has geom priority 1 and the floor priority 0. Both geoms have constant solimp (0.99,0.99,0.001,0.5,2), condim 1. The floor deliberately has solref (0.08,1); the sphere's authored solref must prevail. Native Euler, Newton solver, 100 iterations, tolerance 1e-12, timestep 0.0005 s, 800 steps (0.4 s), update_data_interval=1, native contacts and CPU are fixed. MULTICCD is disabled; the sphere/plane scene contains neither boxes nor meshes, so Newton's margin-zero workaround must be false. All actual option flags and exported geom fields are recorded. Two independent processes per setting, eight formal runs total.

The importer parses authored `solref` and sets its internal raw-mode custom attribute. The experiment never imports or sets internal mode constants. We verify native geom solref, mode diagnostics, and per-contact selected solref; imported ke/kd do not override raw authored solref. Constructor options take priority over model options. `legacy_margin_gap=False` preserves the modern margin/gap meaning. Source references are pinned and hashed in protocol.

## Case 1: positive-format solref damping ratio and rebound

Variant A sphere solref=(0.02,0.2); B=(0.02,1). Both margin and gap are zero. RE FSAFE remains enabled and is recorded. The time constant is 40 timesteps, comfortably above the documented 2h guard; even timeconst*dampratio is at least eight timesteps. This is a damping-ratio intervention at fixed time constant, **not an isolated viscous-damping intervention**: the native positive-format formula is b=2/(d_w*timeconst), k=d/(d_w²*timeconst²*dampratio²), so stiffness changes too.

Independent references are free-flight geometry d(t)=0.1-t before contact, impulse-momentum m(v_end-v_initial)=sum(F_z*h), and kinetic-energy dissipation. These do not reimplement the native solver. A unilateral contact releases when force reaches zero; the bilateral oscillator restitution formula is not an exact oracle. The qualitative underdamped/critically damped distinction motivates broad preregistered thresholds: A outgoing restitution >=0.35, B <=0.25, A-B >=0.20. Critical damping need not produce zero restitution. Outgoing velocity is the final 100-sample mean; require separated surface, positive outgoing speed, and tail velocity peak-to-peak <=1e-4 m/s.

Additional gates: finite state, mass and actual parameter checks; contact normal force >=-1e-10 N; no lateral/angular velocity above 1e-6; maximum kinetic energy <=1.05 times initial; vertical impulse residual <=0.002 N s (allows accumulated float32 Newton/native bridge error); free-flight velocity error <=1e-5 m/s and geometric trajectory error <=2e-5 m. First detection occurs within 2h of analytical t=0.1 s. Native contact distance must agree with pre-step geometry within 2e-5 m. Repeats must agree at position atol 1e-6 m and velocity atol 1e-5 m/s, event times within one timestep.

## Case 2: gap advances detection without advancing force activation

Sphere margin is fixed at 0.01 m. A gap=0, B gap=0.04 m; floor margin/gap=0. Both sphere solref=(0.02,1). **MuJoCo 3.15 detects at distance < margin+gap and activates force at distance < margin.** This is not the obsolete explanation of gap subtracting from the force threshold. Native source `engine_collision_driver.c` calls the collision function with margin+gap, stores includemargin=margin, and excludes contact when dist>=includemargin. At equality the discretization/source comparator controls the exact step; two-timestep event tolerances cover this boundary.

The exact independent free-flight predictions are first detection A=0.09 s, B=0.05 s; first active contact both=0.09 s. Gates: each event within 2h of prediction; detection advances 0.04 s within 2h; active onset difference <=h; B has at least 70 detected inactive samples (`efc_address<0`) before force activation, with |F_z| and contact normal force <=1e-10 N. A/B physical trajectories must remain equal within position 1e-5 m and velocity 1e-4 m/s. All shared finite, geometry, impulse, dissipation, mass, exported-parameter and repeat gates apply. This measures geom margin/gap, not explicit pair overrides, mesh CCD, multiccd, or runtime margin changes.

## Sampling and evidence

States t/body_q/body_qd/joint_q/joint_qd have 801 samples. Each step's native contact arrays are sampled immediately after `mj_step`, whose contact/force calculation used state[n] before integration; step_time is t[n]. No extra `mj_forward` is called. Step arrays include ncon, nefc, contact dist/includemargin/efc_address/solref/solimp/normal force, qfrc_constraint, input geometry and native qpos/qvel after integration. Maximum one sphere-plane contact is asserted. Missing contacts use a validity mask and zero numeric fields, avoiding fabricated NaNs. Native solver iteration/forward-inverse diagnostics are stored where available, but are diagnostics rather than a separate strict-convergence claim.

Every run validates all 809 locked installed Python sources and source references; saves runner/protocol/input-MJCF/config/environment copies and hashes, stdout/stderr warnings, result status, raw NPZ and all partial failed attempts. Failures never change gates. Source/hash or instrumentation faults are reported before any corrected rerun; physical failures remain physical failures. Final analysis separates per-run, intervention and repeat gates, lists actual values, and publishes limits even if criteria fail.

## Versioned official evidence

- https://mujoco.readthedocs.io/en/3.15.0/modeling.html : positive solref, timeconst and damping-ratio scaling, refsafe.
- https://mujoco.readthedocs.io/en/3.15.0/computation/index.html : modern margin/gap detection and inactive contacts.
- https://raw.githubusercontent.com/google-deepmind/mujoco/3.15.0/src/engine/engine_collision_driver.c : priority selection, margin+gap collision call and includemargin exclusion. Exact source and two documentation sources are archived under source-material with SHA-256 in sources.json and protocol.

This is a frictionless single-contact, native CPU, fixed timestep local result. It is not a benchmark of rough/rolling friction, many-body stacking, CCD robustness, MuJoCo Warp, or arbitrary restitution. Newton float32 state round-trips limit exact native-double trajectory equivalence.
