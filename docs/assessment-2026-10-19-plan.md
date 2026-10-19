# Founder assessment — 2026-10-19: findings, plan and decisions

**Source:** the founder's hands-on assessment on 2026-10-19 (one admin, one
operator and one business account created in local dev). Claude traced each
point through the code and proposed a plan. **D-1 to D-6 approved as
recommended, 2026-10-19.** This record is the authoritative copy.

## The assessment

- **Operator:** vehicle registration always in capitals. After registration
  the operator sees only registration screens; jobs, messages and the other
  sections open only after approval.
- **Business:** after registration, a pop-up "Your profile has been submitted
  for verification". When requesting a job, pickup is a dropdown of the
  locations the business entered. The category becomes a dropdown or input
  that updates the product category automatically.
- **Admin:** the verification queue has a selector at the top for each kind of
  user; requests are grouped under the operator/business being registered,
  with all their submitted data on one screen. There is no business
  verification panel today.
- **Product categories:** a "smart" module — a product entered without a
  category gets one on its own.

## Findings

| # | Finding | Where |
| --- | --- | --- |
| F-1 | **A business can never be verified.** `DRAFT → REQUESTED` requires `business.verification_status = VERIFIED` (`BusinessVerifiedWithLocation`), but no endpoint, screen or command sets it. Real businesses cannot post a job; seeded ones were set directly in the database. The light check of `phase-1/verification-architecture.md` §7 was never built. Groups have the same unused flag. | `jobs/guards.py:58`, `business/models.py:61`, `groups/models.py:65` |
| F-2 | **An operator is never approved.** Operators start `PENDING` and nothing moves them to `ACTIVE`; `PENDING` counts as operational, so a new operator already sees Work (jobs marked ineligible). | `operators/models.py:24,68`, `jobs/discovery.py:47` |
| F-3 | Only the hidden `registration_normalized` copy of a plate is uppercased; the displayed plate is stored as typed. | `vehicles/models.py:41,111` |
| F-4 | Pickup is free text only. Copying a saved `BusinessLocation` into the job (`source_kind=BUSINESS_LOCATION`) is in the schema but was deferred for lack of a caller. | `jobs/creation.py:13`, `jobs/models.py:82` |
| F-5 | Cargo category is free text, not checked against config `cargo_categories`; the business-profile category is free text too. | `jobs/api/serializers.py:25`, `CreateJobPage.tsx:277` |
| F-6 | **The 7-day post-completion window for latent-risk cargo (D-JOB-5) never applies from the app.** It keys off `job.latent_risk_cargo`, which the create form never sends and which is not derived from the category; config `latent_risk_categories` is unused. | `jobs/guards.py:537`, `platform_config/defaults.py:85` |
| F-7 | The verification queue is a flat list of records ("OPERATOR · IDENTITY") covering operators, vehicles and operating locations only. | `VerificationQueuePage.tsx` |

## Decisions (approved as recommended, 2026-10-19)

| # | Decision | Approved answer |
| --- | --- | --- |
| D-1 | How business verification is modelled | A `BUSINESS` subject in the existing verification module (documents optional: business registration certificate, KRA PIN). Approval by a reviewer sets `business.verification_status = VERIFIED`. A deviation from the "single flag" of verification-architecture §7, approved as such. |
| D-2 | What "approved operator" means | An explicit, audited admin **Approve** action (`PENDING → ACTIVE`) after review — not automatic when records reach `VERIFIED` (verification records facts; it decides nothing). |
| D-3 | Lock-out of pending operators | Enforced server-side as well: a `PENDING` operator gets no work discovery and cannot negotiate. Existing `ACTIVE` operators are unaffected. |
| D-4 | Which "categories section" | The cargo category when requesting a job; the business-profile category gets the same picker. |
| D-5 | How "smart" categories are | Deterministic keyword matching (EN + SW, held in platform config) suggests a category from the cargo description; no match → `OTHER` with the description kept; an admin "uncategorised" list lets a Platform Admin add a keyword or category through the normal audited, step-up config apply. The system never creates categories on its own (categories are admin-set platform rules, FR-ADM-6, and drive the dispute window); no AI classifier (new external service). The category also sets `latent_risk_cargo` (fixes F-6). |
| D-6 | Groups in the verification queue | Yes — a Groups tab, with the same approval action for the group's flag. |

## Plan (each part its own branch and PR)

1. **Plates in capitals** — uppercase as typed; backend stores uppercase;
   data migration for existing vehicles.
2. **Pickup from saved locations** — dropdown of the business's active
   locations plus "Another address"; API accepts `business_location_id`,
   snapshots it; ownership check + IDOR test.
3. **Business verification** — `BUSINESS` verification subject; submitted
   pop-up + Home banner; "Request transport" disabled with a reason until
   verified; reviewer approval sets the business flag (audited).
4. **Operator approval + lock-down** — admin Approve operator action;
   pending operators see Home checklist, Profile, Vehicles, Operating
   locations and verification only; server refuses discovery and negotiation.
5. **Verification queue by applicant** — tabs Operators · Businesses ·
   Groups; one row per applicant with progress; applicant page with profile,
   every record and evidence, per-record actions and the approval action.
   Per-record decisions, `reviewer_is_submitter` and per-fetch evidence
   authorisation unchanged.
6. **Smart cargo categories** — picker over configured categories (EN/SW),
   server-side validation, keyword suggestion, uncategorised list, category
   → `latent_risk_cargo`.
