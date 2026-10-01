# REST and local protocol

## REST

Base: `http://127.0.0.1:8000/api/v1` in development, configured in client/agent environment files.

JSON success: `{ "success": true, "data": ... }`. Failure: `{ "success": false, "error": { "code": "400", "message": "...", "details": ... } }`.

Browser requests use `Authorization: Bearer <JWT>`. Access tokens last 15 minutes; refresh tokens last seven days and rotate. `ver` must equal the user's current token version. Logout/password changes invalidate all browser login tokens for that account. Paired agent credentials are deliberately separate.

| Method | Path | Purpose |
|---|---|---|
| POST | /auth/register | `{name,email,password}`; password validation, BCrypt-SHA256 |
| POST | /auth/login | `{email,password}` returns access, refresh, user |
| POST | /auth/refresh | `{refresh}` rotates tokens |
| GET / PATCH | /auth/me | Profile, timezone, default_duration, notifications |
| POST | /auth/logout | Revoke all login tokens for this account |
| POST | /auth/password | `{old_password,password}`; revokes login tokens |
| GET | /devices | Own unrevoked devices, pagination |
| POST | /devices/pair | Agent-only workflow using user's JWT; `{name,os}` returns device plus random secret |
| DELETE | /devices/:uuid | Revoke own device |
| DELETE | /devices | Revoke all own devices |
| GET | /sessions | Own history; `page`, `limit`, `status`, `from`, `to`, `search` (device name) |
| GET / PUT | /allowlist | `{apps:["code.exe"]}`; protected entries cannot be edited |
| GET / POST | /schedules | List or create own schedule |
| PATCH / DELETE | /schedules/:id | Owner-only update/delete |
| GET | /insights | Actual focus metrics and recent missed runs |
| GET | /downloads | Public download links |
| GET | /admin | Admin users (paginated), presets, downloads, aggregate statistics |
| PATCH | /admin/users/:id | `{is_active:boolean}`; cannot deactivate self |
| POST | /admin/presets or /admin/downloads | Publish configuration |
| PATCH / DELETE | /admin/presets/:id or /admin/downloads/:id | Edit/remove configuration |

Device-authenticated requests use `X-Device-ID` and `X-Device-Key`. No account ID is trusted from the request body:

| Method | Path | Purpose |
|---|---|---|
| GET | /agent/config | Validate device, heartbeat, own allow-list and device-specific schedules |
| DELETE | /agent/config | Revoke the calling device |
| POST | /agent/events | Authoritative event ingestion; duplicate UUIDs have no second effect |

This intentionally replaces the PDF's browser-written `POST/PATCH /sessions`: **only the agent uploads session events**. The dashboard cannot double-record a session. List envelopes for devices, sessions and admin users are `{items,page,limit,total,totalPages}`; small configuration lists are arrays. Supported sort is fixed newest-first for history/devices, not arbitrary `sort` parameters. Auth endpoints are throttled to 10/minute, anonymous API traffic to 60/minute and authenticated users to 300/minute (development cache; production needs shared cache/proxy rate limits).

Schedule body: `{name,device,days:[0,1,2,3,4],start_time:"09:00",timezone:"Asia/Kolkata",duration_minutes:25,enabled:true,consent:true}`. Monday=0. Read responses include computed `next_at`.

Event envelope: `{event_id:UUID,kind:"started"|"ended"|"missed",data:{...}}`.

- started: session_id, started_at (ISO with timezone), planned_minutes, source (MANUAL/SCHEDULE), mode (windows/mock).
- ended: session_id, ended_at, reason. `timer` means COMPLETED; other reasons CANCELLED. Actual duration is calculated server-side and capped at planned duration.
- missed: occurrence (`scheduleId:localDate`), at, reason.

## Pairing handshake (separate from focus messages)

1. The visible agent generates six random digits, retains a hash for comparison and locally displays the code for 180 seconds. Five failed attempts lock it until local regeneration. The code is never sent to an unauthenticated connection.
2. Browser sends `{v:1,id:UUID,type:"pair",code:"123456",jwt:"..."}` over loopback. Permitted Origin is checked by the WebSocket server; it is not authentication.
3. Agent consumes the code once, calls `/auth/me` to verify identity, then registers its device using that JWT. It does not trust a supplied user ID.
4. Agent receives a backend credential, creates a separate random local credential, and stores both with Windows DPAPI. Backend stores only a SHA-256 hash of its random 256-bit secret.
5. Agent responds `{v:1,id,type:"paired",credential,deviceId,state}`. The browser retains only the local credential in sessionStorage, never the agent's backend credential.
6. Reconnect: `{v:1,id,type:"authenticate",credential,jwt}`. Agent checks local key, live Django identity/owner and device validity before admitting commands.

An interrupted pairing can consume the code before backend failure; generate a fresh local code. A browser without its local credential must unpair/re-pair using the visible companion. There is no silent pairing or account enumeration service.

## Focus messages v1

Loopback bind: `127.0.0.1:4545`. Configurable port; no LAN bind. Origins must match exact configured entries. Maximum frame/message size 8 KiB; no arbitrary command execution. Up to 120 commands/minute per connection.

```json
{"v":1,"id":"request-uuid","type":"getState"}
{"v":1,"id":"request-uuid","type":"enterFocus","durationMin":25,"confirmed":true}
{"v":1,"id":"request-uuid","type":"exitFocus"}
```

`enterFocus` accepts integer durations 1–240. Effective allow-list comes from the authenticated backend; protected entries are enforced inside the adapter. `confirmed:true` reflects the explicit dashboard confirmation. Schedule starts use stored schedule opt-in and the local heads-up.

Responses: `state`, `focusStarted`, `focusEnded`, `error`. Responses echo `id`; unsolicited half-second `state` broadcasts use `id:null`. State separates `pairing`, `focus`, `mode`, deviceId, remaining, session, apps, sync, pending_events and pending_restore. Connection state itself is known to the browser socket. `focusStarted` occurs only after successful activation. Native partial activation failure attempts rollback and sends an error.

Duplicate start/stop request IDs replay their cached response (500 requests per agent process); same ID with different body is rejected. Separate starts while active are rejected. Repeated stops are harmless. After restart the old focus is recovered/ended rather than replayed. Frontend does not automatically retry timed-out focus commands; inspect acknowledged state first.

Remote starts revalidate JWT identity and device status. Offline local End Focus always works. State and end operations on an established authenticated socket remain available during backend outages. Logout revokes backend JWTs; new remote starts fail with revoked tokens, while the local session continues until stopped/expired.
