# Finite effort-limit switching: preregistration draft

No Newton construction or simulation has been performed for this design. The only design calculation is an independent double-precision scalar recurrence.

## Public update contract and scope

Fixed Newton 1.7.0 commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`. `ModelKamino.joints.tau_j_max` aliases `Model.joint_effort_limit` (conversions.py:2138). Every step computes `bound_a = dt * tau_j_max` (kinematics/joints.py:1058). The public `notify_model_changed(JOINT_DOF_FORCE_PROPERTIES)` validates structural invariants and refreshes actuation paths (solver_kamino.py:1198–1210,1558–1647). The official notify test permits finite effort-limit edits (test_kamino_solver_kamino_notify.py:669–679). Adding/removing bounded PD requires a new solver. This experiment changes only positive finite values, preserving the existing effort row. Zero, infinity, sentinel limits, gain/mode changes and unnotified updates are excluded.

## Scene and intervention

One CPU world, one world-to-body Y revolute joint; COM at the hinge; mass 1 kg and isotropic inertia 1 kg m². No geometry, gravity, contact, armature, friction or damping outside PD. POSITION PD has kp=20 N m/rad, kd=2 N m s/rad, target velocity and feed-forward zero. PADMM dense, preconditioner/acceleration enabled, containers warmstart, 200 iterations, all three tolerances 1e-7, graph conditionals disabled. The strict convergence result is diagnostic, never inferred from physical accuracy.

dt=.005 s, six phases of 20 steps (0.6 s total). Target sequence is +.1,+.1,+.1,-.1,-.1,-.1 rad. Variant A limit is .25,4,.25,.25,4,.25 N m; variant B is fixed .25 N m. A mutates the existing limit array and calls public notify before the first step of each changed-limit phase. No solver reconstruction or reset occurs. B receives identical target commands and preserves the limit. Both run twice in independent processes.

## Independent reference and identifiable branch transitions

For the scalar hinge, I=1 kg m² and no external forces. Let q_n and v_n be the beginning-of-step angle and velocity, h the timestep, L the new limit and r the POSITION target. The unconstrained implicit actuator force is

`tau_free = [kp*(r-q_n) - (kd+h*kp)*v_n] / [1 + (h*kd+h²*kp)/I]`.

Then `tau=clip(tau_free,-L,L)`, `v_next=v_n+h*tau/I`, `q_next=q_n+h*v_next`. This solves the scalar implicit PD optimality equation, consistent with m_a=h*kd+h²*kp and the effort-row bias. POSITION ignores velocity targets; kd still damps velocity. The logmap Euler integrator integrates the single-axis rotation exactly for constant per-step velocity. The reference imports only NumPy and never reads solver-computed efforts or residuals.

Design-reference A free-torque ranges by phase [N m]: [1.9064,1.9792], [1.3621,1.9013], [.8997,1.3291], [-3.4134,-3.0826], [-3.4295,-2.8474], [-2.8052,-2.4921]. Thus phases 0/2 are positive saturation, 3/5 negative saturation, 1 positive unsaturated and 4 negative unsaturated. The narrowest free/bound separation exceeds .5 N m, far above the .002 N m effort gate. These are predictions, not measured results. Target reversal occurs with nonzero angular velocity (.21466 rad/s in A), so the reverse branch is nonvacuous.

## Metrics and frozen gate rationale

Effort observations are the reported `State.joint_lambdas_tau` and private applied-body-wrench Y moment, checked independently against the reference and the momentum balance. Reference effort error <=.002 N m, speed error <=.002 rad/s, angle error <=.001 rad. These tolerances are far below the .5 N m branch margins while allowing float32 iterative error; they do not relax solver stopping tolerances. Every post-step effort must obey that step's limit within .002 N m; the first step after each update must meet the new reference, giving zero allowed stale-limit steps.

`bound_a` after each step must match h*L within 1e-7 N m s. The before-notify and after-notify model limits, internal bound, path IDs/counts, and state snapshots are saved. The old bound may remain until step assembly; it is not treated as the new limit before stepping. Path must remain EFFORT_CTS, one effort row throughout. Notify must precede the step and leave body/joint state unchanged within 1e-7. Integrator consistency `q_next-q_n-h*v_next` <=1e-5 rad, momentum effort consistency <=.002 N m, hinge position drift <=1e-5 m. Physical arrays must all be finite; initial unsolved status may contain undefined placeholders, but post-step diagnostics must be finite.

Every preregistered branch must occur on all 20 steps, verified using the independent reference and measured effort: saturated steps follow ±L within .002 N m; unsaturated steps have |effort|<L-.1 N m and the correct sign. Repeat comparison: pose/angle atol1e-5, velocity atol1e-4, effort atol.002, rtol1e-5. Each run retains source validation of all 809 locked Python files, protocol/runner copies, resolved config, raw NPZ, events, logs and hashes. Failures remain; corrections require explicit documented harness revisions and new run IDs, never post-hoc threshold changes.

## Limits

One finite-positive-to-finite-positive update contract, one axis, one CPU configuration and short horizon only. No claims about generic tracking, route allocation changes, zero/infinite limits, changing gains, CUDA/capture, multiple worlds, contacts or general convergence. This case can pass its physical switching criteria while strict PADMM stopping diagnostics fail.
