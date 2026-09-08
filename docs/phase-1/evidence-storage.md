# Evidence & File Storage

Implements Phase 0 `NFR-SEC-4`, `NFR-SEC-8`, `FR-C-7`, `NFR-INT-4`, `NFR-PRIV-2`.

Covers: identity / licence / vehicle / inspection / insurance / good-conduct
documents, pickup & delivery photos, signatures, incident & dispute evidence,
profile & base photos.

---

## 1. Principles

1. **All media is private.** No object is ever served from a public bucket URL.
2. **The API mediates every upload and every download** — it authorizes, it
   validates, it logs.
3. **Integrity is provable** — every referencing domain row stores the object's
   SHA-256; a swapped file is detectable.
4. **HIGH-PII gets a second lock** — application-level envelope encryption on top
   of storage encryption, and an access-log row per fetch.
5. **Retention is enforced** — objects are deleted on a schedule unless a legal
   hold is set.

---

## 2. Storage layout

| Aspect | Design |
|--------|--------|
| Backend | S3-compatible (`django-storages` + `boto3`). Pilot: a managed bucket in the chosen region, or MinIO on the pilot host. Provider/region is **OPEN** and **REQUIRES VALIDATION** (data residency, legal-scope §3.4). |
| Bucket | One **private** bucket, `block all public access`, versioning **on** (accidental-overwrite protection; not a substitute for the append-only domain rows). |
| At-rest encryption | Bucket **SSE** (SSE-S3 or SSE-KMS). |
| Key structure | `evidence/<purpose>/<yyyy>/<mm>/<object_uuid>` — no PII, no guessable enumeration (UUIDv7). |
| Metadata | The `evidence_object` row (see [database-design.md](database-design.md) §4.13) is the source of truth for `content_type`, `size`, `sha256`, `pii_class`, `purpose`, `retention_class`, `linked_entity`, `envelope_key_ref`, `scan_status`, `legal_hold`, `expires_at`. |

---

## 3. Upload flow (API-mediated — RECOMMENDED for the MVP)

Pre-signed `PUT` is faster on bandwidth but pushes validation post-hoc and can't
strip EXIF. For the pilot's data-protection posture and low-end-device reality,
**upload through the API**:

```mermaid
sequenceDiagram
    participant C as Client (PWA)
    participant API
    participant EV as Evidence Service
    participant SC as ClamAV (worker)
    participant OBJ as Object storage

    C->>C: client-side compress image (<= 1600px, ~200-500 KB JPEG)
    C->>API: POST /evidence  (multipart: file, purpose, linked_entity)  Authorization: Bearer
    API->>EV: begin(purpose, linked_entity, actor)
    EV->>EV: authorize actor may attach evidence to linked_entity
    EV->>EV: sniff magic bytes (not just extension); enforce size + type allowlist per purpose
    alt image
        EV->>EV: re-encode (drop EXIF/GPS), make a thumbnail, compute SHA-256
        EV->>OBJ: PUT object (+ envelope-encrypt if pii_class=HIGH)
        EV->>API: 201 { evidence_id, sha256, thumb_url }
    else non-image (PDF, etc.)
        EV->>OBJ: PUT object, scan_status = PENDING (quarantined)
        EV-->>SC: enqueue scan
        SC->>OBJ: fetch, ClamAV scan
        SC->>EV: CLEAN -> usable  /  INFECTED -> delete + alert
        EV->>API: 201 { evidence_id, sha256, scan_status }
    end
```

- **Type allowlist per `purpose`**: e.g. `PROOF_OF_DELIVERY` → JPEG/PNG/WebP only;
  `VERIFICATION_DOC` → JPEG/PNG/PDF; `SIGNATURE` → PNG. Reject everything else.
- **Size caps per purpose** (config): photos ≤ ~5 MB pre-compression, documents
  ≤ ~10 MB.
- **EXIF/GPS stripped** from every image on re-encode — location only enters the
  system via the explicit custody `geo` capture, never smuggled in a photo
  (NFR-PRIV-1/4).
- **SHA-256** computed server-side and returned; the caller stores it on the
  domain row (`job_event.content_hashes`, `verification_record.current_evidence_ids`
  + the object's own `sha256`).
- Non-images stay `PENDING` (unusable, quarantined) until ClamAV returns `CLEAN`
  (NFR-SEC-8). Images skip AV (re-encoding neutralises most image-borne payloads)
  but are still type-sniffed and size-capped.
- **Idempotency-Key** on the upload so a PWA retry doesn't create a duplicate.

Offline capture: the PWA queues photos in IndexedDB (bounded — see
[pwa-architecture.md](pwa-architecture.md)) and replays the upload on reconnect
with the stored idempotency key.

---

## 4. Download / view flow

```
GET /evidence/{id}          -> 302 to a short-lived signed URL  (default)
GET /evidence/{id}/raw      -> streams bytes through the API    (HIGH-PII, or when
                               the client can't follow cross-origin redirects)
GET /evidence/{id}/thumb    -> thumbnail (MEDIUM/LOW only; HIGH-PII has no thumb)
```

Every request:

1. **Authorizes** the actor against the object's `linked_entity`:
   - custody photo / POD → the job's business, the assigned operator/driver, admins;
   - verification document → **Verifier permission only** (NFR-SEC-4, NFR-PRIV-6);
   - incident/dispute evidence → parties to that incident + admins;
   - recipient (link) → only POD they captured, for their job.
2. For `pii_class = HIGH`: writes an **`evidence_access_log`** row (who, when,
   which object, reason, job/incident context) — NFR-SEC-4.
3. Returns a **signed URL with a short TTL** (e.g. 120 s) **or** streams bytes.
   The bucket URL / storage key is **never** returned to the client
   (NFR-SEC-8).
4. Envelope-encrypted objects are decrypted **in the API** (data key unwrapped
   via KMS), streamed, and never written to disk.

Signed URLs are single-purpose, expire fast, and are not logged in full.

---

## 5. Encryption model

| Tier | At rest | Additional |
|------|---------|-----------|
| `LOW` (e.g. base photo) | bucket SSE | — |
| `MEDIUM` (custody photo, POD, signature, incident photo) | bucket SSE | — |
| `HIGH` (ID/passport image, licence image, good-conduct scan) | bucket SSE **+ application envelope encryption**: a random AES-256-GCM data key encrypts the object; the data key is wrapped by a **KMS master key**; `envelope_key_ref` + wrapped key stored on the row. | decrypt only in the API, only for the Verifier permission, only logged |

HIGH-PII **fields** (ID number, `payout_number`) use the same envelope scheme at
the column level (`*_encrypted BYTEA` + `*_key_ref`), with an HMAC **blind index**
only where a lookup is genuinely needed. See [database-design.md](database-design.md) §3.

Keys: master keys in a managed KMS (or, for the smallest pilot, a well-guarded
key in the secrets store with a documented rotation plan). Separate keys per
environment. Rotation re-wraps data keys without re-encrypting objects.

---

## 6. Retention & deletion (NFR-PRIV-2, legal-scope §7 — REQUIRES VALIDATION)

`retention_class` on each object drives a **daily retention sweep** beat job:

| `retention_class` | Applies to | Delete when |
|-------------------|-----------|-------------|
| `VERIFICATION_DOC` | ID / licence / vehicle / good-conduct images | 12 months after the subject is offboarded **or** the document's `expires_at`, whichever first |
| `CUSTODY_MEDIA` | pickup/POD/custody photos, signatures | 7 years after job completion |
| `INCIDENT_MEDIA` | incident & dispute evidence | 7 years after incident closure |
| `PROFILE_MEDIA` | profile / base photos | on offboarding + short tail |

Deletion: the sweep removes the object from storage, nulls the domain row's
`current_evidence_ids` / `photo_evidence_ids` entries, and writes an
`EvidencePurged` audit row. The **domain rows** (verification record, custody
event, incident) **remain** — the fact and its hash are kept; only the media is
gone. A `legal_hold = true` object is skipped until the hold is lifted.

---

## 7. Integrity (NFR-INT-4)

- The object's `sha256` is stored on the `evidence_object` row **and** copied
  onto the referencing domain row (`content_hashes`).
- A background check (weekly) can re-hash a sample of objects and compare — a
  mismatch is an alert.
- Bucket versioning + the append-only domain rows mean a tampered object is both
  detectable and recoverable.

---

## 8. What is deliberately excluded

- No client-facing pre-signed **PUT** in the MVP (revisit if upload latency in
  the field is a real problem — [technical-risks.md](technical-risks.md)).
- No CDN in front of private media (short-TTL signed URLs from the bucket are
  enough at pilot scale; a CDN would add a caching layer to reason about for
  private content).
- No image ML (blur detection, doc classification) beyond the optional
  verification assist checks (FR-V-8).

---

## 9. Events

| Emits | Consumers |
|-------|-----------|
| `EvidenceStored` | the module that requested the upload (attach to its row) |
| `EvidenceScanClean` / `EvidenceScanInfected` | Evidence (mark usable / delete + alert); Notifications on infected |
| `EvidenceAccessed` (HIGH-PII) | Reporting (access-audit stats); Security monitoring |
| `EvidencePurged` | Audit |

| Consumes | For |
|----------|-----|
| beat tick (daily) | retention sweep |
| beat tick (per-minute) | drain the scan queue |
| `AccountOffboarded` | schedule verification-doc + profile-media deletion |
