---
name: feishu-calendar-assistant
description: Feishu calendar scheduling assistant for multi-person free/busy lookup and reliable event creation with attendees. Use when user asks to find overlapping availability, schedule meetings, or debug Feishu calendar API behavior (OAuth, attendee writes, pagination, cleanup).
---

# Feishu Calendar Assistant

Use this skill to run a full Feishu scheduling workflow with minimal manual re-authorization.

## Core workflow

1. **Get a valid user token (prefer one-shot full scope)**
   - Prefer stored token manager:
     - `python3 scripts/feishu-token-manager.py get`
   - If missing/expired without refresh token:
     - ask user to authorize and provide code
     - `python3 scripts/feishu-token-manager.py exchange --code <CODE>`
   - In first-time onboarding, request one-shot full scope to avoid repeated re-auth:
     - `offline_access`
     - `calendar:calendar`
     - `calendar:calendar.event:read/create/update`
     - `contact:user.employee_id:readonly`
     - `contact:contact.base:readonly`

2. **Resolve participant IDs (evidence-first, do NOT rely on subscribed calendars by default)**
   - Priority order:
     1) Parse structured mention entities from inbound message event (if platform provides open_id/user_id).
     2) Resolve via email -> ID (batch id lookup).
     3) Resolve via contact directory search (name -> open_id/user_id).
     4) Last resort: infer from visible event organizer fields.
   - Subscribed-calendar path is fallback only and can miss people.
   - For name lookup reliability, ensure contact scope visibility covers target users.
   - Always report **ID source evidence** in logs/reply when ambiguity exists.

3. **Find target calendars**
   - After IDs are known, resolve calendars for those users.
   - If calendar list is incomplete under current identity, report clearly and request missing IDs/calendar_ids.

4. **Compute overlap availability (preferred: freebusy/batch)**
   - Preferred API: `POST /calendar/v4/freebusy/batch` with RFC3339 `time_min/time_max`.
   - Pass `user_ids` with `user_id_type` and mark missing returns as **unqueryable users**.
   - Fallback to calendar events only when freebusy/batch is unavailable.
   - If using event fallback, **always paginate** (`has_more/page_token`).

5. **Create meeting**
   - Create event on organizer calendar.
   - For attendees, use this structure (critical):
   ```json
   "attendees": [
     {"type": "user", "user_id": "..."},
     {"type": "user", "user_id": "..."}
   ]
   ```
   - Do not use `attendee_id/attendee_id_type` in this workflow.

6. **Verify immediately**
   - Read back event with `need_attendee=true`.
   - Read attendees list endpoint.
   - If mismatch, report precisely and propose remediation.

7. **Cleanup test events** (if requested)
   - List candidate events by title/time window.
   - Keep newest confirmed target, delete test duplicates.

## Commands in this skill

- Token manager: `scripts/feishu-token-manager.py`
- OAuth callback server: `scripts/feishu-oauth-callback.py`
- Free/busy (events fallback): `scripts/feishu-freebusy-overlap.py`
- Free/busy (preferred batch API): `scripts/feishu-freebusy-batch.py`

## Gotchas (must follow)

- Use **user token** for primary calendar writes.
- Token is short-lived (~2h). Refresh early.
- Missing pagination causes false free windows.
- In `free_busy_reader/show_only_free_busy` scenarios, event detail may be limited.
- Validate results against user-observed calendar if discrepancy appears.

## References

- API pitfalls and known issues: `references/api-gotchas.md`
- Reusable workflow prompts: `references/workflow-templates.md`
