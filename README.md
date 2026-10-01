# Focus Mode — PS03

A React dashboard, Django API, and visible Python companion for reversible Windows focus sessions. Built in the selected **FocusMode** folder.


## Start locally (Windows PowerShell)

**Quick start in this prepared folder:** no activation is necessary. Run `./run.ps1 check`, then use three terminals for `./run.ps1 server`, `./run.ps1 client`, and `./run.ps1 agent`. The companion defaults to simulation; use `./run.ps1 agent -Real` for real Windows behavior. `./run.ps1 setup` installs dependencies and copies only missing environment files; it preserves your existing configuration.

The client now uses port 5173 strictly. If that port is occupied, stop the previous development server or deliberately run `npm run dev -- --port 5174`. Both 5173 and 5174 are supported by the default backend and agent origins; existing `.env` files must also include the origin you use. A blank `DATABASE_URL` correctly selects SQLite.

Requires Python 3.12+ with Tkinter, Node 20.19+ or 22+, and Windows for the real companion. Run these commands from this folder. No administrator rights are required.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r server\requirements.txt -r agent\requirements.txt
Copy-Item server\.env.example server\.env
Copy-Item client\.env.example client\.env
Copy-Item agent\.env.example agent\.env
.\.venv\Scripts\python.exe server\manage.py migrate
.\.venv\Scripts\python.exe server\manage.py seed_demo
Set-Location client
npm install
Set-Location ..
```

Three terminals, all starting in the project folder:

```powershell
# Terminal 1: backend
.\.venv\Scripts\python.exe server\manage.py runserver 127.0.0.1:8000
```
```powershell
# Terminal 2: dashboard
Set-Location client
npm run dev
```
```powershell
# Terminal 3: start safely in simulation mode
.\.venv\Scripts\python.exe agent\main.py --adapter mock
# After reviewing behavior, quit the mock companion and run the real adapter:
.\.venv\Scripts\python.exe agent\main.py --adapter windows
```

Open **http://127.0.0.1:5173**. Log in, open My devices, enter the six-digit code from the companion, choose allowed executables, and confirm a focus session. The agent must remain running. End Focus and Quit are available locally without the backend.

The environment used to build this project had no `python` on PATH. The existing `.venv` is already prepared here. On a fresh machine, install Python with Tcl/Tk support before the commands above.

Confirming a manual session requests browser fullscreen immediately and opens the full-page focus view. If browser permission prevents fullscreen, use **Enter fullscreen** or F11. Esc leaves fullscreen without ending the timer. Ending a session leaves fullscreen. Real mode checks eligible windows throughout the session (roughly every half-second), including newly opened and reopened distractions, and minimizes them again. Allowed apps such as Code.exe stay usable as separate desktop apps; they are not embedded in the dashboard. Browsers, agent and protected system software remain available. Simulation never minimizes real windows. Scheduled sessions cannot automatically request browser fullscreen because browsers require a user gesture.

After updating agent code: end the current session, quit the companion, then run `.\run.ps1 agent -Real` again. Refresh the dashboard. Allow-list changes apply to the next session; remove Code.exe before starting if you want VS Code treated as a distraction.

## Development accounts

| Role | Email | Password |
|---|---|---|
| User | student@demo.com | FocusDemo!2026 |
| Admin | admin@demo.com | FocusDemo!2026 |

`seed_demo` is DEBUG-only, creates accounts and a useful preset, and never creates fake focus history. It does not overwrite an existing account password. Never use these credentials in deployment. Browser verification may leave clearly labelled simulation sessions in the local database.

## What is included

- JWT login/register, refresh rotation, immediate backend access-token revocation on logout/password change, BCrypt-SHA256 password hashing, role and ownership checks.
- Responsive landing, auth, overview, active focus, devices, allowed apps, schedules, insights, profile/password, admin, 403 and 404 screens.
- Loopback-only authenticated WebSockets, expiring single-use pairing codes, attempt limits, explicit origins, bounded messages, request IDs and duplicate command protection.
- Visible Tkinter companion and tray; Windows DPAPI secrets; write-ahead recovery journal; offline event queue; real ctypes Windows adapter and an explicitly labelled mock adapter.
- Recurring timezone-aware schedules with opt-in, 15-second heads-up, local cancellation, overlap prevention and missed-run records.
- Actual/planned durations, filtered paginated history, daily chart, streak, best starting hour, completion rate and aggregate admin statistics.
- Updated Windows companion package under `agent/release-focus/FocusMode/`. Keep the whole folder together; `FocusMode.exe` needs `_internal/`. Defaults to mock. Use `FocusMode.exe --adapter windows` for real actions. The older `agent/release/` folder is obsolete.

## Tests and build

```powershell
.\.venv\Scripts\python.exe server\manage.py test core
$env:PYTHONPATH='agent'
.\.venv\Scripts\python.exe -m unittest discover -s agent\tests -v
# This only touches its own newly created test window:
.\.venv\Scripts\python.exe agent\tests\safe_windows_check.py
Set-Location client
npm run lint
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name FocusMode --paths agent --collect-all tzdata --distpath agent\release --workpath agent\build-release --specpath agent agent\main.py
```

See [verification](docs/VERIFICATION.md) for observed results and unverified scenarios. Unit tests that mock the adapter do not certify Windows behavior.

## Architecture and safety

```text
React ── JWT / HTTP ──> Django REST API ──> SQLite / PostgreSQL
  │                            ▲
  └─ authenticated loopback ─> Python companion
         WebSocket              │  outbound events/settings
                                └─ Windows adapter: minimize / restore
```

The website cannot control the OS directly. The companion validates identity through Django and keeps its backend secret encrypted with current-user Windows DPAPI. It preserves supported browsers, helper processes, the Windows directory, critical process names and user-selected executables. Unknown process identities, already-minimized windows, owned windows and windows without a minimize control are skipped. It never kills a process. Reopened eligible distractions are minimized again until End Focus; this is reversible personal focus enforcement, not an OS security boundary.

The timer uses an absolute agent-owned deadline. A closed dashboard does not end the session. Restoration checks process ID, executable path, process creation time and a window-specific marker, reducing handle-reuse risks. Journaling happens before OS changes. A crashed process cannot clean up; minimized windows remain manually usable and the next companion start attempts restoration. See [architecture](docs/ARCHITECTURE.md).

## Important limits

- Real Windows APIs passed a **single disposable-window** test. Multi-app behavior, elevated windows, multiple monitors, actual sleep/wake and crash recovery on a full desktop still require controlled manual verification.
- macOS has an adapter design, not an implementation. No Linux adapter.
- Local HTTP browser pairing/start/timer works. Public HTTPS dashboard to local companion has **not been verified**. WSS certificate hooks exist, but trusted local certificates and browser local-network permissions require deployment-specific testing. Do not disable certificate validation.
- The browser’s pairing credential lives in sessionStorage. Closing the tab loses it; pairing a fresh tab currently requires local unpair and re-pair. Reloading the same tab reconnects. The running timer remains independent.
- Revocation is observed on the next successful agent sync (normally five seconds). Offline devices cannot learn server-side revocation until connectivity returns. Local unpair takes effect immediately.
- Events from a revoked/unpaired device remain bound to that old device; they are never uploaded as a new account. They may remain unsynced after revocation.
- Schedule catch-up records up to seven days of missed occurrences after a previously running agent reconnects. It cannot reconstruct schedules it never downloaded. DST transition behavior needs further real-time testing.
- Notification preferences are stored; OS toast notifications are not implemented. The visible companion provides schedule heads-up.
- No public deployment, remote push, teacher approval or recorded demo video. P2 bonuses are not implemented.

## Documentation

- [Requirement checklist](docs/REQUIREMENTS.md)
- [REST API and local protocol](docs/API.md)
- [Agent walkthrough and viva questions](docs/AGENT_WALKTHROUGH.md)
- [Architecture, recovery and macOS approach](docs/ARCHITECTURE.md)
- [Deployment and packaging](docs/DEPLOYMENT.md)
- [Verification and manual checks](docs/VERIFICATION.md)
- [Four-minute demo script](docs/DEMO.md)
- [Prompt provenance](PROMPTS.md)


