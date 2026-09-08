# Recipient Access (No-Account Link)

Implements Phase 0 `D-RCP-1`, `users-and-roles.md` §5, `FR-C-5a`, `FR-D-2`.

The recipient (consignee) is **not** a platform user. They interact through a
**scoped, time-limited, single-job link** delivered by SMS/WhatsApp.

---

## 1. Requirements (Phase 0)

- No account, no login.
- Scoped to **one job**; unpredictable token; expiring; revocable.
- Permissions: **view *their* delivery's status**, **confirm receipt**, **create
  an incident** — nothing else.
- **No access** to unrelated business/operator data or other jobs.
- Full audit trail; every access attributed as `actor_role = RECIPIENT`.

---

## 2. Token model

| Property | Design |
|----------|--------|
| Generation | 32 bytes from a CSPRNG → URL-safe base64 (~43 chars). ≥ 128 bits of entropy → guessing is infeasible. |
| Storage | **Never stored in plaintext.** Two derived values are stored on `recipient_access_link`: `token_hash` (argon2id or SHA-256) for verification, and `token_lookup` (HMAC-SHA256 with a server-held key) as the **indexable** lookup so resolution is O(1) without a table scan and a DB leak yields neither working links nor an offline-crackable index. |
| URL shape | `https://app.fikisha.co.ke/r/<token>` — a dedicated route, not under `/api`. |
| Delivery | SMS and WhatsApp (`channel_sent`), to `job.recipient_phone` (recorded as `sent_to_phone`). |
| One active link per job | Partial unique: `U(job_id) WHERE revoked_at IS NULL AND expires_at > now()`. Re-issuing (e.g. at `ARRIVED_AT_DESTINATION`) revokes the prior and mints a new one, or extends the existing one — **RECOMMENDED: reuse the same link, refresh `expires_at`**, so a recipient who saved the earlier SMS isn't stranded. |
| Expiry | `expires_at = job.completed_at + config.timeouts.post_completion_window` (72h, or 7 days for High/Very-high & latent-risk cargo — D-JOB-5). Until COMPLETED, `expires_at` is set to a rolling `now() + 7d` and bumped on each custody advance. During a dispute, extended to `dispute closed + window`. |
| Revocation | `revoke(job, reason)` sets `revoked_at`; used by admin, and automatically when a job is `CANCELLED`/`FAILED` before delivery. |

---

## 3. What the link exposes (the scoped view)

`RecipientLinkService.resolve(token)` returns **only**:

- Job reference (a short human code, not the UUID), current status in
  recipient-friendly terms ("On the way", "Arrived", "Delivered").
- Pickup area and destination address (the recipient's own address).
- **Operator identification for the doorstep**: assigned driver's **first name**,
  **vehicle type + plate**, and **operator photo** — the recipient legitimately
  needs this to verify who is handing over goods (mitigates identity-sharing,
  trust-and-safety §7). Nothing else about the operator.
- Expected/So-far custody milestones (arrived at destination time), **no GPS
  track**, no other jobs, no prices, no negotiation, no business internal data,
  no other party's PII beyond the above.
- The two actions permitted by `allowed_actions`: **Confirm receipt**, **Report a
  problem**.
- The **recipient short terms** (legal-scope §4 item 7) inline — including that
  the link may have arrived via WhatsApp and how the recipient's data is used.

`allowed_actions` is an array (`VIEW_STATUS`, `CONFIRM_RECEIPT`, `RAISE_INCIDENT`)
so the set can be narrowed per job / per state (e.g. `CONFIRM_RECEIPT` only
appears once the job is `AT_DESTINATION`).

---

## 4. Actions

### 4.1 Confirm receipt (`AT_DESTINATION → DELIVERED`, actor_role = RECIPIENT)

- Requires an **OTP** sent to `sent_to_phone` (a forwarded link alone cannot
  confirm) **plus** the recipient's typed name; optionally a signature and/or a
  photo. For **Elevated+**, OTP **and** a photo are required (D-TRU-5).
- Calls `JobLifecycleService.transition(job, DELIVERED, recipient_actor,
  {proof_of_delivery})` — the same transition the driver would run, just a
  different actor. Writes `ProofOfDelivery` (`captured_by = RECIPIENT`),
  `RECIPIENT_VERIFIED` + `DELIVERY_CONFIRMED` custody rows,
  `audit_log_entry (actor_role = RECIPIENT, source_channel = API)`.

### 4.2 Report a problem (create an incident, FR-D-2)

- Types available to a recipient: `WRONG_RECIPIENT`, `DAMAGE`, `MISSING_GOODS`,
  `WRONG_GOODS` (`→ OTHER` with label), plus a free-text description and photos.
- **No OTP required** for incident creation — we want wrong-recipient/damage
  caught early, and the downside of a spurious incident is low and rate-limited.
  The incident is flagged `reported_by_kind = RECIPIENT_LINK` for the reviewer.
- `IncidentService.open(job, type, severity=default, reporter=link, ...)` →
  notifies business + operator/group + an administrator; may move the job to
  `DISPUTED` if progression-blocking (FR-D-3).

### 4.3 View status

- Read-only; rate-limited; each `GET /r/<token>` writes a lightweight
  `evidence_access_log`-style audit row (`action = recipient.view`).

---

## 5. Threat model

| Threat | Vector | Mitigation |
|--------|--------|------------|
| **Token guessing / brute force** | Enumerate `/r/<token>` | ≥ 128-bit token; per-IP + per-token rate limit (Redis token bucket); `404` (not `403`) for any non-match so nothing is revealed; alert on a burst of `/r/` 404s from one IP |
| **Leaked / forwarded link** (screenshot, WhatsApp forward, shared phone) | Someone other than the recipient opens it | Scope is minimal (only this job's delivery view); **confirm-receipt requires an OTP to `sent_to_phone`** so a forwarded link can't complete a delivery; incident creation is possible but rate-limited and flagged for a human; the link **expires** at completion + window |
| **Link reuse after the job** | Recipient (or a leak) keeps hitting the URL | `expires_at` enforced on every resolve; after expiry → `404`; `revoked_at` short-circuits |
| **Replay of a captured confirm request** | Resend the `POST /r/<token>/confirm` | The OTP is single-use (`consumed_at`); the transition is idempotent (`Idempotency-Key`); once `DELIVERED`, the guard rejects a second confirm |
| **Phishing** (a fake "Fikisha" link) | Attacker sends their own SMS | Out of the platform's control; mitigations: consistent sender ID, the link always on the real `app.fikisha.co.ke` domain, the recipient short terms explain what a legitimate link does and does not ask for (never a password, never payment) |
| **Data harvesting via the view** | Repeatedly open valid links to scrape operator PII | The view exposes only first name + plate + photo (doorstep-identification minimum); rate-limited; no bulk endpoint; tokens are per-job and not enumerable |
| **Malicious incident spam** | Open many spurious incidents to harass an operator | Per-token + per-IP rate limit on incident creation; a recipient-origin incident that is later found unfounded is recorded and counts against nothing operator-side but is visible to the reviewer; repeated abuse from one phone can have that phone's links auto-revoked |
| **Token in server logs / referrer** | Token appears in access logs or a `Referer` header to the tile provider | The token is a **path** segment; set `Referrer-Policy: no-referrer` on `/r/*`; scrub the `/r/<token>` path to `/r/[token]` in structured logs; the token is not needed after resolve (the client gets a short-lived session-scoped handle for subsequent calls — see §6) |
| **DB compromise** | Attacker reads `recipient_access_link` | Only `token_hash` + `token_lookup` stored — neither yields a working token; `token_lookup` needs the server HMAC key (in KMS/secrets) to even correlate |

---

## 6. Session handling for the link (implementation note)

To keep the raw token out of every subsequent request:

1. `GET /r/<token>` resolves the token, and if valid issues a **short-lived,
   link-scoped bearer** (`recipient_link_session`, ~30 min, bound to the
   `link_id` and the request IP/UA) returned to the browser (memory only, not
   `localStorage`).
2. Subsequent calls (`/r/session/confirm`, `/r/session/incident`,
   `/r/session/status`) use that bearer; the raw token is used once.
3. The link-scoped bearer grants **exactly** `link.allowed_actions` for
   **exactly** `link.job_id`; the authorization engine treats it as
   `actor = RecipientActor(link_id, job_id)`.

---

## 7. Audit & retention

- Every resolve, view, OTP request, confirm, and incident from a link writes an
  `audit_log_entry` with `actor_role = RECIPIENT`, `entity = job`, and the
  `link_id` in `source_meta`.
- Recipient name + phone + incident text are retained **with the job record**
  (7y, legal-scope §7 — REQUIRES VALIDATION); the **link row** itself becomes
  inert at `expires_at` and is a candidate for pruning once its job's retention
  window closes.
- The recipient short terms shown on the link disclose the WhatsApp cross-border
  transfer and the processing of the recipient's data (legal-scope §3.9, §4
  item 7).

---

## 8. Events

| Emits | Consumers |
|-------|-----------|
| `RecipientLinkIssued` | Notifications (send the link) |
| `RecipientConfirmedReceipt` | Jobs (the DELIVERED transition already ran); metrics (POD method) |
| `RecipientRaisedIncident` | Incidents & Disputes; Notifications (business + operator + admin) |

| Consumes | For |
|----------|-----|
| `JobAtDestination` / `JobDelivered` | issue or refresh the link + OTP |
| `JobCompleted` | set the final `expires_at` |
| `JobCancelled` / `JobFailed` (pre-delivery) | auto-revoke |
| beat tick (hourly) | expire lapsed links |
