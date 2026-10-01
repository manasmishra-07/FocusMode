"""Tkinter runs only on main thread. All tray callbacks send queue commands."""

import asyncio
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw
import pystray
from .runtime import Runtime


def launch(data_dir, mode, auto_quit_ms=None):
    failures = []
    observed_state = []
    events = queue.Queue()
    commands = queue.Queue()
    root = tk.Tk()
    root.title("Focus Mode — Companion")
    root.geometry("470x660")
    root.configure(bg="#f4f7fb")
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TLabel", background="#f4f7fb", font=("Segoe UI", 11))
    style.configure("TButton", padding=10, font=("Segoe UI", 11))
    ttk.Label(root, text="◉  Focus Mode", font=("Segoe UI", 23, "bold")).pack(
        pady=(24, 10)
    )
    ttk.Label(
        root,
        text="WINDOWS" if mode == "windows" else "MOCK MODE — no windows are changed",
        foreground="#0d766e",
    ).pack()
    device = ttk.Label(root, text="Starting companion…")
    device.pack(pady=10)
    status = ttk.Label(root, text="IDLE", font=("Segoe UI", 18, "bold"))
    status.pack()
    code = ttk.Label(root, text="", font=("Consolas", 27, "bold"))
    code.pack(pady=12)
    pairing = ttk.Label(root, text="")
    pairing.pack()
    ttk.Button(
        root, text="Generate new pairing code", command=lambda: commands.put("code")
    ).pack(pady=8)
    allow = ttk.Label(
        root,
        text="Always preserves browsers, agent and system apps",
        wraplength=420,
        justify="center",
    )
    allow.pack(pady=10)
    sync = ttk.Label(root, text="", wraplength=420)
    sync.pack()
    notice = ttk.Label(root, text="", foreground="#a24d00", wraplength=420)
    notice.pack(pady=10)
    ttk.Button(
        root,
        text="End Focus / Cancel scheduled start",
        command=lambda: commands.put("stop"),
    ).pack(fill="x", padx=35, pady=5)
    ttk.Button(
        root, text="Unpair this companion", command=lambda: commands.put("unpair")
    ).pack(fill="x", padx=35, pady=5)
    ttk.Button(root, text="Quit safely", command=lambda: commands.put("quit")).pack(
        fill="x", padx=35, pady=5
    )
    root.protocol("WM_DELETE_WINDOW", lambda: commands.put("quit"))
    icon_image = Image.new("RGB", (64, 64), "#4f46e5")
    draw = ImageDraw.Draw(icon_image)
    draw.ellipse((13, 13, 51, 51), outline="white", width=5)
    icon = pystray.Icon(
        "FocusMode",
        icon_image,
        "Focus Mode",
        pystray.Menu(
            pystray.MenuItem("Show companion", lambda: events.put({"show": True})),
            pystray.MenuItem("End Focus", lambda: commands.put("stop")),
            pystray.MenuItem("Quit safely", lambda: commands.put("quit")),
        ),
    )
    threading.Thread(target=icon.run, daemon=True).start()

    def worker():
        try:
            asyncio.run(Runtime(events, commands, data_dir, mode).run())
        except Exception as e:
            events.put({"fatal": str(e)})

    threading.Thread(target=worker, daemon=True).start()
    if auto_quit_ms:
        root.after(auto_quit_ms, lambda: commands.put("quit"))

    def poll():
        while not events.empty():
            event = events.get_nowait()
            if event.get("quit"):
                icon.stop()
                root.destroy()
                return
            if event.get("show"):
                root.deiconify()
                root.lift()
            if event.get("fatal"):
                failures.append(event["fatal"])
                if not auto_quit_ms:
                    messagebox.showerror("Companion could not start", event["fatal"])
                icon.stop()
                root.destroy()
                return
            if "notice" in event:
                notice.configure(text=event["notice"])
                root.deiconify()
                root.lift()
            if "state" in event:
                if not observed_state:
                    observed_state.append(True)
                s = event["state"]
                seconds = s["remaining"]
                device.configure(text=s["name"] + " · " + s["pairing"])
                status.configure(
                    text=(
                        f"{s['focus']}  {seconds//60:02d}:{seconds%60:02d}"
                        if s["focus"] == "FOCUSING"
                        else "Ready for your next session"
                    )
                )
                code.configure(text=event["code"] or "Paired")
                pairing.configure(
                    text=(
                        f"Code expires in {event['code_seconds']} seconds"
                        if event["code"]
                        else "Device credential protected with Windows DPAPI"
                    )
                )
                allow.configure(
                    text="Preserved: browsers, agent, system apps"
                    + ("\n" + ", ".join(s["apps"]) if s["apps"] else "")
                )
                sync.configure(
                    text=f"{s['sync']} · {s['pending_events']} queued events"
                )
                icon.title = "Focus Mode · " + s["focus"]
                if s["focus"] != "FOCUSING" and s["pending_restore"]:
                    notice.configure(
                        text="Some windows could not be restored. Retry End Focus or restore them manually."
                    )
                elif s.get("result", {}).get("error"):
                    notice.configure(text=s["result"]["error"])
                elif s["focus"] == "FOCUSING":
                    notice.configure(
                        text=(
                            "Simulation only"
                            if s["mode"] == "mock"
                            else "App enforcement active. Allowed apps remain usable."
                        )
                    )
                elif not s["scheduled_pending"]:
                    notice.configure(text="")
        root.after(200, poll)

    poll()
    root.mainloop()
    if auto_quit_ms and (failures or not observed_state):
        raise RuntimeError("; ".join(failures) or "Companion never reached ready state")
