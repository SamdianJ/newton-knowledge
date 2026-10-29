"""Loopback-only, read-only website server for the Newton knowledge workspace."""

from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qs, unquote
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse, json, mimetypes, os, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = HERE / "dist"
sys.path.insert(0, str(ROOT / "scripts"))
from knowledge_store import snapshot, KnowledgeError
from build_platform import render

SERVICE = "newton-knowledge-local-v1"
ALLOWED = {
    "solvers",
    "sources",
    "manifests",
    "graph",
    "indexes",
    "agent",
    "evaluations",
    "experience",
    "experiments",
}
SUFFIXES = {
    ".html",
    ".css",
    ".js",
    ".json",
    ".md",
    ".rst",
    ".txt",
    ".py",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".svg",
    ".csv",
    ".npz",
    ".toml",
    ".yml",
    ".yaml",
    ".log",
}


def safe_file(base, relative):
    relative = unquote(relative)
    if "\\" in relative or "\x00" in relative or ":" in relative:
        raise ValueError("Invalid path")
    parts = Path(relative).parts
    if any(p.startswith(".") or p == ".." for p in parts):
        raise ValueError("Private or relative path")
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise FileNotFoundError(relative)
    return path


def search(query):
    return snapshot().search(query)["hits"]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s %s" % (self.log_date_time_string(), fmt % args), flush=True)

    def reply(self, status, body, kind="application/json; charset=utf-8", head=False):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def do_HEAD(self):
        self.handle_get(True)

    def do_GET(self):
        self.handle_get(False)

    def handle_get(self, head):
        host = self.headers.get("Host", "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            return self.reply(403, {"error": "Loopback host required"}, head=head)
        url = urlsplit(self.path)
        q = parse_qs(url.query)
        path = url.path
        try:
            if path == "/api/health":
                return self.reply(
                    200,
                    {
                        "service": SERVICE,
                        "version": "1.7.0",
                        "build_id": snapshot().build_id,
                        "pid": os.getpid(),
                        "port": self.server.server_port,
                    },
                    head=head,
                )
            if path == "/api/catalog":
                return self.reply(200, snapshot().catalog, head=head)
            if path == "/api/graph":
                return self.reply(200, snapshot().graph, head=head)
            if path == "/api/coverage":
                return self.reply(
                    200,
                    {
                        "build_id": snapshot().build_id,
                        "registry": snapshot().catalog["registry"],
                    },
                    head=head,
                )
            if path == "/api/search":
                args = {("query" if k == "q" else k): v[0] for k, v in q.items()}
                if "limit" in args:
                    args["limit"] = int(args["limit"])
                if "include_shared" in args:
                    if args["include_shared"] not in ("true", "false"):
                        raise ValueError("Invalid boolean")
                    args["include_shared"] = args["include_shared"] == "true"
                return self.reply(
                    200, snapshot().invoke("search_knowledge", args), head=head
                )
            if path == "/api/record":
                store = snapshot()
                rid = store.resolve(q.get("id", [""])[0])
                record = store.records.get(rid)
                if not record:
                    return self.reply(404, {"error": "Record not found"}, head=head)
                output = dict(record)
                output["html"] = render(
                    record["body"],
                    record.get("document_path") or "README.md",
                    store.documents,
                )[0]
                return self.reply(
                    200, {"build_id": store.build_id, "record": output}, head=head
                )
            if path == "/api/relations":
                return self.reply(
                    200,
                    snapshot().invoke(
                        "get_relations",
                        {
                            "node_id": q.get("id", [""])[0],
                            "limit": 30,
                            **({"cursor": q["cursor"][0]} if "cursor" in q else {}),
                        },
                    ),
                    head=head,
                )
            if path == "/api/document":
                store = snapshot()
                doc = store.documents.get(q.get("path", [""])[0])
                return self.reply(
                    200 if doc else 404,
                    dict(doc, build_id=store.build_id)
                    if doc
                    else {"error": "Document not found"},
                    head=head,
                )
            if path == "/api/source":
                rel = q.get("path", [""])[0]
                line = int(q.get("line", ["1"])[0])
                result = snapshot().invoke(
                    "get_source",
                    {"path": rel, "start_line": max(1, line - 20), "max_lines": 180},
                )
                result.update(
                    line=line, start=result["start_line"], end=result["end_line"]
                )
                return self.reply(200, result, head=head)
            if path.startswith("/api/"):
                return self.reply(404, {"error": "API not found"}, head=head)
            if path.startswith("/files/"):
                rel = unquote(path[len("/files/") :])
                first = rel.split("/")[0]
                if (
                    first not in ALLOWED
                    and not rel.startswith("knowledge/pages/")
                    and rel
                    not in ("README.md", "site/README.md", "mcp_service/README.md")
                ):
                    raise ValueError("Not a public knowledge file")
                p = safe_file(ROOT, rel)
                if p.suffix.lower() not in SUFFIXES:
                    raise ValueError("Unsupported file")
            else:
                p = safe_file(DIST, path.lstrip("/") or "index.html")
            data = p.read_bytes()
            kind = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            if p.suffix in (".md", ".py", ".rst", ".log", ".toml", ".yml", ".yaml"):
                kind = "text/plain"
            if kind.startswith("text/") or kind in (
                "application/javascript",
                "application/json",
            ):
                kind += "; charset=utf-8"
            if (
                p.name in ("index.html", "index-3d.html")
                and "vbd_parameter_lab" in p.parts
            ):
                # Embed a current report directly; no duplicate trajectory or report source is maintained.
                extra = ""
                if q.get("embed", [""])[0] == "1":
                    extra += "<style>header{display:none}.toolbar{top:0}main{padding:0 8px 30px}.footer{font-size:11px}</style>"
                chosen = q.get("case", [""])[0]
                if chosen:
                    value = json.dumps(chosen).replace("<", "\\u003c")
                    extra += (
                        "<script>const selectedCase=ROWS.find(r=>r.id==="
                        + value
                        + ');if(selectedCase){document.getElementById("search").value=selectedCase.parameter;filter();}</script>'
                    )
                data = data.replace(b"</body>", extra.encode("utf-8") + b"</body>")
            return self.reply(200, data, kind, head=head)
        except FileNotFoundError:
            return self.reply(404, {"error": "File not found"}, head=head)
        except KnowledgeError as exc:
            return self.reply(400, {"error": exc.code, "message": str(exc)}, head=head)
        except (ValueError, UnicodeError):
            return self.reply(400, {"error": "Invalid request"}, head=head)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            print(type(exc).__name__, str(exc), file=sys.stderr, flush=True)
            return self.reply(
                500, {"error": "Local server error; see site/run/stderr.log"}, head=head
            )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=18448)
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    run = HERE / "run"
    run.mkdir(exist_ok=True)
    (run / "server.json").write_text(
        json.dumps(
            {
                "service": SERVICE,
                "pid": os.getpid(),
                "port": args.port,
                "url": f"http://127.0.0.1:{args.port}/",
                "started_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    print(f"Local: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
