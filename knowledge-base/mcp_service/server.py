"""Six schema-validated read-only MCP tools over stdio; stdout is protocol only."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import anyio
from jsonschema import Draft202012Validator
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
    ToolAnnotations,
)
from knowledge_store import KnowledgeError, snapshot

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
DESCRIPTIONS = {
    "search_knowledge": "Search Newton 1.7.0 knowledge. Filter domain, stage and solver before ranking. Follow exact read_next_call and source_next_call; cursors bind query and build. Coverage and evidence are separate.",
    "get_parameter": "Read an exact parameter/model input and its owner, declared/default resolution, source and measured experiments. Specify solver; omission retains the explicitly labeled legacy VBD default.",
    "get_experiment": "Read a saved measured experiment only in the chosen solver. Missing runs return no_measured_evidence, never substitute another solver or execute simulation.",
    "get_document": "Read any search/graph record by record_id, or a whitelisted document path. Empty arguments list documents with pagination. Text excerpts retain original line numbers and next_call.",
    "get_source": "Read source by symbol_id or a discovered repository-relative path, with pinned commit, manifest hash, exact lines and pagination. No arbitrary file access or execution.",
    "get_relations": "Read paginated one-hop edges and exact readable neighbors. Edges are associations with provenance, not inferred causal guarantees. Cursor and edge_cursor resume the same stable stream.",
}


async def list_tools(ctx, params):
    store = snapshot()
    return ListToolsResult(
        tools=[
            Tool(
                name=name,
                description=DESCRIPTIONS[name],
                inputSchema=spec["inputSchema"],
                outputSchema=spec["outputSchema"],
                annotations=ToolAnnotations(**spec["annotations"]),
            )
            for name, spec in store.contract["tools"].items()
        ]
    )


async def call_tool(ctx, params):
    store = None
    try:
        store = snapshot()
        if params.name not in store.contract["tools"]:
            raise KnowledgeError("UNKNOWN_TOOL", "Unknown read tool.")
        errors = sorted(
            Draft202012Validator(
                store.contract["tools"][params.name]["inputSchema"]
            ).iter_errors(params.arguments or {}),
            key=lambda e: str(e.path),
        )
        if errors:
            raise KnowledgeError(
                "INVALID_ARGUMENT", "; ".join(e.message for e in errors)[:1500]
            )
        result = store.invoke(params.name, params.arguments or {})
        Draft202012Validator(
            store.contract["tools"][params.name]["outputSchema"]
        ).validate(result)
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                )
            ],
            structuredContent=result,
        )
    except KnowledgeError as exc:
        result = (
            store.envelope(
                status="error", error={"code": exc.code, "message": str(exc)}
            )
            if store
            else {
                "status": "error",
                "read_only": True,
                "build_id": "unavailable",
                "error": {"code": exc.code, "message": str(exc)},
            }
        )
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                )
            ],
            structuredContent=result,
            isError=True,
        )


server = Server(
    "newton_knowledge",
    version="2.0.0",
    instructions="Read-only pinned Newton 1.7.0. Discover with search_knowledge then follow supplied exact calls. All eight solver backends are indexed; inspect coverage to distinguish explanation, task validation and measurement. Shared records retain their owner and backend applicability. Proposed diagnostics are not measured evidence. Every result carries build_id; restart pagination on STALE_CURSOR.",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
