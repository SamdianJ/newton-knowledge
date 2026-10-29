"""Build one versioned snapshot for website, CLI and MCP from canonical inputs.

Legacy source records and experiment arrays are adapted, never simulated or edited.
The current pointer is replaced only after every snapshot artifact is complete.
"""

from __future__ import annotations

import ast
import hashlib
import html
import json
import re
import shutil
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from urllib.parse import quote

import markdown

from build_index import tokens
from plan_p0 import COMMIT, ROOT, SRC, VERSION
from source_api import inventory
from maintenance import verify_sources, validate_receipt, promote

LAB = ROOT / "experiments/vbd_parameter_lab"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def encoded(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def infer_solver(path):
    for key in (
        "vbd",
        "mujoco",
        "kamino",
        "featherstone",
        "implicit_mpm",
        "semi_implicit",
        "style3d",
        "xpbd",
    ):
        if "/" + key + "/" in "/" + path:
            return key.replace("_", "-")
    return "shared"


def source_ref(path, line, lock):
    return {
        "path": path,
        "line": line,
        "commit": COMMIT,
        "sha256": lock["files"].get(path),
        "verification": "verified_snapshot"
        if path in lock["files"]
        else "local_snapshot_unverified_file",
        "url": f"https://github.com/newton-physics/newton/blob/{COMMIT}/{path}#L{line}",
    }


def references(payload, lock):
    refs = []
    for value in [
        payload.get("definition"),
        payload.get("model_definition"),
        payload.get("consumer"),
        payload.get("source"),
        payload.get("source_ref"),
    ] + payload.get("source_refs", []):
        if (
            isinstance(value, dict)
            and value.get("path")
            and (SRC / value["path"]).is_file()
        ):
            item = {**value, **source_ref(value["path"], value.get("line", 1), lock)}
            if not any(
                (r["path"], r["line"]) == (item["path"], item["line"]) for r in refs
            ):
                refs.append(item)
    return refs


def text_body(title, payload, kind, summary):
    lines = ["# " + title, "", summary or "", ""]
    if kind == "parameter":
        lines += [
            "## 定义与解析",
            "",
            f"所属位置：`{payload.get('owner', '')}`。",
            "",
            f"声明默认：`{payload.get('declared_default_expression', '必填')}`；解析值：`{payload.get('resolved_default')}`。",
            "",
            payload.get("default_policy", ""),
            "",
            payload.get("documentation", ""),
            "",
            payload.get("lifecycle", ""),
        ]
    elif kind == "model_input":
        lines += [
            f"单位：{payload.get('units', '见字段说明')}。",
            "",
            payload.get("default_policy", ""),
        ]
    elif kind == "diagnostic":
        lines += ["状态：proposed，待验证方案。", ""] + [
            f"{i}. {p}" for i, p in enumerate(payload.get("plan", []), 1)
        ]
        lines += ["", payload.get("caution", "")]
    elif kind == "mapping":
        if payload.get("mapping_kind"):
            label = {"implementation_fact": "实现事实（论文仅提供背景）", "mechanism_correspondence": "论文机制对应（人工源码映射）"}.get(payload["mapping_kind"], payload["mapping_kind"])
            lines += ["条目类型：" + label + "。", ""]
        lines += [
            payload.get("correspondence", ""),
            "",
            str(payload.get("paper_locator", "")),
            "",
            payload.get("boundary", ""),
        ]
        if payload.get("symbols"):
            lines += ["", "## 对应函数与调用点", ""]
            for item in payload["symbols"]:
                if isinstance(item, dict) and item.get("url"):
                    lines.append(f"- [{item['name']}]({item['url']})")
                elif isinstance(item, dict):
                    lines.append("- `" + item.get("name", item.get("id", "")) + "`")
                else:
                    lines.append("- `" + str(item) + "`")
        if payload.get("local_experiments"):
            lines += ["", "## 已有局部实验", "", "这些关联只支持列出的窄范围，不表示整项机制或论文已验证。", ""]
            for evidence in payload["local_experiments"]:
                rid = evidence["record_id"]
                lines += [f"- [{rid}](#/record/{quote(rid, safe='')})：{evidence['scope']}。边界：{evidence['limitation']}。"]
        if payload.get("unvalidated_scope"):
            lines += ["", "## 仍未验证", ""] + ["- " + item for item in payload["unvalidated_scope"]]
    elif kind == "claim":
        lines += [
            "## 适用范围",
            "",
            payload.get("scope", "仅限固定源码所说明的路径。"),
            "",
            "关联参数：" + ", ".join(payload.get("parameter_ids", [])),
        ]
    elif kind == "capabilities":
        lines += ["```json", json.dumps(payload, ensure_ascii=False, indent=2), "```"]
    elif kind == "paper":
        lines += [
            f"年份：{payload.get('year')}；页数：{payload.get('pages')}。",
            "",
            payload.get("role", ""),
            "",
            f"[原文入口]({payload.get('url', '')})",
            "",
            f"本地 PDF：`{payload.get('local_path', '')}`。",
        ]
    elif kind == "source_symbol":
        lines += [
            "```python",
            payload.get("public_name", payload.get("name", ""))
            + payload.get("signature", ""),
            "```",
            "",
            payload.get("documentation", payload.get("docstring", "")),
        ]
    elif kind in ("lab_experiment", "experiment"):
        lines += [
            "## 保存的结果",
            "",
            payload.get("observation", ""),
            "",
            "```json",
            json.dumps(
                {k: v for k, v in payload.items() if k != "initial_geometry"},
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    return "\n".join(str(x) for x in lines if x is not None).strip() + "\n"


def route_for(record):
    kind = record["record_type"]
    solver = record.get("owner_solver")
    rid = record["id"]
    payload = record.get("payload", {})
    if kind == "parameter":
        return (
            "#/solvers/"
            + (solver or "shared")
            + "/parameters/"
            + quote(payload.get("name", rid), safe="")
        )
    if kind == "model_input":
        return (
            "#/solvers/"
            + (solver or "shared")
            + "/inputs/"
            + quote(payload.get("field", rid), safe="")
        )
    if kind == "lab_experiment":
        return "#/solvers/" + solver + "/experiments?case=" + payload["id"]
    if kind == "document":
        return "#/document/" + quote(record["document_path"], safe="/")
    if kind == "solver":
        return "#/solvers/" + payload.get("solver", rid.split(":")[-1])
    if kind == "stage":
        return "#/workflow/" + rid.split(":")[-1]
    return "#/record/" + quote(rid, safe="")


def legacy_inputs():
    baseline = read("planning/p0/migration-baseline.json")
    params = [
        {k: v for k, v in p.items() if k != "textual_occurrences"}
        for p in read("solvers/vbd/parameters.json")["records"]
    ]
    models = read("solvers/vbd/model-inputs.json")
    full = read("experiments/vbd_parameter_lab/report-data.json")
    associations = {
        "full_surface": ["pipeline:enable_rigid_soft_full_surface_contact"],
        "substeps": ["process:substeps"],
        "stiffness": ["model:spring_stiffness"],
        "damping": ["model:spring_damping"],
        "contact_stiffness": ["model:soft_contact_ke", "model:shape_material_ke"],
        "friction": ["model:soft_contact_mu", "model:shape_material_mu"],
        "membrane": ["model:tri_materials"],
        "bending": ["model:edge_bending_properties"],
    }
    experiments = []
    graph = read("graph/knowledge-graph.json")
    graph["nodes"] += [
        {
            "id": "pipeline:enable_rigid_soft_full_surface_contact",
            "type": "pipeline_setting",
            "label": "enable_rigid_soft_full_surface_contact",
        },
        {"id": "process:substeps", "type": "process_setting", "label": "substeps"},
    ]
    for experiment in full["experiments"]:
        item = {
            k: v for k, v in experiment.items() if k not in ("variants", "plot_svg")
        }
        item.update(
            record_id="lab:" + item["id"],
            associations=associations.get(
                item["id"], ["newton:1.7.0:SolverVBD:" + item["parameter"]]
            ),
        )
        item["variants"] = [
            {
                k: v
                for k, v in v.items()
                if k
                in (
                    "variant",
                    "value",
                    "metrics",
                    "config",
                    "raw_file",
                    "program_sha256",
                )
            }
            for v in experiment["variants"]
        ]
        for saved in item["variants"]:
            saved["raw_sha256"] = sha(LAB / saved["raw_file"])
        item["initial_geometry"] = [
            {
                "variant": v["variant"],
                "particle_q": v["particle_q"][0][:80],
                "body_q": v["body_q"][0][:80],
                "particle_count": len(v["particle_q"][0]),
                "body_count": len(v["body_q"][0]),
                "truncated": len(v["particle_q"][0]) > 80 or len(v["body_q"][0]) > 80,
                "full_geometry_artifact": "experiments/vbd_parameter_lab/"
                + v["raw_file"],
            }
            for v in experiment["variants"]
        ]
        item["environment"] = full["environment"]
        experiments.append(item)
        graph["nodes"].append(
            {
                "id": item["record_id"],
                "type": "lab_experiment",
                "label": item["title"],
                "experiment_id": item["id"],
                "solver": "vbd",
            }
        )
        for target in item["associations"]:
            graph["edges"].append(
                {
                    "source": item["record_id"],
                    "target": target,
                    "relation": "varies_group_in_case"
                    if len(item["associations"]) > 1 or item["id"] == "membrane"
                    else "varies_in_case",
                    "evidence": "experiments/vbd_parameter_lab/report-data.json",
                }
            )
    for p in params + models:
        p["experiments"] = [
            e["id"] for e in experiments if p["id"] in e["associations"]
        ]
    vbd = {
        "id": "vbd",
        "name": "VBD",
        "parameters": params,
        "model_inputs": models,
        "claims": read("solvers/vbd/claims.json"),
        "mappings": read("solvers/vbd/paper-code-map.json"),
        "diagnostics": read("solvers/vbd/diagnostics.json"),
        "papers": read("manifests/papers.json"),
        "experiments": experiments,
        "counts": {
            "parameters": 47,
            "constructor_optional": 47,
            "config_fields": 0,
            "reset_fields": 0,
            "model_inputs": len(models),
            "papers": 3,
            "experiments": 17,
            "runs": 34,
        },
    }
    solvers = {
        "vbd": vbd,
        "mujoco": read("solvers/mujoco/catalog.json"),
        "kamino": read("solvers/kamino/catalog.json"),
    }
    for measured_path in (
        ROOT / "experiments/solver_parameter_lab/catalog.json",
        ROOT / "experiments/kamino_mechanism_lab/catalog.json",
        ROOT / "experiments/kamino_pd_lab/catalog.json",
        ROOT / "experiments/mujoco_joint_contact_lab/catalog.json",
    ):
        if not measured_path.exists():
            continue
        measured = read(measured_path.relative_to(ROOT))
        if measured["status"] != "passed" or measured["report_sha256"] != sha(
            measured_path.with_name("report-data.json")
        ):
            raise ValueError("New solver experiment catalog failed verification")
        if measured["analyzer_sha256"] != sha(
            measured_path.with_name("analyze_experiments.py")
        ):
            raise ValueError(
                "Experiment analyzer changed; revalidate before publishing"
            )
        for path, expected in measured.get("evidence_files", {}).items():
            if sha(ROOT / path) != expected:
                raise ValueError("Mechanism experiment evidence changed: " + path)
        for item in measured["cases"]:
            solver = item["solver"]
            cat = solvers[solver]
            for variant in item["variants"]:
                if sha(ROOT / variant["raw_file"]) != variant["raw_sha256"]:
                    raise ValueError("New solver raw data changed: " + item["id"])
            cat["experiments"].append(item)
            graph["nodes"].append(
                {
                    "id": item["record_id"],
                    "type": "lab_experiment",
                    "label": item["title"],
                    "solver": solver,
                }
            )
            for target in item["associations"]:
                graph["edges"].append(
                    {
                        "source": item["record_id"],
                        "target": target,
                        "relation": item.get("association_relation") or ("varies_group_in_case"
                        if len(item["associations"]) > 1
                        else "varies_in_case"),
                        "evidence": measured_path.relative_to(ROOT).as_posix(),
                    }
                )
            for p in cat["parameters"] + cat["model_inputs"]:
                if p["id"] in item["associations"]:
                    p.setdefault("experiments", []).append(item["id"])
        for solver in ("mujoco", "kamino"):
            solvers[solver]["counts"].update(
                experiments=len(solvers[solver]["experiments"]),
                runs=sum(len(e["variants"]) for e in solvers[solver]["experiments"]),
            )
    extra = read("graph/extra-solvers.json")
    graph["nodes"] += extra["nodes"]
    graph["edges"] += extra["edges"]
    return solvers, graph, baseline


def render(text, path, known_docs):
    math_blocks = []

    def hold(match):
        math_blocks.append(match.group(1))
        return "\n\nMATHBLOCK" + str(len(math_blocks) - 1) + "END\n\n"

    protected = re.sub(r"\$\$(.*?)\$\$", hold, text, flags=re.S)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"])
    output = md.convert(protected)
    for i, value in enumerate(math_blocks):
        output = output.replace(
            "<p>MATHBLOCK" + str(i) + "END</p>",
            '<div class="math-block">' + html.escape(value) + "</div>",
        )
    output = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        r'<div class="mermaid">\1</div>',
        output,
        flags=re.S,
    )

    def rewrite(match):
        url = html.unescape(match.group(1))
        prefix = f"https://github.com/newton-physics/newton/blob/{COMMIT}/"
        if url.startswith(prefix):
            source, _, anchor = url[len(prefix) :].partition("#")
            line = re.search(r"L(\d+)", anchor)
            value = (
                "#/source/"
                + quote(source, safe="/")
                + "?line="
                + (line.group(1) if line else "1")
            )
        elif not url.startswith(("http:", "https:", "mailto:", "#", "/")):
            target = (ROOT / path).parent / url.split("#")[0]
            try:
                relative = target.resolve().relative_to(ROOT).as_posix()
            except ValueError:
                return match.group(0)
            value = (
                "#/document/" + quote(relative, safe="/")
                if relative in known_docs
                else "/files/" + quote(relative, safe="/")
            )
            if "#" in url:
                value += (
                    "?section=" + quote(url.split("#", 1)[1])
                    if relative in known_docs
                    else "#" + url.split("#", 1)[1]
                )
        else:
            return match.group(0)
        return 'href="' + html.escape(value, quote=True) + '"'

    output = re.sub(r'href="([^"]+)"', rewrite, output)
    return output, md.toc_tokens


def main():
    registry = read("knowledge/registry.json")
    lock = read("manifests/source-lock.json")
    source_errors = verify_sources(SRC, lock)
    if source_errors:
        raise ValueError("Pinned source integrity failed: " + str(source_errors[:8]))
    solvers, graph, baseline = legacy_inputs()
    authored_path = ROOT / "knowledge/authored.json"
    authored = (
        read("knowledge/authored.json")
        if authored_path.exists()
        else {"records": {}, "relations": []}
    )
    extensions = (
        read("knowledge/extensions.json")
        if (ROOT / "knowledge/extensions.json").exists()
        else {"records": [], "relations": []}
    )
    records = {}
    aliases = {}
    legacy_kind_map = {"mechanism_mapping": "mapping", "code_symbol": "source_symbol"}

    def add(
        rid,
        kind,
        title,
        payload,
        solver="shared",
        summary=None,
        body=None,
        domain=None,
        stages=None,
        document_path=None,
        planned=False,
    ):
        summary = (
            summary
            or payload.get("summary_zh")
            or payload.get("description_zh")
            or payload.get("statement_zh")
            or payload.get("correspondence")
            or payload.get("symptom")
            or payload.get("role")
            or title
        )
        domain = domain or ("solver" if solver != "shared" else "framework")
        refs = references(payload, lock)
        record = {
            "id": rid,
            "record_type": kind,
            "kind": kind,
            "title": title,
            "summary": str(summary),
            "domain": domain,
            "stages": stages or (["solver_step"] if solver != "shared" else []),
            "record_scope": "shared" if solver == "shared" else "solver",
            "owner_solver": None if solver == "shared" else solver,
            "owner_module": payload.get(
                "owner_module", "newton.solvers" if solver != "shared" else "newton"
            ),
            "owner": payload.get("owner", payload.get("public_name", "")),
            "applicable_solvers": payload.get(
                "applicable_solvers", [solver] if solver != "shared" else []
            ),
            "support_status": payload.get(
                "support_status", "unknown" if planned else "supported"
            ),
            "coverage": {
                "indexed": not planned,
                "explained": not planned and kind not in ("source_symbol",),
                "task_validated": False,
                "experiment_validated": kind in ("lab_experiment", "experiment") and payload.get("physical_acceptance", "passed") == "passed",
            },
            "content_status": "planned" if planned else "published",
            "source_refs": refs,
            "version": VERSION,
            "commit": COMMIT,
            "body": body
            if body is not None
            else text_body(title, payload, kind, str(summary)),
            "payload": payload,
            "document_path": document_path,
            "evidence_type": "proposed"
            if kind == "diagnostic"
            else "measured"
            if kind in ("lab_experiment", "experiment")
            else "paper_background"
            if kind == "paper"
            else "source_checked",
        }
        record["route"] = route_for(record)
        records[rid] = record
        return record

    for solver, cat in solvers.items():
        for kind, key, label_key in [
            ("parameter", "parameters", "name"),
            ("model_input", "model_inputs", "field"),
            ("claim", "claims", "id"),
            ("mapping", "mappings", "title_zh"),
            ("diagnostic", "diagnostics", "symptom"),
            ("paper", "papers", "title"),
        ]:
            for payload in cat[key]:
                add(
                    payload["id"],
                    kind,
                    payload.get(label_key, payload["id"]),
                    payload,
                    solver,
                )
        for payload in cat["experiments"]:
            add(
                payload["record_id"],
                "lab_experiment",
                payload["title"],
                payload,
                solver,
                summary=payload["observation"],
            )
    for item in read("experiments/results.cpu.json")["tests"]:
        add(
            item["id"],
            "experiment",
            item["id"],
            item,
            "vbd",
            summary="VBD 保存的 CPU 探针，结论仅限该探针。",
        )
    supplemental_docs = [
        {"path": "solvers/kamino/experiments.md", "title": "机制实验与适用边界"},
        {"path": "experiments/kamino_mechanism_lab/README.md", "title": "机制实验原始证据与复现"},
        {"path": "solvers/kamino/pd-experiments.md", "title": "有界 PD 收敛、跟踪与力限切换"},
        {"path": "experiments/kamino_pd_lab/README.md", "title": "PD 诊断实验原始证据与复现"},
        {"path": "solvers/mujoco/experiments.md", "title": "关节、摩擦与接触参数实验"},
        {"path": "experiments/mujoco_joint_contact_lab/README.md", "title": "关节与碰撞实验原始证据与复现"},
    ]
    for doc in baseline["documents"] + [d for d in supplemental_docs if (ROOT / d["path"]).exists()]:
        path = doc["path"]
        text = (ROOT / path).read_text(encoding="utf-8")
        solver = infer_solver(path)
        if path.startswith(("experiments/kamino_mechanism_lab/", "experiments/kamino_pd_lab/")):
            solver = "kamino"
        if path.startswith("experiments/mujoco_joint_contact_lab/"):
            solver = "mujoco"
        if (
            path.startswith("experiments/vbd_parameter_lab/")
            or path == "evaluations/REPORT.md"
        ):
            solver = "vbd"
        title = (solvers[solver]["name"] + " · " if solver in solvers else "") + doc[
            "title"
        ]
        add(
            "page:" + path,
            "document",
            title,
            {"path": path},
            solver,
            summary=text.split("\n\n", 2)[1][:350] if "\n\n" in text else title,
            body=text,
            domain="solver" if solver != "shared" else "development",
            document_path=path,
        )
    maintenance_page = "knowledge/pages/development/maintenance.md"
    if (ROOT / maintenance_page).exists():
        add(
            "page:" + maintenance_page,
            "document",
            "维护、来源更新与版本差异",
            {
                "path": maintenance_page,
                "scope": "knowledge platform operations, not upstream solver physics",
            },
            summary="来源与 API/default 差异、证据失效、原子快照、兼容读取和回归归档。",
            body=(ROOT / maintenance_page).read_text(encoding="utf-8"),
            domain="development",
            document_path=maintenance_page,
        )
    for node in graph["nodes"]:
        if node["id"] in records:
            continue
        kind = legacy_kind_map.get(node["type"], node["type"])
        solver = node.get("solver") or infer_solver(
            node.get("source_ref", {}).get("path", "")
        )
        if node["id"] == "solver:VBD:1.7.0":
            solver = "vbd"
        if node["id"].startswith("model:") and solver == "shared":
            solver = "vbd"
        add(node["id"], kind, node["label"], node, solver)
    # Define common pipeline/process parameters once; VBD has the measured association.
    flag = "pipeline:enable_rigid_soft_full_surface_contact"
    pipeline = SRC / "newton/_src/sim/collide.py"
    cls = next(
        n
        for n in ast.walk(ast.parse(pipeline.read_text(encoding="utf-8")))
        if isinstance(n, ast.ClassDef) and n.name == "CollisionPipeline"
    )
    init = next(
        n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"
    )
    arg = next(
        n
        for n in init.args.kwonlyargs + init.args.args
        if n.arg == "enable_rigid_soft_full_surface_contact"
    )
    ref = source_ref("newton/_src/sim/collide.py", arg.lineno, lock)
    payload = {
        "id": flag,
        "name": "enable_rigid_soft_full_surface_contact",
        "owner": "newton.CollisionPipeline.__init__",
        "layer": "collision_pipeline",
        "declared_default_expression": "False",
        "resolved_default": "False",
        "type": "bool",
        "definition": ref,
        "documentation": "生成刚体 SDF 与软体 edge/face 接触，扩充同一 soft-contact 存储。Newton 1.7.0 由 VBD 指定路径消费；XPBD、SemiImplicit、Featherstone 和 Style3D 的 particle-only 消费路径拒绝这种存储。VBD proxy-particle 耦合模式也不支持；不能外推为所有只消费 rigid_contacts 的后端都会抛错。",
        "summary_zh": "公共管线 full-surface 刚柔接触；VBD 有条件消费，particle-only 后端明确不支持，区别于刚体 hydroelastic。",
        "applicable_solvers": ["vbd"],
        "experiments": ["full_surface"],
        "support_matrix": {
            s: "conditional" if s == "vbd" else "unsupported"
            for s in registry["solver_keys"]
        },
        "support_scope": "edge/face soft-contact response support, not whether a rigid-only backend rejects Contacts storage",
        "support_conditions": {
            "vbd": "VBD owns the required soft/rigid response; proxy-particle coupling rejects full-surface contacts",
            "particle_only": "XPBD/SemiImplicit/Featherstone/Style3D guard rejects full-surface soft-contact storage",
            "rigid_or_mpm": "MuJoCo/Kamino have no soft-body response; ImplicitMPM does not consume these edge/face soft-contact records",
        },
        "source_refs": [
            source_ref("newton/_src/sim/collide.py", 1338, lock),
            source_ref("newton/_src/sim/contacts.py", 646, lock),
            source_ref("newton/_src/solvers/vbd/solver_vbd.py", 1639, lock),
            source_ref("newton/_src/solvers/featherstone/solver_featherstone.py", 626, lock),
            source_ref("newton/_src/solvers/semi_implicit/kernels_contact.py", 723, lock),
            source_ref("newton/_src/solvers/implicit_mpm/solver_implicit_mpm.py", 1925, lock),
        ],
    }
    add(
        flag,
        "parameter",
        payload["name"],
        payload,
        "shared",
        domain="workflow",
        stages=["collision", "solver_step"],
    )
    process = {
        "id": "process:substeps",
        "name": "substeps",
        "owner": "caller simulation loop",
        "layer": "simulation_loop",
        "declared_default_expression": None,
        "default_policy": "调用方决定 frame_dt / substeps，不存在 SolverVBD 构造默认。",
        "resolved_default": None,
        "type": "int",
        "source_refs": [
            source_ref("newton/examples/basic/example_basic_pendulum.py", 116, lock)
        ],
        "applicable_solvers": registry["solver_keys"],
    }
    add(
        process["id"],
        "parameter",
        "substeps",
        process,
        "shared",
        summary="调用方的子步与时间推进设置，和一次 step 内迭代次数不同。",
        domain="workflow",
        stages=["solver_step"],
    )
    for entry in registry["entries"]:
        rid = entry["id"]
        slug = entry.get("solver")
        family = entry["family"]
        overrides = authored["records"].get(rid)
        payload = {**entry, **(overrides or {})}
        planned = not overrides and family != "solver"
        body = (overrides or {}).get("body")
        if body is None:
            body = f"# {entry['title']}\n\n" + (
                f"{entry['title']} 的版本化知识入口。"
                if family == "solver"
                else "此页为已登记的建设入口，目标内容尚未完成。"
            )
            body += (
                "\n\n目标深度："
                + entry["target_depth"]
                + "；当前状态："
                + (
                    "已有深入资料"
                    if slug in solvers
                    else "索引入口"
                    if family == "solver"
                    else "待建设"
                )
                + "。\n"
            )
            if entry.get("public_exports"):
                body += (
                    "\n公开导出："
                    + ", ".join("`" + s + "`" for s in entry["public_exports"])
                    + "。\n"
                )
            body += (
                "\n## 固定来源\n\n"
                + "\n".join(
                    f"- [{r['path']}]({r['url']})" for r in entry["source_refs"]
                )
                + "\n"
            )
        path = entry["canonical_path"]
        (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / path).write_text(body, encoding="utf-8")
        record = add(
            rid,
            family,
            entry["title"],
            payload,
            slug or "shared",
            summary=(overrides or {}).get("summary", entry["title"]),
            body=body,
            domain=(overrides or {}).get(
                "domain",
                "development"
                if rid
                in (
                    "topic:environment",
                    "topic:development-testing",
                    "topic:migration-integrations",
                )
                else "workflow"
                if family in ("stage", "recipe")
                else "solver"
                if family == "solver"
                else "framework",
            ),
            stages=entry["stages"],
            document_path=path,
            planned=planned,
        )
        if family == "solver":
            if slug not in solvers:
                solvers[slug] = {
                    "id": slug,
                    "name": entry["title"].removeprefix("Solver"),
                    "parameters": [],
                    "model_inputs": [],
                    "claims": [],
                    "mappings": [],
                    "diagnostics": [],
                    "papers": [],
                    "experiments": [],
                    "counts": {
                        "parameters": 0,
                        "constructor_optional": 0,
                        "config_fields": 0,
                        "reset_fields": 0,
                        "model_inputs": 0,
                        "papers": 0,
                        "experiments": 0,
                        "runs": 0,
                    },
                }
            solvers[slug].update(
                coverage_level="deep"
                if slug in ("vbd", "mujoco", "kamino")
                else "indexed",
                registry_id=rid,
                public_class="newton.solvers." + entry["public_class"],
            )
        for alias in entry["aliases"]:
            if alias not in records or (
                family == "solver" and alias.startswith("solver:")
            ):
                aliases[alias] = {"id": rid}
    api = inventory(registry)
    write(ROOT / "indexes/public-api.json", {"version": VERSION, "symbols": api})
    for symbol in api:
        solver = infer_solver(symbol["path"])
        owner = (
            ".".join(symbol["public_name"].split(".")[:2])
            if symbol["public_name"].split(".")[1]
            in (
                "actuators",
                "controllers",
                "geometry",
                "ik",
                "math",
                "selection",
                "sensors",
                "solvers",
                "usd",
                "utils",
                "viewer",
            )
            else "newton"
        )
        if (
            owner == "newton.solvers"
            and solver == "shared"
            and symbol["public_name"].startswith("newton.solvers.experimental.coupled")
        ):
            owner = "newton.solvers.experimental.coupled"
        payload = {
            **symbol,
            "source_refs": [source_ref(symbol["path"], symbol["line"], lock)],
            "owner_module": owner,
        }
        module_id = "module:" + (
            owner.split(".")[-1] if owner != "newton" else "newton"
        )
        module_entry = next(
            (e for e in registry["entries"] if e["id"] == module_id), None
        )
        if solver == "shared":
            payload["applicable_solvers"] = (
                authored["records"].get(module_id, {}).get("applicable_solvers", [])
            )
        stages = module_entry["stages"] if module_entry else []
        public = symbol["public_name"]
        if public.startswith("newton.ModelBuilder"):
            stages = ["asset_import", "preprocess", "initialization"]
        if any(
            public.startswith("newton.ModelBuilder." + name)
            for name in ("add_urdf", "add_usd", "add_mjcf")
        ):
            stages = ["asset_import"]
        if public.startswith("newton.Control"):
            stages = ["control"]
        if public.startswith("newton.CollisionPipeline"):
            stages = ["initialization", "collision"]
        add(
            symbol["id"],
            "source_symbol",
            symbol["public_name"],
            payload,
            solver,
            summary=symbol["summary"],
            domain="solver" if solver != "shared" else "framework",
            stages=["solver_step"] if solver != "shared" else stages,
        )
    for entry in extensions["records"]:
        path = entry["canonical_path"]
        (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / path).write_text(entry["body"], encoding="utf-8")
        add(
            entry["id"],
            entry["family"],
            entry["title"],
            entry,
            entry.get("solver") or "shared",
            summary=entry["summary"],
            body=entry["body"],
            domain=entry["domain"],
            stages=entry["stages"],
            document_path=path,
        )
    for entry in registry["entries"] + extensions["records"]:
        record = records[entry["id"]]
        if entry["target_depth"] == "I":
            record["coverage"]["explained"] = False
        entry["observed_depth"] = (
            "E"
            if record["coverage"]["explained"]
            else "I"
            if record["coverage"]["indexed"]
            else "not_curated"
        )
        entry["observed_state"] = {
            "E": "已解释 · 未完成任务验证",
            "I": "已索引",
            "not_curated": "待建设",
        }[entry["observed_depth"]]
        entry["summary"] = record["summary"]
        entry["description"] = next(
            (
                p
                for p in record["body"].split("\n\n")[2:]
                if p.strip() and not p.startswith(("#", "-", "```"))
            ),
            "",
        )[:650]
        doc = next(
            (
                r
                for r in record["source_refs"]
                if r["path"].startswith("docs/") and r["path"].endswith(".rst")
            ),
            None,
        )
        entry["official_url"] = (
            "https://newton-physics.github.io/newton/latest/"
            + doc["path"][5:-4]
            + ".html"
            if doc
            else None
        )
    receipts = (
        read("knowledge/validation-receipts.json")
        if (ROOT / "knowledge/validation-receipts.json").exists()
        else {"records": {}}
    )
    for path, expected in {
        (item["report"], item["report_sha256"]) for item in receipts["records"].values()
    }:
        if sha(ROOT / path) != expected:
            raise ValueError("Validation report hash changed: " + path)
    for rid, receipt in receipts["records"].items():
        if rid in records and validate_receipt(
            records[rid]["body"], receipt, ROOT, records[rid]["source_refs"]
        ):
            records[rid]["coverage"]["task_validated"] = True
            records[rid]["validation_evidence"] = receipt
            report_id = "validation:" + receipt["report_sha256"][:24]
            records[rid]["validation_evidence"]["report_record_id"] = report_id
            if report_id not in records:
                report = read(receipt["report"])
                evidence = add(
                    report_id,
                    "validation_report",
                    report.get("phase", "Task") + " · immutable task validation",
                    {
                        "path": receipt["report"],
                        "sha256": receipt["report_sha256"],
                        "validated_build_id": receipt["validated_build_id"],
                        "scope": "deterministic tool evidence checks; no free-form LLM or physical claim",
                    },
                    body=json.dumps(
                        {
                            **{
                                k: v
                                for k, v in report.items()
                                if k
                                in (
                                    "phase",
                                    "status",
                                    "build_id",
                                    "passed",
                                    "failed",
                                    "calls",
                                    "metrics",
                                )
                            },
                            "tasks": [
                                {k: t[k] for k in ("id", "status", "calls") if k in t}
                                for t in report.get("tasks", [])
                            ],
                            "original_report": receipt["report"],
                            "original_report_sha256": receipt["report_sha256"],
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    summary="固定验收报告与哈希；任务覆盖独立于物理实测。",
                    domain="development",
                )
                evidence["evidence_type"] = "task_validation"
            graph["edges"].append(
                {
                    "source": rid,
                    "target": report_id,
                    "relation": "validated_by",
                    "evidence_type": "task_validation",
                    "body_sha256": receipt["body_sha256"],
                }
            )
    for entry in registry["entries"] + extensions["records"]:
        record = records[entry["id"]]
        if record["coverage"]["task_validated"]:
            entry["observed_state"] = (
                "已索引 · 索引范围任务已验证"
                if entry["target_depth"] == "I"
                else "已解释 · 任务已验证"
            )
            if entry["target_depth"] != "I":
                entry["observed_depth"] = "T"
    # Old document sections resolve precisely without competing with whole documents in search.
    old_database = ROOT / "indexes/knowledge.sqlite"
    if old_database.exists():
        with sqlite3.connect(old_database.as_uri() + "?mode=ro", uri=True) as con:
            for rid, kind, record in con.execute("SELECT id,kind,record FROM records"):
                if kind == "document" and rid not in records:
                    data = json.loads(record)
                    if data.get("path") and "page:" + data["path"] in records:
                        aliases[rid] = {
                            "id": "page:" + data["path"],
                            "section": data.get("section"),
                        }
    # Preserve any legacy index-only entries, including capability records.
    for old in baseline["search_records"]:
        if old["id"] in records or old["id"] in aliases:
            continue
        if old["kind"] == "capabilities":
            payload = read("solvers/vbd/capabilities.json")
        else:
            payload = (
                {
                    "id": old["id"],
                    "legacy_route": old["route"],
                    "summary_zh": old["summary"],
                }
                if "summary" in old
                else old
            )
        add(
            old["id"],
            old["kind"],
            old["title"],
            payload,
            old["solver"],
            summary=old["title"],
        )
    nodes = {n["id"]: dict(n) for n in graph["nodes"]}
    edges = list(graph["edges"])
    for rid, record in records.items():
        node = nodes.setdefault(
            rid, {"id": rid, "type": record["record_type"], "label": record["title"]}
        )
        node.update(
            solver=record["owner_solver"] or "shared",
            record_type=record["record_type"],
            domain=record["domain"],
            stages=record["stages"],
            record_scope=record["record_scope"],
        )
        if record["record_type"] == "mapping":
            for evidence in record["payload"].get("local_experiments", []):
                target = records.get(evidence["record_id"])
                if not target or target["record_type"] != "lab_experiment" or target["owner_solver"] != record["owner_solver"]:
                    raise ValueError("Mapping local evidence must reference a measured lab of the same solver: " + rid)
                edges.append({
                    "source": rid,
                    "target": evidence["record_id"],
                    "relation": "partial_local_evidence",
                    "evidence_type": "measured_narrow_scope",
                    "scope": evidence["scope"],
                    "limitation": evidence["limitation"],
                })
        for reference in record["source_refs"]:
            source_id = "source:" + reference["path"] + ":" + str(reference["line"])
            nodes.setdefault(
                source_id,
                {
                    "id": source_id,
                    "type": "source_symbol",
                    "label": reference["path"].split("/")[-1]
                    + ":"
                    + str(reference["line"]),
                    "solver": infer_solver(reference["path"]),
                    "source_ref": reference,
                },
            )
            edges.append(
                {
                    "source": rid,
                    "target": source_id,
                    "relation": "supported_by",
                    "source_refs": [reference],
                    "evidence_type": "source_checked",
                }
            )
    for symbol in api:
        owner = records[symbol["id"]]["owner_module"]
        module_id = "module:" + (
            owner.split(".")[-1] if owner != "newton" else "newton"
        )
        if module_id in records:
            edges.append(
                {
                    "source": module_id,
                    "target": symbol["id"],
                    "relation": "exports",
                    "source_refs": records[symbol["id"]]["source_refs"],
                    "evidence_type": "source_checked",
                }
            )
    for relation in authored.get("relations", []):
        edges.append(relation)
    edges.extend(extensions["relations"])
    for alias, target in aliases.items():
        if alias in nodes and target["id"] in nodes:
            for edge in list(edges):
                if alias in (edge["source"], edge["target"]):
                    edges.append(
                        {
                            **edge,
                            "source": target["id"]
                            if edge["source"] == alias
                            else edge["source"],
                            "target": target["id"]
                            if edge["target"] == alias
                            else edge["target"],
                        }
                    )
    unique = {}
    for edge in edges:
        if edge["source"] not in nodes or edge["target"] not in nodes:
            raise ValueError("Dangling edge: " + str(edge))
        key = (edge["source"], edge["relation"], edge["target"])
        if key not in unique:
            unique[key] = edge
    graph = {"nodes": list(nodes.values()), "edges": list(unique.values())}
    for edge in graph["edges"]:
        edge["id"] = (
            "edge:"
            + hashlib.sha256(
                encoded([edge["source"], edge["relation"], edge["target"]])
            ).hexdigest()[:20]
        )
    documents = {}
    for record in records.values():
        path = record.get("document_path")
        if path:
            documents[path] = {
                "path": path,
                "title": record["title"],
                "group": (
                    solvers[record["owner_solver"]]["name"]
                    if record["owner_solver"] in solvers
                    else "Newton 公共知识"
                ),
                "solver": record["owner_solver"] or "shared",
                "domain": record["domain"],
                "record_id": record["id"],
                "text": record["body"],
            }
    for path, doc in documents.items():
        doc["html"], doc["toc"] = render(doc["text"], path, documents)
    hashes = {
        "experiment_programs": sha(ROOT / "manifests/experiment-programs.json"),
        "records": hashlib.sha256(encoded(records)).hexdigest(),
        "graph": hashlib.sha256(encoded(graph)).hexdigest(),
        "documents": hashlib.sha256(encoded(documents)).hexdigest(),
        "registry": hashlib.sha256(encoded(registry)).hexdigest(),
        "contract": sha(ROOT / "planning/p0/mcp-contract.json"),
    }
    programs = {
        path: sha(ROOT / path)
        for path in [
            "scripts/build_platform.py",
            "scripts/knowledge_store.py",
            "scripts/maintenance.py",
            "scripts/source_api.py",
            "scripts/author_platform.py",
            "scripts/author_extensions.py",
            "scripts/common_content.py",
            "scripts/author_docs.py",
            "scripts/curated.py",
            "scripts/model_and_cases.py",
            "scripts/extend_solvers.py",
            "scripts/solver_mechanism_content.py",
            "scripts/kamino_experiment_content.py",
            "scripts/kamino_pd_content.py",
            "scripts/mujoco_experiment_content.py",
            "scripts/build_solid_replays.py",
            "scripts/replay_geometry_kamino.py",
            "experiments/solid_replay/geometry.json",
            "experiments/solid_replay/renderer.js",
            "experiments/solid_replay/viewer.js",
            "experiments/solid_replay/viewer.css",
            "experiments/solid_replay/README.md",
            "experiments/solver_parameter_lab/index.html",
            "mcp_service/server.py",
            "site/server.py",
            "site/dist/platform.js",
            "site/dist/platform.css",
            "experiments/solver_parameter_lab/viewer.js",
            "experiments/solver_parameter_lab/viewer.css",
            "experiments/kamino_mechanism_lab/viewer.js",
            "experiments/kamino_mechanism_lab/viewer.css",
            "experiments/kamino_mechanism_lab/index.html",
            "experiments/kamino_mechanism_lab/analyze_experiments.py",
            "experiments/kamino_pd_lab/viewer.js",
            "experiments/kamino_pd_lab/viewer.css",
            "experiments/kamino_pd_lab/index.html",
            "experiments/kamino_pd_lab/analyze_experiments.py",
            "experiments/mujoco_joint_contact_lab/analyze_experiments.py",
            "experiments/mujoco_joint_contact_lab/viewer.js",
            "experiments/mujoco_joint_contact_lab/viewer.css",
            "experiments/mujoco_joint_contact_lab/index.html",
        ]
    }
    hashes["platform_programs"] = hashlib.sha256(encoded(programs)).hexdigest()
    build_id = hashlib.sha256(encoded(hashes)).hexdigest()[:24]
    graph["build_id"] = build_id
    catalog = {
        "version": VERSION,
        "commit": COMMIT,
        "build_id": build_id,
        "built_at": datetime.now(UTC).isoformat(),
        "solver": "shared",
        "legacy_default_solver": "vbd",
        "registry": registry,
        "extensions": [
            {k: v for k, v in e.items() if k != "body"} for e in extensions["records"]
        ],
        "solvers": solvers,
        "documents": [
            {k: v for k, v in doc.items() if k not in ("html", "text")}
            for doc in documents.values()
        ],
        "total_counts": {
            "solvers": len(solvers),
            "parameters": sum(
                r["record_type"] == "parameter" for r in records.values()
            ),
            "solver_parameters": sum(len(c["parameters"]) for c in solvers.values()),
            "papers": sum(len(c["papers"]) for c in solvers.values()),
            "documents": len(documents),
            "nodes": len(nodes),
            "edges": len(graph["edges"]),
            "records": len(records),
        },
        "aliases": aliases,
        "source_lock_sha256": sha(ROOT / "manifests/source-lock.json"),
    }
    # Legacy fields are explicitly scoped compatibility data, never the global UI context.
    for key in (
        "parameters",
        "model_inputs",
        "claims",
        "mappings",
        "diagnostics",
        "papers",
        "experiments",
        "counts",
    ):
        catalog[key] = solvers["vbd"][key]
    destination = ROOT / "knowledge/builds" / build_id
    if destination.exists():
        manifest = read(str((destination / "manifest.json").relative_to(ROOT)))
        if manifest["input_hashes"] != hashes or any(
            sha(destination / name) != value
            for name, value in manifest["files"].items()
        ):
            raise ValueError(
                "Existing immutable snapshot failed verification: " + build_id
            )
        catalog = read(str((destination / "catalog.json").relative_to(ROOT)))
        pointer = {
            "build_id": build_id,
            "path": destination.relative_to(ROOT).as_posix(),
            "manifest_sha256": sha(destination / "manifest.json"),
        }
        temporary = ROOT / "knowledge/current.tmp"
        write(temporary, pointer)
        temporary.replace(ROOT / "knowledge/current.json")
        for name in ("catalog.json", "documents.json", "graph.json"):
            shutil.copyfile(destination / name, ROOT / "site/dist" / name)
        shutil.copyfile(
            destination / "knowledge.sqlite", ROOT / "site/data/site.sqlite"
        )
        print(
            json.dumps(
                {
                    "build_id": build_id,
                    "reused": True,
                    **catalog["total_counts"],
                    "aliases": len(aliases),
                }
            )
        )
        return
    final_destination = destination
    destination = ROOT / "knowledge/staging" / (build_id + "-" + uuid.uuid4().hex)
    destination.mkdir(parents=True)
    write(destination / "catalog.json", catalog)
    write(destination / "records.json", records)
    write(destination / "graph.json", graph)
    write(destination / "documents.json", documents)
    database = destination / "knowledge.sqlite"
    if database.exists():
        database.unlink()
    with closing(sqlite3.connect(database)) as con:
        con.executescript(
            "CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE records(id TEXT PRIMARY KEY,kind TEXT,title TEXT,summary TEXT,route TEXT,tokens TEXT,solver TEXT,domain TEXT,stages TEXT,record_scope TEXT); CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED,tokens);"
        )
        rows = []
        search_rows = []
        for record in records.values():
            r = record
            scope = r["owner_solver"] or "shared"
            search_text = " ".join(
                [r["id"], r["title"], r["summary"], r["body"], r["owner_module"]]
            )
            # Long concept explanations cover several topics. Index overlapping
            # passages so adding a section does not dilute an earlier passage's
            # BM25 score. Keep the complete body in records/documents; other
            # record types retain their original one-row lexical index.
            body = r["body"]
            fragments = (
                [body]
                if r["record_type"] != "concept" or len(body) <= 1600
                else [body[i : i + 1600] for i in range(0, len(body), 1440)]
            )
            for fragment in fragments:
                fragment_text = " ".join(
                    [r["id"], r["title"], r["summary"], fragment, r["owner_module"]]
                )
                search_rows.append((r["id"], " ".join(tokens(fragment_text))))
            rows.append(
                (
                    r["id"],
                    r["record_type"],
                    r["title"],
                    r["summary"][:500],
                    r["route"],
                    " ".join(tokens(search_text)),
                    scope,
                    r["domain"],
                    json.dumps(r["stages"]),
                    r["record_scope"],
                )
            )
        con.executemany("INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
        con.executemany("INSERT INTO search VALUES (?,?)", search_rows)
        con.execute("INSERT INTO meta VALUES (?,?)", ("build_id", build_id))
        con.commit()
    files = {
        p.name: sha(p)
        for p in destination.iterdir()
        if p.is_file() and p.name != "manifest.json"
    }
    manifest = {
        "build_id": build_id,
        "version": VERSION,
        "commit": COMMIT,
        "files": files,
        "source_lock_sha256": catalog["source_lock_sha256"],
        "input_hashes": hashes,
        "programs": programs,
    }
    write(destination / "manifest.json", manifest)
    promote(destination, final_destination)
    destination = final_destination
    database = destination / "knowledge.sqlite"
    pointer = {
        "build_id": build_id,
        "path": destination.relative_to(ROOT).as_posix(),
        "manifest_sha256": sha(destination / "manifest.json"),
    }
    temporary = ROOT / "knowledge/current.tmp"
    write(temporary, pointer)
    temporary.replace(ROOT / "knowledge/current.json")
    # Compatibility mirrors for existing readers are updated only after the canonical snapshot is complete.
    for name in ("catalog.json", "documents.json", "graph.json"):
        shutil.copyfile(destination / name, ROOT / "site/dist" / name)
    shutil.copyfile(database, ROOT / "site/data/site.sqlite")
    print(
        json.dumps(
            {"build_id": build_id, **catalog["total_counts"], "aliases": len(aliases)}
        )
    )


if __name__ == "__main__":
    main()
