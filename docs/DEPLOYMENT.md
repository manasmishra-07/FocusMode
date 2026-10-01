# Deployment and packaging

Nothing has been deployed or pushed remotely. Local development is the verified target.

## PostgreSQL API deployment

Set `DEBUG=false`, a unique long random `SECRET_KEY`, exact `ALLOWED_HOSTS`, exact HTTPS `CLIENT_ORIGINS`, and `DATABASE_URL=postgres://user:password@host:5432/focus`. The installed psycopg driver supports PostgreSQL. Do not deploy the demo database/accounts. Run migrations on the deployment database.

Use a production WSGI server (for example gunicorn on Linux, installed separately) with `config.wsgi:application` from `server/`. Configure HTTPS at a trusted reverse proxy, host validation and request/body limits. If TLS is terminated upstream, explicitly configure Django's secure proxy header only for that trusted proxy; otherwise HTTPS redirect may loop. `SECURE_SSL_REDIRECT`, secure session/CSRF cookies and HSTS activate when DEBUG is false. Run `manage.py check --deploy` and address environment-specific findings before release. Add a shared cache for multi-worker throttling; Django's local-memory development throttle is not a distributed rate limiter.

Back up PostgreSQL, restrict database access, retain only necessary account/session data, and add monitoring. Configure JSON 404/500 responses at the edge as appropriate. Django handles REST exceptions with a stable JSON shape. Do not expose the dev server to the public Internet.

## Frontend

Set `VITE_API_URL` to the HTTPS API's `/api/v1` address at build time. `npm run build` writes `client/dist`. Serve with SPA history fallback to index.html, correct static content types and a CSP restricting connect-src to the intended API and local companion. Current typography loads from Google Fonts and falls back to local sans-serif; self-host those fonts for a completely offline/private deployment. No analytics or AI API is used.

## HTTPS dashboard to local companion

Local HTTP at 127.0.0.1:5173 to ws://127.0.0.1:4545 was tested. Public HTTPS → localhost was **not tested** and must not be assumed to work identically across browsers. Mixed content, private/local-network access rules, consent prompts and local certificate trust vary.

The agent accepts optional `AGENT_TLS_CERT` and `AGENT_TLS_KEY` for WSS. Use a certificate trusted by that user's browser and valid for the chosen loopback name/address, configure `VITE_AGENT_URL=wss://...`, and include the exact deployed dashboard origin in `ALLOWED_ORIGINS`. The server still binds only loopback. The project does not install a root CA or disable browser security. Test in supported Edge/Chrome/Firefox versions on a real deployment before publishing a promise of hosted compatibility. Until then use the verified local dashboard.

## Build the Windows companion

From repository root:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name FocusMode --paths agent --collect-all tzdata --distpath agent\dist --workpath agent\build --specpath agent agent\main.py
```

Distribute the entire `agent/dist/FocusMode` directory, including `_internal`, as a zip or an installer you review. This is a directory build, not a standalone single executable. Place a configured `.env` beside the executable if needed; do not package real credentials. Run `FocusMode.exe --adapter mock` first. Use `--adapter windows` only when ready for real confirmed focus behavior. No auto-start or hidden installation is configured.

DPAPI/journal files normally live under `%LOCALAPPDATA%/FocusMode`. `--data-dir` supports an explicit alternative. Never share credentials.bin. New configurations must keep exact loopback bindings and origins. The generated build is unsigned; publisher signing and clean-machine antivirus/install checks remain release tasks.

Admin download configuration accepts HTTPS links to builds you choose to host. It does not itself publish artifacts. No public build URL is fabricated.
