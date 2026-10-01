"""Atomic local journal; secrets are encrypted with current-user Windows DPAPI."""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sqlite3
import uuid


def protect(data, decrypt=False):
    if os.name != "nt":
        raise RuntimeError("OS-backed credentials currently require Windows")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(Blob),
    ]
    fn.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


class Store:
    def __init__(self, directory):
        self.path = Path(directory)
        self.path.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path / "journal.sqlite3")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        self.db.commit()

    def get(self, key, default=None):
        row = self.db.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO kv VALUES (?,?)", (key, json.dumps(value))
            )

    def credentials(self):
        path = self.path / "credentials.bin"
        return json.loads(protect(path.read_bytes(), True)) if path.exists() else None

    def save_credentials(self, data):
        path = self.path / "credentials.bin"
        if data is None:
            path.unlink(missing_ok=True)
            return
        tmp = self.path / "credentials.tmp"
        tmp.write_bytes(protect(json.dumps(data).encode()))
        tmp.replace(path)

    def event(self, kind, data):
        eid = str(uuid.uuid4())
        body = {
            "event_id": eid,
            "kind": kind,
            "data": data,
            "local_device_id": self.get("device_id"),
        }
        with self.db:
            self.db.execute("INSERT INTO events VALUES (?,?)", (eid, json.dumps(body)))

    def transition(self, session, kind, data):
        """Commit event and session state together, so restart cannot lose either half."""
        eid = str(uuid.uuid4())
        body = {
            "event_id": eid,
            "kind": kind,
            "data": data,
            "local_device_id": self.get("device_id"),
        }
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO kv VALUES (?,?)",
                ("session", json.dumps(session)),
            )
            self.db.execute("INSERT INTO events VALUES (?,?)", (eid, json.dumps(body)))

    def pending(self):
        return [
            (eid, json.loads(body))
            for eid, body in self.db.execute(
                "SELECT id,body FROM events ORDER BY rowid"
            )
        ]

    def ack(self, eid):
        with self.db:
            self.db.execute("DELETE FROM events WHERE id=?", (eid,))
