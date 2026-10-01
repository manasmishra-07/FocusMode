# The Python companion, explained for a viva

## The big idea

A browser is not allowed to minimize other applications. Our small desktop program has the Windows permissions needed to do that. The website asks the program to focus; it never sends an operating-system command. The program can refuse the request and always lets the local user stop.

Think of three independent questions: **Am I paired? Is the browser connected? Am I focusing?** A paired device can be disconnected. A focusing device can have no browser open. Keeping those states separate prevents misleading status badges.

## Files in execution order

### `main.py`

Reads local environment configuration and command-line options. `--adapter mock` does no OS work; `--adapter windows` selects the native implementation. It calls `launch` with the chosen storage folder. Packaged builds read `.env` next to the executable.

### `focus_agent/ui.py`

Creates Tkinter on the main thread. Labels show the computer name, pairing state/code, remaining time, preserved apps and synchronization. The tray menu and window buttons can end focus or quit. Closing the window is a safe quit, not a hidden background mode.

Networking runs on a worker thread. Two thread-safe queues connect it to Tkinter: `commands` carries stop/quit/code/unpair requests to the worker; `events` carries state and notices to the UI. Tkinter's `root.after` checks the queue every 200 ms. Tray callbacks only put messages on queues, so they never manipulate Tk widgets from the wrong thread.

### `focus_agent/runtime.py`

Assembles the program. It binds the loopback port before recovery to reject a second running instance safely. It opens the store, loads credentials, creates the adapter/controller and starts the WebSocket server. A half-second loop processes local buttons, checks the timer and updates clients/UI. A separate coroutine polls settings and retries events every five seconds. Blocking HTTP calls run using `asyncio.to_thread`, allowing the timer and local stop to continue during network delays.

`revoke` ends focus, clears local credentials, closes authenticated sockets and generates a new code. Local unpair also tries to upload pending events and revoke the server record; if offline, the user can revoke it later from the dashboard. `finally` invokes the same cleanup on normal quit or unexpected runtime exit.

### `focus_agent/pairing.py`

`rotate` generates six cryptographically random digits using `secrets`, sets a three-minute monotonic expiry and resets the attempt count. `consume` hashes the submitted code, compares it without an early-exit string comparison, and rejects expired, reused or locked codes. Five wrong guesses lock the code until the user asks for a fresh one locally.

### `focus_agent/protocol.py`

Checks JSON structure, version, request ID, message size (server configuration), request rate and authentication. `pair` verifies the code and Django identity. `authenticate` verifies both the local credential and account ownership. `getState` reads truth from the agent; `enterFocus` validates backend identity/config and invokes the controller; `exitFocus` restores through the controller.

An asyncio lock serializes commands. A bounded response cache remembers start/stop request IDs, so retransmission does not create another session. Reusing an ID with different contents is an error. A second fresh start while focusing is rejected by the controller.

### `focus_agent/controller.py`

The OS-independent session lifecycle. `enter_focus(options)` validates a 1–240 minute integer and explicit confirmation, stores a provisional session, asks the adapter to act, then records a successful start. `exit_focus(reason)` calls restoration and atomically records the end. `tick()` compares the current absolute time to `deadline`. `get_state()` builds a readable state object.

The constructor recovers previous placement changes. An activated interrupted session is ended as `restart`; a provisional session that never completed activation does not become a successful focus session. The injectable clock makes sleep/timer tests fast and deterministic.

### `focus_agent/allowlist.py`

Validates executable basenames such as `code.exe`. Hard-coded browser/helper/system entries and the Windows directory are preserved. User entries only add protection. Nothing a browser message sends can remove the built-in protection.

### `focus_agent/windows.py`

`WindowsAdapter` uses ctypes declarations to match the Windows C API's pointer and integer types. `identity(hwnd)` finds the PID, executable path and process creation time. If those cannot be read safely, the window is skipped.

`enter_focus` enumerates candidates, records original `WINDOWPLACEMENT` and commits a journal before requesting minimization. A unique property tags each window so a reused handle cannot restore a different window. An acknowledgement check detects failures and triggers rollback. `exit_focus` validates identity/marker and restores saved placements. Failed restorations stay in the journal for retry. `MockAdapter` implements the same methods while changing no windows.

### `focus_agent/storage.py`

Small SQLite key/value and event tables are a durable local notebook. A session transition and its corresponding event commit together. `pending` returns queued events in order and `ack` removes a successfully uploaded event. Each event records its original device binding locally.

The credential file is separate and encrypted through Windows DPAPI, tied to the current OS user. It is replaced atomically. The recovery journal contains local handles, placement and process identity, but never window titles. These details are not uploaded.

### `focus_agent/api.py`

Outbound HTTP wrapper. A fixed locally configured API URL prevents a browser request from redirecting credentials to an attacker. Remote URLs require HTTPS; loopback HTTP is permitted for development. `identity`, `register`, `config`, `upload` have narrow purposes. The device secret is used only by this client, not by browser JavaScript. Request timeouts keep offline sync bounded.

### `focus_agent/schedules.py`

Converts the current moment into each schedule's IANA timezone, finds due weekday/time occurrences, deduplicates local-date keys, and shows a 15-second notice. A late, overlapping, disabled or locally cancelled occurrence becomes a missed event. `cancel` is called by End Focus. Old occurrences are never immediately forced to run.

## Trace one complete session

1. User logs in; browser has JWTs.
2. User reads companion code and pairs. Agent verifies Django identity and stores device credentials.
3. Dashboard sends a request ID, integer duration and confirmation.
4. Protocol authenticates → controller validates → adapter journals and minimizes.
5. Controller queues a started event. Browser sees `focusStarted` only now.
6. Runtime keeps ticking even if the browser disconnects; sync independently uploads events.
7. A stop or deadline uses the same cleanup, restoring matching windows and queuing an ended event.
8. Django deduplicates the event and calculates actual time; insights read persisted real sessions.

## Viva questions and concise answers

**Why not do this entirely in React?** Browser sandboxing intentionally prevents arbitrary access to other application windows.

**Why not kill distracting processes?** It can discard unsaved work. Minimizing changes presentation and remains manually reversible.

**Why does the timer live in Python?** Browser tabs close, suspend and throttle timers. The installed companion is the authority for the local session.

**Are Origin checks enough?** No. We also require random credentials and a Django-verified identity. Origin is a separate browser-origin defense.

**What happens if the backend is down?** The current session and local stop still work. Events queue. New dashboard starts requiring backend verification fail clearly. Schedules pause until successful sync.

**Can a crashed process restore windows?** No. Users can restore normal minimized windows themselves, and the next agent start attempts journal recovery.

**Why record process creation time and a marker?** Windows can reuse process IDs and window handles. Extra identity checks avoid touching a different window later.

**Why can repeated requests be safe?** Request IDs cache command outcomes; event IDs deduplicate persistence. These solve two different duplication problems.

**Do the tests prove all Windows applications work?** No. Mock tests prove control flow. A real disposable-window check proves basic Windows calls. Elevated apps, real sleep/wake and multi-monitor behavior still need manual coverage.

**Why SQLite?** Immediate local setup and clear Django models. PostgreSQL is a documented deployment option. This is an intentional substitution for the PDF's MongoDB and needs teacher acceptance.
