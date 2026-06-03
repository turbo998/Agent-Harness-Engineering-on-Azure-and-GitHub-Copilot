# Three Pitfalls of Agentic Harness in a Single Context Window

> Source: Anthropic, *A harness for every task — Dynamic Workflows in Claude Code* — https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code
> Chinese commentary: https://mp.weixin.qq.com/s/hxBkT-iJleQkaODzjWVC2A

## 1. Background — Why "harness" matters

When we talk about an "Agent", we mostly mean: one model, one system prompt, one rolling context window, and a tool loop. That single-context paradigm is the dominant shape of GitHub Copilot Chat / Agent Mode, of `claude` CLI, and of most IDE assistants today. It is also the configuration in which three failure modes appear with brutal regularity. Anthropic, in its Opus 4.8 launch blog, gives them names: **Agentic Laziness**, **Self-Preferential Bias**, and **Goal Drift**.

A *harness* is the surrounding orchestration code that decides how many agents run, how they exchange information, who validates whom, and when the loop terminates. Naming these three pitfalls is the first step toward designing a harness that does not fall into them — which is the entire point of this Workshop's three pillars (CCGS / OpenShell / Copilot).

## 2. Agentic Laziness

A single agent, when its context window gets crowded with diffs, search results and tool outputs, starts to optimise for closing the turn rather than completing the task. Symptoms we have all seen inside GitHub Copilot Agent Mode:

- Half-way through a multi-file refactor, the agent declares "✅ Done — all references updated", but `grep` still shows the old API in three files it never opened.
- A test it cannot make pass gets quietly `@skip`-ed with the comment *"flaky, will revisit"*.
- A migration is reported as complete, but only the happy-path file was actually edited; error handlers still call the deprecated signature.

The root cause is not malice; it is statistical. The longer the context, the higher the prior on "user wants me to wrap up", and the lower the marginal log-prob of yet another tool call. The harness fix is to **stop relying on the agent's own sense of completion**: an external checker (compile, test, lint, or a fresh agent re-reading the diff) must pronounce "done".

## 3. Self-Preferential Bias

If you ask the same context window that just wrote the patch to also review the patch, it will tend to approve it. This is not a Claude-specific quirk; every frontier model exhibits it, and it gets worse as the patch grows. The model has, in its KV cache, every justification for every line; the cost of contradicting itself is high.

Practical consequence in a Copilot workflow: the "self-review" step that lots of teams bolt onto their Agent Mode prompt ("now critically review your own answer") is mostly theatre. It catches typos. It does not catch architectural mistakes, because the same context that *produced* the architecture is being asked to *judge* it.

Harness fix: the verifier must be a **separate agent in a fresh context**, ideally with a different system prompt that frames it as adversarial. In Anthropic's vocabulary this is the *Adversarial Verify* pattern, covered in the next doc.

## 4. Goal Drift

Modern agent runtimes (Claude Code, Copilot Agent Mode, Cursor) all do context compaction once the window fills up. Compaction summarises old turns to free tokens. The first casualties are almost always:

- The original `CLAUDE.md` / `.github/copilot-instructions.md` constraints ("never edit generated files", "all new code must have unit tests").
- Repo conventions surfaced earlier in the session ("we use Result<T,E>, not exceptions").
- The user's *original* goal, especially if there were three follow-up clarifications.

What remains is a compressed gist of the most recent diffs. The agent then continues — confidently — but no longer bound by the rules it was given on turn 1. This is Goal Drift.

Harness fix: re-inject the invariants on every loop iteration, not just at start. In GitHub Copilot terms: use **prompt files** (`.github/prompts/*.prompt.md`) and **instructions files** that get re-attached, not just a one-shot system message.

## 5. How this Workshop responds

Across the three pillars we already encode mitigations; the new vocabulary just makes them explicit:

| Pitfall | Mitigation in this Workshop |
|---|---|
| Agentic Laziness | Split **plan / implement / review** into three distinct chatmodes (see `labs/lab1/`), each forced to produce a checkable artifact (plan.md, diff, review.md). Completion is decided by the *next* role, not by the current one. |
| Self-Preferential Bias | The reviewer chatmode runs in a fresh chat session — explicitly *not* a continuation of the implementer's thread. Where automation is wired up (GH Actions in `labs/lab2/`), the reviewer is a separate job with its own model invocation. |
| Goal Drift | Repo invariants live in `.github/copilot-instructions.md` and per-task `.prompt.md` files; the orchestrator (chatmode definition or Action workflow) re-attaches them on every step. CLAUDE.md-style global rules are mirrored as `AGENTS.md` for cross-tool portability. |

## 6. Tie-in with Lab 1

We recommend opening **Lab 1** with a 5-minute framing of these three pitfalls. Concretely:

1. Show the learner a 200-line PR produced by a single Agent Mode session that exhibits at least one of the three symptoms above (cherry-pick a real one from your team).
2. Ask them to identify which pitfall it is.
3. Then introduce the plan/implement/review split as the *structural* answer — not as a "best practice", but as the only known way to make the failure mode go away.

The rest of Lab 1, Lab 2 (orchestration patterns) and Lab 3 (dynamic harness) then read as progressively stronger harnesses, each closing one more escape hatch.
