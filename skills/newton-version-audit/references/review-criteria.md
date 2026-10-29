# Compatibility review criteria

Static signatures include internal declarations; they are leads for inspection, not public-API guarantees. Trace construction/finalization before treating `None`, model fields, factory defaults or backend options as effective physical values.

| Area | Inspect for drift | Validation to plan when relevant |
| --- | --- | --- |
| Framework | Builder/finalize, Model/State/Control ownership, state swap/force clearing, q vs qd/DOF layout, collision/step order, units/up-axis | Small articulation, dimensions/ownership, controlled step, reset and repeatable initialization |
| Assets | URDF/MJCF/USD signatures, scale/axis, inertia, shape/material conversion, mesh preprocessing | Same asset; mass/inertia, transforms, limits and collision geometry against frozen expectations |
| Rigid collision | Contact ownership, margin/gap, filtering/capacity, friction combination and backend conversion | Resting/sliding/sticking, friction, penetration/contact counts; inspect effective backend parameters |
| Deformable collision | Self-contact, topology exclusions, candidate coverage/capacity, supported primitives | Self-contact and rigid-deformable scenes; penetration, missed contacts and stability |
| MuJoCo | Conversion, damping/armature/limits, actuators, condim/sliding/torsional/rolling friction, backend versions | Passive joint, limits, driven tracking and selected contact regimes |
| VBD | Materials/ALM/DAT meanings, iterations/substeps, compliance, joint/rigid/deformable support | Stretch/bend/contact and joint cases for the changed mechanism |
| Kamino | Closed-loop topology/FK, PADMM vs DVI, drives/force limits, reset/warm start, residual normalization | Closed-loop/FK residuals; equal-scene PADMM/DVI comparison; unsaturated tracking, force-limit switching and reset; report strict flags separately from scaled residuals |
| Papers | Algorithm assumptions, code symbols, implemented subsets, solver ownership | Re-resolve mappings at target commit; explain implementation boundaries rather than declaring a paper invalid |
| Environment | Python/Warp/MuJoCo/optional deps, CPU/GPU/driver, precision | Import/construction and device checks when requested/available; frozen physical reruns for numerical claims |

Freeze scene/initial state, units, dt/substeps, duration, repetitions, tolerance/normalization and success thresholds before rerunning. Use saved protocols where appropriate. Changing force limits or normalization prevents a direct comparison unless explicitly accounted for.

An unchanged file may depend on changed shared code/libraries. Graph neighbors are possible impacts, not confirmed incompatibilities. New files can require new concepts even when no existing record references them. Missing files in a full checkout are removal candidates; missing files outside package-only scope are unknown.

Separate knowledge/source updates, API adaptations, environment requirements and experiment gaps. Confirm incompatibility only from source evidence or a reproducible target failure. Without target source, state the limits of hashes/declarations and request narrow missing excerpts or a pinned public source ref.
