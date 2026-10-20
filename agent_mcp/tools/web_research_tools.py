"""Authenticated web research through the maintained Agent-MCP dispatcher."""

import json
from urllib.parse import urlsplit
from uuid import uuid4

import mcp.types as mcp_types

from ..core.auth import verify_token
from ..external.parallel_search import call_parallel, web_search_enabled
from .registry import register_tool

# Opaque research run -> local owner token. Never use an MCP connection ID as a
# conversation ID: hosts can reuse connections across unrelated conversations.
# Runs survive reconnects, errors and cancellation, and end on close/reset/restart.
_research_runs: dict[str, str] = {}
MAX_RESEARCH_RUNS = 256
MAX_RUNS_PER_AGENT = 16


def _text(message: str) -> list[mcp_types.TextContent]:
    return [mcp_types.TextContent(type="text", text=message)]


def _authorize(arguments: dict) -> str:
    if not web_search_enabled():
        raise ValueError("Web search is disabled by AGENT_MCP_ENABLE_WEB_SEARCH.")
    token = arguments.get("token")
    if not isinstance(token, str) or not verify_token(token):
        raise ValueError("Unauthorized: Valid agent token required.")
    return token


def _owned_run(arguments: dict, token: str) -> str:
    research_id = arguments.get("research_id")
    if not isinstance(research_id, str) or _research_runs.get(research_id) != token:
        raise ValueError(
            "Unknown research_id for this agent. Start a web research run."
        )
    return research_id


def _string(value, name: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be nonempty text of at most {limit} characters.")
    return value


def _strings(value, name: str, limit: int) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= limit:
        raise ValueError(f"{name} must contain 1 to {limit} strings.")
    return [_string(item, name, 2000) for item in value]


async def web_research_tool_impl(arguments: dict) -> list[mcp_types.TextContent]:
    """The runtime creates a UUID once; related calls carry the returned handle."""
    try:
        token = _authorize(arguments)
        action = arguments.get("action")
        if action not in {"start", "reset", "close"}:
            raise ValueError("action must be start, reset or close.")
        if action != "start":
            old_id = _owned_run(arguments, token)
            del _research_runs[old_id]
            if action == "close":
                return _text("Web research run closed.")

        # Reclaim handles belonging to agents that have been terminated.
        for run_id, owner in list(_research_runs.items()):
            if not verify_token(owner):
                del _research_runs[run_id]
        if (
            len(_research_runs) >= MAX_RESEARCH_RUNS
            or sum(owner == token for owner in _research_runs.values())
            >= MAX_RUNS_PER_AGENT
        ):
            raise ValueError(
                "Too many research runs. Close a run before starting another."
            )
        research_id = str(uuid4())
        _research_runs[research_id] = token
        return _text(json.dumps({"research_id": research_id}))
    except ValueError as error:
        return _text(f"Web research error: {error}")


async def _query(arguments: dict, tool: str) -> list[mcp_types.TextContent]:
    try:
        token = _authorize(arguments)
        research_id = _owned_run(arguments, token)
        payload = {}
        if tool == "web_search" or "objective" in arguments:
            payload["objective"] = _string(
                arguments.get("objective"),
                "objective",
                200 if tool == "web_fetch" else 5000,
            )
        if tool == "web_search" or "search_queries" in arguments:
            payload["search_queries"] = _strings(
                arguments.get("search_queries"), "search_queries", 10
            )
        if tool == "web_fetch":
            urls = _strings(arguments.get("urls"), "urls", 20)
            for url in urls:
                parsed = urlsplit(url)
                if (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username is not None
                    or parsed.password is not None
                ):
                    raise ValueError("urls must be HTTP(S) URLs without credentials.")
            payload["urls"] = urls
            full_content = arguments.get("full_content", False)
            if not isinstance(full_content, bool):
                raise ValueError("full_content must be a boolean.")
            payload["full_content"] = full_content
        return await call_parallel(tool, payload, research_id)
    except ValueError as error:
        return _text(f"Web research error: {error}")
    except TimeoutError:
        return _text("Web research timed out. Retry with the same research_id.")
    except Exception:  # noqa: BLE001 - sanitize SDK/HTTP task-group errors
        # Do not echo HTTP exception messages that may contain configured secrets.
        # Cancellation is a BaseException and must propagate to the host.
        return _text(
            "Web research request failed. Check the endpoint, credentials and "
            "connectivity; retry with the same research_id."
        )


async def web_search_tool_impl(arguments: dict) -> list[mcp_types.TextContent]:
    return await _query(arguments, "web_search")


async def web_fetch_tool_impl(arguments: dict) -> list[mcp_types.TextContent]:
    return await _query(arguments, "web_fetch")


_token = {"type": "string", "description": "Your local Agent-MCP agent token."}
_research_id = {
    "type": "string",
    "description": "Handle returned by web_research. Reuse for related calls.",
}
_queries = {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 10}


def register_web_research_tools():
    # Register unconditionally so .env settings loaded during server startup are
    # respected by the handlers, rather than frozen at Python import time.
    common = {"token": _token, "research_id": _research_id}
    register_tool(
        name="web_research",
        description=(
            "Manage a web research conversation: start returns a new research_id; "
            "reset replaces an existing run for a new conversation; close releases it. "
            "Use the same ID for related web_search and web_fetch calls."
        ),
        input_schema={
            "type": "object",
            "properties": {
                **common,
                "action": {"type": "string", "enum": ["start", "reset", "close"]},
            },
            "required": ["token", "action"],
            "additionalProperties": False,
        },
        implementation=web_research_tool_impl,
        enabled=web_search_enabled,
    )
    register_tool(
        name="web_search",
        description=(
            "Search the public web with Parallel Search MCP (Fast mode without an "
            "account or API key). Start web_research first. Returns source URLs and "
            "excerpts for current development questions; local project RAG is separate."
        ),
        input_schema={
            "type": "object",
            "properties": {
                **common,
                "objective": {"type": "string", "maxLength": 5000},
                "search_queries": _queries,
            },
            "required": ["token", "research_id", "objective", "search_queries"],
            "additionalProperties": False,
        },
        implementation=web_search_tool_impl,
        enabled=web_search_enabled,
    )
    register_tool(
        name="web_fetch",
        description=(
            "Read HTTP(S) pages with Parallel Search MCP. Reuse the research_id and "
            "search_queries from web_search. Excerpts are the default; request "
            "full_content only when the complete page is needed."
        ),
        input_schema={
            "type": "object",
            "properties": {
                **common,
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 20,
                },
                "objective": {"type": "string", "maxLength": 200},
                "search_queries": _queries,
                "full_content": {"type": "boolean", "default": False},
            },
            "required": ["token", "research_id", "urls"],
            "additionalProperties": False,
        },
        implementation=web_fetch_tool_impl,
        enabled=web_search_enabled,
    )


register_web_research_tools()
