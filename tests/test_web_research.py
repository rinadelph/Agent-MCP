"""Exercise real Agent-MCP dispatch and HTTP MCP, without model inference or mocks."""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from agent_mcp.app.main_app import mcp_app_instance, mcp_call_tool_handler
from agent_mcp.core import globals as g
from agent_mcp.external.parallel_search import SEARCH_URL, USER_AGENT
from agent_mcp.tools import web_research_tools

TOKEN = "test-agent-local-token"
OTHER_TOKEN = "other-agent-local-token"


def text_content(result):
    content = result.content if hasattr(result, "content") else result
    return "\n".join(c.text for c in content if c.type == "text")


def requests(log):
    return [json.loads(line) for line in log.read_text().splitlines()]


def calls(log):
    return [
        row["body"]["params"]
        for row in requests(log)
        if (row["body"] or {}).get("method") == "tools/call"
    ]


@pytest.fixture
def configured_agent(monkeypatch, tmp_path):
    old_agents, old_admin = g.active_agents, g.admin_token
    g.active_agents = {
        TOKEN: {"agent_id": "researcher"},
        OTHER_TOKEN: {"agent_id": "other-researcher"},
    }
    g.admin_token = "test-admin-token"
    web_research_tools._research_runs.clear()
    for name in ("PARALLEL_API_KEY", "OPENAI_API_KEY", "AGENT_MCP_SEARCH_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MCP_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("AGENT_MCP_ENABLE_WEB_SEARCH", "true")
    monkeypatch.setenv("AGENT_MCP_WEB_TIMEOUT_SECONDS", "3")
    yield
    g.active_agents, g.admin_token = old_agents, old_admin
    web_research_tools._research_runs.clear()


@pytest.fixture
def parallel_server(configured_agent, monkeypatch, tmp_path):
    with socket.socket() as port_socket:
        port_socket.bind(("127.0.0.1", 0))
        port = port_socket.getsockname()[1]
    log = tmp_path / "requests.jsonl"
    log.touch()
    env = {
        **os.environ,
        "PARALLEL_FIXTURE_PORT": str(port),
        "PARALLEL_FIXTURE_LOG": str(log),
    }
    url = f"http://127.0.0.1:{port}/mcp/"
    with (tmp_path / "server.log").open("w") as output:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name("parallel_mcp_fixture.py"))],
            env=env,
            stdout=output,
            stderr=output,
        )
        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    httpx.get(url, timeout=0.2)
                    break
                except httpx.TransportError:
                    if process.poll() is not None or time.monotonic() >= deadline:
                        pytest.fail("Local MCP fixture did not start")
                    time.sleep(0.05)
            # Ignore the readiness probe when verifying project requests.
            log.write_text("")
            monkeypatch.setenv("AGENT_MCP_SEARCH_URL", url)
            yield log
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


@pytest.fixture
def connection(configured_agent):
    return create_connected_server_and_client_session(mcp_app_instance)


async def start(client, token=TOKEN, **kwargs):
    response = await client.call_tool(
        "web_research", {"token": token, "action": "start", **kwargs}
    )
    return json.loads(text_content(response))["research_id"]


def search_args(research_id, objective="Find MCP concepts", token=TOKEN):
    return {
        "token": token,
        "research_id": research_id,
        "objective": objective,
        "search_queries": ["model context protocol tools"],
    }


@pytest.mark.asyncio
async def test_anonymous_search_fetch_and_followup(connection, parallel_server):
    async with connection as client:
        available = {tool.name for tool in (await client.list_tools()).tools}
        assert {
            "web_research",
            "web_search",
            "web_fetch",
            "ask_project_rag",
        } <= available
        research_id = await start(client)
        assert str(UUID(research_id)) == research_id
        search = await client.call_tool("web_search", search_args(research_id))
        result = json.loads(text_content(search))["results"][0]
        assert result["excerpts"] == ["Tools connect agents to external information."]
        fetch = await client.call_tool(
            "web_fetch",
            {
                "token": TOKEN,
                "research_id": research_id,
                "urls": [result["url"]],
                "search_queries": ["model context protocol tools"],
            },
        )
        assert "Fetched source documentation" in text_content(fetch)
        assert result["url"] in text_content(fetch)
        await client.call_tool(
            "web_search", search_args(research_id, "Find a follow-up")
        )
        captured = calls(parallel_server)
        assert [r["name"] for r in captured] == [
            "web_search",
            "web_fetch",
            "web_search",
        ]
        assert {r["arguments"]["session_id"] for r in captured} == {research_id}
        assert captured[1]["arguments"]["full_content"] is False
        rows = requests(parallel_server)
        assert {r["path"] for r in rows} == {"/mcp/"}
        assert all(r["user_agent"] == USER_AGENT for r in rows)
        assert all(r["authorization"] is None for r in rows)
        assert TOKEN not in parallel_server.read_text()
        assert "model_name" not in parallel_server.read_text()


@pytest.mark.asyncio
async def test_independent_interleaved_runs_reset_and_close(
    connection, parallel_server
):
    async with connection as client:
        first, second = await start(client), await start(client)
        assert first != second
        await asyncio.gather(
            client.call_tool("web_search", search_args(first, "First research")),
            client.call_tool("web_search", search_args(second, "Second research")),
        )
        await client.call_tool("web_search", search_args(first, "First follow-up"))
        reset = await client.call_tool(
            "web_research", {"token": TOKEN, "action": "reset", "research_id": first}
        )
        replacement = json.loads(text_content(reset))["research_id"]
        assert replacement not in {first, second}
        denied = await client.call_tool("web_search", search_args(first))
        assert "Unknown research_id" in text_content(denied)
        await client.call_tool(
            "web_search", search_args(replacement, "New conversation")
        )
        await client.call_tool("web_search", search_args(second, "Second follow-up"))
        await client.call_tool(
            "web_research", {"token": TOKEN, "action": "close", "research_id": second}
        )
        denied = await client.call_tool("web_search", search_args(second))
        assert "Unknown research_id" in text_content(denied)
        observed = {
            c["arguments"]["objective"]: c["arguments"]["session_id"]
            for c in calls(parallel_server)
        }
        assert observed == {
            "First research": first,
            "Second research": second,
            "First follow-up": first,
            "New conversation": replacement,
            "Second follow-up": second,
        }


@pytest.mark.asyncio
async def test_permissions_and_owner_isolation(connection, parallel_server):
    async with connection as client:
        research_id = await start(client)
        for token, expected in [
            (OTHER_TOKEN, "Unknown research_id"),
            ("invalid", "Unauthorized"),
        ]:
            response = await client.call_tool(
                "web_search", search_args(research_id, token=token)
            )
            assert expected in text_content(response)
        del g.active_agents[TOKEN]
        response = await client.call_tool("web_search", search_args(research_id))
        assert "Unauthorized" in text_content(response)
        assert not calls(parallel_server)


@pytest.mark.asyncio
async def test_disable_after_import_hides_and_blocks_tools(
    connection, parallel_server, monkeypatch
):
    async with connection as client:
        research_id = await start(client)
        monkeypatch.setenv("AGENT_MCP_ENABLE_WEB_SEARCH", "false")
        available = {tool.name for tool in (await client.list_tools()).tools}
        assert not {"web_research", "web_search", "web_fetch"} & available
        assert "ask_project_rag" in available
        # Bypass client discovery to prove an explicit disabled call is still denied.
        result = await mcp_call_tool_handler("web_search", search_args(research_id))
        assert "disabled" in text_content(result)
        assert not calls(parallel_server)


@pytest.mark.asyncio
async def test_explicit_credentials_override_and_no_fallback(
    connection, parallel_server, monkeypatch
):
    async with connection as client:
        monkeypatch.setenv("PARALLEL_API_KEY", "configured-test-key")
        research_id = await start(client)
        result = await client.call_tool("web_search", search_args(research_id))
        assert "https://example.com/source" in text_content(result)
        assert all(
            r["authorization"] == "Bearer configured-test-key"
            for r in requests(parallel_server)
        )
        monkeypatch.setenv("PARALLEL_API_KEY", "invalid-test-key")
        result = await client.call_tool("web_search", search_args(research_id))
        assert "request failed" in text_content(result)
        assert "invalid-test-key" not in text_content(result)
        assert all(r["path"] == "/mcp/" for r in requests(parallel_server))
        monkeypatch.setenv("AGENT_MCP_SEARCH_URL", "not-a-url")
        before = len(requests(parallel_server))
        result = await client.call_tool("web_search", search_args(research_id))
        assert "endpoint must use HTTPS" in text_content(result)
        assert len(requests(parallel_server)) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("objective", ["quota", "error"])
async def test_service_error_and_retry_keep_identity(
    connection, parallel_server, objective
):
    async with connection as client:
        research_id = await start(client)
        result = await client.call_tool(
            "web_search", search_args(research_id, objective)
        )
        assert "Parallel error:" in text_content(result)
        assert ("quota" if objective == "quota" else "unavailable") in text_content(
            result
        )
        await client.call_tool("web_search", search_args(research_id))
        assert [c["arguments"]["session_id"] for c in calls(parallel_server)] == [
            research_id
        ] * 2


@pytest.mark.asyncio
async def test_timeout_cancellation_and_retry_keep_identity(
    connection, parallel_server, monkeypatch
):
    async with connection as client:
        research_id = await start(client)
        monkeypatch.setenv("AGENT_MCP_WEB_TIMEOUT_SECONDS", "0.2")
        response = await mcp_call_tool_handler(
            "web_search", search_args(research_id, "slow")
        )
        assert "timed out" in text_content(response)
        monkeypatch.setenv("AGENT_MCP_WEB_TIMEOUT_SECONDS", "3")
        task = asyncio.create_task(
            mcp_call_tool_handler("web_search", search_args(research_id, "slow"))
        )
        deadline = time.monotonic() + 2
        while len(calls(parallel_server)) < 2:
            assert time.monotonic() < deadline
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        result = await client.call_tool("web_search", search_args(research_id))
        assert "https://example.com/source" in text_content(result)
        assert [c["arguments"]["session_id"] for c in calls(parallel_server)] == [
            research_id
        ] * 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "values"),
    [
        ("web_search", {"objective": "", "search_queries": ["query"]}),
        ("web_search", {"objective": "Research", "search_queries": []}),
        ("web_search", {"objective": "Research", "search_queries": [False]}),
        ("web_fetch", {"urls": ["file:///etc/passwd"]}),
        ("web_fetch", {"urls": ["https://user:pass@example.com"]}),
        ("web_fetch", {"urls": ["https://example.com"], "full_content": "yes"}),
    ],
)
async def test_invalid_arguments_do_not_send_requests(
    connection, parallel_server, tool, values
):
    async with connection as client:
        research_id = await start(client)
        result = await mcp_call_tool_handler(
            tool, {"token": TOKEN, "research_id": research_id, **values}
        )
        assert "error" in text_content(result).lower()
        assert not calls(parallel_server)


def test_default_endpoint_and_existing_choices(configured_agent):
    assert SEARCH_URL == "https://search.parallel.ai/mcp"
    assert "PARALLEL_API_KEY" not in os.environ
    assert "OPENAI_API_KEY" not in os.environ
    # This integration does not change the existing project RAG registration.
    from agent_mcp.tools.registry import tool_implementations

    assert "ask_project_rag" in tool_implementations


@pytest.mark.asyncio
async def test_fetch_explicit_options_and_run_limit(connection, parallel_server):
    async with connection as client:
        run_ids = [
            await start(client) for _ in range(web_research_tools.MAX_RUNS_PER_AGENT)
        ]
        limited = await client.call_tool(
            "web_research", {"token": TOKEN, "action": "start"}
        )
        assert "Too many research runs" in text_content(limited)
        await client.call_tool(
            "web_fetch",
            {
                "token": TOKEN,
                "research_id": run_ids[0],
                "urls": ["https://example.com/source"],
                "objective": "Read the complete document",
                "full_content": True,
            },
        )
        sent = calls(parallel_server)[0]["arguments"]
        assert sent["full_content"] is True
        assert sent["objective"] == "Read the complete document"
        assert "search_queries" not in sent
        assert sent["session_id"] == run_ids[0]
        await client.call_tool(
            "web_research",
            {"token": TOKEN, "action": "close", "research_id": run_ids[0]},
        )
        assert await start(client) not in run_ids
