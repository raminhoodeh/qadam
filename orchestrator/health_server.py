"""Tiny dependency-free HTTP health endpoint."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any, Union

HealthProvider = Callable[[], Union[dict[str, Any], Awaitable[dict[str, Any]]]]


async def serve_health(host: str, port: int, provider: HealthProvider) -> asyncio.AbstractServer:
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await reader.read(4096)
        result = provider()
        if hasattr(result, "__await__"):
            result = await result  # type: ignore[assignment]
        body = json.dumps(result, sort_keys=True).encode("utf-8")
        writer.write(
            b"HTTP/1.1 200 OK\r\n"
            + b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n".encode("ascii")
            + b"Connection: close\r\n\r\n"
            + body
        )
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    return await asyncio.start_server(handle, host, port)
