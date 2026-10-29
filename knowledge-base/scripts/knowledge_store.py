"""Read-only canonical snapshot access shared by HTTP, CLI and stdio MCP.

Snapshots are immutable. Cursors bind a query, stream and build, so rebuilding
cannot silently mix pages. Payloads stay in JSON; FTS stores only search text.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from build_index import tokens

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.7.0"
COMMIT = "7e75abe28b8d69522bc0b34837aaed2c303dff5a"
SOLVERS = (
    "vbd",
    "mujoco",
    "kamino",
    "featherstone",
    "implicit-mpm",
    "semi-implicit",
    "style3d",
    "xpbd",
)
STAGES = (
    "asset_import",
    "preprocess",
    "initialization",
    "control",
    "collision",
    "solver_step",
    "output",
)
_cached = None
_fingerprint = None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def artifact(relative):
    file = strict_path(ROOT, relative)
    viewer = os.environ.get("NEWTON_KB_SITE_URL", "http://127.0.0.1:18448").rstrip("/")
    return {
        "path": relative,
        "local_path": str(file),
        "file_uri": file.as_uri(),
        "web_url": viewer + "/files/" + relative,
    }


class KnowledgeError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def strict_path(base, value):
    if not value or any(c in value for c in ("\\", ":", "%", "\x00")):
        raise KnowledgeError("INVALID_PATH", "Use a literal repository-relative path.")
    path = Path(value)
    if path.is_absolute() or any(p.startswith(".") for p in path.parts):
        raise KnowledgeError(
            "INVALID_PATH", "Absolute, hidden and traversal paths are forbidden."
        )
    result = (base / path).resolve()
    if not result.is_relative_to(base.resolve()):
        raise KnowledgeError("INVALID_PATH", "Path leaves the permitted root.")
    return result


class Snapshot:
    def __init__(self, pointer):
        self.path = strict_path(ROOT, pointer["path"])
        manifest_path = self.path / "manifest.json"
        if digest(manifest_path) != pointer["manifest_sha256"]:
            raise KnowledgeError(
                "SNAPSHOT_INTEGRITY",
                "Snapshot manifest hash differs from current pointer.",
            )
        self.manifest = load(manifest_path)
        for relative, expected in self.manifest.get("programs", {}).items():
            if digest(strict_path(ROOT, relative)) != expected:
                raise KnowledgeError(
                    "PROGRAM_MISMATCH",
                    "Platform program changed; rebuild before reading: " + relative,
                )
        self.build_id = pointer["build_id"]
        if self.manifest["build_id"] != self.build_id:
            raise KnowledgeError("SNAPSHOT_INTEGRITY", "Build identifiers disagree.")
        for name, expected in self.manifest["files"].items():
            if digest(strict_path(self.path, name)) != expected:
                raise KnowledgeError(
                    "SNAPSHOT_INTEGRITY", "Snapshot file changed: " + name
                )
        if (
            digest(ROOT / "manifests/source-lock.json")
            != self.manifest["source_lock_sha256"]
        ):
            raise KnowledgeError(
                "SOURCE_LOCK_MISMATCH", "Source lock differs; rebuild the snapshot."
            )
        self.catalog = load(self.path / "catalog.json")
        self.records = load(self.path / "records.json")
        self.graph = load(self.path / "graph.json")
        self.documents = load(self.path / "documents.json")
        self.nodes = {n["id"]: n for n in self.graph["nodes"]}
        self.aliases = self.catalog["aliases"]
        self.source_lock = load(ROOT / "manifests/source-lock.json")
        self.contract = load(ROOT / "planning/p0/mcp-contract.json")
        if (
            digest(ROOT / "planning/p0/mcp-contract.json")
            != self.manifest["input_hashes"]["contract"]
        ):
            raise KnowledgeError(
                "CONTRACT_MISMATCH",
                "Contract differs from the published snapshot; rebuild first.",
            )
        if digest(ROOT / "manifests/experiment-programs.json") != self.manifest[
            "input_hashes"
        ].get("experiment_programs"):
            raise KnowledgeError(
                "SOURCE_LOCK_MISMATCH", "Experiment program lock differs; rebuild."
            )
        for obj in (self.catalog, self.graph):
            if obj["build_id"] != self.build_id:
                raise KnowledgeError(
                    "SNAPSHOT_INTEGRITY", "Catalog/graph build differs."
                )
        with closing(
            sqlite3.connect(
                (self.path / "knowledge.sqlite").as_uri() + "?mode=ro", uri=True
            )
        ) as con:
            if (
                con.execute("SELECT value FROM meta WHERE key='build_id'").fetchone()[0]
                != self.build_id
            ):
                raise KnowledgeError("SNAPSHOT_INTEGRITY", "Search build differs.")

    def resolve(self, rid):
        return self.aliases.get(rid, {}).get("id", rid)

    def envelope(
        self, requested=None, resolved=None, filters=None, status="ok", **values
    ):
        result = dict(
            status=status,
            version=VERSION,
            source_commit=COMMIT,
            build_id=self.build_id,
            read_only=True,
            requested_scope=requested or {},
            resolved_scope=resolved or {},
            applied_filters=filters or {},
            **values,
        )
        scope = (
            (resolved or {}).get("solver")
            or values.get("record", {}).get("owner_solver")
            or "shared"
        )
        result["solver"] = {"vbd": "VBD", "mujoco": "MuJoCo", "kamino": "Kamino"}.get(
            scope, scope
        )
        result["knowledge_built_at"] = self.catalog["built_at"]
        return result

    def cursor(self, stream, query, offset):
        raw = {
            "build": self.build_id,
            "stream": stream,
            "query": hashlib.sha256(
                json.dumps(query, sort_keys=True).encode()
            ).hexdigest(),
            "offset": offset,
        }
        return (
            base64.urlsafe_b64encode(json.dumps(raw, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )

    def offset(self, cursor, stream, query, default=0):
        if cursor is None:
            return default
        try:
            raw = json.loads(
                base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
            )
            expected = json.loads(
                base64.urlsafe_b64decode(
                    self.cursor(stream, query, 0)
                    + "=" * (-len(self.cursor(stream, query, 0)) % 4)
                )
            )
        except (ValueError, TypeError, KeyError):
            raise KnowledgeError("INVALID_CURSOR", "Malformed cursor.") from None
        if not isinstance(raw, dict):
            raise KnowledgeError("INVALID_CURSOR", "Cursor payload must be an object.")
        if raw.get("build") != self.build_id:
            raise KnowledgeError(
                "STALE_CURSOR", "Snapshot changed; restart pagination without a cursor."
            )
        if (
            raw.get("stream") != stream
            or raw.get("query") != expected["query"]
            or type(raw.get("offset")) is not int
            or raw["offset"] < 0
        ):
            raise KnowledgeError(
                "CURSOR_QUERY_MISMATCH", "Cursor does not belong to these arguments."
            )
        return raw["offset"]

    def next_call(self, record):
        rid = record["id"]
        kind = record["record_type"]
        scope = record["owner_solver"] or "shared"
        if kind in ("parameter", "model_input"):
            return {
                "tool": "get_parameter",
                "arguments": {"record_id": rid, "solver": scope},
            }
        if kind in ("lab_experiment", "experiment"):
            return {
                "tool": "get_experiment",
                "arguments": {"experiment_id": rid, "solver": scope},
            }
        if kind == "source_symbol" and record["source_refs"]:
            return {"tool": "get_source", "arguments": {"symbol_id": rid}}
        return {"tool": "get_document", "arguments": {"record_id": rid}}

    def source_call(self, ref):
        return {
            "tool": "get_source",
            "arguments": {
                "path": ref["path"],
                "start_line": ref.get("line", 1),
                "max_lines": 60,
            },
        }

    def compact(self, record):
        return {
            **{
                k: record[k]
                for k in (
                    "id",
                    "record_type",
                    "title",
                    "record_scope",
                    "owner_solver",
                    "owner_module",
                    "domain",
                    "stages",
                    "coverage",
                    "evidence_type",
                    "route",
                )
            },
            "summary": record["summary"][:100],
            "read_next_call": self.next_call(record),
            "source_next_call": self.source_call(record["source_refs"][0])
            if record["source_refs"]
            else None,
            "solver_record_id": "solver:" + record["owner_solver"]
            if record["owner_solver"]
            else None,
            "solver_next_call": {
                "tool": "get_document",
                "arguments": {"record_id": "solver:" + record["owner_solver"]},
            }
            if record["owner_solver"]
            else None,
        }

    def search(
        self,
        query,
        kind="all",
        domain="all",
        stage="all",
        solver="all",
        include_shared=False,
        limit=6,
        cursor=None,
        version=VERSION,
    ):
        if kind != "all" and kind not in {
            r["record_type"] for r in self.records.values()
        }:
            raise KnowledgeError("INVALID_ARGUMENT", "Unknown record kind: " + kind)
        filters = dict(
            kind=kind,
            domain=domain,
            stage=stage,
            solver=solver,
            include_shared=include_shared,
        )
        key = dict(query=query, **filters, limit=limit)
        offset = self.offset(cursor, "search", key)
        # Build a scoped candidate set BEFORE applying lexical scores or pagination.
        eligible = {
            rid: r
            for rid, r in self.records.items()
            if rid not in self.aliases
            and (kind == "all" or r["record_type"] == kind)
            and (domain == "all" or r["domain"] == domain)
            and (stage == "all" or stage in r["stages"])
            and (
                solver == "all"
                or (r["owner_solver"] or "shared") == solver
                or (
                    include_shared
                    and solver != "shared"
                    and r["record_scope"] == "shared"
                    and solver in r["applicable_solvers"]
                )
            )
        }
        aliases = {
            "full surface": "enable_rigid_soft_full_surface_contact",
            "full_surface": "enable_rigid_soft_full_surface_contact",
            "穿模": "contact full_surface",
            "子步": "substeps",
            "接触力": "SensorContact CONTACT_F",
            "多世界": "worlds",
            "重置": "reset",
            "可微": "differentiable Tape",
        }
        expanded = (
            query + " " + " ".join(v for k, v in aliases.items() if k in query.lower())
        )
        ts = tokens(expanded)
        scores = {}
        if ts:
            match = " OR ".join('"' + t.replace('"', '""') + '"' for t in ts)
            with closing(
                sqlite3.connect(
                    (self.path / "knowledge.sqlite").as_uri() + "?mode=ro", uri=True
                )
            ) as con:
                for rid, score in con.execute(
                    "SELECT id,bm25(search) FROM search WHERE search MATCH ?", (match,)
                ):
                    if rid in eligible:
                        # A long concept may have several indexed passages.
                        # Rank its strongest passage once, independent of SQL
                        # row order; apply record-level adjustments below once.
                        scores[rid] = min(scores.get(rid, float("inf")), float(score))
        q = query.strip().lower()
        for rid, r in eligible.items():
            name = r["title"].lower()
            ident = rid.lower()
            if q in (name, ident) or (
                len(name) > 2 and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", q)
            ):
                scores[rid] = -1000 - len(name)
            elif len(q) > 2 and q in name:
                scores[rid] = min(scores.get(rid, 0), -100)
            if rid in scores:
                if r["content_status"] == "planned":
                    scores[rid] += 50
                if r["record_type"] in ("source_symbol", "source"):
                    scores[rid] += 2
        ordered = sorted(scores, key=lambda rid: (scores[rid], rid))
        # Explicit cross-solver questions need evidence from each named owner.
        # Select each owner's strongest lexical hit before filling with the
        # remaining hits; do not let verbose records from one solver crowd out
        # another solver explicitly requested by the reader.
        named_solvers = [
            key for key in self.catalog["solvers"]
            if re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", q)
        ]
        comparison_query = bool(re.search(r"比较|对比|区别|差异|\bcompare\b|\bcomparison\b|\bversus\b|\bvs\.?", q))
        if solver == "all" and len(named_solvers) > 1 and comparison_query:
            representatives = {
                next((rid for rid in ordered if eligible[rid]["owner_solver"] == owner), None)
                for owner in named_solvers
            } - {None}
            ordered = ([rid for rid in ordered if rid in representatives]
                       + [rid for rid in ordered if rid not in representatives])
        selected = ordered[offset : offset + limit]
        hits = [self.compact(eligible[rid]) for rid in selected]
        known = (
            [
                r
                for r in self.records.values()
                if r["record_type"] == "source_symbol"
                and q in (r["id"].lower(), r["title"].lower())
                and (solver == "all" or (r["owner_solver"] or "shared") == solver)
            ]
            if not hits
            else []
        )
        status = "ok" if hits else "not_indexed" if known else "no_match"
        return self.envelope(
            {"solver": solver},
            {"solver": solver},
            filters,
            status,
            query=query,
            known_public_symbols=[self.compact(r) for r in known[:3]],
            hits=hits,
            total=len(ordered),
            next_cursor=self.cursor("search", key, offset + len(hits))
            if offset + len(hits) < len(ordered)
            else None,
            ranking="lexical relevance with explicit named-solver diversity, not confidence",
        )

    def parameter(
        self, name="", record_id="", solver="vbd", version=VERSION, legacy_default=False
    ):
        requested_solver = solver
        if not name and not record_id:
            raise KnowledgeError("MISSING_LOCATOR", "Provide name or record_id.")
        if record_id:
            target = self.records.get(self.resolve(record_id))
            if target and (target["owner_solver"] or "shared") != solver:
                raise KnowledgeError(
                    "SCOPE_CONFLICT",
                    "record_id belongs to "
                    + (target["owner_solver"] or "shared")
                    + ", not "
                    + solver,
                )
        aliases = {
            "tri_ke": ["tri_materials"],
            "tri_ka": ["tri_materials"],
            "tri_ke + tri_ka": ["tri_materials"],
            "edge_ke": ["edge_bending_properties"],
            "contact_ke": ["soft_contact_ke", "shape_material_ke"],
            "contact_mu": ["soft_contact_mu", "shape_material_mu"],
        }
        if solver == "vbd" and not record_id and name in aliases:
            results = [
                self.parameter(name=n, solver=solver, legacy_default=legacy_default)
                for n in aliases[name]
            ]
            return self.envelope(
                {"solver": solver},
                {
                    "solver": solver,
                    "scope_resolution": "legacy_default"
                    if legacy_default
                    else "explicit",
                },
                {"solver": solver},
                requested_name=name,
                resolution="explicit_component_or_group_alias",
                parameters=[r["parameter"] for r in results],
                records=[r["record"] for r in results],
                limitations=[
                    "A group experiment does not independently validate every material component."
                ],
            )
        if (
            solver == "vbd"
            and not record_id
            and (
                name
                in (
                    "full_surface",
                    "enable_rigid_soft_full_surface_contact",
                    "substeps",
                )
            )
        ):
            solver = "shared"
            if name == "full_surface":
                name = "enable_rigid_soft_full_surface_contact"
        rid = self.resolve(record_id or name)
        candidates = [
            r
            for r in self.records.values()
            if r["record_type"] in ("parameter", "model_input")
            and (r["owner_solver"] or "shared") == solver
            and (
                r["id"] == rid
                or name
                in (r["title"], r["payload"].get("name"), r["payload"].get("field"))
            )
        ]
        if not candidates and solver == "kamino" and name and not record_id:
            matches = [
                r
                for r in self.records.values()
                if r["record_type"] == "parameter"
                and r["owner_solver"] == solver
                and r["title"].endswith("." + name)
            ]
            if len(matches) > 1:
                raise KnowledgeError(
                    "AMBIGUOUS_RECORD",
                    "Use a qualified config name: "
                    + ", ".join(r["title"] for r in matches),
                )
            candidates = matches
        scope = {
            "solver": solver,
            "scope_resolution": "legacy_default" if legacy_default else "explicit",
            "parameter_owner_resolution": "shared_pipeline_or_process"
            if solver != requested_solver
            else "selected_solver",
        }
        if not candidates:
            public_class = self.catalog["solvers"].get(solver, {}).get("public_class")
            source = (
                self.records.get("symbol:" + public_class) if public_class else None
            )
            declared = False
            if source and name:
                try:
                    method = ast.parse(
                        "def constructor" + source["payload"]["signature"] + ": pass"
                    ).body[0]
                    declared = name in [
                        arg.arg for arg in method.args.args + method.args.kwonlyargs
                    ]
                except SyntaxError:
                    pass
            status = "not_indexed" if declared else "no_match"
            return self.envelope(
                {"solver": solver},
                scope,
                {"solver": solver},
                status,
                query=name or record_id,
                reason="No parameter record in this scope; this is not proof of unsupported physics.",
                known_declaration=declared,
                source_next_call=self.next_call(source) if source else None,
            )
        if len(candidates) > 1:
            raise KnowledgeError(
                "AMBIGUOUS_RECORD", "Use the exact record_id returned by search."
            )
        r = candidates[0]
        if (
            name
            and record_id
            and name
            not in (
                r["title"],
                r["payload"].get("name"),
                r["payload"].get("field"),
                r["id"],
            )
        ):
            raise KnowledgeError("RECORD_NAME_MISMATCH", "record_id and name disagree.")
        p = r["payload"]
        linked = []
        for e in p.get("experiments", []):
            item = next(
                (
                    a
                    for a in self.records.values()
                    if a["record_type"] == "lab_experiment"
                    and a["owner_solver"] == (r["owner_solver"] or "vbd")
                    and a["payload"].get("id") == e
                ),
                None,
            )
            if item:
                linked.append(self.compact(item))
        return self.envelope(
            {"solver": requested_solver},
            scope,
            {"solver": solver},
            record=self.compact(r),
            parameter=p,
            parameters=[p],
            source_refs=r["source_refs"],
            experiments=linked,
            experiment_status="measured" if linked else "no_measured_evidence",
            related_node_id=r["id"],
        )

    def experiment(
        self, experiment_id, detail="summary", solver="vbd", version=VERSION
    ):
        rid = self.resolve(experiment_id)
        candidates = [
            r
            for r in self.records.values()
            if r["record_type"] in ("lab_experiment", "experiment")
            and r["owner_solver"] == solver
            and (r["id"] == rid or r["payload"].get("id") == experiment_id)
        ]
        if not candidates:
            return self.envelope(
                {"solver": solver},
                {"solver": solver},
                {"solver": solver},
                "no_measured_evidence",
                experiment_id=experiment_id,
                reason="No saved measured run for this experiment in the selected solver.",
            )
        r = candidates[0]
        p = dict(r["payload"])
        p.pop("plot_svg", None)
        if detail == "summary":
            p.pop("initial_geometry", None)
        for variant in p.get("variants", []):
            raw = (
                ROOT / "experiments/vbd_parameter_lab" / variant["raw_file"]
                if solver == "vbd"
                else ROOT / variant["raw_file"]
            )
            if variant.get("raw_sha256") and digest(raw) != variant["raw_sha256"]:
                raise KnowledgeError(
                    "ARTIFACT_HASH_MISMATCH",
                    "Measured raw data changed since this build.",
                )
        result = self.envelope(
            {"solver": solver},
            {"solver": solver},
            {"solver": solver},
            record=self.compact(r),
            experiment=p,
            source_refs=r["source_refs"],
            detail=detail,
            scope_note="Observed only for the saved scene, configuration and runtime; not a universal tuning guarantee.",
        )
        if solver == "vbd" and r["record_type"] == "lab_experiment":
            result["artifacts"] = [
                {
                    "path": "experiments/vbd_parameter_lab/" + v["raw_file"],
                    "url": "/files/experiments/vbd_parameter_lab/" + v["raw_file"],
                    "program_sha256": v.get("program_sha256"),
                }
                for v in p["variants"]
            ]
            result["view_url"] = (
                "/files/experiments/vbd_parameter_lab/index-3d.html?case=" + p["id"]
            )
        elif r["record_type"] == "lab_experiment":
            result["artifacts"] = [
                {
                    "path": v["raw_file"],
                    "url": "/files/" + v["raw_file"],
                    "sha256": v["raw_sha256"],
                    "program_sha256": v["program_sha256"],
                }
                for v in p["variants"]
            ]
            result["view_url"] = p["viewer_url"]
            result["program_source_call"] = p["program_source_call"]
        return result

    def document(
        self,
        path="",
        record_id="",
        section="",
        start_line=1,
        max_lines=100,
        limit=50,
        cursor=None,
        include_outline=False,
        version=VERSION,
    ):
        if not path and not record_id:
            key = {"limit": limit}
            offset = self.offset(cursor, "documents", key)
            rows = sorted(
                (
                    {
                        k: v
                        for k, v in self.compact(self.records[d["record_id"]]).items()
                        if k
                        in (
                            "id",
                            "title",
                            "record_scope",
                            "owner_solver",
                            "read_next_call",
                            "coverage",
                        )
                    }
                    | {"path": d["path"]}
                    for d in self.documents.values()
                ),
                key=lambda r: r["id"],
            )
            return self.envelope(
                items=rows[offset : offset + limit],
                total=len(rows),
                next_cursor=self.cursor("documents", key, offset + limit)
                if offset + limit < len(rows)
                else None,
            )
        if cursor:
            raise KnowledgeError(
                "INVALID_ARGUMENT_COMBINATION",
                "cursor paginates document inventory; text uses start_line / next_call.",
            )
        alias = self.aliases.get(record_id, {})
        rid = (
            self.resolve(record_id)
            if record_id
            else self.documents.get(path, {}).get("record_id")
        )
        record = self.records.get(rid)
        if not record:
            return self.envelope(
                status="no_match",
                reason="No readable record or document with this identifier.",
            )
        if path and record.get("document_path") != path:
            raise KnowledgeError("RECORD_PATH_MISMATCH", "record_id and path disagree.")
        section = section or alias.get("section") or ""
        lines = record["body"].splitlines()
        start = start_line
        end = len(lines)
        if section:
            target = section.lstrip("# ").strip().lower()
            found = next(
                (
                    (i, len(m.group(1)))
                    for i, line in enumerate(lines)
                    if (m := re.match(r"^(#{1,6}) (.+)", line))
                    and (
                        m.group(2).strip().lower() == target
                        or re.sub(r"[^\w\- ]", "", m.group(2)).replace(" ", "-").lower()
                        == target
                    )
                ),
                None,
            )
            if found is None:
                return self.envelope(
                    status="no_match",
                    reason="Heading not found; request include_outline=true.",
                )
            index, depth = found
            start = max(start, index + 1)
            end = next(
                (
                    i
                    for i in range(index + 1, len(lines))
                    if (m := re.match(r"^(#{1,6}) ", lines[i]))
                    and len(m.group(1)) <= depth
                ),
                len(lines),
            )
        start = min(start, end + 1)
        stop = min(end, start + max_lines - 1)
        selected = []
        count = 0
        for line in lines[start - 1 : stop]:
            if count + len(line) + 1 > 18000:
                break
            selected.append(line)
            count += len(line) + 1
        stop = start + len(selected) - 1
        more = stop < end
        result = self.envelope(
            status="not_indexed" if record["content_status"] == "planned" else "ok",
            record=self.compact(record),
            path=record.get("document_path"),
            section=section,
            start_line=start,
            end_line=stop,
            total_lines=len(lines),
            text="\n".join(selected),
            truncated=more,
            next_call={
                "tool": "get_document",
                "arguments": {
                    "record_id": rid,
                    "section": section,
                    "start_line": stop + 1,
                    "max_lines": max_lines,
                },
            }
            if more
            else None,
            source_refs=record["source_refs"],
            metadata={
                k: v
                for k, v in record["payload"].items()
                if k
                in (
                    "scope",
                    "sha256",
                    "validated_build_id",
                    "status",
                    "support_matrix",
                    "runtime_status",
                    "parameter_ids",
                    "conditional_defaults",
                    "paper_id",
                    "paper_locator",
                    "year",
                    "doi",
                    "url",
                    "local_path",
                    "pages",
                    "sha256",
                    "role",
                    "units",
                    "default_policy",
                    "consumer",
                )
            },
            relations_next_call={
                "tool": "get_relations",
                "arguments": {"node_id": rid},
            },
        )
        if include_outline:
            result["outline"] = [
                {"line": i + 1, "heading": m.group(2), "level": len(m.group(1))}
                for i, line in enumerate(lines)
                if (m := re.match(r"^(#{1,6}) (.+)", line))
            ]
        return result

    def source(
        self,
        path="",
        symbol_id="",
        start_line=1,
        max_lines=100,
        scope="newton",
        version=VERSION,
    ):
        if symbol_id:
            rid = self.resolve(symbol_id)
            record = self.records.get(rid)
            node = self.nodes.get(rid)
            refs = (
                record["source_refs"]
                if record
                else [node["source_ref"]]
                if node and node.get("source_ref")
                else []
            )
            if not refs:
                return self.envelope(
                    status="no_match", reason="No source location for this symbol."
                )
            ref = refs[0]
            if path and path != ref["path"]:
                raise KnowledgeError(
                    "SYMBOL_PATH_MISMATCH", "symbol_id and path disagree."
                )
            path = ref["path"]
            if start_line == 1:
                start_line = ref["line"]
        if scope == "newton":
            base = ROOT / "sources/newton-v1.7.0"
            file = strict_path(base, path)
            expected = self.source_lock["files"].get(path)
            if not expected:
                raise KnowledgeError(
                    "SOURCE_NOT_LOCKED", "Path is not in the pinned source manifest."
                )
        else:
            frozen = load(ROOT / "manifests/experiment-programs.json")["files"]
            if path not in frozen:
                raise KnowledgeError(
                    "SOURCE_NOT_LOCKED",
                    "Only frozen experiment programs are readable in this scope.",
                )
            base = ROOT / (
                "experiments"
                if path.startswith(("solver_parameter_lab/", "kamino_mechanism_lab/", "kamino_pd_lab/", "mujoco_joint_contact_lab/"))
                else "experiments/vbd_parameter_lab"
            )
            file = strict_path(base, path)
            expected = frozen[path]
        actual = digest(file)
        if actual != expected:
            raise KnowledgeError(
                "SOURCE_HASH_MISMATCH",
                "Source changed since manifest; do not use this excerpt as pinned evidence.",
            )
        if file.stat().st_size > 2000000 or file.suffix not in (
            ".py",
            ".md",
            ".rst",
            ".txt",
            ".json",
            ".toml",
            ".yml",
            ".yaml",
        ):
            raise KnowledgeError(
                "UNSUPPORTED_SOURCE", "Only bounded source text can be read."
            )
        lines = file.read_text(encoding="utf-8").splitlines()
        if start_line > len(lines):
            raise KnowledgeError(
                "LINE_OUT_OF_RANGE", "Source start_line exceeds the file length."
            )
        start = start_line
        selected = []
        count = 0
        for line in lines[start - 1 : start + max_lines - 1]:
            if not selected and len(line) + 1 > 18000:
                raise KnowledgeError(
                    "LINE_TOO_LARGE", "A source line exceeds the excerpt budget."
                )
            if count + len(line) + 1 > 18000:
                break
            selected.append(line)
            count += len(line) + 1
        end = start + len(selected) - 1
        more = end < len(lines)
        return self.envelope(
            resolved={"scope": scope},
            path=path,
            symbol_id=symbol_id,
            start_line=start,
            end_line=end,
            total_lines=len(lines),
            lines=selected,
            text="\n".join(selected),
            sha256=actual,
            manifest_sha256=expected,
            verification="verified_snapshot",
            truncated=more,
            url=f"https://github.com/newton-physics/newton/blob/{COMMIT}/{path}#L{start}-L{end}"
            if scope == "newton"
            else "/files/experiments/"
            + (
                path
                if path.startswith(("solver_parameter_lab/", "kamino_mechanism_lab/", "kamino_pd_lab/", "mujoco_joint_contact_lab/"))
                else "vbd_parameter_lab/" + path
            ),
            next_call={
                "tool": "get_source",
                "arguments": {
                    "path": path,
                    "start_line": end + 1,
                    "max_lines": max_lines,
                    "scope": scope,
                },
            }
            if more
            else None,
        )

    def relations(
        self,
        node_id,
        limit=12,
        offset=0,
        cursor=None,
        edge_cursor=None,
        version=VERSION,
    ):
        rid = self.resolve(node_id)
        if rid not in self.nodes:
            return self.envelope(status="no_match", reason="Unknown graph node.")
        query = {"node_id": rid, "limit": limit}
        start = self.offset(cursor or edge_cursor, "relations", query, offset)
        if cursor and edge_cursor and cursor != edge_cursor:
            raise KnowledgeError(
                "CURSOR_QUERY_MISMATCH",
                "Node and edge cursor must identify the same page.",
            )
        edges = sorted(
            (e for e in self.graph["edges"] if rid in (e["source"], e["target"])),
            key=lambda e: (
                0
                if e["relation"] == "related_workflow"
                else 1
                if e["relation"] == "uses_public_api"
                else 2
                if e["relation"] == "supported_by"
                else 3,
                e["id"],
            ),
        )
        page = edges[start : start + limit]
        seen_before = {
            e["target"] if e["source"] == rid else e["source"] for e in edges[:start]
        }
        neighbors = []
        page_with_calls = []
        for edge in page:
            other = edge["target"] if edge["source"] == rid else edge["source"]
            record = self.records.get(other)
            if record:
                item = self.compact(record)
            else:
                node = self.nodes[other]
                ref = node.get("source_ref")
                item = {
                    "id": other,
                    "title": node["label"],
                    "record_type": node["type"],
                    "read_next_call": self.source_call(ref)
                    if ref
                    else {"tool": "get_document", "arguments": {"record_id": other}},
                }
            page_with_calls.append(
                {
                    **edge,
                    "related_node_id": other,
                    "related_title": item["title"],
                    "read_next_call": item["read_next_call"],
                }
            )
            if item["id"] not in seen_before and item["id"] not in [
                n["id"] for n in neighbors
            ]:
                neighbors.append(item)
        next_cursor = (
            self.cursor("relations", query, start + len(page))
            if start + len(page) < len(edges)
            else None
        )
        return self.envelope(
            node_id=rid,
            edges=page_with_calls,
            neighbors=neighbors,
            total_edges=len(edges),
            total_neighbors=len(
                {e["target"] if e["source"] == rid else e["source"] for e in edges}
            ),
            pagination="Synchronized stable edge stream. Neighbors are emitted on first appearance only; every edge includes the exact neighbor reader.",
            offset=start,
            next_offset=start + len(page) if next_cursor else None,
            next_cursor=next_cursor,
            edge_cursor=next_cursor,
            next_call={
                "tool": "get_relations",
                "arguments": {"node_id": rid, "limit": limit, "cursor": next_cursor},
            }
            if next_cursor
            else None,
            semantics="One hop; source-backed associations and curated mappings are not inferred causal guarantees.",
        )

    def invoke(self, name, arguments):
        if name not in self.contract["tools"]:
            raise KnowledgeError("UNKNOWN_TOOL", "Unknown read tool.")
        schema = self.contract["tools"][name]["inputSchema"]
        props = schema["properties"]
        extras = set(arguments) - set(props)
        if extras:
            raise KnowledgeError(
                "UNKNOWN_ARGUMENT",
                "Unsupported arguments: " + ", ".join(sorted(extras)),
            )
        missing = set(schema.get("required", [])) - set(arguments)
        if missing:
            raise KnowledgeError(
                "MISSING_ARGUMENT", "Missing arguments: " + ", ".join(sorted(missing))
            )
        args = {
            key: arguments.get(key, value.get("default"))
            for key, value in props.items()
            if key in arguments or "default" in value
        }
        for key, value in args.items():
            rule = props[key]
            types = rule.get("type")
            types = [types] if isinstance(types, str) else types
            if types:
                valid = any(
                    (t == "null" and value is None)
                    or (t == "string" and isinstance(value, str))
                    or (t == "boolean" and type(value) is bool)
                    or (t == "integer" and type(value) is int)
                    for t in types
                )
                if not valid:
                    raise KnowledgeError("INVALID_ARGUMENT", "Invalid type for " + key)
            if "enum" in rule and value not in rule["enum"]:
                raise KnowledgeError(
                    "INVALID_ARGUMENT", "Unknown " + key + ": " + str(value)
                )
            if isinstance(value, str) and (
                len(value) < rule.get("minLength", 0)
                or len(value) > rule.get("maxLength", 100000)
            ):
                raise KnowledgeError("INVALID_ARGUMENT", "Invalid length for " + key)
            if type(value) is int and (
                value < rule.get("minimum", value) or value > rule.get("maximum", value)
            ):
                raise KnowledgeError("INVALID_ARGUMENT", "Out of range: " + key)
        if args.get("version", VERSION) != VERSION:
            return self.envelope(
                requested={"version": args["version"]},
                status="unsupported_version",
                reason="Only the pinned Newton 1.7.0 is indexed.",
            )
        if name == "get_parameter":
            args["legacy_default"] = "solver" not in arguments
        methods = {
            "search_knowledge": self.search,
            "get_parameter": self.parameter,
            "get_experiment": self.experiment,
            "get_document": self.document,
            "get_source": self.source,
            "get_relations": self.relations,
        }
        result = methods[name](**args)
        self.compatibility(name, result)
        # Aliases repeat text in JSON. Return a shorter *complete line window*
        # with a real continuation, rather than deleting fields to meet budget.
        while (
            len(json.dumps(result, ensure_ascii=False, separators=(",", ":"))) > 32000
            and name in ("get_source", "get_document")
            and result.get("next_call")
            and args.get("max_lines", 100) > 1
        ):
            args["max_lines"] = max(1, args.get("max_lines", 100) // 2)
            result = methods[name](**args)
            self.compatibility(name, result)
        if len(json.dumps(result, ensure_ascii=False, separators=(",", ":"))) > 32000:
            raise KnowledgeError(
                "RESPONSE_BUDGET",
                "Response exceeds 32000 logical JSON characters; reduce limit/max_lines. Raw artifacts remain referenced, never silently omitted.",
            )
        return result

    def compatibility(self, name, result):
        """Preserve pre-platform output shapes without changing canonical ownership."""
        if result["status"] != "ok":
            return
        if name == "search_knowledge":
            for hit in result.get("hits", []):
                hit.update(
                    kind=hit["record_type"],
                    solver=hit["owner_solver"] or "shared",
                    next_call=hit["read_next_call"],
                )
                hit.pop("solver_record_id", None)
            result["has_more"] = bool(result.get("next_cursor"))
            if len(result.get("hits", [])) <= 5:
                for width in (60, 30, 0):
                    if (
                        len(
                            json.dumps(
                                result, ensure_ascii=False, separators=(",", ":")
                            )
                        )
                        <= 6000
                    ):
                        break
                    for hit in result["hits"]:
                        hit["summary"] = hit["summary"][:width]
        if name == "get_parameter":
            for p in result.get("parameters", []):
                record = self.records[p["id"]]
                p = p.copy()
                experiments = [
                    r
                    for r in self.records.values()
                    if r["record_type"] == "lab_experiment"
                    and r["owner_solver"] == (record["owner_solver"] or "vbd")
                    and r["payload"]["id"] in p.get("experiments", [])
                ]
                p.update(
                    name=p.get("name", p.get("field")),
                    owner=p.get("owner", "newton.Model"),
                    layer=p.get(
                        "layer",
                        "model_input"
                        if record["record_type"] == "model_input"
                        else "solver_constructor",
                    ),
                    summary=record["summary"],
                    source_refs=record["source_refs"],
                    related_node_id=record["id"],
                    declared_default=p.get("declared_default_expression"),
                    associated_experiments=[
                        {
                            "id": e["payload"]["id"],
                            "title": e["title"],
                            "next_call": self.next_call(e),
                        }
                        for e in experiments
                    ],
                )
                i = next(
                    i
                    for i, old in enumerate(result["parameters"])
                    if old["id"] == p["id"]
                )
                result["parameters"][i] = p
        if name in ("get_document", "get_source") and "text" in result:
            result["content"] = result["text"]
            result["next_start_line"] = (
                result["next_call"]["arguments"]["start_line"]
                if result.get("next_call")
                else None
            )
            if name == "get_source":
                result["matches_recorded_hash"] = (
                    result["sha256"] == result["manifest_sha256"]
                )
            else:
                r = self.records[result["record"]["id"]]
                result.update(
                    title=r["title"],
                    format="markdown",
                    sha256=hashlib.sha256(r["body"].encode()).hexdigest(),
                    sections=[
                        {"line": i + 1, "title": m.group(2), "level": len(m.group(1))}
                        for i, line in enumerate(r["body"].splitlines())
                        if (m := re.match(r"^(#{1,6}) (.+)", line))
                    ],
                )
        if name == "get_document" and "items" in result:
            result["documents"] = [
                {
                    "path": r.get("path"),
                    "title": r["title"],
                    "solver": r.get("owner_solver") or "shared",
                }
                for r in result["items"]
            ]
        if name == "get_experiment" and "experiment" in result:
            p = result["experiment"]
            result.update(
                {
                    k: v
                    for k, v in p.items()
                    if k
                    not in (
                        "variants",
                        "initial_geometry",
                        "source_refs",
                        "status",
                        "version",
                        "build_id",
                        "read_only",
                        "source_commit",
                    )
                }
            )
            if result["record"]["record_type"] != "lab_experiment":
                return
            result["variants"] = []
            for v in p.get("variants", []):
                path = (
                    "experiments/vbd_parameter_lab/" + v["raw_file"]
                    if result["record"]["owner_solver"] == "vbd"
                    else v["raw_file"]
                )
                result["variants"].append(
                    {
                        "variant": v["variant"],
                        "value": v.get("value", v["config"].get("treatment")),
                        "metrics": v["metrics"],
                        "config": v["config"],
                        "runner_sha256": v.get("program_sha256"),
                        "raw_data": artifact(path),
                    }
                )
            result["raw_artifacts"] = result.pop("artifacts", [])
            if result.get("detail") == "full":
                for variant in result["variants"]:
                    initial = next(
                        g
                        for g in p["initial_geometry"]
                        if g["variant"] == variant["variant"]
                    )
                    variant["initial_state"] = {
                        "particle_q": initial.get("particle_q", []),
                        "body_q": initial["body_q"],
                        "truncated": initial.get("truncated", False),
                        "full_geometry_artifact": initial.get(
                            "full_geometry_artifact", variant["raw_data"]["path"]
                        ),
                    }
            solver = result["record"]["owner_solver"]
            root = (
                "experiments/vbd_parameter_lab/"
                if solver == "vbd"
                else p.get("artifact_root", "experiments/solver_parameter_lab/")
            )
            curve = root + p["plot"] if solver == "vbd" else p.get("curve_file", root + p["id"] + ".svg")
            runner = p.get("runner_file", root + ("run_lab.py" if solver == "vbd" else "run_experiments.py"))
            viewer = os.environ.get(
                "NEWTON_KB_SITE_URL", "http://127.0.0.1:18448"
            ).rstrip("/")
            result["artifacts"] = {
                "curve": artifact(curve),
                "runner": artifact(runner),
                "report": artifact(
                    root + ("index-3d.html" if solver == "vbd" else "index.html")
                ),
                "viewer_url": viewer
                + "/#/solvers/"
                + solver
                + "/experiments?case="
                + p["id"],
            }


def snapshot():
    global _cached, _fingerprint
    pointer = load(ROOT / "knowledge/current.json")
    base = strict_path(ROOT, pointer["path"])
    names = (
        "manifest.json",
        "catalog.json",
        "records.json",
        "graph.json",
        "documents.json",
        "knowledge.sqlite",
    )
    paths = [base / n for n in names] + [
        ROOT / "manifests/source-lock.json",
        ROOT / "planning/p0/mcp-contract.json",
        ROOT / "manifests/experiment-programs.json",
    ]
    manifest = load(base / "manifest.json")
    paths += [ROOT / name for name in manifest.get("programs", {})]
    fingerprint = (
        pointer["build_id"],
        pointer["manifest_sha256"],
        tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in paths),
    )
    if fingerprint != _fingerprint:
        _cached = Snapshot(pointer)
        _fingerprint = fingerprint
    return _cached


def invoke(name, arguments):
    return snapshot().invoke(name, arguments)
