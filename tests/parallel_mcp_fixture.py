"""Real local MCP server used by the dispatcher integration tests."""

import asyncio
import json
import os

import anyio
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

mcp = FastMCP(
    "parallel-test-server",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/mcp/",
)


@mcp.tool()
async def web_search(objective: str, search_queries: list[str], session_id: str) -> str:
    if objective == "slow":
        await asyncio.sleep(10)
    if objective == "quota":
        raise ValueError(
            "Free anonymous quota exceeded. Retry later with the same session."
        )
    if objective == "error":
        raise ValueError("Search service unavailable")
    return json.dumps(
        {
            "results": [
                {
                    "title": "MCP concepts",
                    "url": "https://example.com/source",
                    "excerpts": ["Tools connect agents to external information."],
                }
            ]
        }
    )


@mcp.tool()
async def web_fetch(
    urls: list[str],
    session_id: str,
    objective: str | None = None,
    search_queries: list[str] | None = None,
    full_content: bool = False,
) -> str:
    return json.dumps(
        {"url": urls[0], "content": "# MCP concepts\nFetched source documentation."}
    )


app = mcp.streamable_http_app()


@app.middleware("http")
async def record_request(request, call_next):
    body = await request.body()
    row = {
        "path": request.url.path,
        "method": request.method,
        "user_agent": request.headers.get("user-agent"),
        "authorization": request.headers.get("authorization"),
        "body": json.loads(body) if body else None,
    }
    async with await anyio.open_file(os.environ["PARALLEL_FIXTURE_LOG"], "a") as log:
        await log.write(json.dumps(row) + "\n")
    if request.headers.get("authorization") == "Bearer invalid-test-key":
        return JSONResponse({"error": "Invalid key"}, status_code=401)
    return await call_next(request)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["PARALLEL_FIXTURE_PORT"]))
