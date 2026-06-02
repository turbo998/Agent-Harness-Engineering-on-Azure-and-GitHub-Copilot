---
description: "Orchestrate a staged 4-agent review team (Architect → Security → UX → QA) over a PR or changeset, with explicit Phase Gates between each stage. Adapted from Claude-Code-Game-Studios `/team-combat` pattern."
mode: agent
tools: ['codebase', 'search', 'usages', 'changes', 'githubRepo', 'editFiles']
variables:
  - name: target
    description: "Pull request URL/number, branch name, commit range, or comma-separated file list to review"
  - name: review_mode
    description: "full | lean | solo  — full: 4 agents + all gates; lean: 4 agents, skip approval gates 1&3; solo: collapse all into a single pass. Default: lean"
---

# 🎬 `/team-copilot-review` — Staged Multi-Agent PR Review

> 改编自 [Claude-Code-Game-Studios `/team-combat`](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/main/.claude/skills/team-combat/SKILL.md) 的多 agent 流水线模式 + Phase Gates。
> 对应 Workshop **Lab 3**：演示 sequential handoff + 显式审批门 + Review Mode 三档伸缩。

## Argument Check

If `{{target}}` is empty, output exactly:

> "Usage: `/team-copilot-review <PR-URL | branch | file-list> [--review full|lean|solo]` — please supply a review target."

Then **stop immediately** without spawning any agent.

---

## Phase 0 · Resolve Review Mode

Resolve `{{review_mode}}`:

1. If user passed `--review <mode>` → use it.
2. Else read `.github/review-mode.txt` if present → use whatever is written there.
3. Else default to **`lean`**.

| Mode | Pipeline Behavior |
|------|-------------------|
| **`full`** | All 4 agents + Phase Gate after every phase + final consolidated gate |
| **`lean`** | All 4 agents, but skip Phase Gate 1 (architect) and Phase Gate 3 (UX); keep Security and final gates |
| **`solo`** | Single pass — invoke each agent inline, no gates, write a single report |

Print the resolved mode at the top of the run so the user knows what to expect.

---

## Team Composition

| Phase | Agent | Owns | Output |
|-------|-------|------|--------|
| 1 | `@architect` | Diff-level architecture, layering, contracts, blast radius | `## Architecture Findings` |
| 2 | `@security-reviewer` | Input validation, authn/z, secrets, injection, SSRF, supply chain | `## Security Findings` |
| 3 | `@product-reviewer` | API ergonomics, error messages, naming, docs, UX of public surface | `## UX / DX Findings` |
| 4 | `@test-engineer` | Test coverage gaps, missing edge cases, regression risk | `## QA Findings` + suggested test stubs |

All four agents are already shipped in `lab-starter/.github/agents/`. If any are missing, abort with: *"Agent file `<name>.md` not found — see `lab-starter/.github/agents/` to add it."*

---

## Pipeline

### Phase 1 · Architecture (Architect)

Invoke `@architect` over `{{target}}`:

- Identify all changed modules, their layering depth, and cross-cutting impact
- Flag any contract / interface / DB schema changes
- Score blast radius: **Local / Module / Service / Cross-service**
- Output a max 10-bullet **Architecture Findings** list

**Phase Gate 1** (skipped in `lean` and `solo`):

> Agent → user: "Architecture review complete. Blast radius = **<level>**. I see N notable issues.
>   ① Proceed to Security?  ② Stop and let me fix architecture first?  ③ Rerun on a narrower scope?"

Wait for the user. If `proceed` → Phase 2. Else act on the choice.

### Phase 2 · Security (Security Reviewer)

Invoke `@security-reviewer`. Always emits structured findings:

```
CRITICAL  — must fix before merge
WARNING   — fix in this PR or open follow-up issue
INFO      — heads-up / hardening suggestion
```

**Phase Gate 2** (always runs, even in `lean`):

> Agent → user: "Security review found `<N>` CRITICAL / `<M>` WARNING / `<K>` INFO.
>   ① Proceed to UX review?  ② Stop and triage security first?  ③ Convert findings to issues now?"

If any **CRITICAL** is present and user picks ①, prepend the consolidated report with a 🚨 banner.

### Phase 3 · UX / DX (Product Reviewer)

Invoke `@product-reviewer` — focus on the **public surface** changes:

- Endpoint naming consistency, HTTP semantics
- Error message clarity (no stack-trace leaks, actionable wording)
- Doc/README/CHANGELOG drift
- Backward compatibility impact

**Phase Gate 3** (skipped in `lean` and `solo`):

> Agent → user: "UX review done. Proceed to QA, or pause to discuss naming/contract issues?"

### Phase 4 · QA (Test Engineer)

Invoke `@test-engineer`:

- For each changed function/endpoint, list **missing test cases** with rationale
- Propose **drop-in test stubs** (file + test name + assertion sketch) — do NOT write them yet
- Estimate effort: S (≤30 min) / M (≤2 h) / L (>2 h)

---

## Consolidated Report

Aggregate all four phase outputs into a single report and **print it to the conversation** (do not write to disk yet):

```markdown
# 🔍 Multi-Agent Review · <target> · mode=<review_mode>

## 📊 Summary
| Phase | Critical | Warning | Info | Recommend |
|-------|---------:|--------:|-----:|-----------|
| Architecture |  |  |  | ✅ / ⚠️ / 🛑 |
| Security |  |  |  |  |
| UX / DX |  |  |  |  |
| QA |  |  |  |  |

**Overall:** ✅ Approve / ⚠️ Request Changes / 🛑 Block

## 🔥 Top 3 Blockers
1. ...
2. ...
3. ...

## 📋 All Findings
[concatenated from each phase, sorted by severity]

## 🧪 Suggested Test Stubs
[from @test-engineer]
```

---

## Final Gate (always runs)

> Agent → user: "Consolidated report is in the chat. Next?
>   ① Write to `reviews/<PR-id>.md` and stop.
>   ② Convert all CRITICAL findings to GitHub issues via `@speckit.taskstoissues`.
>   ③ Have `@test-engineer` actually write the suggested test stubs (requires per-file approval).
>   ④ Nothing — I'll handle it manually."

**Never** call `Write` / `Edit` / `git commit` / open an issue without an explicit pick.

---

## Workshop Hooks (Lab 3)

- **Demo mode (`lean`)**: 8–10 minutes — shows Security gate + final gate, fits the lab time budget.
- **Discussion**: have learners flip the same PR through `full` vs `solo` and compare:
  - Which gates **caught real issues** vs **felt like ceremony**?
  - Where would you put a `--review` default for *your* team?
- **Extension**: replace `@architect` with a domain-specific agent (e.g. `@perf-engineer`, `@a11y-reviewer`) and observe how the gate vocabulary stays the same — the **pipeline shape generalizes**.

## References

- Pattern source: [`/team-combat` in Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/main/.claude/skills/team-combat/SKILL.md)
- Phase-gate philosophy: `.claude/docs/director-gates.md` (CCGS)
- Companion doc: `docs/collaboration-protocol-template.md` — every agent above MUST follow Question → Options → Decision → Draft → Approval.
