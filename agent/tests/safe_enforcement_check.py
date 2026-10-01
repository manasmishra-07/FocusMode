"""Native continuous-enforcement test; can touch ONLY its disposable Tk window.

The test changes that window's reported process identity to an ordinary test app
so production's Python-helper protection remains intact. All Win32 calls are real.
"""
import ctypes
import queue
import sys
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from focus_agent.storage import Store
from focus_agent.windows import WindowsAdapter
from focus_agent.controller import Controller


def run():
    root = tk.Tk()
    root.title("Focus Mode disposable enforcement test")
    root.geometry("420x180+120+120")
    tk.Label(root, text="Only this test window will be minimized and restored.").pack(pady=60)
    root.update()
    user32 = ctypes.WinDLL("user32")
    user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.GetAncestor.restype = ctypes.c_void_p
    hwnd = int(user32.GetAncestor(root.winfo_id(), 2))
    results = queue.Queue()

    class TestAdapter(WindowsAdapter):
        def identity(self, candidate):
            identity = super().identity(candidate)
            if identity and int(candidate) == hwnd:
                identity = {**identity, "pid": -1, "path": r"C:\FocusModeTest\disposable.exe"}
            return identity

    def worker():
        try:
            with tempfile.TemporaryDirectory() as directory:
                store = Store(directory)
                adapter = TestAdapter(store, only_hwnd=hwnd)
                now = [1000]
                controller = Controller(adapter, store, lambda: now[0])
                try:
                    # Allowed window stays usable through repeated ticks.
                    controller.enter_focus({"durationMin": 1, "confirmed": True, "apps": ["disposable.exe"]})
                    controller.tick()
                    assert not adapter.u.IsIconic(hwnd)
                    assert not store.get("windows", [])
                    controller.exit_focus()
                    # Removing that allow-list entry makes the same window a distraction.
                    controller.enter_focus({"durationMin": 1, "confirmed": True, "apps": []})
                    assert adapter.u.IsIconic(hwnd)
                    original = store.get("windows")[0]
                    adapter.u.ShowWindowAsync(hwnd, 9)
                    time.sleep(0.3)
                    assert not adapter.u.IsIconic(hwnd)
                    controller.tick()
                    assert adapter.u.IsIconic(hwnd), "Reopened distraction was not minimized"
                    assert store.get("windows") == [original], "Original placement overwritten"
                    controller.exit_focus()
                    time.sleep(0.3)
                    assert not adapter.u.IsIconic(hwnd)
                    controller.tick()
                    assert not adapter.u.IsIconic(hwnd), "Enforcement continued after End"
                    controller.enter_focus({"durationMin": 1, "confirmed": True, "apps": []})
                    now[0] += 61
                    controller.tick()
                    time.sleep(0.3)
                    assert not adapter.u.IsIconic(hwnd)
                    assert controller.session is None
                    assert store.get("windows") == []
                    # A window that becomes eligible AFTER activation is journalled too.
                    adapter.u.ShowWindowAsync(hwnd, 6)
                    time.sleep(0.3)
                    controller.enter_focus({"durationMin": 1, "confirmed": True, "apps": []})
                    assert store.get("windows") == []
                    adapter.u.ShowWindowAsync(hwnd, 9)
                    time.sleep(0.3)
                    controller.tick()
                    assert adapter.u.IsIconic(hwnd)
                    assert len(store.get("windows")) == 1
                    controller.exit_focus()
                    time.sleep(0.3)
                    assert not adapter.u.IsIconic(hwnd)
                finally:
                    adapter.exit_focus("test_cleanup")
                    store.db.close()
            results.put(None)
        except BaseException as error:
            results.put(error)

    outcome = []
    def poll():
        try:
            outcome.append(results.get_nowait())
            root.destroy()
        except queue.Empty:
            root.after(50, poll)

    threading.Thread(target=worker, daemon=True).start()
    root.after(50, poll)
    root.mainloop()
    if not outcome or outcome[0] is not None:
        raise RuntimeError(f"Native test failed: {outcome}")
    print("PASS: allowed app preserved; reopened and newly eligible distractions minimized; original placement retained; manual and timed end restore; enforcement stops.")


if __name__ == "__main__":
    run()
