"""Version 1 loopback protocol. Authenticated commands are serialized by one event loop."""

import asyncio
import json
import secrets
import time
from collections import OrderedDict


class Protocol:
    def __init__(self, runtime):
        self.r = runtime
        self.cache = OrderedDict()
        self.lock = asyncio.Lock()

    async def handle(self, ws):
        authenticated = False
        last_auth = 0
        credential = None
        jwt = None
        count = 0
        window = time.monotonic()
        try:
            async for raw in ws:
                request_id = None
                try:
                    if time.monotonic() - window > 60:
                        count = 0
                        window = time.monotonic()
                    count += 1
                    if count > 120:
                        raise ValueError("Too many messages")
                    msg = json.loads(raw)
                    if (
                        not isinstance(msg, dict)
                        or msg.get("v") != 1
                        or not isinstance(msg.get("id"), str)
                        or not 1 <= len(msg["id"]) <= 80
                    ):
                        raise ValueError("Expected v:1 and a request id")
                    request_id = msg["id"]
                    kind = msg.get("type")
                    async with self.lock:
                        if kind == "pair":
                            if self.r.credentials:
                                raise ValueError(
                                    "Already paired. Unpair locally first."
                                )
                            self.r.pairing.consume(msg.get("code"))
                            jwt = msg.get("jwt")
                            if not isinstance(jwt, str) or len(jwt) > 4096:
                                raise ValueError("Login token required")
                            identity = await asyncio.to_thread(self.r.api.identity, jwt)
                            result = await asyncio.to_thread(
                                self.r.api.register,
                                jwt,
                                self.r.name,
                                self.r.controller.adapter.mode,
                            )
                            credential = secrets.token_urlsafe(32)
                            self.r.credentials = {
                                "device_id": result["device"]["id"],
                                "credential": result["credential"],
                                "owner_id": identity["id"],
                                "local_key": credential,
                            }
                            self.r.store.save_credentials(self.r.credentials)
                            self.r.api.credentials = self.r.credentials
                            self.r.store.set(
                                "device_id", self.r.credentials["device_id"]
                            )
                            authenticated = True
                            last_auth = time.monotonic()
                            self.r.clients.add(ws)
                            response = {
                                "type": "paired",
                                "credential": credential,
                                "deviceId": result["device"]["id"],
                                "state": self.r.state(),
                            }
                        elif kind == "authenticate":
                            saved = self.r.credentials
                            if (
                                not saved
                                or not isinstance(msg.get("credential"), str)
                                or not secrets.compare_digest(
                                    saved["local_key"], msg["credential"]
                                )
                            ):
                                raise ValueError(
                                    "Pair this browser with the companion first"
                                )
                            jwt = msg.get("jwt")
                            if not isinstance(jwt, str) or len(jwt) > 4096:
                                raise ValueError("Login token required")
                            identity = await asyncio.to_thread(self.r.api.identity, jwt)
                            await asyncio.to_thread(self.r.api.config)
                            if identity["id"] != saved["owner_id"]:
                                raise ValueError("Device belongs to another account")
                            authenticated = True
                            credential = msg["credential"]
                            last_auth = time.monotonic()
                            self.r.clients.add(ws)
                            response = {"type": "state", "state": self.r.state()}
                        else:
                            saved = self.r.credentials
                            if (
                                not authenticated
                                or not saved
                                or credential != saved["local_key"]
                            ):
                                raise ValueError("Authentication required")
                            # Existing focus and local stop work offline. New remote starts require recent backend validation.
                            if kind == "getState":
                                response = {"type": "state", "state": self.r.state()}
                            elif kind in ("enterFocus", "exitFocus"):
                                fingerprint = json.dumps(msg, sort_keys=True)
                                key = (saved["device_id"], request_id)
                                if key in self.cache:
                                    previous, cached = self.cache[key]
                                    if previous != fingerprint:
                                        raise ValueError(
                                            "Request id reused with different content"
                                        )
                                    await ws.send(json.dumps(cached))
                                    continue
                                if kind == "enterFocus":
                                    if time.monotonic() - last_auth > 600:
                                        raise ValueError(
                                            "Reauthenticate to start another session"
                                        )
                                    identity = await asyncio.to_thread(
                                        self.r.api.identity, jwt
                                    )
                                    if identity["id"] != saved["owner_id"]:
                                        raise ValueError("Account no longer authorized")
                                    config = await asyncio.to_thread(self.r.api.config)
                                    options = {
                                        **msg,
                                        "apps": config["apps"],
                                        "source": "MANUAL",
                                    }
                                    self.r.controller.enter_focus(options)
                                else:
                                    self.r.scheduler.cancel()
                                    self.r.controller.exit_focus("manual")
                                response = {
                                    "type": (
                                        "focusStarted"
                                        if kind == "enterFocus"
                                        else "focusEnded"
                                    ),
                                    "state": self.r.state(),
                                }
                                cached = {"v": 1, "id": request_id, **response}
                                self.cache[key] = (fingerprint, cached)
                                if len(self.cache) > 500:
                                    self.cache.popitem(last=False)
                            else:
                                raise ValueError("Unknown message type")
                    await ws.send(json.dumps({"v": 1, "id": request_id, **response}))
                except Exception as e:
                    await ws.send(
                        json.dumps(
                            {
                                "v": 1,
                                "id": request_id,
                                "type": "error",
                                "message": str(e)[:250],
                            }
                        )
                    )
        finally:
            self.r.clients.discard(ws)
