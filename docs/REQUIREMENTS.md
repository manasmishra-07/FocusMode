# PS03 requirement traceability

Source: supplied 19-page PS3 Focus Mode PDF plus the user's pasted implementation brief. PDF instructions about publishing, repository creation and team commits are not authorization to do those actions. User-requested Django/Python choices override the PDF's stack recommendations.

Status terms: **Implemented / checked** = tested to the stated scope, **Implemented / limited verification** = source exists but broader behavior needs testing, **Documented** = design/instructions only, **Not implemented** = not claimed.

| ID / priority | Implementation | Verification / status |
|---|---|---|
| AUTH-1 P0 | Django User, JWT, BCrypt-SHA256, login/signup/logout, admin seed | Backend tests and browser login checked; token revocation/ownership tests pass |
| AGENT-1 P0 | Tkinter window, pystray icon/menu, end/quit, device/code/status | Visible mock companion launched; Windows package generated; tray interaction needs manual review |
| PAIR-1 P0 | Expiring one-time six-digit local code, verified identity, device credentials | Browser pairing checked; wrong/expired/reused/locked tests pass |
| LINK-1 P0 | Versioned authenticated loopback WebSocket, status, reconnect | Real local socket tests and browser reconnect checked; deployed HTTPS unverified |
| FOCUS-1 P0 | Native window minimization adapter, honest acknowledgement | Disposable-window native calls checked; full desktop activation not exercised |
| FOCUS-2 P0 | Identity/marker-validated restoration, local/web end, shared cleanup | Native safe-window restoration and mocked manual cleanup checked |
| FOCUS-3 P0 | Agent absolute deadline, duration picker/custom, countdown | Browser one-minute mock expiry plus deterministic timer/sleep tests checked |
| SAFE-1 P0 | Hard-coded protected set, Windows directory, editable extra allow-list | Protection/validation tests; protected helper skipped in Windows check |
| SAFE-2 P0 | Native dialog confirmation every manual session; visible status/end controls | Browser confirmation checked; no uncontrolled real focus session run |
| SESS-1 P0 | Durable agent-only start/end queue, event dedup, filtered history, actual/planned duration | Retry/analytics/filter tests; actual mock browser session persisted |
| X-PLAT-1 P1 | Windows adapter; documented macOS Accessibility/Keychain design | Windows safe-window scope checked; macOS not implemented |
| SCHED-1 P1 | Device schedules, weekdays/IANA zone, opt-in, heads-up/cancel, missed runs | Deterministic heads-up/dedup/late tests; real DST/long offline behavior not verified |
| ANALYTICS-1 P1 | Real-session totals/daily/streak/completion/best hour, admin aggregate | Backend aggregation checked; simulation excluded |
| RECONN-1 P1 | Reconnect status, durable recovery, deadline reconciliation | Socket disconnect and mock recovery/sleep tests; actual OS sleep/crash remains manual |
| BLOCK-1 P2 | Website block-list | Not implemented |
| POMO-1 P2 | Focus/break cycles, ambient sound | Not implemented |
| MULTI-1 P2 | Multiple records per account; local computer only | Basic records included; selecting/control of another machine not implemented |
| GAMIFY-1 P2 | Badges/leaderboards/goals | Not implemented |

## Required screens and extra brief requirements

| Requirement | Location | Status |
|---|---|---|
| Landing + setup/download guidance | React Landing / Devices | Implemented; no fabricated public installer link |
| Login/signup/protected routes | React Auth/App + Django auth views | Checked login, ownership, auth boundaries |
| Overview + active focus | React Dashboard/Focus | Checked desktop/mobile and live mock timer |
| Devices/pair/unpair | React Devices, backend Device, runtime revoke | Pair checked; remote revocation tested; offline revocation semantics documented |
| Protected + editable apps/presets | AllowList API and React Allowlist | Implemented; protected validation tested |
| Schedules CRUD | Schedule API and React Schedules | Implemented; device ownership and validation tested |
| Insights + session filters | Insights API and React Insights | Implemented; metric/filter tests |
| Profile/defaults/timezone/password | Me/Password API + SettingsPage | Implemented; password flow not exercised through browser |
| Admin users/presets/downloads/stats | AdminView + React Admin | Implemented; role denial tested; complete admin UI walkthrough remains manual |
| 403 / 404 | React ErrorPage | Implemented |
| Loading/empty/error/success states | useData, errors, cards, status toast | Implemented; representative browser review |
| Keyboard and responsive layout | semantic buttons/labels/native dialog + CSS | 360px/desktop reviewed; formal WCAG audit pending |
| Notifications | Stored preference; visible schedule heads-up | Partial: OS notification delivery not implemented |
| Model set | User, Device, FocusSession, AllowList, Schedule, Preset + events/missed/downloads | SQLite migrations generated and applied |
| Production config / PostgreSQL | env files, settings, DEPLOYMENT | Documented/configurable; PostgreSQL not run here |
| API errors/status/pagination/throttle | core/api.py, serializers, auth throttle | Implemented; fixed sorting; small config lists unpaginated |
| DPAPI credentials | agent/storage.py | Real current-user roundtrip tested outside sandbox |
| Single session/device + duplicate safety | Controller + protocol cache | Tests pass |
| Offline event retry + server dedup | Runtime/Store + AgentEvents | Queue persistence/dedup tested; end-to-end prolonged outage not exercised |
| Recovery write-ahead journal | WindowsAdapter + Store + Controller | Mock restart tested; native restart recovery still manual |
| Packaging | PyInstaller directory build | Generated, bundled Tcl/Tk/tzdata; clean-machine release validation pending |
| Readme/env/deps/demo/prompt log | Root + docs | Supplied |
| Teacher acceptance / remote repo / public hosting / demo recording | Human submission tasks | Not performed, no authorization inferred from PDF |

This is a functional local implementation with explicit verification limits, not a claim that every production/OS edge case is certified.
