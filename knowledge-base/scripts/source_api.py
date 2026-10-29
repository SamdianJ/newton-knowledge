"""Resolve public exports and source locations statically; never import Newton."""

from __future__ import annotations

import ast
from functools import lru_cache

from plan_p0 import SRC, exports


@lru_cache(maxsize=256)
def tree(path):
    return ast.parse((SRC / path).read_text(encoding="utf-8"))


def module_file(base):
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py").relative_to(SRC).as_posix()
    if (base / "__init__.py").is_file():
        return (base / "__init__.py").relative_to(SRC).as_posix()
    return None


def import_base(path, node):
    base = (SRC / path).parent
    for _ in range(max(0, node.level - 1)):
        base = base.parent
    if node.module:
        base = base.joinpath(*node.module.split("."))
    return base


def resolve(path, name, visited=None):
    visited = set() if visited is None else visited
    if (path, name) in visited:
        return None
    visited.add((path, name))
    nodes = list(tree(path).body)
    for node in list(nodes):
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "TYPE_CHECKING"
        ):
            nodes.extend(node.body)
    for node in nodes:
        if (
            isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return path, node
    for node in nodes:
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        base = import_base(path, node)
        for alias in node.names:
            if (alias.asname or alias.name) == name:
                direct = module_file(base)
                if direct:
                    result = resolve(direct, alias.name, visited)
                    if result:
                        return result
                nested = module_file(base / alias.name)
                if nested:
                    return nested, tree(nested)
            elif alias.name == "*":
                direct = module_file(base)
                if direct and name in exports(direct):
                    result = resolve(direct, name, visited)
                    if result:
                        return result
    # Newton's solvers module is a lazy public facade over _src.solvers.
    if path == "newton/solvers.py" and name != "experimental":
        result = resolve("newton/_src/solvers/__init__.py", name, visited)
        if result:
            return result
    for node in nodes:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                return path, node
    return None


def describe(public_name, path, node):
    if isinstance(node, ast.Module):
        kind = "module"
        line = 1
        end = len((SRC / path).read_text(encoding="utf-8").splitlines())
    else:
        kind = (
            "class"
            if isinstance(node, ast.ClassDef)
            else "function"
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            else "constant"
        )
        line = node.lineno
        end = node.end_lineno
    doc = (
        ast.get_docstring(node)
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
        else ""
    )
    signature = ""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        signature = "(" + ast.unparse(node.args) + ")"
    elif isinstance(node, ast.ClassDef):
        init = next(
            (
                n
                for n in node.body
                if isinstance(n, ast.FunctionDef) and n.name == "__init__"
            ),
            None,
        )
        if init:
            signature = "(" + ast.unparse(init.args) + ")"
    return {
        "id": "symbol:" + public_name,
        "public_name": public_name,
        "symbol_kind": kind,
        "path": path,
        "line": line,
        "end_line": end,
        "signature": signature,
        "documentation": doc or "",
        "summary": (doc or ("公开 " + kind + " 入口")).split("\n")[0],
    }


def inventory(registry):
    symbols = []
    seen = set()
    for entry in registry["entries"]:
        if entry["family"] != "api":
            continue
        module = entry["owner_module"]
        path = entry["source_path"]
        for name in entry["public_exports"]:
            if name.startswith("_"):
                continue
            result = resolve(path, name)
            if not result:
                # Keep discoverability at the verified public declaration rather than fabricate an implementation location.
                item = {
                    "id": "symbol:" + module + "." + name,
                    "public_name": module + "." + name,
                    "symbol_kind": "export",
                    "path": path,
                    "line": 1,
                    "signature": "",
                    "documentation": "公开导出；实现位置需进一步核查。",
                    "summary": "公开导出 " + name,
                    "resolution": "public_export_only",
                }
                symbols.append(item)
                continue
            impl, node = result
            full = module + "." + name
            if full not in seen:
                symbols.append(describe(full, impl, node))
                seen.add(full)
            if isinstance(node, ast.ClassDef):
                for member in node.body:
                    if isinstance(
                        member, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ) and not member.name.startswith("_"):
                        member_name = full + "." + member.name
                        if member_name not in seen:
                            symbols.append(describe(member_name, impl, member))
                            seen.add(member_name)
                    elif isinstance(
                        member, ast.ClassDef
                    ) and not member.name.startswith("_"):
                        member_name = full + "." + member.name
                        if member_name not in seen:
                            symbols.append(describe(member_name, impl, member))
                            seen.add(member_name)
                # Public arrays are declared in class/constructor annotations, not __all__.
                # The assigned None is an allocation placeholder, never a physical default.
                init = next(
                    (
                        n
                        for n in node.body
                        if isinstance(n, ast.FunctionDef) and n.name == "__init__"
                    ),
                    None,
                )
                declarations = list(node.body) + (list(ast.walk(init)) if init else [])
                strings = {
                    n.lineno: n.value.value
                    for n in declarations
                    if isinstance(n, ast.Expr)
                    and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str)
                }
                for member in declarations:
                    if not isinstance(member, ast.AnnAssign):
                        continue
                    target = member.target
                    field = (
                        target.id
                        if isinstance(target, ast.Name) and member in node.body
                        else target.attr
                        if isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                        else None
                    )
                    if not field or field.startswith("_") or full + "." + field in seen:
                        continue
                    member_name = full + "." + field
                    doc = strings.get(member.end_lineno + 1, "")
                    symbols.append(
                        {
                            "id": "symbol:" + member_name,
                            "public_name": member_name,
                            "symbol_kind": "attribute",
                            "path": impl,
                            "line": member.lineno,
                            "end_line": member.end_lineno,
                            "signature": ": " + ast.unparse(member.annotation),
                            "documentation": doc
                            + "\nDeclaration values such as None are allocation placeholders; inspect the finalized model/state for actual arrays.",
                            "summary": doc.split("\n")[0]
                            if doc
                            else "公开声明属性 " + field,
                        }
                    )
                    seen.add(member_name)
    # Experimental coupled is a named, explicitly indexed extension, not a ninth ordinary backend.
    path = "newton/_src/solvers/coupled/__init__.py"
    for name in exports(path) if (SRC / path).is_file() else []:
        result = resolve(path, name)
        if result:
            impl, node = result
            symbols.append(
                describe("newton.solvers.experimental.coupled." + name, impl, node)
            )
    return symbols


if __name__ == "__main__":
    import json
    from plan_p0 import ROOT

    data = inventory(
        json.loads((ROOT / "knowledge/registry.json").read_text(encoding="utf-8"))
    )
    target = ROOT / "indexes/public-api.json"
    target.write_text(
        json.dumps({"version": "1.7.0", "symbols": data}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "public_symbols_and_methods": len(data),
                "unresolved_exports": sum(
                    s.get("resolution") == "public_export_only" for s in data
                ),
            }
        )
    )
