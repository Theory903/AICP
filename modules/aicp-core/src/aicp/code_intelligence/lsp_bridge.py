import asyncio
import json
from typing import Any

from .models import LspServerConfig


class LspBridge:
    def __init__(self, config: LspServerConfig):
        self.config = config
        self._process: asyncio.subprocess.Process | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future[Any]] = {}

    async def register_client(self, language: str, config: LspServerConfig):
        self.config = config

    async def start(self):
        self._process = await asyncio.create_subprocess_exec(
            *self.config.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._reader = self._process.stdout
        self._writer = self._process.stdin

    async def start_all(self):
        await self.start()

    async def stop(self):
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None

    async def stop_all(self):
        await self.stop()

    async def _request(self, method: str, params: dict[str, Any]) -> Any:
        if not self._writer:
            return [] if method.endswith("/definition") or method.endswith("/references") else {}
        self._request_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        payload = json.dumps(message).encode("utf-8")
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode()
        self._writer.write(header + payload)
        await self._writer.drain()
        return [] if method.endswith("/definition") or method.endswith("/references") else {}

    async def get_hover(self, uri: str, line: int, character: int) -> dict:
        result = await self._request(
            "textDocument/hover",
            {"textDocument": {"uri": uri}, "position": {"line": line, "character": character}},
        )
        return result if isinstance(result, dict) else {}

    async def go_to_definition(self, language: str, uri: str, line: int, character: int):
        return await self.get_definitions(uri, line, character)

    async def find_references(self, language: str, uri: str, line: int, character: int):
        return await self.get_references(uri, line, character)

    async def get_definitions(self, uri: str, line: int, character: int) -> list[dict]:
        result = await self._request(
            "textDocument/definition",
            {"textDocument": {"uri": uri}, "position": {"line": line, "character": character}},
        )
        return result if isinstance(result, list) else ([] if not result else [result])

    async def get_references(self, uri: str, line: int, character: int) -> list[dict]:
        result = await self._request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
                "context": {"includeDeclaration": True},
            },
        )
        return result if isinstance(result, list) else ([] if not result else [result])
