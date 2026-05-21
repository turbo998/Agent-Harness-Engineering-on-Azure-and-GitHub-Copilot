# Lab 4: Spec-Driven Development with GitHub Spec-Kit

## Lab Objective

Experience the leap from **hand-crafted multi-agent handoff (Lab 3)** to an **industrialized SDD multi-agent pipeline**:

```
/speckit.constitution → /speckit.specify → /speckit.plan → /speckit.tasks → /speckit.analyze → /speckit.implement
     constitution           specification       technical plan      task breakdown    cross-artifact review    implementation
```

After completing this lab, participants should be able to:

1. Understand the core idea of **Spec-Driven Development (SDD)**: distill conversational coding into auditable, reusable, role-separable spec artifacts
2. Read the `.specify/` and `.github/agents/speckit.*` directory structure injected by spec-kit
3. Use the 14 built-in spec-kit agents to drive a mini feature through the full SDD flow (implement step is narrated only)
4. Map spec-kit's built-in agent handoffs to the hand-crafted handoffs from Lab 3

## Duration

**30–35 minutes** (instructor-led demo; learners optionally follow along)

## Relationship to Lab 3

> **Continuation**: Lab 3 taught you "why multi-agent + how to wire handoffs by hand"; Lab 4 gives you "the off-the-shelf SDD multi-agent pipeline template."

| Dimension | Lab 3: Hand-crafted Multi-Agent | Lab 4: Spec-Kit Industrialized SDD |
|---|---|---|
| Number of agents | 4 custom (developer / test / sec / doc) | 14 built-in `speckit.*` agents |
| Handoff mechanism | Learner manually switches `@agent` in chat | Each agent declares `handoffs:` in frontmatter; Copilot Chat renders buttons |
| Artifacts | Code + tests + docs (scattered) | `constitution.md` + `spec.md` + `plan.md` + `tasks.md` (phased, persisted) |
| Auditability | Weak (all in chat history) | Strong (every phase is git-tracked markdown) |
| Task parallelism | Learner plans mentally | `tasks.md` auto-tags `[P]` parallel markers |
| Scope | Small tasks in a single repo | Any mid-to-large feature / team collaboration |

**Narrative arc**: hand-crafted → industrialized → spec-driven.

---

## Prerequisites / Environment Check

### Required

- Python **3.11+** (mandatory since spec-kit 0.8)
- `uv` package manager (or pipx / pip --user)
- VS Code **Insiders** (best Custom Agents support) + GitHub Copilot Chat
- Completed Lab 2 / Lab 3; familiar with the `lab-starter` Ticket Service code

### One-shot check

```bash
specify check
```

Expected output: `✔ git`, `✔ python>=3.11`, `✔ copilot integration` all green.

### Fallback if the instructor VM is missing tools

```bash
# Install uv (if missing)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install specify-cli (pin main branch to avoid 0.10 breaking changes)
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# Verify
specify --version   # expect 0.8.x.dev or newer
```

> ⚠️ **0.10 breaking change warning**: `--ai copilot` is deprecated; from 0.10 the flag is **`--integration copilot`** (required). This lab uniformly uses the new syntax.

### Pre-seeded git tag for the demo (strongly recommended)

To avoid live-running `specify init` (network / Python version / existing `copilot-instructions.md` conflicts), the repo ships a pre-seeded git tag:

```bash
cd lab-starter
git checkout speckit-baseline   # jump to the post-init state
```

The tag contains:
- `.specify/` (36 files: templates, scripts, memory, workflows)
- `.github/prompts/speckit.*.prompt.md` (14 files)
- `.github/agents/speckit.*.agent.md` (14 files; the real system prompt body lives here)

---

## Hands-on Steps

### Step 0: Concept intro — 3 min

**Instructor narration:**

> In the previous lab we manually wired 4 agents in sequence. But in a real team you can't rewrite agents and re-plan handoffs from scratch for every project.
>
> GitHub's open-source **spec-kit** (2025) industrializes this: it ships **14 pre-built agents** plus an **SDD workflow template** (constitution → spec → plan → tasks → implement). You focus on the business; the template owns the process.
>
> That's **Spec-Driven Development**: distilling conversational coding into auditable spec artifacts.

---

### Step 1: Inspect the artifact tree — 3 min

Switch to the pre-seeded tag:

```bash
cd lab-starter
git checkout speckit-baseline
```

In VS Code Explorer, expand:

```
lab-starter/
├── .specify/
│   ├── memory/constitution.md          ← project constitution (placeholders, to be filled)
│   ├── templates/                      ← 5 templates: spec / plan / tasks / checklist / constitution
│   ├── scripts/bash/                   ← 5 helper scripts (create feature branch, etc.)
│   ├── workflows/speckit/workflow.yml  ← top-level workflow definition
│   └── extensions/git/                 ← built-in git extension (auto branch + commit hooks)
└── .github/
    ├── copilot-instructions.md         ← injected by spec-kit; tells Copilot to read current plan
    ├── prompts/                        ← 14 .prompt.md (each just 3 lines of frontmatter)
    └── agents/                         ← 14 .agent.md (real system prompts, 300+ lines each)
```

**Highlight:**

1. **Two-layer structure**: `.prompt.md` is minimal (just `agent: speckit.xxx`); the real logic is in the matching `.agent.md`. This is new in spec-kit 0.8 — it routes through VS Code Custom Agents.
2. **handoffs field**: open any `.github/agents/speckit.specify.agent.md` and look at the frontmatter:

   ```yaml
   handoffs:
     - label: Build Technical Plan
       agent: speckit.plan
       prompt: Create a plan for the spec. I am building with...
     - label: Clarify Spec Requirements
       agent: speckit.clarify
   ```

   → This is **the industrialized version of Lab 3's hand-crafted handoff**. Each agent explicitly declares its next stops; Copilot Chat renders them as buttons.

3. The repo's existing 10 custom Workshop agents (architect / red-team / etc.) and the 14 injected `speckit.*` agents **coexist in the same directory**, namespaced by the `speckit.` prefix — **no conflict**.

---

### Step 2: `/speckit.constitution` — fill the project constitution — 5 min

In VS Code Copilot Chat:

```
/speckit.constitution
```

Then provide the body:

```text
Please populate the constitution for our Ticket Service project with the following principles:

1. **Test Coverage**: All new endpoints must have unit tests + integration tests, with line coverage >= 80%.
2. **API Design**: Follow REST conventions; use plural nouns; return appropriate HTTP status codes (200/201/204/400/404/500).
3. **Security**: Input validation on every endpoint; never leak stack traces in error responses; log auth failures.
4. **Observability**: Every endpoint must log request id + duration; errors logged with full context.
5. **Backward Compatibility**: Never break existing endpoints in a minor release.
```

**Expected artifact**: `.specify/memory/constitution.md` is filled in by Copilot, replacing every `[PRINCIPLE_X_NAME]` placeholder.

**Instructor narration**:

> The constitution is the **top-level constraint** on every downstream spec/plan. `/speckit.plan` will read it automatically — that's why `plan.md` ends up containing hard requirements like "80% test coverage".

---

### Step 3: `/speckit.specify` — write the search-endpoint spec — 6–8 min

Our mini feature: **add a `GET /tickets/search?q=` endpoint to the Ticket Service** (same business line as Lab 2/3).

In Copilot Chat:

```
/speckit.specify
```

Feature description:

```text
Add a search endpoint to the Ticket Service.

Requirements:
- Endpoint: GET /tickets/search?q=<keyword>
- Search behavior: case-insensitive substring match against ticket.title and ticket.description
- Pagination: support ?limit=<n>&offset=<m>, default limit=20, max=100
- Response: { total: number, items: Ticket[] }
- Error handling: 400 if q is empty or > 200 chars
- Performance: must return within 100ms for stores up to 10k tickets
```

**Expected artifacts**:

1. A branch `001-ticket-search` (or similar number + short-name) is created automatically
2. `specs/001-ticket-search/spec.md` (full spec document)
3. `specs/001-ticket-search/checklists/requirements.md` (auto-generated requirements checklist)
4. `.specify/feature.json` (metadata for the currently active feature)

**Instructor narration**:

> Three things to notice:
>
> 1. **Automatic branch creation** — enforced git workflow isolation, one branch per feature.
> 2. **At most 3 `[NEEDS CLARIFICATION]` markers** — spec-kit explicitly caps this so specs don't accumulate unresolved questions.
> 3. **Checklist generated for free** — you don't manually enumerate acceptance criteria.

---

### Step 4: `/speckit.plan` + `/speckit.tasks` — 6–8 min

#### 4.1 Generate the technical plan

```
/speckit.plan
```

Prompt:

```text
Plan the implementation using the existing Node.js + Express stack in lab-starter.
Reuse ticketStore.js patterns. Add an in-memory index for fast substring search.
Include test plan using existing jest setup.
```

**Expected artifact**: `specs/001-ticket-search/plan.md`, including:
- Stack choice (reuses Node + Express + Jest)
- Data structure design (in-memory inverted index)
- File change list (`ticketStore.js`, `app.js`, `tests/search.test.js`)
- Test strategy (unit + integration + perf benchmark)
- Explicit mapping to the 5 constitution principles

#### 4.2 Break down into tasks

```
/speckit.tasks
```

**Expected artifact**: `specs/001-ticket-search/tasks.md`, typically:

```markdown
## Tasks
- [ ] T001 Add `searchTickets(q, limit, offset)` to ticketStore.js
- [ ] T002 [P] Add input validation helper `validateSearchQuery(q)`
- [ ] T003 Wire GET /tickets/search route in app.js
- [ ] T004 [P] Unit tests for searchTickets in tests/searchTickets.test.js
- [ ] T005 [P] Integration tests for GET /tickets/search in tests/search.api.test.js
- [ ] T006 Performance benchmark (10k tickets, < 100ms)
- [ ] T007 Update docs/api.md
```

**Focus on the `[P]` marker**:

> spec-kit analyzes task dependencies and tags tasks that **have no dependencies, touch different files, and are safely parallelizable** with `[P]`. If you use Mission Control or multiple cloud coding agents, the `[P]` tasks can run in parallel.
>
> → This is **the industrialized version of Lab 3's "parallel execution" pattern**.

---

### Step 5: `/speckit.analyze` — cross-artifact review — 3 min

```
/speckit.analyze
```

**Expected behavior**: spec-kit performs a **read-only** cross-read of `constitution.md` + `spec.md` + `plan.md` + `tasks.md` and emits a structured review report.

**Severity levels**:

| Level | Meaning | Action |
|---|---|---|
| **CRITICAL** | Violates the constitution / internal contradictions | Must fix before implement |
| **WARNING** | Design risk but not blocking | Add mitigation in the plan |
| **INFO** | Optimization suggestion | Optional |

**Instructor narration**:

> This is a "read-only agent" — same idea as Lab 3's Security Reviewer: **review rights and write rights are separated**.
> What's different is that spec-kit's analyze is **cross-artifact**: it checks whether the spec covers every constitution clause, whether the plan implements every spec requirement, and whether tasks cover every plan change. That's hard to achieve with hand-crafted agents.

---

### Step 6: `/speckit.implement` — narrated only — 2 min

```
/speckit.implement       ← do NOT run live; narrate only
```

**Instructor narration**:

> implement does the following:
>
> 1. Walks `tasks.md` in order (respecting `[P]` for parallelism) and executes each task
> 2. After each task completes, it **auto-commits** (driven by the built-in git extension)
> 3. After all tasks complete, it runs the test suite
>
> Why is **auto-commit per task** so important?
>
> - On failure, you can roll back precisely to any task boundary
> - PR review gets one commit per task — much easier to audit
> - This is the **last mile from "conversational coding" to "auditable SDD"**
>
> Homework: run implement end-to-end in your own environment and inspect the commit history.

---

### Step 7: Q&A + homework — 3 min

---

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| `--ai copilot` deprecation warning | Red text in terminal | Use `--integration copilot` (mandatory from 0.10) |
| Python too old | `specify init` errors immediately | `winget install Python.Python.3.11` / `pyenv install 3.11` |
| `copilot-instructions.md` conflict | Existing custom instructions overwritten | Wrap the spec-kit area with `<!-- SPECKIT START --> ... <!-- SPECKIT END -->`, or run init in a subdirectory |
| `.prompt.md` looks empty | Learner is confused | Make it explicit: the real body is in the matching `.agent.md` |
| 14 speckit.* agents flood the menu | Selector noise | Use `chat.agent.hide` in VS Code Settings |
| Copilot Chat shows no handoff buttons | Outdated VS Code | Upgrade to the latest VS Code Insiders |
| `specify check` complains about git remote | Repo has no origin | `git remote add origin <url>` and retry |

---

## Homework / Advanced Exploration

### Required

1. Run `/speckit.implement` end-to-end in your own environment and verify each task gets its own auto-commit
2. Add a new task to `tasks.md` by hand (e.g., "add fuzzy match option") and observe how implement handles it

### Stretch goals

1. **Hook into Mission Control**: dispatch `[P]` tasks to multiple cloud coding agents and watch parallel PRs land
2. **Author your own `speckit.*` agent**: following the spec-kit pattern, add `speckit.security-review.agent.md` and slot it into the `analyze → implement` handoff
3. **Offline install**: prepare offline wheels of spec-kit for an enterprise air-gapped environment (see `docs/enterprise-deployment-guide.md`)
4. **Cross-runtime collaboration**: let Copilot drive the front half (constitution → tasks), hand `tasks.md` to a Hermes Agent on an Azure VM for implement

---

## Completion Criteria

- [ ] Understand the 6-stage SDD pipeline (constitution → specify → plan → tasks → analyze → implement)
- [ ] Can locate `.specify/` and `.github/agents/speckit.*` in VS Code
- [ ] Completed `/speckit.constitution`
- [ ] Completed `/speckit.specify` and observed the auto-created branch + spec.md
- [ ] Completed `/speckit.plan` + `/speckit.tasks` and can explain the `[P]` marker
- [ ] Ran `/speckit.analyze` and understand the severity levels
- [ ] Can articulate how spec-kit handoffs map to Lab 3's hand-crafted handoffs

---

## References

- GitHub Spec-Kit repo: <https://github.com/github/spec-kit>
- SDD concept (GitHub Blog): <https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai>
- VS Code Custom Agents docs: <https://code.visualstudio.com/docs/copilot/customization/custom-agents>
- Workshop evaluation report: `docs/speckit-eval-report.md` (instructor-internal)
- Lab 3 recap: `labs/lab3-multi-agent-collaboration.md`
