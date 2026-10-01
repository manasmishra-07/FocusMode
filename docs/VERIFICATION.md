# Verification record — 1 October 2026

## Observed results

### Continuous focus correction

- Frontend lint and production build pass; 8 Django tests and 13 agent tests pass. Agent tests require unsandboxed Windows DPAPI access; the invalid-origin handshake log is an intentional rejection test.
- `agent/tests/safe_enforcement_check.py` uses one disposable Tk window, restricts enumeration to its HWND, and substitutes its identity only inside the test. Real Win32 calls verify allowed-app preservation, re-minimization after reopening, first-placement retention, manual and timed restoration, and no enforcement after ending. It never targets other desktop windows.
- Confirmation now requests fullscreen synchronously from the click, before network work. Full-page layout works independently of fullscreen permission. Browser-specific automatic fullscreen remains a manual verification item; build/lint alone do not prove browser permission behavior.
- Restart the companion after this update; an already-running Python process still contains the old one-shot behavior.
- Updated PyInstaller package builds at `agent/release-focus/FocusMode/FocusMode.exe`. Windows Application Control blocked launching this new executable, so its smoke test is unverified; the source-based launcher and native disposable-window tests work. The old release directory is obsolete after OneDrive prevented rebuilding in place.

### Resumed build verification

- Preserved the user's additional 5174 CORS origins and existing environment/database files.
- Fixed blank `DATABASE_URL` startup failure; added a regression test.
- Fixed JWT refresh being rejected by expired Authorization headers; added a regression test.
- Eight Django tests now pass, including both regression cases. Updated production build and ESLint pass.
- Restored missing `server/.env.example` and `client/.env.example` templates without overwriting `.env` files.
- Added a component launcher (`run.ps1`) using the existing virtual environment, and strict Vite port selection to avoid unexpected origin changes.
- Re-ran all 11 companion tests and the native disposable-window check successfully.
- Rebuilt the executable into `agent/release/FocusMode/` because OneDrive locked the previous build cache. The packaged `FocusMode.exe --smoke-test` opened the real Tk/tray runtime in mock mode with temporary storage, reached ready state, and exited successfully (code 0).
- Verified login and the rendered dashboard again against the repaired backend. Saved the preview as `docs/dashboard.jpg`. Existing accounts and the recorded simulation session were preserved.

### Earlier implementation checks

- Django migrations applied to local SQLite; system check reports no issues.
- Six backend test cases passed: auth/password hashing, role/ownership boundaries, logout access/refresh revocation, allow-list/schedule validation, event retry deduplication, filtered history and real-vs-mock analytics.
- Eleven companion test cases passed: invalid/expired/reused/locked codes, duplicate starts/repeated stops, absolute timer with simulated browser closure/sleep, durable restart queue, activation rollback, protected apps and durations, schedule heads-up/dedup/missed runs, real Windows DPAPI encryption/decryption, real loopback unauthenticated rejection, duplicate request-ID replay, disallowed Origin rejection and schema rejection.
- Native Windows disposable-window test passed. It created one new Tk window, verified the protected Python helper is skipped, manually minimized **that exact test window only**, and restored it via journal identity/marker checks. It never initiated full desktop focus. This validates native calls and restoration but is not full multi-app focus acceptance.
- Browser: development account logged in, visible mock companion paired through the form, same-tab reconnect recovered authenticated state, pre-session confirmation appeared, a one-minute mock session was acknowledged and timed out, and the UI returned to idle.
- Responsive browser review at 1440px and 360px. Mobile navigation and dashboard render; no intentionally fixed desktop width on the mobile content.
- Vite production build passed. ESLint passed. npm audit reported zero known dependency vulnerabilities at install time (not a security certification).
- PyInstaller directory build generated with Tcl/Tk and tzdata included. The first sandboxed build omitted Tcl/Tk because the sandbox blocked its data directory; it was rebuilt outside the sandbox. Only the corrected build should be used.

Tests requiring Windows DPAPI/Tk needed normal user execution outside the sandbox. No privilege elevation or administrator-only OS features are required by the application itself.

## Manual verification still required

1. Run real Windows mode on a controlled desktop containing disposable documents. Confirm browsers/agent/system apps are preserved and an eligible unlisted app minimizes and restores placement.
2. Test multiple monitors, maximized windows, virtual desktops, UWP/elevated applications and inaccessible process identities. The conservative adapter should skip unsafe/unsupported windows; any partial failure should be visible and rolled back.
3. Exercise real sleep/wake and terminate the agent during controlled focus, then restart. A terminated process cannot execute cleanup; verify manual taskbar restoration and journal recovery.
4. Disconnect the backend during a running mock session, end locally, reconnect, and inspect FIFO retry and exactly-once persisted events. Unit tests cover the pieces; a prolonged integrated outage needs manual coverage.
5. Test public HTTPS frontend → local WSS agent on supported browsers with a valid trusted certificate and expected local-network permissions. No deployed HTTPS result is claimed.
6. Test timezone daylight-saving gaps/folds and long offline schedule reconciliation. Current catch-up horizon is seven days; skipped wall-clock times and future clock jumps need additional testing.
7. Review all tray actions, keyboard tab order, screen reader announcement quality, measured contrast, and admin CRUD end-to-end.
8. Run the packaged directory on a clean Windows user/machine. Unsigned build publisher trust and installer signing are not implemented.

## Reproducible safe commands

See README for unit/build commands. `agent/tests/browser_companion.py` opens a visible **mock** fixture with temporary state and prints only its locally displayed pairing code to the test terminal. Quit it from its own window after testing. It is not a production headless agent or a network code-disclosure endpoint.

`agent/tests/safe_windows_check.py` restricts adapter enumeration to the disposable test HWND; the test's explicit raw minimization only targets that window. Do not replace it with an unrestricted real focus call to speed up verification.
