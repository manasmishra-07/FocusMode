# Prompt provenance

No fictitious team prompts or commits are listed. This build used one user-provided task and a detailed attached implementation brief.

1. User request: “build this project under focusmode folder3”. Selected workspace was `C:\Users\manas\OneDrive\Desktop\FocusMode`.
2. User-supplied pasted brief: “Build the ‘PS3 — Focus Mode: Distraction Lockdown Dashboard’ project in the selected workspace.” It requested React/Vite/JavaScript, Django REST Framework/JWT/SQLite, a Python/Tkinter/pystray Windows companion, authenticated local WebSockets, ctypes integration, tests and documentation. It explicitly prohibited unrelated commands, arbitrary OS-control services, uncontrolled focus testing, remote pushes/public deployment and claiming teacher approval.
3. Source specification: `PS3_Focus_Mode_Lockdown_Dashboard.pdf`, 19 pages. Requirements were extracted and mapped in docs/REQUIREMENTS.md. MERN/MongoDB is superseded by the user's explicit Django choice and flagged for teacher acceptance.

Implementation work proceeded in these stages (these are work notes, not invented additional user prompts):

- Inspect empty workspace and extract PDF requirements.
- Build Django models/auth/API/permissions and migrations.
- Build agent pairing, protocol, storage, controller and mock adapter.
- Implement conservative Windows minimization/restoration adapter.
- Connect React screens and explicit consent flow.
- Add schedules, analytics and admin configuration.
- Verify backend/agent tests, real loopback security behavior and one disposable Windows window.
- Verify browser login/pairing/countdown and mobile layout.
- Package the Windows companion and document startup, architecture, caveats and viva walkthrough.

The PDF asks for 10–20 key team prompts. Only actual provided prompts are recorded here; the submitting team should append their real subsequent prompts rather than pad the log.

## Resume after user modifications

User: “so now restart ur work from here and start building this whole project as soon as possible before hitting daily limit ok”. Inspected current committed files first, retained additional CORS configuration and existing data, repaired SQLite fallback and expired-token refresh, added regression tests and `run.ps1`, rebuilt the Windows package, and verified its mock smoke test plus the browser dashboard.
# Continuous focus correction

User requested automatic fullscreen on session confirmation and enforcement throughout the session. Added gesture-triggered fullscreen, full-page active view, repeated reversible minimization with a preserved recovery journal, and native disposable-window tests for allow-list behavior, reopening, newly eligible windows, and ending. Browser and allowed-app exemptions follow the PS. Package launch verification remains blocked by Windows Application Control.
