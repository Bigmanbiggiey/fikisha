# Claude Code Toolkit — Audit & Team Skill Policy

**Status:** DISCOVERY / AUDIT — FOR FOUNDER DECISION
**Date:** 2026-09-10
**Scope:** read-only inspection of `C:\Users\PCMF\Documents\claude-code-toolkit` and the
plugin state it documents (`~/.claude/plugins/`).
**Explicitly not done:** no toolkit file changed; no Fikisha application code, model, API,
schema, or existing doc changed; Design Phase 3 not started; no plugin installed, enabled,
disabled, or updated.

---

## 1. Executive summary

**What it is.** The "toolkit" is **not a set of custom in-house skills**. It is a
**15-file, read-only documentation package** that inventories and explains a large set of
**Claude Code plugins that are already installed on this machine at user scope**
(`~/.claude/`), so they are active in every project including Fikisha. The folder contains
zero executable code, zero project configuration, and nothing Fikisha-specific.

**What was actually installed (verified against `~/.claude/plugins/installed_plugins.json`):**
**45 plugins** from 4 marketplaces + 2 loose skills, bundling roughly **51 slash commands,
96 subagents, 128 skills, and 4 MCP servers** (`github`, `context7`, `figma`, `stripe` —
each dormant until separately authed).

**Sources:** Anthropic official (`claude-plugins-official`, 12 plugins), a **community**
repo `wshobson/agents` (`claude-code-workflows`, 30 plugins), a **community** repo
`obra/superpowers` (`superpowers-dev`, 1 plugin / 13 workflow skills), Anthropic
`anthropics/skills` (`document-skills` + `example-skills`, 16 skills), and 2 loose
`shadcn` skills.

**Bottom line.** The plugin set is a strong capability library for the Fikisha stack
(Django/DRF · PostgreSQL · React PWA · Docker). Most of its value lands **later**, in the
first heavy implementation phase (Phase 2D+). A meaningful minority is **redundant** with
disciplines Fikisha already practises (docs-before-code, ADRs, clean commits, recorded
verification, approval gates). A small but important set **conflicts** with Fikisha's
founder-gated, single-branch, sequential phase model — chiefly the "always-on" and
"MANDATORY" self-activating skills, the full-auto feature orchestrators, and the
git-worktree / parallel-subagent skills. None of it should silently change an approved
product or architecture decision, and nothing in the toolkit forces that if adoption is
deliberate.

**Recommended adoption model:** *curated, phase-gated opt-in*. Adopt ~12 plugins as
"standard for implementation phases", keep ~20 dormant until relevant, treat ~6 as
"manual-approval only", and do not use `stripe` at all (wrong domain for Fikisha).

**Highest-priority action, independent of the toolkit:** Fikisha has **no `CLAUDE.md`**.
Create one.

---

## 2. Toolkit structure

```
claude-code-toolkit/                         (15 files, ~250 KB, all Markdown, read-only)
├── README.md            overview, "what got installed", how the piece types work
├── INSTALL.md           marketplaces, exact install commands, re-install script,
│                        `claude plugin` management commands, MCP first-use auth, token-cost notes
├── OVERLAPS.md          8 slash-command name clashes; redundant plugins; subagent name spam;
│                        token/context cost; trust & safety notes
├── LINKS.md             upstream doc URLs for every marketplace, plugin, MCP, and stack tech
├── reference/
│   ├── plugins.md       every plugin → its commands / agents / skills / MCP (45 plugins)
│   ├── commands.md      all 51 slash commands in one table (+ clash warnings)
│   ├── agents.md        all 96 subagents, grouped by plugin (many namespaced duplicates)
│   └── skills.md        all 128 skills, grouped by plugin, with trigger descriptions
└── guides/             task playbooks for this machine's stack
    ├── 01-frontend-react.md          React / Tailwind / TS / Next.js
    ├── 02-backend-python.md          Django / Flask / FastAPI / Python
    ├── 03-databases.md               PostgreSQL / MySQL / MongoDB
    ├── 04-devops-cloud.md            Docker / K8s / AWS / CI-CD / observability
    ├── 05-quality-security-testing.md  review / security / testing / TDD
    ├── 06-docs-and-workflow.md       docs / CLAUDE.md / git-PR / feature planning
    └── 07-deliverables.md            docx / pdf / xlsx / pptx / diagrams / brand assets
```

Nothing here is a "skill" in the Claude Code sense — the `guides/*` files are curated
prose playbooks, and the `reference/*` files are generated indexes. The behaviour-changing
artifacts are the **installed plugins**, which live in `~/.claude/plugins/cache/` and are
listed in `~/.claude/plugins/installed_plugins.json` (all `"scope": "user"`,
installed 2026-09-09).

### Piece types (from README.md)

| Type | How it activates | Count |
| --- | --- | --- |
| **Skill** | Loads automatically when the model judges it relevant; a few are user-invocable as `/name` | ~128 |
| **Slash command** | User types `/name` | ~51 |
| **Subagent** | Delegated via the Task tool, or "use the X subagent"; runs in its own context | ~96 |
| **MCP server** | Adds tools once connected/authed | 4 (`github`, `context7`, `figma`, `stripe`) |

### Internal inconsistencies noted

- README says "51 slash commands · 96 subagents · 128 skills"; `plugins.md` header says
  "45 plugins"; the README marketplace table sums to 47 plugin-equivalents (12+30+1+2+2).
  Minor; counts below use `installed_plugins.json` as the source of truth (45 plugins).
- `commands.md` renders with the header row (`| Command | Plugin | What it does |`) at the
  bottom of the table — a cosmetic Markdown glitch, not a content problem.
- Several skill descriptions are truncated mid-sentence in `skills.md` / `plugins.md`
  (upstream copy, not a local error).

---

## 3. Skill / plugin inventory

Because the surface is 128 skills + 96 subagents, a 128-row table would be low-signal.
This inventory is at **plugin granularity** (the unit you enable/disable), followed by a
**deep-dive on the individual skills that matter most for Fikisha**. Per-skill trigger
text is in `reference/skills.md`.

### 3a. Plugin inventory (all 45 + loose + relevant built-ins)

Legend — **Relevance:** F = Fikisha-relevant now/soon · L = later (deploy/scale) ·
S = specialised/rare · X = out of scope. **Rec:** Adopt = standard for implementation
phases · Adapt = use sub-parts only · Optional = situational · Caution = manual approval ·
Off = keep disabled during Fikisha work.

| Plugin | Source | Bundles | Purpose | Rel | Rec |
| --- | --- | --- | --- | --- | --- |
| **context7** | official | MCP | Live, version-pinned library docs injected into context | F | Adopt |
| **claude-md-management** | official | `/revise-claude-md`, `claude-md-improver` skill | Create/audit/maintain `CLAUDE.md` | F | Adopt |
| **claude-code-setup** | official | `claude-automation-recommender` skill | Recommend hooks/skills/subagents/MCP for a repo | F | Adopt (run once) |
| **commit-commands** | official | `/commit`, `/commit-push-pr`, `/clean_gone` | Clean commits / PR creation | F | Adopt |
| **comprehensive-review** | wshobson (community) | `/full-review`, `/pr-enhance`; `architect-review`, `code-reviewer`, `security-auditor` agents | Deep multi-agent review as a release gate | F | Adopt (pre-merge) |
| **feature-dev** | official | `/feature-dev`; `code-architect`, `code-explorer`, `code-reviewer` agents | Guided single-repo feature: explore→architect→implement→review | F | Adapt (sub-steps only) |
| **backend-development** | wshobson | `/feature-development`; `backend-architect`, `event-sourcing-architect`, `graphql-architect`, `performance-engineer`, `security-auditor`, `tdd-orchestrator`, `test-automator` agents; 10 skills (architecture-patterns, api-design-principles, cqrs, saga, event-store, projections, microservices, temporal…) | Backend architecture + feature orchestration | F | Adapt |
| **python-development** | wshobson | `django-pro`, `fastapi-pro`, `python-pro` agents; 17 skills (code-style, design-patterns, anti-patterns, type-safety, testing-patterns, error-handling, resilience, background-jobs, observability, configuration, packaging, project-structure, performance, async, resource-management, uv) | Modern Python / Django engineering discipline | F | Adopt |
| **api-scaffolding** | wshobson | `backend-architect`, `django-pro`, `fastapi-pro`, `graphql-architect` agents; `fastapi-templates` skill | Greenfield API surface design | F | Adapt |
| **backend-api-security** | wshobson | `backend-architect`, `backend-security-coder` agents | Secure-coding while writing endpoints (authn/z, rate-limit, input validation) | F | Adopt (endpoint work) |
| **database-design** | wshobson | `database-architect`, `sql-pro` agents; `postgresql-table-design` skill | Schema design, PG types/indexes/constraints | F | Adopt |
| **database-migrations** | wshobson | `/sql-migrations`, `/migration-observability`; `database-admin`, `database-optimizer` agents | Zero-downtime migrations, lock analysis, rollback plans | F | Adopt |
| **javascript-typescript** | wshobson | `/typescript-scaffold`; `javascript-pro`, `typescript-pro` agents; 4 skills (advanced-types, modern-patterns, testing-patterns, nodejs-backend) | TS type-safety and JS idioms for the PWA | F | Adopt |
| **frontend-mobile-development** | wshobson | `/component-scaffold`; `frontend-developer`, `mobile-developer` agents; 4 skills (nextjs-app-router, react-native, react-state-management, tailwind-design-system) | React UI implementation | F | Adopt (web parts) |
| **frontend-design** | official | `frontend-design` skill | Distinctive, non-templated visual design direction | F | Adopt (design phases) |
| **modern-web-guidance** | official | `modern-web-guidance`, `chrome-extensions` skills | Current web-platform best practice search | F | Optional |
| **accessibility-compliance** | wshobson | `/accessibility-audit`; `ui-visual-validator` agent; `wcag-audit-patterns`, `screen-reader-testing` skills | WCAG 2.2 audits, AT testing, visual validation | F | Adopt (all UI) |
| **tdd-workflows** | wshobson | `/tdd-red|green|refactor|cycle`; `tdd-orchestrator`, `code-reviewer` agents | Strict red-green-refactor discipline | F | Optional (per module) |
| **unit-testing** | wshobson | `/test-generate`; `test-automator`, `debugger` agents | Generate/structure test suites | F | Adopt |
| **debugging-toolkit** | wshobson | `/smart-debug`; `debugger`, `dx-optimizer` agents | Methodical root-cause debugging | F | Adopt |
| **error-debugging** | wshobson | `/error-analysis`, `/error-trace`, `/multi-agent-review`; `debugger`, `error-detective` agents | Stack-trace / log analysis | F | Adopt |
| **error-diagnostics** | wshobson | near-duplicate fork of error-debugging (+`/smart-debug` alias) | — | F | Off (dup — OVERLAPS trim) |
| **code-refactoring** | wshobson | `/refactor-clean`, `/tech-debt`, `/context-restore`; `code-reviewer`, `legacy-modernizer` agents | SOLID refactors, tech-debt scoring | F | Caution |
| **codebase-cleanup** | wshobson | `/refactor-clean`, `/tech-debt`, `/deps-audit` (all clash) | ~80% overlap with code-refactoring | F | Off (dup — OVERLAPS trim) |
| **dependency-management** | wshobson | `/deps-audit`; `legacy-modernizer` agent | CVE / staleness / license audit + remediation | F | Adopt |
| **git-pr-workflows** | wshobson | `/git-workflow`, `/pr-enhance`, `/onboard`; `code-reviewer` agent | Branch strategy, PR polish, repo onboarding | F | Adopt |
| **documentation-generation** | wshobson | `/doc-generate`; `api-documenter`, `docs-architect`, `mermaid-expert`, `reference-builder`, `tutorial-engineer` agents; `architecture-decision-records`, `changelog-automation`, `openapi-spec-generation` skills | Project docs, ADRs, changelogs, OpenAPI, diagrams | F | Adopt |
| **code-documentation** | wshobson | `/code-explain`, `/doc-generate` (clash); `code-reviewer`, `docs-architect`, `tutorial-engineer` agents | Prose explanation of modules | F | Off (dup — OVERLAPS trim) |
| **claude-security** | official | `claude-security` orchestrator + 7 restricted scan/patch agents; `claude-security` skill | Deep in-session vuln scan; verified patch files | F | Adopt (scan-changes) / Caution (full scan) |
| **security-scanning** | wshobson | `/security-sast`, `/security-dependencies`, `/security-hardening`; `security-auditor`, `threat-modeling-expert` agents; 5 skills (STRIDE, attack-tree, SAST-config, security-requirement-extraction, threat-mitigation-mapping) | CI-style SAST/deps/OWASP + threat modelling | F | Adopt (threat-model per trust/custody feature) |
| **superpowers** | obra (community) | 13 workflow skills: brainstorming, writing-plans, executing-plans, subagent-driven-development, dispatching-parallel-agents, using-git-worktrees, finishing-a-development-branch, test-driven-development, systematic-debugging, requesting-code-review, receiving-code-review, verification-before-completion, using-superpowers, writing-skills | Spec-first "plan → build → 2-stage review" discipline + agent orchestration | F | Adapt (planning + verification only; see Conflicts) |
| **full-stack-orchestration** | wshobson | `/full-stack-feature`; `deployment-engineer`, `performance-engineer`, `security-auditor`, `test-automator` agents | Coordinates FE + BE + DB + infra in one run | F | Caution |
| **cloud-infrastructure** | wshobson | `cloud-architect`, `kubernetes-architect`, `terraform-specialist`, `network-engineer`, `service-mesh-expert` agents; 8 skills (Terraform modules, mTLS, Istio/Linkerd, multi-cloud, hybrid networking, cost-optimization…) | Cloud architecture & IaC | L | Off (until deploy) |
| **kubernetes-operations** | wshobson | `kubernetes-architect` agent; 4 skills (manifest-gen, Helm, k8s-security-policies, GitOps) | K8s manifests & security | L | Off (until deploy) |
| **cicd-automation** | wshobson | `/workflow-automate`; `cloud-architect`, `deployment-engineer`, `devops-troubleshooter`, `kubernetes-architect`, `terraform-specialist` agents; 4 skills (GH Actions, GitLab CI, pipeline design, secrets-management) | CI/CD pipeline design & troubleshooting | L | Off (until deploy) |
| **deployment-strategies** | wshobson | `deployment-engineer`, `terraform-specialist` agents | Blue-green / canary / rollback choice | L | Off (until deploy) |
| **observability-monitoring** | wshobson | `/monitor-setup`, `/slo-implement`; `observability-engineer`, `performance-engineer`, `database-optimizer`, `network-engineer` agents; 4 skills (Prometheus, Grafana, distributed-tracing, SLO) | Monitoring, SLIs/SLOs, tracing | L | Off (until deploy) |
| **database-cloud-optimization** | wshobson | `/cost-optimize`; `backend-architect`, `cloud-architect`, `database-architect`, `database-optimizer` agents | DB cost/scale right-sizing | L | Off (until scale) |
| **data-engineering** | wshobson | `/data-pipeline`, `/data-driven-feature`; `data-engineer`, `backend-architect` agents; 4 skills (Airflow, dbt, Spark, data-quality) | ETL / analytics pipelines | S/X | Off (not in scope) |
| **github** | official | MCP | Real GitHub repo/PR/issue/Actions operations | F | Caution (real account) |
| **figma** | official | MCP + 15 `figma-*` skills | Figma ↔ code, design-system generation | S | Optional (only if design team supplies Figma) |
| **stripe** | official | MCP + `/explain-error`, `/test-cards`; `Company Researcher` agent; 8 skills (Connect, billing, Stripe Tax, apps, provisioning…) | Stripe payments integration | X | **Do not use** (Fikisha holds no fare; Kenya = M-Pesa/eTIMS) |
| **playground** | official | `/playground`, `playground` skill | Single-file interactive HTML explorers | S | Optional |
| **document-skills** | Anthropic skills | `docx`, `pdf`, `pptx`, `xlsx` skills | Real Office/PDF file creation & editing | F | Optional (founder deliverables) |
| **example-skills** | Anthropic skills | 12 skills: web-artifacts-builder, webapp-testing, mcp-builder, skill-creator, frontend-design, canvas-design, algorithmic-art, brand-guidelines, theme-factory, doc-coauthoring, internal-comms, slack-gif-creator | Artifacts, E2E web testing, skill authoring, visual/brand assets, doc co-authoring | F (subset) | Optional |
| _loose_ **shadcn** | shadcn-ui/ui | skill (`~/.claude/skills/`) | Correct shadcn/ui component add/compose (needs `components.json`) | F (if shadcn adopted) | Optional |
| _loose_ **migrate-radix-to-base** | shadcn-ui/ui | skill | Migrate components Radix → Base UI | S | Off |
| _built-in_ `/code-review`, `/security-review`, `/simplify`, `artifact-design`, `dataviz`, `design` | Claude Code | — | Fast daily review / security pass / cleanup / artifact & data-viz design | F | Adopt (already available) |

### 3b. Deep-dive: individual skills that matter for Fikisha

| Skill | Plugin | Purpose | When to use | Inputs | Outputs | Depends on | Workflow impact | Quality benefit | Conflict risk | Rec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `verification-before-completion` | superpowers | Forbid "done/fixed/passing" claims without running the check and pasting output | Before any completion claim, commit, or PR | the work + its test/lint/build commands | evidence block (command + output) then the claim | a runnable check | Adds an evidence step before every "complete" | Kills false-green; matches Fikisha's "recorded smoke-test run" habit | none — reinforces current practice | **Adopt as standing habit** |
| `brainstorming` | superpowers | Structured intent/requirements/design exploration before building | Start of a phase where the brief leaves design open | the ask / phase brief | agreed requirements + design sketch | — | Inserts a discovery step | Prevents building the wrong thing | Mild: Fikisha briefs are usually already complete → often skip | Adapt (only when brief is open) |
| `writing-plans` / `executing-plans` | superpowers | Turn a spec into a written multi-step plan; execute with review checkpoints | Multi-step work inside an approved phase | spec/requirements | plan file in `tasks/` + checkpointed execution | brainstorming (ideally) | Formalises sub-phase planning | Traceable steps, review gates | Overlaps Fikisha's brief/STOP model; use *within* a phase, not to replace founder gates | Adapt |
| `architecture-decision-records` | documentation-generation | Author/maintain ADRs to a standard format | Any significant technical decision | the decision + options + consequences | ADR file | — | Standardises what Fikisha already does ad hoc (ADR-2A/2B/2C) | Consistent, reviewable decision trail | none | **Adopt** |
| `postgresql-table-design` | database-design | PG-specific schema review: types, indexes, constraints, partitioning | Designing/reviewing any new table | proposed schema | annotated schema + index/constraint set | — | Adds a PG review pass to schema work | Fewer migration surprises; matches PG16 + append-only-trigger model | none | **Adopt (Phase 2D+)** |
| `/migration-observability` | database-migrations | Lock analysis + rollback plan for a migration on a large table | Any risky column/table change | migration + table size | lock risk report + rollback plan | — | Adds a safety gate before running migrations | Protects append-only / audit tables | none | **Adopt (Phase 2D+)** |
| `api-design-principles` | backend-development | REST/GraphQL design: versioning, pagination, error shape | Designing/reviewing endpoints | endpoint sketch | design critique | — | Adds a consistency check | Matches Fikisha's RFC-9457 + cursor-pagination conventions | none | Adopt |
| `event-sourcing-architect` (agent) | backend-development | Event store / projections / saga / eventual consistency | Work touching the outbox, domain events, audit chain | the flow | design guidance | — | Deep help exactly where Fikisha is non-trivial (transactional outbox, hash-chained audit) | Fewer consistency bugs | none | Adopt (situational) |
| `backend-security-coder` (agent) | backend-api-security | Secure coding for a specific endpoint (authz, rate-limit, validation) | While writing any write endpoint | endpoint code | hardened code + notes | — | Pairs security into implementation | Fikisha is a trust/custody platform — high value | none | **Adopt (endpoint work)** |
| `stride-analysis-patterns` + `attack-tree-construction` | security-scanning | STRIDE threat model + attack trees for a feature | Before implementing any trust / verification / custody / auth / payment feature | feature design | threat list + mitigations mapped to controls | `threat-modeling-expert` agent | Adds a pre-implementation security gate | Directly serves Fikisha's trust-and-safety mandate | none | **Adopt (per sensitive feature)** |
| `claude-security` → "scan changes" | claude-security | Vuln scan of a branch/PR diff, every finding challenged before report | After implementing a phase branch, before merge | the diff | verified findings (+ optional patch files) | git | Adds a security gate to the merge flow | Cheap, repeatable; catches regressions | Token cost only if run as full-repo | **Adopt (scan-changes)** ; Caution (full scan) |
| `/code-review` (built-in) → `/full-review` (comprehensive-review) | Claude Code / wshobson | Fast daily review → deep multi-agent release review | Daily during coding → once before a phase merge | changed code | prioritised findings | — | Two-tier review ladder | Matches "testing and validation" + approval-gate pillars | `/pr-enhance` name clash (know which you invoke) | **Adopt** |
| `wcag-audit-patterns` + `screen-reader-testing` + `ui-visual-validator` | accessibility-compliance | WCAG 2.2 audit, AT testing, visual regression/label check | All PWA UI work (design annotations now, code later) | page/component or wireframe | audit report + fixes | Playwright (for live AT tests) | Bakes a11y into UI cadence | Serves design-brief's 44px targets / offline vocab / EN-SW clarity | none | **Adopt (all UI)** |
| `frontend-design` | official / example-skills | Aesthetic direction, typography, non-templated choices | Visual-design phases (Phase 4+), light touch in Phase 3 | design intent | direction + rationale | — | Raises UI quality bar | Avoids generic "AI slop" look | exists twice (harmless) | Adopt (design phases) |
| `mermaid-expert` (agent) | documentation-generation | Flow / sequence / ERD / state diagrams | Design Phase 3 screen-flow maps; architecture docs | description | Mermaid source | — | Standard diagramming | Consistent, versionable diagrams | none | **Adopt (Design Phase 3)** |
| `web-artifacts-builder` / `/playground` | example-skills / playground | Interactive multi-component claude.ai HTML artifact / single-file explorer | Only if founder wants a clickable Phase 3 prototype | flows/IA | hosted or single-file prototype | — | Optional prototyping step | Faster founder feedback than static wireframes | scope creep if over-used | Optional (Design Phase 3, on request) |
| `doc-coauthoring` | example-skills | Structured section-by-section doc authoring with reader-verification | Authoring long Fikisha design/spec docs | topic + context | refined doc | — | Formalises how design-phase docs are produced | Better-structured deliverables | none | Optional |
| `docx` / `pdf` | document-skills | Real Word/PDF creation & editing | Only if founder wants a phase deliverable as `.docx`/`.pdf` | Markdown/source | `.docx` / `.pdf` file | — | Adds a packaging step | Client-ready artifacts | produces real files — say where | Optional |
| `claude-md-improver` + `/revise-claude-md` | claude-md-management | Create/audit `CLAUDE.md`; fold session learnings in | Now (create), then end of each work session | repo + session | `CLAUDE.md` + quality report | — | Establishes project memory Fikisha lacks | Consistent agent behaviour across sessions | none | **Adopt (create CLAUDE.md now)** |
| `claude-automation-recommender` | claude-code-setup | Recommend hooks/skills/subagents/MCP for this repo | Once, after this audit | Fikisha repo | recommendation list | — | Informs the skill policy | Tailors setup to Fikisha | advisory only | Adopt (run once) |
| `context7` (MCP) | context7 | Pull exact API docs for a pinned lib version | Any coding against Django 5.2 / DRF / React 18 / Vite / TanStack etc. | lib + version | live doc excerpts into context | network; optional API key | Reduces stale-pattern risk | Correctness against the *actual* pinned versions | anonymous = rate-limited | **Adopt** |
| `dependency-management` `/deps-audit` | dependency-management | CVE / staleness / license audit + remediation | Periodically, and before a release | lockfiles | audit + remediation plan | — | Adds a supply-chain gate | Matches Fikisha's pinned-deps discipline | `/deps-audit` name clash | Adopt |
| `using-git-worktrees` / `finishing-a-development-branch` / `dispatching-parallel-agents` / `subagent-driven-development` | superpowers | Isolated worktrees; parallel subagent execution; branch-integration decisions | Large independent workstreams | plan | branches/worktrees; parallel work | git | **Creates/switches branches; spawns parallel agents** | Speed on big parallel work | **Conflicts** with single-branch, sequential, founder-gated phases; OVERLAPS.md warns re dirty trees | **Caution (manual opt-in only)** |
| `using-superpowers` | superpowers | "Use at the start of *any* conversation; requires skill invocation before ANY response, including clarifying questions" | n/a | — | forces a skill-selection preamble every turn | — | Would inject a step into every turn incl. approval-gate reviews | Consistency for teams that live in superpowers | **Conflicts** with Fikisha's deliberate, user-driven cadence | **Do not adopt as-is** |
| `/feature-development`, `/full-stack-feature`, `/feature-dev` (full auto run) | backend-development / full-stack-orchestration / feature-dev | "Requirements → deployment" in one orchestrated run | Greenfield features on a fast-moving repo | requirements | architecture + code + tests + (deploy) | many agents | Bundles architecture + implementation (+ deploy) into one pass | Fast for throwaway/greenfield | **Conflicts** with explicit phase boundaries + "no silent architecture decisions" + STOP-after-phase | **Caution — sub-steps only, never full auto** |

---

## 4. Skill descriptions — the methodologies introduced

Grouped by discipline (the toolkit's own `guides/` split, refined):

- **Research & context.** `context7` (version-pinned live docs), `modern-web-guidance`
  ("execute first for HTML/CSS/JS"), `claude-automation-recommender`.
- **Planning & requirements.** superpowers `brainstorming` → `writing-plans` →
  `executing-plans`; `feature-dev` `code-explorer`/`code-architect`; wshobson
  `/feature-development`, `/full-stack-feature`. Methodology: spec-first, plan written to
  `tasks/`, execution with review checkpoints.
- **Architecture review.** `comprehensive-review` `architect-review`; `backend-development`
  `architecture-patterns` (Clean/Hexagonal/DDD), `backend-architect`,
  `event-sourcing-architect`; `database-design` `database-architect`;
  `api-design-principles`.
- **Coding standards.** `python-development` (17 skills — style, design-patterns,
  anti-patterns, type-safety, project-structure, error-handling, resilience,
  resource-management, configuration, packaging, performance, async, background-jobs,
  observability, uv); `javascript-typescript` (advanced-types, modern-patterns);
  `python-anti-patterns` as an explicit review checklist.
- **Testing.** `tdd-workflows` (`/tdd-red|green|refactor|cycle`, strict RGR); `unit-testing`
  (`/test-generate`); superpowers `test-driven-development` (TDD baked into the build loop);
  `python-testing-patterns`, `javascript-testing-patterns` (pytest/Vitest, fixtures,
  mocking); `webapp-testing` (Playwright E2E on a running app).
- **Debugging.** `debugging-toolkit` `/smart-debug`; `error-debugging`
  `/error-analysis`/`/error-trace` + `error-detective` (log/stack-trace correlation);
  superpowers `systematic-debugging` (reproduce → failing test → fix).
- **Security.** `claude-security` (in-session deep scan, each finding challenged, verified
  patch files); `security-scanning` (SAST config, dependency scan, OWASP, STRIDE,
  attack trees, threat→control mapping, security-requirement extraction);
  `backend-api-security` `backend-security-coder` (secure coding at endpoint level);
  built-in `/security-review`.
- **Code review.** built-in `/code-review` (fast daily); `comprehensive-review`
  `/full-review` (architecture + security + performance + testing agents, release gate);
  superpowers `requesting-code-review` / `receiving-code-review` (technical-rigour protocol
  for giving and taking review — verify, don't perform agreement).
- **Documentation.** `documentation-generation` `/doc-generate`, `architecture-decision-records`,
  `changelog-automation` (Keep-a-Changelog), `openapi-spec-generation` (OpenAPI 3.1),
  `mermaid-expert`, `reference-builder`, `tutorial-engineer`, `docs-architect`;
  `claude-md-management` (`CLAUDE.md` audit + session capture); `doc-coauthoring`.
- **UI / UX / accessibility.** `frontend-design` (aesthetic direction),
  `tailwind-design-system` (tokens/scales), `shadcn` (component add/compose),
  `accessibility-compliance` (`/accessibility-audit`, `wcag-audit-patterns`,
  `screen-reader-testing`), `ui-visual-validator` (screenshot/visual-regression),
  `figma-*` (design↔code, needs MCP), `modern-web-guidance`.
- **Database & API.** `database-design` (`postgresql-table-design`, `database-architect`,
  `sql-pro`), `database-migrations` (`/sql-migrations` zero-downtime,
  `/migration-observability` lock/rollback), `api-scaffolding` (`fastapi-templates`).
- **DevOps / release.** `cloud-infrastructure`, `kubernetes-operations`,
  `cicd-automation` (`/workflow-automate`, GH Actions / GitLab CI templates,
  `secrets-management`), `deployment-strategies` (blue-green/canary/rollback),
  `observability-monitoring` (`/monitor-setup`, `/slo-implement`, Prometheus/Grafana/
  tracing), `changelog-automation`.
- **Git workflow.** `commit-commands` (`/commit`, `/commit-push-pr`, `/clean_gone`),
  `git-pr-workflows` (`/git-workflow` with quality gates, `/pr-enhance`, `/onboard`),
  superpowers `using-git-worktrees`, `finishing-a-development-branch`.
- **Verification / quality gates.** superpowers `verification-before-completion`
  (evidence before assertions); `git-pr-workflows` "quality gates"; `/full-review` +
  `claude-security` as pre-merge gates.
- **Agent orchestration / task decomposition.** superpowers `dispatching-parallel-agents`,
  `subagent-driven-development`; `full-stack-orchestration` (`/full-stack-feature`);
  `feature-dev`; `comprehensive-review` (multi-agent review fan-out).
- **Deliverables.** `document-skills` (`docx`/`pdf`/`pptx`/`xlsx`); `example-skills`
  (`web-artifacts-builder`, `canvas-design`, `brand-guidelines`, `theme-factory`,
  `internal-comms`, `slack-gif-creator`, `algorithmic-art`).
- **Meta / skill authoring.** `skill-creator`, `mcp-builder`, superpowers `writing-skills`.

**Overlap map (from OVERLAPS.md + observation):** 8 slash-command name clashes
(`/pr-enhance`, `/smart-debug`, `/error-analysis`, `/error-trace`, `/refactor-clean`,
`/tech-debt`, `/deps-audit`, `/doc-generate`); `error-diagnostics` is a near-identical
fork of `error-debugging`; `codebase-cleanup` ~80% overlaps `code-refactoring`;
`code-documentation` is a subset of `documentation-generation`; `frontend-design` ships
twice; the same subagent role (`code-reviewer` ×6, `security-auditor` ×4,
`terraform-specialist` ×3, `database-optimizer` ×3) is re-exported under namespaced names.
Three review disciplines overlap (built-in `/code-review` → `/full-review` →
`claude-security`), and two TDD styles overlap (`tdd-workflows` vs superpowers TDD).

---

## 5. Skill dependencies & ordering

### Prerequisites / dependent skills

- `context7` — no prereq; feeds every coding skill.
- `brainstorming` → `writing-plans` → `executing-plans` — strict order; plans depend on
  agreed requirements.
- `stride-analysis-patterns` / `attack-tree-construction` depend on the
  `threat-modeling-expert` agent and a feature design existing.
- `claude-security` "scan changes" depends on a git diff (a branch or PR).
- `webapp-testing` depends on a running dev server + `npx playwright install`.
- `shadcn` depends on `components.json` (`npx shadcn@latest init`).
- `figma-*` skills depend on the `figma` MCP being authed; several declare themselves
  **MANDATORY prerequisites** before specific Figma MCP tool calls.
- SAST skills (`/security-sast`, `sast-configuration`) expect Semgrep/CodeQL installed for
  real results; without them you get configuration + guidance only.
- `/migration-observability` depends on a written migration + a target table.
- `changelog-automation` depends on a commit convention being followed.
- `verification-before-completion` depends on a runnable check existing.

### Recommended pipeline (toolkit ordering, reconciled with the Fikisha phase model)

```
RESEARCH & CONTEXT          context7 (auto), modern-web-guidance, claude-automation-recommender
        ↓
PLANNING & REQUIREMENTS     brainstorming → writing-plans     [only if the phase brief leaves design open]
        ↓
ARCHITECTURE & DESIGN       architect-review · architecture-patterns · database-architect ·
                            api-design-principles · ADR skill · frontend-design · a11y patterns
        ↓  ── FOUNDER APPROVAL GATE (human; unchanged) ──
IMPLEMENTATION              stack packs (python-development / backend-development /
                            javascript-typescript / frontend-mobile / database-design+migrations)
                            + backend-security-coder for endpoints
                            + tests alongside (unit-testing / tdd-workflows optional)
        ↓
VERIFY                      verification-before-completion  (run checks, paste output)
        ↓
SECURITY                    claude-security "scan changes"  +  STRIDE threat-model review
        ↓
CODE REVIEW                 /code-review (fast)  →  /full-review (deep, pre-merge)
        ↓  ── FOUNDER APPROVAL GATE (human; unchanged) ──
MERGE / RELEASE             commit-commands · git-pr-workflows · changelog-automation
                            (deployment-strategies / observability only once there is a deploy target)
```

### Skills that must not run simultaneously / are mutually exclusive

- Two feature orchestrators on the same task (`/feature-dev` vs `/full-stack-feature` vs
  `/feature-development`) — pick one by scope.
- `tdd-workflows` phase commands **and** superpowers `test-driven-development` on the same
  module — one TDD style per module.
- `using-git-worktrees` / `dispatching-parallel-agents` / `subagent-driven-development`
  **during a founder-gated sequential phase** — they fork branches and parallelise, which
  breaks the single-branch review model.
- The overlapping duplicates (`error-diagnostics` vs `error-debugging`; `codebase-cleanup`
  vs `code-refactoring`; `code-documentation` vs `documentation-generation`) — enable one
  per pair.

### Skills that act as gates

- **verification-before-completion** — evidence gate before any "done" claim or commit.
- **`/full-review` + `claude-security` scan-changes** — pre-merge gate for a phase branch.
- **STRIDE threat model** — pre-implementation gate for any trust/custody/auth/payment
  feature.
- **`/migration-observability`** — pre-run gate for a risky migration.
- The **founder approval gate** at phase boundaries remains human and is unchanged by any
  skill.

---

## 6. Comparison with the existing Fikisha workflow

Fikisha's methodology: `Discovery → Product decisions → Architecture → Implementation
phases → Validation → Approval gates`, with explicit phase boundaries, source-of-truth
docs, no silent product/architecture changes, docs-before-implementation, clean git
commits, explicit open-question tracking, Claude as engineer / founder as product
decision-maker.

### A. What the toolkit improves

1. **Version-correct implementation** — `context7` pins the real Django 5.2 / DRF /
   React 18 / Vite APIs instead of training-data guesses.
2. **Security depth** — STRIDE threat modelling per feature and `claude-security`
   scan-changes give Fikisha's trust/verification/custody domain a repeatable security
   gate it does not yet have as a named step.
3. **Migration safety** — `/migration-observability` (lock analysis + rollback) is
   valuable against the append-only / Postgres-trigger model.
4. **Schema rigour** — `postgresql-table-design` adds a PG-specific review pass.
5. **Event-sourcing help** — `event-sourcing-architect` targets exactly Fikisha's
   non-trivial parts (transactional outbox, hash-chained audit, domain events).
6. **Accessibility as a habit** — `accessibility-compliance` operationalises the
   design-brief's 44px / offline-vocabulary / EN-SW-clarity intent.
7. **Project memory** — `claude-md-management` fills a real gap (no `CLAUDE.md` exists).
8. **Consistent ADRs** — a single ADR skill standardises what is currently done by hand
   (`phase-2X-decisions.md`).
9. **Review ladder** — built-in `/code-review` daily + `/full-review` pre-merge formalises
   the "Validation" pillar for code phases.
10. **Evidence discipline** — superpowers `verification-before-completion` names and
    enforces the "recorded smoke-test run, all green" habit already used at phase end.

### B. What the toolkit duplicates (Fikisha already does this, well)

1. **Planning + approval gates** — the phase-brief → execute → STOP model is already a
   planning-and-gate discipline; superpowers `writing-plans`/`executing-plans` overlaps
   but does not replace the founder gate.
2. **Docs before code** — Phases 0–1 were documentation-only by rule; the design track
   (Phases 0–2) is docs-first. `doc-coauthoring` / `documentation-generation` add tools,
   not a new principle.
3. **ADRs** — already present as `phase-2a/2b/2c-decisions.md` with a deviations table.
4. **Clean commits** — Fikisha commits are already scoped, messaged, and trailered;
   `commit-commands` mostly automates what is already done.
5. **Spec-review discipline** — the Design Phase 1 & 2 reviews (against approved docs, with
   an evidence table) are already a rigorous manual review; `/full-review` is a *code*
   review tool and only partly overlaps.
6. **Verification before completion** — already the de-facto phase-exit rule.

### C. What the toolkit conflicts with

1. **`using-superpowers`** ("use at the start of *any* conversation; skill invocation
   required before ANY response, including clarifying questions") — an always-on preamble
   that fights Fikisha's deliberate, founder-driven, review-heavy cadence.
2. **Full-auto feature orchestrators** (`/feature-development`, `/full-stack-feature`,
   `/feature-dev` end-to-end) — "requirements → deployment in one run" bundles
   architecture + implementation (+ deploy), which violates explicit phase boundaries and
   "no silent architecture decisions / STOP after each phase".
3. **`using-git-worktrees` / `finishing-a-development-branch` /
   `dispatching-parallel-agents` / `subagent-driven-development`** — auto branch/worktree
   creation and parallel subagent fan-out break the single-branch, sequential,
   founder-reviewed model; OVERLAPS.md itself warns they "will create/switch branches".
4. **"MANDATORY / execute FIRST / NEVER call X directly" framings** in
   `modern-web-guidance`, many `figma-*` skills, and `stripe-directory` ("MUST be used
   BEFORE web search") — individually low-harm, collectively they erode "Claude acts on
   explicit instruction within a phase".
5. **`/refactor-clean`, `/tech-debt`, `codebase-cleanup`, `legacy-modernizer`** —
   broad-sweep code changes conflict with Fikisha's surgical, reviewed-diff norm and
   "no premature implementation".
6. **`stripe`** — assumes Stripe; Fikisha explicitly holds no fare (no wallet/escrow) and
   Kenya settlement is M-Pesa/eTIMS. Not a conflict of behaviour, but a domain mismatch
   that would mislead if it self-activated on the word "payment".
7. **Community-repo trust** — `claude-code-workflows` and `superpowers-dev` are community
   repos; `claude plugin marketplace update` can change agent/hook behaviour. Fikisha's
   audit-trail and append-only guarantees mean tool-behaviour changes must be deliberate,
   not picked up silently.
8. **Passive context cost** — 45 plugins / 96 agents / 128 skill frontmatters are a large
   resident surface; risk of context pressure during long phase work (OVERLAPS.md §4).
9. **MCP servers act on real accounts** — `github` opens/edits real PRs; `stripe` acts on
   a real Stripe account once authed. Needs an explicit per-action approval gate.

### D. What should become standard (implementation phases)

`context7` · `claude-md-management` (+ create `CLAUDE.md`) · `documentation-generation`
ADR skill · `python-development` · `backend-development` (architecture/API/event-sourcing
sub-parts) · `backend-api-security` · `database-design` · `database-migrations` ·
`javascript-typescript` · `frontend-mobile-development` (web) · `accessibility-compliance`
· `unit-testing` + `debugging-toolkit` + `error-debugging` · `security-scanning` (STRIDE)
+ `claude-security` scan-changes · built-in `/code-review` + `/full-review` ·
`commit-commands` + `git-pr-workflows` · `dependency-management` · superpowers
`verification-before-completion` (as a habit).

### E. What stays optional / situational

superpowers planning loop (`brainstorming`/`writing-plans`) · `tdd-workflows` phase
commands · `frontend-design` (design phases) · `figma-*` (only with founder-supplied Figma)
· `document-skills` (founder deliverables) · `web-artifacts-builder` / `/playground`
(prototypes on request) · `doc-coauthoring` · deliverable/brand/art skills ·
`skill-creator` / `mcp-builder` (when a repeatable in-house process emerges).
**Dormant until a deploy target exists:** `cloud-infrastructure`, `kubernetes-operations`,
`cicd-automation`, `deployment-strategies`, `observability-monitoring`,
`database-cloud-optimization`. **Not used:** `stripe`, `data-engineering`,
`migrate-radix-to-base`.

---

## 7. Conflicts / risks (consolidated)

| # | Risk | Severity | Mitigation |
| --- | --- | --- | --- |
| R1 | `using-superpowers` forces a skill preamble on every turn | Med | Do not adopt; if superpowers stays enabled, treat this skill as inert for Fikisha and never invoke it |
| R2 | Full-auto feature orchestrators bundle architecture + impl + deploy | High | Never run end-to-end on Fikisha; use only `code-explorer`/`code-architect` sub-steps, then STOP for founder approval |
| R3 | Worktree / parallel-subagent skills fork branches mid-phase | Med | Manual opt-in only; never during a founder-gated sequential phase; never on a dirty tree |
| R4 | "MANDATORY/FIRST/NEVER" self-activating skills override phase intent | Low–Med | Policy line: a skill's self-description never outranks a founder phase instruction |
| R5 | Broad refactor/cleanup sweeps → uncontrolled diffs | Med | `/refactor-clean` etc. only on an explicit, scoped request with a reviewed diff |
| R6 | Community-plugin `update` changes agent/hook behaviour silently | Med | Skim the diff before `marketplace update`; record plugin versions in `CLAUDE.md` |
| R7 | Context bloat from 45 plugins / 96 agents / 128 skills | Med | Disable the dormant devops/data/stripe/figma plugins during Fikisha phases; apply the OVERLAPS.md trim set |
| R8 | MCP writes to real accounts (`github` PRs, `stripe`) | Med | Per-action founder approval; `stripe` unused; `github` MCP writes only on explicit instruction |
| R9 | 8 slash-command name clashes → wrong tool silently runs | Low | Apply OVERLAPS trim (`disable error-diagnostics`, `codebase-cleanup`, `code-documentation`); name the plugin when invoking a clashing command |
| R10 | SAST skills imply results without Semgrep/CodeQL installed | Low | Treat SAST output as config/guidance unless the scanners are installed; rely on `claude-security` for actual findings |
| R11 | `claude-security` full "scan codebase" burns tokens | Low–Med | Default to "scan changes"; full scan only on explicit request |
| R12 | `stripe` self-activating on "payment" language | Low | Keep `stripe` disabled; Fikisha payment work (far future) is M-Pesa/eTIMS |
| R13 | A skill proposes an approach that contradicts an approved Fikisha decision | Med | Standing rule: approved product/architecture decisions are authoritative; a skill suggestion is an input, not an override — record a deviation ADR or an open question instead |

---

## 8. Recommended team skill categories

Derived from the toolkit's own 7-guide split and the Fikisha phase pipeline:

| Category | Contains | Gate role |
| --- | --- | --- |
| **0 · RESEARCH & CONTEXT** | context7, modern-web-guidance, claude-automation-recommender | none (always-on support) |
| **1 · PLANNING & REQUIREMENTS** | superpowers brainstorming / writing-plans / executing-plans; feature-dev code-explorer/code-architect | feeds the architecture gate |
| **2 · ARCHITECTURE & DESIGN** | architect-review, architecture-patterns, backend-architect, event-sourcing-architect, database-architect, api-design-principles, ADR skill, frontend-design, accessibility patterns, mermaid-expert | **founder approval gate** |
| **3 · IMPLEMENTATION** | python-development, backend-development, api-scaffolding, backend-api-security, database-design, database-migrations, javascript-typescript, frontend-mobile-development, shadcn/tailwind | — |
| **4 · TESTING & VALIDATION** | tdd-workflows, unit-testing, javascript/python-testing-patterns, webapp-testing, superpowers verification-before-completion | **evidence gate** |
| **5 · SECURITY** | security-scanning (STRIDE, attack-tree, SAST), backend-api-security, claude-security | **pre-merge security gate** + pre-impl threat model |
| **6 · CODE REVIEW & QUALITY** | built-in /code-review, comprehensive-review /full-review, superpowers requesting/receiving-code-review, code-refactoring (scoped) | **pre-merge review gate** |
| **7 · DOCUMENTATION** | documentation-generation (+ADR, changelog, openapi), claude-md-management, doc-coauthoring, mermaid-expert | — |
| **8 · GIT & RELEASE** | commit-commands, git-pr-workflows, changelog-automation, dependency-management | — |
| **9 · DEVOPS & INFRA** (dormant) | cloud-infrastructure, kubernetes-operations, cicd-automation, deployment-strategies, observability-monitoring, database-cloud-optimization | activate only at deploy |
| **10 · DELIVERABLES** (situational) | document-skills, web-artifacts-builder, playground, canvas/brand/theme, internal-comms, slack-gif-creator | — |
| **11 · META / SKILL AUTHORING** | skill-creator, mcp-builder, superpowers writing-skills | — |

---

## 9. Recommended activation rules

Mapped to the Fikisha phase model. "Consider" = the model should proactively reach for it;
"Never auto" = only on an explicit founder/engineer instruction.

| Trigger | Consider | Never auto |
| --- | --- | --- |
| Start of any phase / session | Category 0 (context7 auto) | — |
| Phase brief received, design **left open** | Category 1 (brainstorming → writing-plans) | Category 1 when the brief is already complete (usual Fikisha case) |
| New architecture / schema / API / event-flow proposed | Category 2 + ADR skill; then **STOP for founder approval** | committing an architecture change without the gate |
| Implementing an **approved** phase | Category 3 stack pack + Category 4 tests alongside | feature orchestrators end-to-end; worktree/parallel-agent skills |
| Feature touches trust / verification / custody / auth / OTP / payment | Category 5 STRIDE threat model **before** coding; claude-security scan-changes **after** | shipping the feature without the threat model |
| Any PWA UI work (incl. Phase 3 annotations) | frontend-design + accessibility-compliance + ui-visual-validator | — |
| About to claim "done / fixed / passing", or before a commit | verification-before-completion (run checks, paste output) | success claims without evidence |
| Before merging a phase branch | /code-review → /full-review → claude-security scan-changes; then **founder approval gate** | merging without review + founder sign-off |
| Risky migration (large table, type change, index on hot table) | /migration-observability (lock + rollback) | running it blind |
| End of a work session | claude-md-improver / capture learnings to memory | — |
| Release / tag | changelog-automation; deployment-strategies + observability **iff** a deploy target exists | — |
| "Refactor / clean up / modernise X" | code-refactoring **scoped to X**, reviewed diff | repo-wide sweeps |
| GitHub PR/issue operations | github MCP **on explicit instruction** | autonomous PR edits |

Guardrail against under/over-use: **one skill per need per phase step**; if two skills
cover the same need (review ladder, TDD styles, debug forks) pick the lighter one first
and escalate only if it is insufficient.

---

## 10. Recommended skill ordering

See §5 for the full pipeline diagram and the mutually-exclusive / gate lists. Summary:

```
Research → Plan(if open) → Architecture(+ADR) → [FOUNDER GATE] →
Implement(+tests) → Verify(evidence) → Security(scan+STRIDE) →
Review(/code-review → /full-review) → [FOUNDER GATE] → Merge → Changelog/Release
```

- **Never simultaneously:** two feature orchestrators; two TDD styles on one module;
  worktree/parallel-agent skills during a founder-gated phase; duplicate plugin pairs
  both enabled.
- **Gates:** founder approval (human, unchanged) · verification-before-completion
  (evidence) · /full-review + claude-security (pre-merge) · STRIDE (pre-impl, sensitive
  features) · /migration-observability (pre-run migrations).

---

## 11. Proposed team operating model

**Principle:** the Fikisha phase model is the operating system; skills are libraries it
calls. Skills accelerate work *inside* a phase and *inform* the gates; they never move a
gate or make a product/architecture decision.

1. **Curated enable-set.** Keep the Category 0–8 plugins enabled; disable Category 9
   (devops), `data-engineering`, `stripe`, `migrate-radix-to-base`, and the OVERLAPS trim
   set (`error-diagnostics`, `codebase-cleanup`, `code-documentation`) during Fikisha
   work. Re-enable Category 9 when a deploy target exists.
2. **Write `CLAUDE.md`** (Fikisha repo root) capturing: the modular-monolith rules
   (no cross-module model imports; interact via services/authz/events), the phase +
   STOP-line model, append-only/audit invariants, pragmatic-mypy, integer-KES money,
   EN/SW, RFC-9457 + cursor pagination, the current STOP line, and the pinned plugin
   versions this policy assumes.
3. **Commit this policy** (or a trimmed version) to the repo — e.g.
   `docs/engineering/claude-skills-policy.md` — and reference it from `CLAUDE.md`, so the
   activation rules survive context resets and apply on every machine.
4. **Gates stay human where they are human.** The founder approval gate at phase
   boundaries is unchanged. Skill-driven gates (evidence, review, security, migration
   safety) are *additions inside* a phase, not replacements for founder sign-off.
5. **Deliberate updates only.** Pin plugin versions; before
   `claude plugin marketplace update` on a community repo, skim the diff and note the
   version bump in `CLAUDE.md`.
6. **Reuse via skills, not a monolith.** When a Fikisha-specific process repeats
   (e.g. "phase brief → module scaffold + ADR stub + test skeleton"), capture it with
   `skill-creator` rather than growing one mega-prompt.
7. **Per-project reuse.** This model is stack-shaped, not Fikisha-shaped — the same
   enable-set + `CLAUDE.md` + policy file pattern applies to the other Django/React
   projects on this machine.

---

## 12. Fikisha-specific implications

1. **No `CLAUDE.md` exists.** Highest-priority gap, independent of skill adoption. Without
   it, every session re-derives the modular-monolith rules, the STOP line, and the
   append-only invariants from docs/memory.
2. **Phase 2D (Trust & Reputation) then Jobs** is the first heavy code phase — that is
   where Categories 3–6 pay off. Until then, most implementation plugins are latent.
3. **Design Phase 3 (Wireframes)** is a *design* deliverable, not code. The relevant
   skills are a small subset (see §13); the implementation/testing/security/database/devops
   packs are **not** relevant to Phase 3.
4. **`stripe` is a distractor.** Fikisha holds no fare; settlement is M-Pesa/eTIMS in a
   later phase. Keep it disabled so it never self-activates on "payment"/"commission".
5. **superpowers must be scoped.** Its `verification-before-completion` and planning skills
   are genuinely useful; its `using-superpowers` (always-on), worktree, and
   parallel-subagent skills must not run during founder-gated phases.
6. **Security tooling maps directly onto the mandate.** Fikisha's whole reason for the
   verification/custody/trust design is safety — STRIDE-per-feature and
   claude-security-scan-per-branch should become named steps in Phase 2D+.
7. **Event-sourcing / migration skills fit the existing foundation** (transactional
   outbox, hash-chained append-only audit, Postgres BEFORE-UPDATE/DELETE triggers,
   UUIDv7). `event-sourcing-architect`, `postgresql-table-design`, and
   `/migration-observability` are high-value there.
8. **Nothing in the toolkit changes an approved decision** — and the operating model in
   §11 makes that explicit: a skill suggestion that contradicts an approved product or
   architecture decision is logged as a deviation ADR or an open question, never applied
   silently.

---

## 13. Skills recommended for Design Phase 3 (Wireframes & Interaction Structure)

Design Phase 3 is low-fidelity structure, not visual design and not code.

| Use | Skill / tool | Why |
| --- | --- | --- |
| Screen-flow diagrams, navigation maps, state-to-screen maps | `mermaid-expert` (documentation-generation) / built-in mermaid | Versionable diagrams inside the Phase 3 doc |
| WCAG-aware wireframe annotations (targets, focus order, labels, offline/empty/error states) | `accessibility-compliance` — `wcag-audit-patterns`, `screen-reader-testing` | Bakes the design-brief's 44px / offline-vocabulary / EN-SW-clarity intent into the wireframe spec early |
| Aesthetic/layout direction where a wireframe needs a point of view | `frontend-design` (light touch only) | Keeps structure decisions from hardening into templated defaults |
| Structured authoring of the Phase 3 document | `doc-coauthoring` | Section-by-section, reader-verified |
| Current PWA / responsive / web-platform patterns | `modern-web-guidance`, `context7` | Phase 3 navigation (bottom nav, offline, install) should reflect current best practice |
| **Optional, on founder request:** a clickable prototype of the priority delivery journey | `web-artifacts-builder` or `/playground` | Faster founder feedback than static wireframes |
| **Optional, on founder request:** the Phase 3 spec as `.docx`/`.pdf` | `document-skills` (`docx`, `pdf`) | Client-ready packaging |

**Not for Phase 3:** `feature-dev`, `python-development`, `backend-development`,
`database-*`, `tdd-workflows`, `unit-testing`, `security-scanning`, `claude-security`,
all Category 9 devops. `tailwind-design-system` and `shadcn` wait until a token system is
defined (a later design/build phase). `figma-*` only if the design team hands over Figma
files.

---

## 14. Skills recommended for future implementation (Phase 2D+ code)

- **Backend:** `python-development` (django-pro; testing-patterns, type-safety,
  anti-patterns, error-handling, resilience, background-jobs, observability,
  configuration, project-structure); `backend-development` (`backend-architect`,
  `architecture-patterns`, `api-design-principles`, `event-sourcing-architect` for the
  outbox/audit/event work); `api-scaffolding` `fastapi-templates` only if a FastAPI
  service is ever added.
- **API security:** `backend-api-security` `backend-security-coder` on every write
  endpoint.
- **Database:** `database-design` (`postgresql-table-design`, `database-architect`,
  `sql-pro`); `database-migrations` (`/sql-migrations`, `/migration-observability`).
- **Frontend:** `javascript-typescript` (`typescript-pro`, advanced-types);
  `frontend-mobile-development` (`frontend-developer`, `react-state-management`);
  `accessibility-compliance`; `shadcn` / `tailwind-design-system` if adopted.
- **Testing:** `unit-testing` (`/test-generate`), `tdd-workflows` (optional per module),
  `webapp-testing` (Playwright E2E), `python-testing-patterns`.
- **Debugging:** `debugging-toolkit` (`/smart-debug`), `error-debugging`
  (`/error-analysis`, `error-detective`), superpowers `systematic-debugging`.
- **Security:** `security-scanning` (STRIDE, attack-tree) per sensitive feature;
  `claude-security` "scan changes" per phase branch.
- **Review:** built-in `/code-review` daily; `comprehensive-review` `/full-review`
  pre-merge; superpowers `requesting-code-review` / `receiving-code-review`.
- **Docs:** `documentation-generation` (`architecture-decision-records`,
  `openapi-spec-generation`, `changelog-automation`, `mermaid-expert`).
- **Git / deps:** `commit-commands`, `git-pr-workflows`, `dependency-management`.
- **Throughout:** `context7`.
- **Deploy phase only:** `cloud-infrastructure`, `kubernetes-operations`,
  `cicd-automation`, `deployment-strategies`, `observability-monitoring`
  (`/slo-implement`, Prometheus/Grafana/tracing), `database-cloud-optimization`.

---

## 15. Skills requiring caution / manual approval

| Skill / plugin | Why | Rule |
| --- | --- | --- |
| `claude-security` full "scan codebase" | Token burn | Use "scan changes"; full scan only on explicit request |
| superpowers `using-git-worktrees`, `finishing-a-development-branch`, `dispatching-parallel-agents`, `subagent-driven-development` | Fork branches / worktrees / parallel agents | Manual opt-in only; never during a founder-gated sequential phase |
| superpowers `using-superpowers` | Always-on preamble, skill-before-any-response | Do not adopt; treat as inert for Fikisha |
| `/feature-development`, `/full-stack-feature`, `/feature-dev` (end-to-end) | Bundle architecture + impl (+ deploy) | Sub-steps only (`code-explorer`, `code-architect`), then STOP for founder approval |
| `/refactor-clean`, `/tech-debt`, `codebase-cleanup`, `legacy-modernizer` | Broad, hard-to-review diffs | Scoped request + reviewed diff only |
| `github` MCP | Acts on the real GitHub account (opens/edits PRs) | Explicit per-action instruction |
| `stripe` MCP + skills | Real Stripe account once authed; wrong domain for Fikisha | **Do not use**; keep disabled |
| `figma` MCP + `figma-*` skills | Inert without auth; "MANDATORY prerequisite" framings | Only with founder-supplied Figma access |
| `claude plugin marketplace update` on community repos | Can change agent/hook behaviour | Skim the diff first; record version bump |
| `modern-web-guidance` / figma "MANDATORY/FIRST" skills | Self-activating language | Fine to let run; their "MUST" never outranks a founder phase instruction |
| `data-engineering` (Airflow/Spark/dbt) | Heavy, irrelevant | Keep disabled |
| SAST skills (`/security-sast`, `sast-configuration`) | Imply results without Semgrep/CodeQL | Treat as guidance unless scanners installed |

---

## 16. Open questions (for the founder)

1. **`CLAUDE.md`** — approve creating one now? What must it contain beyond the list in
   §11.2?
2. **Skill policy file** — commit a trimmed version of this document as
   `docs/engineering/claude-skills-policy.md` and reference it from `CLAUDE.md`, or keep
   the policy inside `CLAUDE.md` only?
3. **superpowers planning loop** — adopt `brainstorming`/`writing-plans` as the standard
   *sub-phase* planning tool, or keep the founder-brief-only model and use them ad hoc?
4. **TDD** — adopt `tdd-workflows` red/green/refactor commands for Phase 2D, or keep
   pytest-first without the phase ceremony?
5. **OVERLAPS trim** — approve `claude plugin disable error-diagnostics codebase-cleanup
   code-documentation` (loses no capability)? Any others?
6. **Context budget** — approve disabling the dormant devops/data/stripe/figma plugins
   during Fikisha phases to protect context on long sessions?
7. **Security cadence** — STRIDE threat model **per feature** or **per phase**?
   claude-security scan **per branch** or **per phase**?
8. **Community-plugin updates** — who approves, and on what cadence?
9. **Design Phase 3 prototype** — static wireframes + mermaid only, or also a clickable
   `web-artifacts-builder` prototype of the Business → Operator → Driver → Recipient
   journey?
10. **Deliverable format** — do future phase docs stay Markdown-in-repo (current
    practice), or also get packaged as `.docx`/`.pdf` via `document-skills`?

---

## Appendix — verification of toolkit claims

- `~/.claude/plugins/installed_plugins.json` lists **45 plugins**, all
  `"scope": "user"`, `installedAt` 2026-09-09, matching `INSTALL.md`.
- Marketplaces present under `~/.claude/plugins/marketplaces/`:
  `claude-plugins-official`, `claude-code-workflows`, `superpowers-dev`,
  `anthropic-agent-skills`.
- Loose skills present under `~/.claude/skills/`: `shadcn`, `migrate-radix-to-base`
  (matches `INSTALL.md`).
- `superpowers` = v6.3.0; `claude-security` = v0.11.0; `figma` = v2.2.107;
  `stripe` = v0.7.4; wshobson plugins pinned to git SHA `a30778f8…`.
- MCP auth state: `~/.claude/mcp-needs-auth-cache.json` present — the 4 MCP servers
  are installed but not yet all authed, consistent with `INSTALL.md §4`.
- **No file in `C:\Users\PCMF\Documents\claude-code-toolkit` was modified, renamed, or
  moved. No plugin was installed, enabled, disabled, or updated. No Fikisha application
  file was touched.**
