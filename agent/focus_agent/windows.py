"""Conservative Win32 adapter. Never kills processes or repeatedly blocks windows."""

import ctypes as c
from ctypes import wintypes as w
import os
import time
import secrets
from .allowlist import protected


class Placement(c.Structure):
    _fields_ = [
        ("length", w.UINT),
        ("flags", w.UINT),
        ("showCmd", w.UINT),
        ("ptMinPosition", w.POINT),
        ("ptMaxPosition", w.POINT),
        ("rcNormalPosition", w.RECT),
    ]


class WindowsAdapter:
    mode = "windows"

    def __init__(self, store, only_hwnd=None):
        if os.name != "nt":
            raise RuntimeError("Windows adapter only runs on Windows")
        self.store = store
        self.only_hwnd = only_hwnd
        self.u = c.WinDLL("user32", use_last_error=True)
        self.k = c.WinDLL("kernel32", use_last_error=True)
        self.callback_type = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        signatures = {
            "EnumWindows": ([self.callback_type, w.LPARAM], w.BOOL),
            "IsWindowVisible": ([w.HWND], w.BOOL),
            "IsIconic": ([w.HWND], w.BOOL),
            "IsWindow": ([w.HWND], w.BOOL),
            "GetWindow": ([w.HWND, w.UINT], w.HWND),
            "GetWindowLongW": ([w.HWND, c.c_int], w.LONG),
            "GetWindowThreadProcessId": ([w.HWND, c.POINTER(w.DWORD)], w.DWORD),
            "GetWindowPlacement": ([w.HWND, c.POINTER(Placement)], w.BOOL),
            "SetWindowPlacement": ([w.HWND, c.POINTER(Placement)], w.BOOL),
            "ShowWindowAsync": ([w.HWND, c.c_int], w.BOOL),
            "SetPropW": ([w.HWND, w.LPCWSTR, w.HANDLE], w.BOOL),
            "GetPropW": ([w.HWND, w.LPCWSTR], w.HANDLE),
            "RemovePropW": ([w.HWND, w.LPCWSTR], w.HANDLE),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.u, name)
            fn.argtypes = args
            fn.restype = result
        for name, args, result in [
            ("OpenProcess", [w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            (
                "QueryFullProcessImageNameW",
                [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)],
                w.BOOL,
            ),
            (
                "GetProcessTimes",
                [
                    w.HANDLE,
                    c.POINTER(w.FILETIME),
                    c.POINTER(w.FILETIME),
                    c.POINTER(w.FILETIME),
                    c.POINTER(w.FILETIME),
                ],
                w.BOOL,
            ),
            ("CloseHandle", [w.HANDLE], w.BOOL),
        ]:
            fn = getattr(self.k, name)
            fn.argtypes = args
            fn.restype = result

    def identity(self, hwnd):
        pid = w.DWORD()
        self.u.GetWindowThreadProcessId(hwnd, c.byref(pid))
        handle = self.k.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return None
        try:
            path = c.create_unicode_buffer(32768)
            size = w.DWORD(len(path))
            creation, exit_time, kernel, user = (
                w.FILETIME(),
                w.FILETIME(),
                w.FILETIME(),
                w.FILETIME(),
            )
            if not self.k.QueryFullProcessImageNameW(handle, 0, path, c.byref(size)):
                return None
            if not self.k.GetProcessTimes(
                handle,
                c.byref(creation),
                c.byref(exit_time),
                c.byref(kernel),
                c.byref(user),
            ):
                return None
            return {
                "pid": pid.value,
                "path": path.value,
                "created": (creation.dwHighDateTime << 32) | creation.dwLowDateTime,
            }
        finally:
            self.k.CloseHandle(handle)

    def enter_focus(self, options):
        records = []
        skipped = 0
        errors = []

        def visit(hwnd, _):
            nonlocal skipped
            if self.only_hwnd and int(hwnd) != self.only_hwnd:
                return True
            if (
                not self.u.IsWindowVisible(hwnd)
                or self.u.IsIconic(hwnd)
                or self.u.GetWindow(hwnd, 4)
            ):
                return True
            if not self.u.GetWindowLongW(hwnd, -16) & 0x00020000:
                return True  # WS_MINIMIZEBOX
            identity = self.identity(hwnd)
            if (
                not identity
                or protected(identity["path"], options["apps"])
                or identity["pid"] == os.getpid()
            ):
                skipped += 1
                return True
            placement = Placement()
            placement.length = c.sizeof(placement)
            if not self.u.GetWindowPlacement(hwnd, c.byref(placement)):
                skipped += 1
                return True
            records.append(
                {
                    "hwnd": int(hwnd),
                    "identity": identity,
                    "placement": bytes(placement).hex(),
                    "marker": secrets.randbelow(2**30) + 1,
                }
            )
            return True

        callback = self.callback_type(visit)
        if not self.u.EnumWindows(callback, 0):
            raise RuntimeError("Unable to enumerate application windows")
        # Write-ahead journal BEFORE the first OS action. A restart can recover a partial activation.
        self.store.set("windows", records)
        for record in records:
            if self.identity(record["hwnd"]) != record["identity"]:
                continue
            if not self.u.SetPropW(
                record["hwnd"], "FocusModeRecovery", record["marker"]
            ):
                errors.append("Could not mark a window for safe restoration")
                continue
            if not self.u.ShowWindowAsync(record["hwnd"], 6):
                errors.append("A window could not be minimized")
        time.sleep(0.2)
        for record in records:
            if (
                self.identity(record["hwnd"]) == record["identity"]
                and self.u.GetPropW(record["hwnd"], "FocusModeRecovery")
                == record["marker"]
                and not self.u.IsIconic(record["hwnd"])
            ):
                errors.append("A window did not acknowledge minimisation")
        if errors:
            self.exit_focus("activation_failed")
            raise RuntimeError("; ".join(errors))
        return {"changed": len(records), "skipped": skipped}

    def exit_focus(self, reason):
        pending = []
        for record in self.store.get("windows", []):
            hwnd = record["hwnd"]
            if not self.u.IsWindow(hwnd) or self.identity(hwnd) != record["identity"]:
                continue
            if self.u.GetPropW(hwnd, "FocusModeRecovery") != record.get("marker"):
                continue
            placement = Placement.from_buffer_copy(bytes.fromhex(record["placement"]))
            placement.length = c.sizeof(placement)
            if not self.u.SetWindowPlacement(hwnd, c.byref(placement)):
                pending.append(record)
            else:
                self.u.RemovePropW(hwnd, "FocusModeRecovery")
        self.store.set("windows", pending)
        return {"restore_failures": len(pending)}

    def get_state(self):
        return {
            "mode": self.mode,
            "pending_restore": len(self.store.get("windows", [])),
        }


class MockAdapter:
    mode = "mock"

    def __init__(self, store):
        self.store = store

    def enter_focus(self, options):
        return {"changed": 0, "skipped": 0}

    def exit_focus(self, reason):
        return {"restore_failures": 0}

    def get_state(self):
        return {"mode": "mock", "pending_restore": len(self.store.get('windows', []))}
