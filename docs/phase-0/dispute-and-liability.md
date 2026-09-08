# Disputes and Liability

## 1. Stance on liability

**The platform is not automatically liable for every incident.** It is a
coordination layer over transport capacity it does not own. Its role in an
incident is to **record evidence, structure the process, and facilitate
resolution** — starting from the amicable practice that already exists between
parties — and to escalate when that fails.

- The platform does **not** invent legal, insurance, or liability guarantees.
- Where liability, insurance, goods-in-transit cover, consumer-protection, or
  carrier-responsibility rules are uncertain, they are recorded as
  **REQUIRES KENYAN PROFESSIONAL VALIDATION** and must be confirmed with
  qualified Kenyan legal/insurance advisors before any commitment is made to
  users.
- Terms of Service and an operator agreement will need to state, in validated
  language, what the platform does and does not undertake. Drafting these
  **REQUIRES KENYAN PROFESSIONAL VALIDATION** and is an input to Phase 1, not a
  Phase 0 output.

---

## 2. Incident types (from the brief)

`DAMAGE`, `LOSS`, `MISSING_GOODS` (partial shortage), `WRONG_RECIPIENT`,
`WRONG_PICKUP`, `MISCONDUCT`, `BREAKDOWN`, `ACCIDENT`, `DELAY`, `CANCELLATION`,
`OTHER` (free-text label required).

Each incident carries a **severity** (LOW / MEDIUM / HIGH / CRITICAL —
administrator-set, with defaults by type) that influences SLA and escalation.

---

## 3. Data model (conceptual — see [domain-model.md](domain-model.md))

- **Incident** — type, severity, reported_by, reported_at, description, related
  job, related chain-of-custody entries, status, current owner (admin),
  timeline.
- **Evidence** — media/document references, uploaded_by, uploaded_at, type,
  integrity hash, caption. Append-only.
- **Statement** — party, role, text, submitted_at, related incident. Append-only;
  a party may add further statements but not edit prior ones.
- **Dispute** — created when parties do not agree on the incident outcome;
  links one or more incidents; has status, assigned officer, resolution.
- **Resolution** — outcome code, rationale, any recorded financial adjustment
  (e.g. commission waived/reduced, agreed compensation between parties —
  **recorded, not necessarily processed by the platform in MVP**), actions taken
  (ratings impact, trust-level change, suspension), resolved_by, resolved_at.
- **Escalation** — reason, from/to, timestamp; e.g. to founder, or a note that
  parties have been advised to pursue external/legal channels.

All of the above are **append-only** and fully **audit-logged**.

---

## 4. Process

```
1. REPORT
   Any involved party (business, operator) — and, recommended, the recipient via
   a link — can open an incident against a job. Admin can also open one.
   Job moves to DISPUTED if the incident blocks progression (see job-lifecycle.md).

2. EVIDENCE & STATEMENTS
   Parties upload photos/documents and submit statements within a configurable
   window. The relevant chain-of-custody entries are automatically attached.

3. AMICABLE RESOLUTION FIRST
   The platform presents both parties' positions and a structured prompt to
   agree an outcome directly (matches existing practice). If they agree, the
   agreed outcome is recorded as the Resolution and the job is routed to its
   terminal state.

4. ADMINISTRATIVE REVIEW
   If no agreement, a dispute officer reviews job data, negotiation history,
   chain of custody, evidence, and statements, then records a Resolution with
   rationale and actions.

5. RESOLUTION
   Outcome recorded. Job routed to COMPLETED / FAILED / CANCELLED (or resumed to
   its pre-dispute state if the issue is cleared and admin allows — open
   question in job-lifecycle.md). Commission treatment decided (applies /
   reduced / waived). Reputation and trust effects applied.

6. ESCALATION
   For CRITICAL matters (accident with injury, theft, fraud) or unresolved
   disputes, the officer escalates to the founder and records that parties have
   been advised of external options. The platform does not adjudicate criminal
   matters; it preserves records that parties or authorities may need.
```

### 4.1 SLA targets (WORKING ASSUMPTION — tune in pilot)
| Severity | Acknowledge | First admin action | Target resolution |
|----------|-------------|--------------------|-------------------|
| CRITICAL | ≤ 1h | ≤ 2h | Case-by-case; immediate escalation |
| HIGH | ≤ 4h | ≤ 8h | ≤ 3 days |
| MEDIUM | ≤ 12h | ≤ 24h | ≤ 5 days |
| LOW | ≤ 24h | ≤ 48h | ≤ 7 days |

---

## 5. Financial adjustments in disputes (MVP boundary)

- MVP does **not** hold funds, so the platform **cannot** force a refund or
  payout between parties. It can:
  - **Record** an agreed compensation between the parties.
  - **Adjust its own commission** (waive/reduce) for the job.
  - Apply **reputation and trust** consequences.
- Whether the platform should later hold funds / offer a resolution fund /
  facilitate compensation is a **FUTURE CONSIDERATION** and
  **REQUIRES KENYAN PROFESSIONAL VALIDATION**.

---

## 6. Reputation & trust consequences

- Confirmed fault (via amicable agreement or admin finding) is recorded against
  the responsible party and feeds:
  - the two-way rating summary,
  - operator trust-level assessment (serious or repeated fault can block
    progression or cause regression / Restricted status),
  - business standing (repeated bad-faith reports or non-payment can restrict a
    business).
- Unfounded or bad-faith reports are themselves recorded and can count against
  the reporter.

---

## 7. What the platform explicitly does NOT claim (pending validation)

| Claim NOT made in MVP | Reason |
|-----------------------|--------|
| That the platform insures cargo | No insurance product; REQUIRES KENYAN PROFESSIONAL VALIDATION |
| That the platform guarantees delivery, timing, or condition | It coordinates independent operators |
| That the platform is the carrier / freight forwarder of record | Legal characterisation REQUIRES KENYAN PROFESSIONAL VALIDATION |
| That the platform will compensate for loss/damage | Not without a validated policy and funding mechanism |
| That platform verification equals a legal fitness certification | Verification is platform due diligence, not a regulatory act |

These boundaries must be reflected accurately in user-facing terms — drafted with
qualified Kenyan counsel in Phase 1.

---

## 8. Open questions

| Question | Recommendation |
|----------|----------------|
| Can recipients raise incidents without an account? | Yes, via a per-job link — catches wrong-recipient/damage early *(still OPEN — founder to confirm)* |
| Is there a post-completion dispute window, and how long? | **RESOLVED 2026-09-08 (D-JOB-5): 72h all bands; 7 days for High/Very-high & latent-risk cargo.** Delivery-acceptance auto-complete: 24h Standard/Elevated, 48h High+. |
| Should the platform ever hold a small dispute/resolution fund? | Defer; validate legally first |
| Who is the escalation point of last resort during the pilot? | The founder; document contact + hours |
| Do we need a standard evidence checklist per incident type? | Yes — build simple per-type prompts (e.g. DAMAGE → photos of goods + packaging + waybill) |
| External reporting obligations (police abstract for accidents, etc.) | REQUIRES KENYAN PROFESSIONAL VALIDATION |

---

## 9. Status summary

| Item | Category |
|------|----------|
| Platform is not automatically liable; records + facilitates | CONFIRMED DECISION |
| Incident → evidence/statements → amicable-first → admin review → resolution → escalation | CONFIRMED DECISION |
| Append-only, audit-logged incident/evidence/statement/resolution records | CONFIRMED DECISION |
| No platform-forced refunds/payouts in MVP; commission adjustment + reputation only | CONFIRMED DECISION (consequence of no-escrow MVP) |
| SLA targets | WORKING ASSUMPTION — tune in pilot |
| Post-completion & delivery-acceptance dispute windows | CONFIRMED 2026-09-08 (D-JOB-5) |
| Cancellation consequences (reputation-only; "3 in 30 days" → admin flag) | CONFIRMED 2026-09-08 (D-DIS-3) |
| Recipient-initiated incidents | OPEN QUESTION — recommend yes |
| Any liability / insurance / carrier-status / ToS language | REQUIRES KENYAN PROFESSIONAL VALIDATION — full map in [legal-scope.md](legal-scope.md) |
