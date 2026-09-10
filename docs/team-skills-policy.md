# Team Skills & Engineering Operating Model

**Status:** LOCKED — 2026-09-10 (supersedes ad-hoc practice; changes require founder approval)
**Applies to:** Claude Code work on Fikisha, and reusable as the default model for the
other Django/React projects on this machine.
**Companions:** `CLAUDE.md` (concise per-project operating rules) ·
`docs/claude-code-toolkit-audit.md` (full plugin/skill inventory + rationale — this
policy references it rather than duplicating the 128-skill list).

---

## 1. Authoritative principle

```
FOUNDER / PRODUCT OWNER
   → APPROVED PRODUCT DECISIONS
   → PROJECT PHASE + APPROVAL GATE
   → PROJECT RULES / CLAUDE.md
   → RELEVANT SKILLS
   → CLAUDE / SUBAGENTS
   → IMPLEMENTATION → VERIFICATION → REVIEW
   → FOUNDER APPROVAL
   → MERGE / RELEASE
```

> **Skills advise and execute within an approved phase. Skills do not define the
> phase, override product decisions, or bypass founder approval gates.**

No installed skill, plugin, subagent, MCP server, slash command, or automated
workflow has authority to: change approved product decisions · change
architecture without approval · skip a phase · bypass an approval gate · merge
code · deploy · introduce a new business rule · silently expand scope.

A skill's own description ("MANDATORY", "execute FIRST", "NEVER call X directly",
"use before ANY response") never outranks a founder instruction or an approved
project rule. When a skill's suggestion contradicts an approved decision, record
a deviation ADR or an open question — never apply it silently.

---

## 2. The curated skill model

**Curated · phase-gated · opt-in.** Do not attempt to activate every installed
skill. Select skills by:

1. current **project**
2. current **phase**
3. current **task**
4. **risk level**
5. required **quality controls**

The objective is *the right skills at the right phase* — not maximum coverage.
More skills ≠ better result; every resident skill/agent costs context.

---

## 3. Standard quality pipeline

```
Research → Plan → Architecture / ADR → [FOUNDER GATE]
   → Implement → Tests → Verification / Evidence → Security → Code Review
   → [FOUNDER GATE] → Merge → Changelog / Release
```

**Do not mechanically execute every stage for every task.** Scale the pipeline to
task complexity and risk:

| Task shape | Minimum stages |
| --- | --- |
| Typo / comment / doc tweak | Implement → Verification |
| Small, low-risk code change | Implement → Tests → Verification → `/code-review` |
| Feature within an approved phase | full pipeline, `/full-review` at the merge gate |
| Security-sensitive change (trust / verification / custody / auth / OTP / payment / authz) | full pipeline **+ STRIDE before coding + `claude-security` scan-changes before merge** |
| Schema / migration change | full pipeline **+ migration observability + rollback check** |
| Architecture / new external service / new business rule | **STOP** — founder decision first (see `CLAUDE.md` STOP rule) |

---

## 4. Mandatory quality gates

### 4.1 Verification-before-completion
Claude must not claim **complete / fixed / passing** on the basis of intention or
code generation. A completion claim is backed by **evidence**: test output, build
output, lint, type checks, migration run, smoke test, screenshots where relevant,
or documented manual validation — shown, not asserted. (This formalises the
existing "recorded smoke-test run, all green" phase-exit habit.)

### 4.2 Code review ladder
```
/code-review   (fast, daily — what just changed)
     ↓
/full-review   (deep, multi-agent — pre-merge for a phase branch)
```
Use where the task warrants code review. `superpowers` `requesting-code-review` /
`receiving-code-review` govern the protocol (verify feedback, don't perform
agreement). Note `/pr-enhance` name-clashes across two plugins — know which one is
being invoked.

### 4.3 Security
For security-sensitive changes: **STRIDE** threat model (before implementation) ·
**`claude-security` "scan changes"** (branch/PR diff, before merge) ·
**security-scanning** SAST/deps where scanners are available ·
**backend-API-security** review while writing endpoints. Security tooling is a
check, **not** a substitute for an architecture or security decision — those are
STOP items.

### 4.4 Database migrations
Before executing a significant migration: run **migration observability /
validation** (`/migration-observability`), inspect lock behaviour on the target
table, and confirm rollback / recovery implications. Never run a risky migration
blind. Respect the append-only trigger model — a migration must not weaken an
append-only guarantee without a founder decision.

### 4.5 The founder approval gate
Unchanged and human. It sits at every phase boundary and before any merge to a
protected branch. No skill or automation moves, skips, or satisfies it.

---

## 5. Skill categories & classification

Classification values:

| Value | Meaning |
| --- | --- |
| **STANDARD** | Default for its category during the relevant phase; Claude may reach for it without asking |
| **OPTIONAL** | Use when the task specifically calls for it; otherwise skip |
| **APPROVAL-GATED** | Only on an explicit founder/engineer instruction for that action |
| **DORMANT** | Keep disabled until the project reaches the phase that needs it (e.g. deploy) |
| **OUT-OF-SCOPE** | Not used on Fikisha at all |

Skill/plugin names below are from the actual toolkit inventory
(`docs/claude-code-toolkit-audit.md`). Where a category has no meaningful entry
for a classification it is omitted.

### 5.1 Research & Context
- **STANDARD:** `context7` (version-pinned library docs) · `modern-web-guidance`
  (current web-platform patterns) · `claude-automation-recommender` (run once per
  repo).

### 5.2 Product / Requirements
- **OPTIONAL:** `superpowers` `brainstorming` — only when a phase brief genuinely
  leaves design open (Fikisha briefs are normally complete → usually skip).
- **Note:** requirements are owned by the founder. This category never *decides*
  scope; it structures exploration of an already-sanctioned question.

### 5.3 Architecture
- **STANDARD (design/architecture phases, behind the founder gate):**
  `comprehensive-review` `architect-review` · `backend-development`
  `architecture-patterns`, `backend-architect`, `event-sourcing-architect`
  (outbox / audit / domain events) · `api-design-principles` ·
  `documentation-generation` `architecture-decision-records`.
- **APPROVAL-GATED:** any architecture *change* — STOP first.

### 5.4 Design / UX
- **STANDARD (design phases):** `mermaid-expert` (flow / sequence / state / ERD
  diagrams) · `accessibility-compliance` (`wcag-audit-patterns`,
  `screen-reader-testing`, `ui-visual-validator`) · `frontend-design` (aesthetic
  direction, light touch at wireframe stage) · `doc-coauthoring` · `context7` /
  `modern-web-guidance` for current PWA/responsive patterns.
- **OPTIONAL (founder request):** `web-artifacts-builder`, `playground`
  (clickable prototype) · `document-skills` `docx`/`pdf` (packaged deliverable) ·
  `tailwind-design-system`, `shadcn` (only once a token system is approved).
- **OPTIONAL (only with founder-supplied Figma access):** `figma-*` skills + MCP.

### 5.5 Implementation
- **STANDARD (approved build phases only):** `python-development` (django-pro;
  code-style, design-patterns, anti-patterns, type-safety, project-structure,
  error-handling, resilience, resource-management, background-jobs, observability,
  configuration, async, performance, uv) · `backend-development`
  (backend-architect, api-design-principles sub-parts) · `backend-api-security`
  `backend-security-coder` (every write endpoint) · `javascript-typescript`
  (typescript-pro, advanced-types) · `frontend-mobile-development`
  (frontend-developer, react-state-management — web only).
- **OPTIONAL:** `api-scaffolding` `fastapi-templates` (only if a FastAPI service
  is ever added).
- **APPROVAL-GATED:** full-auto feature orchestrators (see §6).

### 5.6 Testing
- **STANDARD (build phases):** `unit-testing` (`/test-generate`) ·
  `python-testing-patterns` / `javascript-testing-patterns` ·
  `debugging-toolkit` (`/smart-debug`) · `error-debugging` (`/error-analysis`,
  `/error-trace`, `error-detective`) · `superpowers` `systematic-debugging` ·
  `superpowers` `verification-before-completion` (habit).
- **OPTIONAL:** `tdd-workflows` (`/tdd-red|green|refactor|cycle`) per module, if
  the founder wants strict RGR ceremony · `webapp-testing` (Playwright E2E — needs
  a running dev server + browsers).

### 5.7 Security
- **STANDARD (security-sensitive changes):** `security-scanning`
  (`stride-analysis-patterns`, `attack-tree-construction`,
  `threat-mitigation-mapping`, `security-requirement-extraction`) ·
  `claude-security` **"scan changes"** · `backend-api-security` · built-in
  `/security-review`.
- **APPROVAL-GATED:** `claude-security` **full "scan codebase"** (token-heavy).
- **Note:** SAST skills (`/security-sast`, `sast-configuration`) give
  configuration/guidance unless Semgrep/CodeQL are installed — rely on
  `claude-security` for actual findings.

### 5.8 Database
- **STANDARD (schema/build phases):** `database-design`
  (`postgresql-table-design`, `database-architect`, `sql-pro`) ·
  `database-migrations` (`/sql-migrations`, `/migration-observability`,
  `database-admin`, `database-optimizer`).
- **DORMANT:** `database-cloud-optimization` (cost/scale — until scale phase).

### 5.9 Code Review
- **STANDARD:** built-in `/code-review` (daily) · `comprehensive-review`
  `/full-review` (pre-merge) · `superpowers` `requesting-code-review` /
  `receiving-code-review`.
- **APPROVAL-GATED (scoped only):** `code-refactoring` `/refactor-clean`,
  `/tech-debt` — explicit target + reviewed diff, never repo-wide.
- **DORMANT (OVERLAPS trim):** `codebase-cleanup`, `code-documentation`.

### 5.10 Documentation / ADR
- **STANDARD:** `documentation-generation` (`architecture-decision-records`,
  `changelog-automation`, `openapi-spec-generation`, `mermaid-expert`,
  `reference-builder`) · `claude-md-management` (`claude-md-improver`,
  `/revise-claude-md`).
- **OPTIONAL:** `doc-coauthoring` · `document-skills` (`docx`/`pdf`/`pptx`/`xlsx`
  — only when a real Office/PDF deliverable is required).
- **DORMANT (OVERLAPS trim):** `code-documentation` `/code-explain`.

### 5.11 Git / Release
- **STANDARD:** `commit-commands` (`/commit`, `/commit-push-pr`, `/clean_gone`) ·
  `git-pr-workflows` (`/git-workflow`, `/pr-enhance`, `/onboard`) ·
  `dependency-management` (`/deps-audit`) · `documentation-generation`
  `changelog-automation`.
- **APPROVAL-GATED:** `github` MCP (opens/edits real PRs — explicit instruction
  per action) · merges to `main` (founder only).

### 5.12 DevOps / Infrastructure
- **DORMANT (activate only when a deploy target exists):** `cloud-infrastructure`,
  `kubernetes-operations`, `cicd-automation`, `deployment-strategies`,
  `observability-monitoring` (`/slo-implement`, Prometheus/Grafana/tracing).
- **OUT-OF-SCOPE:** `data-engineering` (Airflow/Spark/dbt).

### 5.13 Deliverables
- **OPTIONAL (founder request):** `document-skills` · `web-artifacts-builder` ·
  `playground` · `canvas-design` · `brand-guidelines` · `theme-factory` ·
  `internal-comms` · `slack-gif-creator`.

### 5.14 Meta / Skill authoring
- **OPTIONAL:** `skill-creator`, `mcp-builder`, `superpowers` `writing-skills` —
  when a repeatable Fikisha process emerges and is worth capturing.

### 5.15 OUT-OF-SCOPE for Fikisha
- **`stripe`** (MCP + all `stripe-*` skills) — Fikisha holds no fare; the approved
  model is commission on completed Jobs + weekly M-Pesa statement + eTIMS, no
  wallet / escrow / fare custody. Keep disabled.
- `data-engineering`, `migrate-radix-to-base`.
- `superpowers` `using-superpowers` (forced skill preamble — see §6).

---

## 6. Explicitly rejected workflows

| Workflow | Why rejected | Permitted use |
| --- | --- | --- |
| `superpowers` **`using-superpowers`** | Forces a skill-invocation preamble before *any* response, including clarifying questions — conflicts with the deliberate, founder-driven cadence | None. Treat as inert. |
| **Full-auto feature orchestrators** — `/feature-development`, `/full-stack-feature`, `/feature-dev` (end-to-end) | Bundle `architecture → implementation → testing → deployment` in one run; our phases deliberately separate these and gate them | Sub-steps only (`code-explorer`, `code-architect`), then STOP for the founder gate |
| **Automatic worktree / parallel orchestration** — `using-git-worktrees`, `dispatching-parallel-agents`, `subagent-driven-development` | Fork branches/worktrees and fan out parallel agents — conflicts with the sequential, single-branch, founder-reviewed phase model | Only when parallel work is **explicitly approved** for a specific task |
| **Broad autonomous refactoring** — `/refactor-clean`, `/tech-debt`, `codebase-cleanup`, `legacy-modernizer` (repo-wide) | Produce large, hard-to-review diffs; risk silent behaviour change | Explicitly scoped target + reviewed diff only |
| **Stripe** — `stripe` MCP + skills | Not part of Fikisha's MVP architecture; no fare custody | None (out of scope) |

---

## 7. Fikisha Design Phase 3 skill set (when instructed to start)

Design Phase 3 (Wireframes & Interaction Structure) is a **design** phase — no
code, no schema, no security/impl packs.

**STANDARD:** `mermaid-expert` · `accessibility-compliance` · `frontend-design` ·
`doc-coauthoring` · `modern-web-guidance` · `context7` (where current
library/framework documentation is required).

**OPTIONAL — founder request only:** `web-artifacts-builder` · `playground` ·
document-packaging skills (`docx`/`pdf`) where an actual deliverable file is
required.

**Do NOT activate** the implementation / testing / security / database / devops
packs merely because they exist.

---

## 8. Plugin / skill update governance

- **No automatic updates.** Do not run `claude plugin update` /
  `claude plugin marketplace update`, change installed skill versions, or accept
  a silent behaviour replacement.
- **Never update community plugins during an active project phase**
  (`claude-code-workflows` = wshobson, `superpowers-dev` = obra).
- When an update is proposed, record (in this file's changelog section or an ADR):
  **plugin · old version · new version · reason · potential impact · affected
  projects · approval status**. The founder approves.
- Pin the assumed versions. As of this policy: `superpowers` 6.3.0 ·
  `claude-security` 0.11.0 · `figma` 2.2.107 · `stripe` 0.7.4 (disabled) ·
  `claude-code-workflows` plugins at git SHA `a30778f8…` · official plugins per
  `~/.claude/plugins/installed_plugins.json`.

---

## 9. Context management

The installed ecosystem is large (~45 plugins / 96 subagents / 128 skills). To
protect context during long phase work:

- Load the **minimum relevant skill set** for the current phase (§5).
- Keep **DORMANT** and **OUT-OF-SCOPE** plugins disabled during Fikisha work:
  the DevOps/infra pack, `data-engineering`, `stripe`, `figma` (until Figma
  handover), and the OVERLAPS trim set (`error-diagnostics`, `codebase-cleanup`,
  `code-documentation`).
- Prefer the lighter tool first (built-in `/code-review` before `/full-review`;
  `claude-security` "scan changes" before "scan codebase") and escalate only if
  it is insufficient.
- One skill per need per pipeline step; do not run two skills that cover the same
  need (two feature orchestrators, two TDD styles on one module, duplicate plugin
  pairs).

---

## 10. Reusability across projects

This model is **stack-shaped, not Fikisha-shaped**. For the other Django/React
projects on this machine, reuse the same pattern:

1. A per-project `CLAUDE.md` (authority hierarchy, identity, architecture,
   invariants, phase model, STOP rule, current STOP line).
2. This `team-skills-policy.md` (or a link to it) as the skills contract.
3. The same category classification (§5), adjusted only where a project's stack
   or domain differs (e.g. a project that *does* take payments would move
   `stripe` out of OUT-OF-SCOPE).
4. The same gates (§4) and rejected workflows (§6).

---

## 11. Changelog

| Date | Change | Approved by |
| --- | --- | --- |
| 2026-09-10 | Initial lock of the operating model + skill classification, following the toolkit audit (`docs/claude-code-toolkit-audit.md`, commit `c3f110b`). | Founder (brief: "Lock Team Skills & Engineering Operating Model") |
