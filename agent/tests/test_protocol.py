import asyncio
import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from websockets.asyncio.server import serve
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus
from focus_agent.protocol import Protocol
from focus_agent.pairing import Pairing
from focus_agent.storage import Store
from focus_agent.controller import Controller
from focus_agent.windows import MockAdapter


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.credentials = {
            "device_id": "test-device",
            "local_key": "test-key",
            "owner_id": 1,
        }
        self.controller = Controller(MockAdapter(self.store), self.store)
        api = SimpleNamespace(
            identity=Mock(return_value={"id": 1}),
            config=Mock(return_value={"apps": []}),
        )
        self.runtime = SimpleNamespace(
            credentials=self.credentials,
            api=api,
            clients=set(),
            controller=self.controller,
            scheduler=SimpleNamespace(cancel=lambda: None),
            state=self.controller.get_state,
        )
        self.server = await serve(
            Protocol(self.runtime).handle,
            "127.0.0.1",
            0,
            origins=["http://127.0.0.1:5173"],
            max_size=8192,
        )
        self.url = f"ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}"

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()
        self.store.db.close()
        self.tmp.cleanup()

    async def exchange(self, ws, message):
        await ws.send(json.dumps(message))
        return json.loads(await ws.recv())

    async def test_auth_duplicate_ids_and_disconnect(self):
        async with connect(self.url, origin="http://127.0.0.1:5173", proxy=None) as ws:
            result = await self.exchange(
                ws,
                {
                    "v": 1,
                    "id": "1",
                    "type": "enterFocus",
                    "durationMin": 1,
                    "confirmed": True,
                },
            )
            self.assertEqual(result["type"], "error")
            result = await self.exchange(
                ws,
                {
                    "v": 1,
                    "id": "2",
                    "type": "authenticate",
                    "credential": "wrong",
                    "jwt": "test",
                },
            )
            self.assertEqual(result["type"], "error")
            result = await self.exchange(
                ws,
                {
                    "v": 1,
                    "id": "3",
                    "type": "authenticate",
                    "credential": "test-key",
                    "jwt": "test",
                },
            )
            self.assertEqual(result["type"], "state")
            command = {
                "v": 1,
                "id": "4",
                "type": "enterFocus",
                "durationMin": 1,
                "confirmed": True,
            }
            first = await self.exchange(ws, command)
            second = await self.exchange(ws, command)
            self.assertEqual(first, second)
            self.assertEqual(first["type"], "focusStarted")
            different = await self.exchange(ws, {**command, "durationMin": 2})
            self.assertEqual(different["type"], "error")
        self.assertEqual(self.controller.get_state()["focus"], "FOCUSING")
        self.controller.exit_focus("local_stop")
        self.controller.exit_focus("local_stop")
        self.assertEqual(len(self.store.pending()), 2)

    async def test_origin_rejected(self):
        with self.assertRaises(InvalidStatus):
            async with connect(
                self.url, origin="https://untrusted.invalid", proxy=None
            ):
                pass

    async def test_schema_validation(self):
        async with connect(self.url, origin="http://127.0.0.1:5173", proxy=None) as ws:
            for command in [
                [],
                {"v": 2, "id": "1"},
                {"v": 1, "id": 42},
                {"v": 1, "id": "x", "type": "arbitraryShell"},
            ]:
                self.assertEqual((await self.exchange(ws, command))["type"], "error")
