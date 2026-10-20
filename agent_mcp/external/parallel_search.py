"""Streamable HTTP client for Parallel Search MCP, independent of local RAG."""

import math
import os
from datetime import timedelta
from urllib.parse import urlsplit

import anyio
import mcp.types as mcp_types
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

SEARCH_URL = "https://search.parallel.ai/mcp"
USER_AGENT = "Agent-MCP (+https://github.com/rinadelph/Agent-MCP)"


def web_search_enabled() -> bool:
    return os.environ.get("AGENT_MCP_ENABLE_WEB_SEARCH", "true").lower() == "true"


async def call_parallel(
    tool: str, arguments: dict, research_id: str
) -> list[mcp_types.TextContent]:
    """Keep research identity outside the lifetime of the HTTP connection.

    The caller owns research_id. Connections may be recreated after an error or
    cancellation without changing the research run or its quota accounting.
    """
    url = os.environ.get("AGENT_MCP_SEARCH_URL", SEARCH_URL)
    parsed = urlsplit(url)
    local_http = parsed.scheme == "http" and parsed.hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or (parsed.scheme != "https" and not local_http)
    ):
        raise ValueError("Search endpoint must use HTTPS (or HTTP on loopback).")

    timeout = float(os.environ.get("AGENT_MCP_WEB_TIMEOUT_SECONDS", "30"))
    if not math.isfinite(timeout) or not 0 < timeout <= 120:
        raise ValueError("Web timeout must be greater than 0 and at most 120 seconds.")

    headers = {"User-Agent": USER_AGENT}
    key = os.environ.get("PARALLEL_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"

    # No local token, agent ID, user text-derived ID or guessed model is sent.
    payload = {**arguments, "session_id": research_id}
    with anyio.fail_after(timeout):
        async with (
            streamablehttp_client(
                url,
                headers=headers,
                # Older supported SDKs use timedelta.seconds internally. Keep
                # that transport budget positive; fail_after owns the deadline.
                timeout=timedelta(seconds=math.ceil(timeout)),
                sse_read_timeout=timedelta(seconds=math.ceil(timeout)),
            ) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.call_tool(tool, payload)

    content = [c for c in result.content if isinstance(c, mcp_types.TextContent)]
    if result.isError:
        detail = "\n".join(c.text for c in content) or "No error detail returned."
        return [mcp_types.TextContent(type="text", text=f"Parallel error: {detail}")]
    if not content:
        raise ValueError("Parallel returned no text content.")
    return content
