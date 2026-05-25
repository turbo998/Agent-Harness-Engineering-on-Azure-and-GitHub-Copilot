# Multi-Agent Orchestration: GitHub Copilot vs Claude Code Agent Teams

> Perspective: starting from GitHub Copilot, compared against Claude Code's experimental **Agent Teams** feature (2026-05). Answers the two questions partners ask most: "I already have Copilot — why care how others do multi-agent?" and "Where does Copilot's own multi-agent roadmap land in this picture?"
>
> Source article (Chinese): https://mp.weixin.qq.com/s/_qlK7sP3V_5P-z6XaHc2sA — by "鲁工" (Lu Gong)

---

## TL;DR

Copilot and Claude Code are on the **same engineering track** for multi-agent (local orchestration + shared artifacts + quality gates), but the product shape and cost curve differ:

| Dimension | GitHub Copilot | Claude Code Agent Teams |
|-----------|----------------|-------------------------|
| Local collaboration | Custom Agents (`.github/agents/*.md`) + handoff | Agent Teams (experimental, behind flag) |
| Cloud parallelism | **Coding Agent + Mission Control / Agent HQ** | None native — relies on local tmux/iTerm2 panes |
| Trigger | Explicit `@agent-name` | Prompt keywords `agent team` / `teammate` |
| Teammate communication | Via shared files / PRs / Issues (async) | **Direct teammate-to-teammate messaging** (sync) |
| Task board | Mission Control / Agent HQ UI | Terminal `Ctrl+T` shared task list |
| Cost model | Per-seat + Coding Agent task quota | Each teammate is a separate API instance — **3–4× token vs single session** |
| Governance / approval | `copilot-instructions.md` + branch protection + PR review | Plan approval + three new hooks (`TeammateIdle` / `TaskCreated` / `TaskCompleted`) |
| Best fit | Cross-repo parallel delivery, CI/CD-driven automation | Single-repo research, review, competing-hypothesis debugging |

**One-liner**: Copilot is **enterprise cloud orchestration** (Mission Control + Coding Agent for real cross-repo parallelism); Claude Code Agent Teams is **developer-local deep collaboration** ("teammates discussing" inside one repo). Not substitutes — pick by task boundary.

---

## 1. Concept Mapping: Translating Claude Code Terms to Copilot

| Claude Code | GitHub Copilot equivalent | Notes |
|-------------|---------------------------|-------|
| Subagents | **Custom Agents** in `.github/agents/*.md` | Own system prompt, tools, model; invoked via `@agent-name` |
| Agent Teams (lead + teammates) | **Mission Control / Agent HQ** + multiple Coding Agents | Copilot's "team lead" is the Mission Control plane; "teammates" are cloud Coding Agent instances |
| Shared task list (`Ctrl+T`) | Mission Control board + GitHub Issues / Projects | Copilot's task state is first-class on GitHub |
| Plan approval | PR review + branch protection rules | Copilot uses native GitHub approval — better for enterprise governance |
| Hooks (`TaskCreated`, etc.) | GitHub Actions / Repository rulesets / Branch protection | Copilot puts hard constraints at the repo-governance layer, not the agent runtime |
| `~/.claude/teams/` local dir | Mission Control cloud state / GitHub UI | Copilot's collaboration state is in the cloud, multi-user visible; Claude Code is on local disk |

**Key insight**: Claude Code designs multi-agent as **in-process / in-terminal** collaboration. Copilot designs it as **cross-repo, cross-PR, auditable** engineering. That difference defines each product's sweet spot.

---

## 2. What Copilot Users Should Learn from Agent Teams

Even if you only use Copilot, three engineering ideas from Agent Teams are worth borrowing:

### 2.1 Teammates That Can Talk to Each Other Directly

Copilot's Custom Agents currently communicate **indirectly through files and PRs** (A edits code → opens PR → B reviews). Agent Teams gives teammates **synchronous dialogue**, which helps with:

- **Competing-hypothesis debugging**: 3 teammates each run a theory in parallel and reconcile when they contradict
- **Multi-angle review**: security / performance / test-coverage in parallel, mutual challenge, then synthesis

**Copilot's closest analogue today**: run 3 Coding Agents in Mission Control, each owning an angle, with a human or a "synthesizer agent" aggregating PR / Issue comments. Less synchronous, but **fully auditable** — every discussion is a PR/Issue/commit.

### 2.2 Explicit "Plan → Approve → Execute" Loop

Agent Teams encourages the lead to require a plan before teammates touch code, with the criteria written into the prompt ("must include test coverage", "must include rollback strategy").

**Copilot equivalent**:
- Codify plan standards in `.github/copilot-instructions.md`
- Use **Spec-driven workflow** (see lab 4) — agent produces SPEC + ADR first, reviewed (by human or automation) before implementation
- Use **GitHub Actions** at PR time to enforce security scans and coverage thresholds — Copilot's version of the "hook hard constraint"

### 2.3 Sweet Spot: 3–5 Teammates × 5–6 Tasks Each

This is a **cross-product engineering rule**. Equally true for Copilot Mission Control:

- Launch 15 Coding Agents on 15 repos? Coordination cost explodes, PR review queue floods
- 3–5 agents with 5–6 related tasks each is the balance point where humans can review and models stay under quota

This is the "capacity planning" number partners need when rolling out.

---

## 3. Cost & Quota Comparison

| Item | GitHub Copilot | Claude Code Agent Teams |
|------|----------------|-------------------------|
| Billing model | Per-seat + Coding Agent task quota (Business/Enterprise includes allotment) | Direct API token spend (Pro/Team/Max includes allotment) |
| Multi-agent multiplier | Each Coding Agent task billed independently | **3–4× single-session tokens** |
| Quota risk | Coding Agent tasks queue/reject on overflow | Even Max 20x hits the **5-hour rolling quota** |
| Enterprise predictability | High (per seat) | Medium (task complexity dominates) |

**Partner talking point**: Copilot's multi-agent is easier on enterprise finance. Claude Code Agent Teams has stronger raw concurrency but needs a "token blackhole" plan. Both should be piloted first on **research / review** tasks with no write side-effects.

---

## 4. Scenario Selection Matrix (Four Tiers)

| Task profile | Recommended | Why |
|--------------|-------------|-----|
| Single session, strong sequential dependency | **VS Code Copilot Chat (default Agent mode)** | No coordination overhead needed |
| Single repo, splittable subtasks | **Copilot Custom Agents handoff** (this workshop, lab 3) | Team shares `.github/agents/`, config-as-code |
| Single repo, needs "teammate discussion" | **Claude Code Agent Teams** | Sync teammate messaging helps competing-hypothesis debugging |
| Cross-repo, cross-PR parallelism | **Copilot Coding Agent + Mission Control / Agent HQ** | Cloud-native orchestration + GitHub governance |
| Hundreds of sub-agents, large-scale fan-out | **Cloud Swarm (Kimi K2.6 / custom)** | Local orchestration no longer fits |

---

## 5. Partner-Facing Recommendations

1. **Avoid framing it as "replacement"**: when a customer asks "is Agent Teams going to replace Copilot?", break the task into the four tiers above and route by boundary.
2. **Copilot's moat is the governance layer**: PR approval, branch protection, Coding Agent + Actions integration — capabilities Claude Code does not yet have at the enterprise tier.
3. **Borrow the engineering wisdom**: 3–5 sweet spot, Plan approval criteria, lead-with-research/review — these hold regardless of product, put them in your enablement materials.
4. **Hybrid is fine**: developers can use Claude Code Agent Teams locally for deep single-repo collaboration, while team-wide and cross-repo work goes through Copilot Mission Control. No conflict.

---

## 6. Cross-Reference to This Workshop

- **Lab 3 — Multi-Agent Collaboration**: Custom Agents handoff ≈ Claude Code subagents. Use this doc as extended reading for lab 3's "Advanced Discussion".
- **Lab 4 — Spec-Driven / Multi-Role Code Review**: corresponds to Agent Teams' "Plan approval" + "multi-angle review".
- **Lab 5 — Ship and Release**: Coding Agent + Mission Control is the "cloud orchestration" reference implementation against Claude Code's local approach.

---

## References

- Source article: https://mp.weixin.qq.com/s/_qlK7sP3V_5P-z6XaHc2sA
- Claude Code Agent Teams official docs (experimental — enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)
- GitHub Copilot Coding Agent / Mission Control / Agent HQ official docs
- Workshop Lab 3 / Lab 4 / Lab 5
