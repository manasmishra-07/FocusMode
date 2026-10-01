# Architecture and safety

## Ownership

React owns presentation and intent. Django owns accounts, permissions, persistent device records, settings and history. The companion owns live state, timers, OS actions and recovery. Django has no endpoint that initiates OS actions, and the companion has no arbitrary shell endpoint.

The explicit `mock` adapter provides integration behavior without touching windows. `windows` uses ctypes with pointer-safe Win32 signatures. P0 platform behavior is Windows; macOS is a design only.

## Focus transaction

1. Confirm duration and preserved apps in the dashboard. Pairing and live connection must already be established.
2. Validate identity/credential/config and reject overlapping sessions.
3. Save a provisional local session. Enumerate only eligible visible, unowned top-level windows with a minimize control; skip minimized, protected or unidentifiable windows.
4. GetWindowPlacement captures each original placement. Commit the journal before changes. Set a unique window property, then request minimization through ShowWindowAsync. Verify IsIconic after a short acknowledgement interval.
5. If any request fails, restore candidates and report the error. Otherwise atomically commit activated session plus started event.
6. A half-second loop checks the absolute deadline. Manual stop, timer, quit, unpair and restart share controller cleanup.
7. Restore only identity-matching windows with the expected marker; remove markers on success. Retain failed restoration records for retry and show a warning. Atomically queue ended event and clear the session.

Process identity = PID + executable path + process creation time. A per-window property also protects against HWND reuse within the same process. The journal stores handles/placement/process identity locally; no window titles are read or uploaded.

Windows are minimized once, not continually policed. Users may reopen apps at any time. No process termination, global keyboard capture, registry policy, hosts-file edit, auto-start installation or persistent restriction is used.

## Failure behavior

Closing the browser has no timer effect. After sleep, wall-clock deadline reconciliation ends expired focus. A system-clock change can shift expiry; a monotonic-vs-wall-clock reconciliation policy is a future hardening item.

A crash cannot perform cleanup. Windows remain ordinary minimized applications, available from the taskbar. Restart loads the durable journal and attempts restoration. Unactivated provisional sessions are discarded after recovery; activated sessions queue a cancelled end. Abrupt OS shutdown may destroy windows entirely; identity checks then skip them. Two instances cannot share the port: the runtime binds exclusively before touching recovery state.

SQLite commits event and state transitions atomically. Outbound events are FIFO, uploaded only by the agent; backend event UUIDs deduplicate retries. Events are locally bound to their original device ID, preventing old events from leaking into a newly paired account. Revoked device events may remain unsynced; they are not silently reassigned. No window inventory is sent to Django.

## Credentials

DPAPI encrypts device/backend and local socket credentials for the current Windows user. The randomly generated pairing code expires and locks after five failed attempts. In-memory plaintext exists only for local display and entered-code comparison; the backend never stores the code. The browser local credential is per-tab sessionStorage. An XSS could access browser tokens; production needs strict CSP and careful dependency review. The agent's backend credential never enters the browser.

The API URL is fixed by local configuration, not supplied in socket messages. Non-loopback HTTP backend URLs are rejected; remote configuration requires HTTPS. Explicit WebSocket Origin validation, random credentials, JWT identity verification and loopback binding provide separate defenses. A compromised local user process is outside this threat model.

## Schedules

Authorized config is polled every five seconds. Monday=0; IANA timezone IDs use zoneinfo/tzdata. The agent persists evaluated occurrence keys and last check time. A timely occurrence gets a 15-second visible heads-up; local End Focus cancels it. Disabled, delayed or overlapping starts become missed events. On reconnection, at most seven prior days are reconciled without retroactively forcing focus. Unknown never-downloaded schedules cannot be reconstructed.

## Analytics definitions

Only ended `windows` sessions count toward metrics. `mock` sessions are shown in history with a simulation label. Actual seconds are end-start, capped at planned seconds. Totals sum actual seconds. A session's entire duration belongs to its start date/hour in the user's profile timezone, including sessions that span midnight. Seven-day charts end today. A streak counts consecutive days with positive focus time, ending today or yesterday. Completion rate = timed completions / all ended real sessions. Best hour is the starting hour with the greatest total actual focus time. Admin aggregates contain counts/time, not window activity.

## macOS adapter approach (not implemented)

Implement the same enter_focus(options), exit_focus(reason), get_state() interface with PyObjC/ApplicationServices Accessibility APIs. Request Accessibility permission through a visible onboarding step. Enumerate user applications/windows through AXUIElement, preserve Safari/Chrome/Firefox, the agent and system UI, record AXMinimized state and stable process/window identities, then set AXMinimized. Restore only windows changed by the agent. Use NSStatusItem for a menu-bar presence and Keychain for device credentials. Permission denial must leave focus idle and report instructions. Test Mission Control spaces, fullscreen windows and destroyed/recreated AX objects before claiming support. Do not fake macOS support by enabling the Windows adapter.

## API references used

- [GetWindowPlacement](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowplacement): the structure length must be set before calling.
- [Window features](https://learn.microsoft.com/en-us/windows/win32/winmsg/window-features): placement includes window state and restored/minimized/maximized positions.
- [WebSocket server documentation](https://websockets.readthedocs.io/en/15.0/reference/asyncio/server.html): loopback server, origins and bounded message handling.
