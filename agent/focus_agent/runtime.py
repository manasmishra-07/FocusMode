import asyncio
import os
import socket
import ssl
import time
from pathlib import Path
from websockets.asyncio.server import serve
from .storage import Store
from .api import API, Revoked
from .pairing import Pairing
from .controller import Controller
from .windows import WindowsAdapter, MockAdapter
from .schedules import Scheduler
from .protocol import Protocol


class Runtime:
    def __init__(self, ui_queue, commands, data_dir, mode):
        self.ui_queue = ui_queue
        self.commands = commands
        self.data_dir = data_dir
        self.mode = mode
        self.clients = set()
        self.running = True

    def notice(self, text):
        self.ui_queue.put({"notice": text})

    def state(self):
        return {
            **self.controller.get_state(),
            "pairing": "PAIRED" if self.credentials else "UNPAIRED",
            "deviceId": self.credentials["device_id"] if self.credentials else None,
            "name": self.name,
            "apps": self.config.get("apps", []),
            "sync": self.sync,
            "pending_events": len(self.store.pending()),
            "scheduled_pending": bool(self.scheduler.pending),
        }

    async def revoke(self, local=False):
        self.scheduler.cancel()
        self.controller.exit_focus("unpaired")
        if local:
            try:
                for eid, event in self.store.pending():
                    if event.get("local_device_id") == self.credentials["device_id"]:
                        await asyncio.to_thread(self.api.upload, event)
                        self.store.ack(eid)
                await asyncio.to_thread(self.api.request, "DELETE", "/agent/config")
            except Exception:
                self.notice(
                    "Local access removed. Backend revocation could not be confirmed; revoke the device in the dashboard."
                )
        self.store.save_credentials(None)
        self.credentials = None
        self.api.credentials = None
        self.config = {}
        for client in list(self.clients):
            await client.close()
        self.pairing.rotate()

    async def sync_loop(self):
        while self.running:
            if self.credentials:
                try:
                    self.config = await asyncio.to_thread(self.api.config)
                    for eid, event in self.store.pending():
                        if (
                            event.get("local_device_id")
                            != self.credentials["device_id"]
                        ):
                            continue
                        await asyncio.to_thread(self.api.upload, event)
                        self.store.ack(eid)
                    self.sync = "Synced"
                except Revoked:
                    await self.revoke()
                    self.sync = "Revoked — pair again"
                except Exception:
                    self.sync = "Offline — events queued"
            await asyncio.sleep(5)

    async def run(self):
        # Bind before recovery: a second instance must not restore the first one's windows.
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(("127.0.0.1", int(os.getenv("AGENT_PORT", "4545"))))
        listener.listen()
        listener.setblocking(False)
        self.store = Store(self.data_dir)
        self.name = socket.gethostname()
        self.credentials = self.store.credentials()
        self.api = API(os.getenv("API_URL", "http://127.0.0.1:8000/api/v1"))
        self.api.credentials = self.credentials
        self.pairing = Pairing()
        self.config = {}
        self.sync = "Waiting for backend"
        if self.mode == 'mock' and self.store.get('windows', []):
            WindowsAdapter(self.store).exit_focus('recovery_before_mock')
        self.controller = Controller(
            (
                WindowsAdapter(self.store)
                if self.mode == "windows"
                else MockAdapter(self.store)
            ),
            self.store,
        )
        self.scheduler = Scheduler(self.store, self.controller, self.notice)
        protocol = Protocol(self)
        tls = None
        if os.getenv("AGENT_TLS_CERT"):
            tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.load_cert_chain(
                os.environ["AGENT_TLS_CERT"], os.environ["AGENT_TLS_KEY"]
            )
        origins = os.getenv(
            "ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
        ).split(",")
        try:
            async with serve(
                protocol.handle,
                sock=listener,
                origins=origins,
                max_size=8192,
                max_queue=8,
                ssl=tls,
            ):
                sync = asyncio.create_task(self.sync_loop())
                previous_focus = self.controller.get_state()["focus"]
                try:
                    while self.running:
                        while not self.commands.empty():
                            command = self.commands.get_nowait()
                            if command == "stop":
                                self.scheduler.cancel()
                                self.controller.exit_focus("local_stop")
                            elif command == "quit":
                                self.running = False
                            elif command == "code" and not self.credentials:
                                self.pairing.rotate()
                            elif command == "unpair":
                                await self.revoke(local=True)
                        self.controller.tick()
                        if self.credentials and self.sync == "Synced":
                            self.scheduler.tick(
                                self.config.get("schedules", []),
                                self.config.get("apps", []),
                                time.time(),
                            )
                        state = self.state()
                        message_type = "state"
                        if state["focus"] != previous_focus:
                            message_type = (
                                "focusStarted"
                                if state["focus"] == "FOCUSING"
                                else "focusEnded"
                            )
                        previous_focus = state["focus"]
                        self.ui_queue.put(
                            {
                                "state": state,
                                "code": (
                                    self.pairing.code if not self.credentials else ""
                                ),
                                "code_seconds": max(
                                    0, int(self.pairing.expires - time.monotonic())
                                ),
                            }
                        )
                        import json

                        for client in list(self.clients):
                            try:
                                await asyncio.wait_for(
                                    client.send(
                                        json.dumps(
                                            {
                                                "v": 1,
                                                "id": None,
                                                "type": message_type,
                                                "state": state,
                                            }
                                        )
                                    ),
                                    1,
                                )
                            except Exception:
                                self.clients.discard(client)
                        await asyncio.sleep(0.5)
                finally:
                    sync.cancel()
                    try:
                        await sync
                    except asyncio.CancelledError:
                        pass
        finally:
            self.controller.exit_focus("quit")
            self.store.db.close()
        self.ui_queue.put({"quit": True})
