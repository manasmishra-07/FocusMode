"""Touches ONLY a newly created disposable Tk window, never other applications.
Checks native placement/minimization/restoration and identity protections.
This is NOT a full desktop compatibility certification.
"""

import ctypes
import sys
import tempfile
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from focus_agent.storage import Store
from focus_agent.windows import WindowsAdapter, Placement


def run():
    root = tk.Tk()
    root.title("Focus Mode disposable Windows verification")
    root.geometry("420x180+120+120")
    tk.Label(
        root,
        text="Only this disposable test window will be minimized.\nIt will be restored and closed automatically.",
    ).pack(pady=45)
    directory = tempfile.TemporaryDirectory()
    store = Store(directory.name)
    adapter = WindowsAdapter(store)
    adapter.u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    adapter.u.GetAncestor.restype = ctypes.c_void_p
    outcome = []

    def verify_restored(hwnd):
        try:
            assert not adapter.u.IsIconic(hwnd), "Window was not restored"
            assert store.get("windows") == []
            outcome.append(True)
            print(
                "PASS: native minimization, identity-checked restoration, protected Python window skipped",
                flush=True,
            )
        finally:
            root.destroy()

    def restore(hwnd):
        try:
            assert adapter.u.IsIconic(hwnd), "Window was not minimized"
            assert adapter.exit_focus("safe_test")["restore_failures"] == 0
            root.after(400, lambda: verify_restored(hwnd))
        except Exception:
            adapter.exit_focus("test_error")
            root.destroy()
            raise

    def check():
        hwnd = adapter.u.GetAncestor(root.winfo_id(), 2)
        adapter.only_hwnd = int(hwnd)
        result = adapter.enter_focus({"apps": []})
        assert result["changed"] == 0, "Protected helper must be preserved"
        placement = Placement()
        placement.length = ctypes.sizeof(placement)
        assert adapter.u.GetWindowPlacement(hwnd, ctypes.byref(placement))
        record = {
            "hwnd": int(hwnd),
            "identity": adapter.identity(hwnd),
            "placement": bytes(placement).hex(),
            "marker": 123987,
        }
        store.set("windows", [record])
        assert adapter.u.SetPropW(hwnd, "FocusModeRecovery", record["marker"])
        assert adapter.u.ShowWindowAsync(hwnd, 6)
        root.after(400, lambda: restore(hwnd))

    root.after(600, check)
    try:
        root.mainloop()
    finally:
        adapter.exit_focus("test_cleanup")
        store.db.close()
        directory.cleanup()
    if not outcome:
        raise RuntimeError("Safe window test did not complete")


if __name__ == "__main__":
    run()
