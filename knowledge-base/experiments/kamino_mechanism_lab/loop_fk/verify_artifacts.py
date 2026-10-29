"""Check saved provenance and applied interventions without rerunning physics."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    results = []
    for path in sorted((HERE / "runs").glob("*/result.json")):
        run = path.parent
        result, protocol = load(path), load(run / "protocol.json")
        checks = {"saved_protocol_hash": sha(run/"protocol.json") == result["protocol_sha256"], "saved_runner_hash": sha(run/"runner.py") == result["runner_sha256"], "log_exists": (run/"run.log").is_file()}
        if result["status"] == "completed":
            case = next(c for c in protocol["cases"] if c["id"] == result["case_id"])
            config, scene, environment = load(run/"resolved-config.json"), load(run/"scene.json"), load(run/"environment.json")
            settings = {**protocol["solver"], **case["solver_override"], **case["variants"][result["variant"]]}
            for field, expected in settings.items():
                if field == "loop_closing_hinge":
                    checks["actual_topology"] = len(scene["model_arrays"]["joint_parent"]) == (5 if expected else 4)
                    continue
                parts = ("dynamics_solver" if field == "backend" else field).split(".")
                actual = config
                for part in parts:
                    actual = actual[part]
                checks["resolved_"+field] = actual == expected
            checks["raw_hash"] = sha(run/"trajectory.npz") == result["trajectory_sha256"]
            checks["installed_source_hashes"] = environment["source_verified"] and environment["installed_locked_python_files_verified"] == 809 and not environment["installed_unlocked_python_paths"]
        results.append({"run":run.name, "execution_status":result["status"], "passed":all(checks.values()), "checks":checks})
    out = {"status":"passed" if all(r["passed"] for r in results) else "failed", "runs":results, "scope":"Saved content hashes, actual resolved settings and topology. No physical acceptance threshold changed."}
    (HERE/"artifact-verification.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"runs":len(results)}))


if __name__ == "__main__":
    main()
