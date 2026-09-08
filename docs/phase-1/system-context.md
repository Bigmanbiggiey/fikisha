# System Context

C4 level 1: who and what interacts with Fikisha, and where the trust boundaries
are. Detail on internal structure is in [architecture.md](architecture.md).

---

## 1. Actors

| Actor | Account? | How they reach the system | Key interactions |
|-------|----------|---------------------------|------------------|
| **Business user** | Yes (phone + OTP) | PWA | Create/manage jobs, negotiate, confirm, track, rate, raise/participate in incidents, confirm pickup in-app (fallback), view delivery records |
| **Transport Operator (individual)** | Yes (phone + OTP) | PWA (mobile-first, Swahili-prominent) | Complete profile + verification, register vehicles/bases, set availability, discover jobs, negotiate, accept, execute custody steps, capture pickup/POD OTP + photos, view earnings + statements, rate, raise incidents |
| **Operator Group — primary contact / MANAGER** | Yes (phone + OTP) | PWA | Manage group profile, members, group vehicles; browse eligible jobs for the fleet; negotiate; **assign a specific member DRIVER + vehicle**; view the group's statement |
| **Operator Group — member DRIVER** | Yes (phone + OTP), individually verified | PWA | Same custody/execution surface as an individual operator, for jobs assigned to them by the manager (or accepted directly if the group allows) |
| **Recipient / Consignee** | **No account** | A **scoped, time-limited per-job link** (SMS/WhatsApp) opened in any browser | View *their* delivery's status, **confirm receipt** (name + OTP/signature/photo), **raise an incident** with photos + a statement |
| **Operations Officer** (pilot admin role) | Yes (phone + OTP **+ TOTP MFA**) | PWA admin surface + Django Admin | Work the verification queue, monitor active jobs, intervene (reassign/cancel/contact), incident intake, facilitate amicable resolution, propose trust changes |
| **Platform Admin** (the founder; pilot admin role) | Yes (phone + OTP **+ TOTP MFA**) | PWA admin surface + Django Admin | Everything the Operations Officer can do **plus** platform configuration, account suspension/offboarding, binding dispute resolution at any band, high-value job approval, manage other admins — **all actions audited, including the founder's** |

The 4-role split (Verifier / Operations / Dispute Officer / Platform Admin) is a
**configuration** of the role→permission map, not a code change (D-ADM-1).

---

## 2. External systems

| External system | Direction | Purpose | Trust / compliance notes |
|-----------------|-----------|---------|--------------------------|
| **SMS gateway** (e.g. Africa's Talking) | Out (send) + In (delivery-receipt webhook) | OTP delivery (primary), job-event notifications, recipient link | Transactional only; registered sender ID; webhook signature verified; per-message cost recorded |
| **WhatsApp BSP / Meta** | Out (send templates) + In (status webhook) | Job-event notifications, recipient link (not OTP-primary) | **Cross-border transfer to the US** — REQUIRES VALIDATION (legal-scope §3.9); pre-approved templates only; falls back to SMS on failure |
| **Geocoding + distance provider** | Out (request/response), cached | Resolve addresses to coordinates; pickup→destination distance for matching + metrics | Results cached; ops can override distance manually; provider is OPEN |
| **Map tile provider** | Out (client fetches tiles) | Map display in the PWA | Bounded caching; static-map fallback for low-end devices |
| **KRA eTIMS** (or accredited middleware) | Out (submit invoice) + In (reference/ack) | eTIMS-compliant commission invoices attached to weekly statements | **Integration mode REQUIRES VALIDATION**; adapter-isolated; manual-reference fallback |
| **M-Pesa (Safaricom Daraja) — merchant paybill** | In (optional C2B confirmation webhook) | Reconcile **the platform's own commission** payments against statements | The platform **never holds the transport fare**; manual reconciliation is the week-1 default; webhook signature verified |
| **Object storage (S3-compatible)** | Out + In | Store and retrieve evidence media (verification docs, custody/POD photos, incident/dispute evidence) | Private bucket; SSE at rest; app-level envelope encryption for HIGH-PII; access always mediated by the API |
| **Error tracking (Sentry / GlitchTip)** | Out | Exception capture | PII scrubbed before send |
| **Email (optional)** | Out | Admin notifications, statement copies (optional) | Not a primary channel; SHOULD |

There is **no** integration with banks, insurers, NTSA, ODPC, or the DCI in the
MVP. Verification is document-upload + human review. Any future automated check
(insurance status, licence validity, good-conduct lookup) is future-roadmap and
would be a new adapter.

---

## 3. Context diagram

```mermaid
graph TB
    subgraph People
      BIZ["Business user"]
      OPR["Operator / Group manager / Driver"]
      RCP["Recipient (no account)"]
      OPS["Operations Officer"]
      PA["Platform Admin (founder)"]
    end

    subgraph Fikisha["Fikisha platform (modular monolith + workers)"]
      PWA["PWA client<br/>(installable, offline-tolerant)"]
      API["API + Domain services"]
      WRK["Background workers<br/>(Celery)"]
      DB[("PostgreSQL")]
      OBJ[("Object storage<br/>(private, encrypted)")]
      RDS[("Redis")]
    end

    subgraph External
      SMS["SMS gateway"]
      WA["WhatsApp BSP / Meta"]
      GEO["Geocoding / distance"]
      TILES["Map tiles"]
      ETIMS["KRA eTIMS"]
      MPESA["M-Pesa merchant paybill"]
      ERR["Error tracking"]
    end

    BIZ --> PWA
    OPR --> PWA
    OPS --> PWA
    PA --> PWA
    RCP -->|"per-job link"| PWA

    PWA -->|"HTTPS / JSON, Bearer token"| API
    API <--> DB
    API <--> RDS
    API <--> OBJ
    API -->|"enqueue"| RDS
    WRK <--> RDS
    WRK <--> DB
    WRK <--> OBJ

    WRK -->|"send"| SMS
    WRK -->|"send template"| WA
    API -->|"geocode / distance (cached)"| GEO
    PWA -->|"tiles"| TILES
    WRK -->|"submit invoice"| ETIMS
    MPESA -->|"C2B confirmation webhook (optional)"| API
    SMS -->|"delivery receipt webhook"| API
    WA -->|"status webhook"| API
    API -->|"exceptions"| ERR
    WRK -->|"exceptions"| ERR
```

---

## 4. Trust boundaries

```mermaid
graph LR
    subgraph Untrusted["Untrusted zone"]
      C1["PWA on user device"]
      C2["Recipient browser (link)"]
      C3["Provider webhooks (inbound)"]
    end

    subgraph Edge["Edge (TLS termination, WAF-lite, rate limiting)"]
      RP["Caddy / nginx"]
    end

    subgraph AppTrust["Application trust zone (private network)"]
      APP["API + services"]
      W["Workers"]
    end

    subgraph DataTrust["Data trust zone (most restricted)"]
      PG[("PostgreSQL")]
      OB[("Object storage")]
      RE[("Redis")]
      SEC[("Secrets / KMS")]
    end

    C1 -->|HTTPS| RP
    C2 -->|HTTPS| RP
    C3 -->|HTTPS + signature| RP
    RP --> APP
    APP --> PG
    APP --> OB
    APP --> RE
    APP --> SEC
    W --> PG
    W --> OB
    W --> RE
    W --> SEC
```

Boundary rules:

1. **Everything from a client is untrusted.** All authorization, all state
   transitions, all validation happen server-side (NFR-SEC-2). The PWA only
   *hides* controls for UX; it never *enforces*.
2. **The recipient link is untrusted and unauthenticated** but tightly scoped:
   it can only touch one job's delivery-facing surface, is rate-limited, and
   confirm-receipt requires an OTP to the recipient's phone on file. See
   [recipient-access.md](recipient-access.md).
3. **Inbound webhooks are untrusted** until their signature / HMAC / shared
   secret is verified and the source IP is allowlisted where the provider
   supports it. Processing is idempotent.
4. **Object storage is never reached by a client.** Uploads and downloads go
   through the API, which authorizes the request and logs PII-document access.
5. **Secrets** (DB credentials, provider keys, signing keys, envelope-encryption
   keys) live only in the secrets store / KMS, injected as environment at
   runtime, never in source control (NFR-SEC-5).
6. **Workers share the data trust zone** with the API but take no inbound
   client traffic; they consume the queue and the outbox.

---

## 5. Data residency posture

Phase 0 (legal-scope §3.4) prefers **Kenya-region, or a safeguarded region,**
hosting and a **Kenyan SMS aggregator** to minimise cross-border personal-data
transfers. The architecture:

- Keeps the **database and object storage in one chosen region**, selected to
  favour data residency subject to the DPIA (OPEN — see
  [technical-risks.md](technical-risks.md)).
- Applies **app-level envelope encryption** to HIGH-PII fields and objects (ID
  numbers, licence images, payout numbers) so region choice is not the only
  control.
- Records every processor and the data it receives (SMS, WhatsApp/Meta, geo,
  tiles, error tracking, hosting) for the **processor register** and the DPAs
  (legal-scope §4 item 4).
- Treats the **WhatsApp/Meta transfer** and the **recipient-link processing of a
  non-user's data** as explicitly REQUIRES VALIDATION items, surfaced in the
  Privacy Notice and recipient short terms.
