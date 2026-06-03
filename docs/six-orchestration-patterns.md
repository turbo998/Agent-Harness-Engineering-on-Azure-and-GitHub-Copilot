# Six Orchestration Patterns for an Agentic Harness

> Source: Anthropic, *A harness for every task — Dynamic Workflows in Claude Code* — https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code
> Chinese commentary: https://mp.weixin.qq.com/s/hxBkT-iJleQkaODzjWVC2A

Once you accept that a single agent in a single context window has [three structural failure modes](./three-pitfalls-of-agentic-harness.md), the next question is: *what shape of multi-agent orchestration actually fixes them?* Anthropic's Opus 4.8 blog enumerates six recurring patterns. This doc gives each of them a one-paragraph definition, a Claude-Workflow-style pseudo-JS sketch, and the equivalent path in the GitHub Copilot ecosystem (custom chatmodes, `@workspace` agents, MCP servers, VS Code tasks, GitHub Actions matrix). Each section ends with a Lab 2 exercise pointer.

## 1. Classify-Route

**Definition.** A lightweight classifier agent reads the input, decides which downstream specialist should handle it, and routes accordingly. The classifier is cheap and stateless; specialists are heavy and domain-specific.

**Claude Workflow sketch.**

```js
const kind = await agent({ system: "Classify into {bug, feature, doc, infra}" , input });
const handler = { bug: bugAgent, feature: featAgent, doc: docAgent, infra: infraAgent }[kind];
return await handler(input);
```

**GHCP equivalents.**
- A single **custom chatmode** (`triage.chatmode.md`) whose only job is to emit a label, plus 4 specialist chatmodes the user is told to switch to.
- A **GitHub Actions** workflow with `jobs.<id>.if:` guards on the classifier's JSON output (use `actions/github-script` to call Copilot).
- An **MCP router server** that exposes one tool `route(intent)` and dispatches to per-domain tool subsets.

**Lab 2 exercise.** "Build a triage chatmode that classifies an incoming issue, then writes the routing decision as a sticky comment on the issue. Each label triggers a different `.prompt.md`."

## 2. Fan-out-Reduce

**Definition.** Split the work into N independent subtasks, run them in parallel, then have a reducer agent merge the results. Classical map-reduce, but the map workers are LLMs and the reducer is also an LLM (sometimes deterministic code).

**Claude Workflow sketch.**

```js
const chunks = splitFiles(repo, 20);
const findings = await parallel(chunks.map(c => agent({ system: "Find dead code in these files", input: c })));
return await agent({ system: "Merge findings, dedupe, rank by risk", input: findings });
```

**GHCP equivalents.**
- **GitHub Actions matrix**: `strategy.matrix.shard: [0..N]`, each shard runs the same Copilot prompt over its slice, a final job runs the reducer prompt.
- **VS Code tasks** with `dependsOn` for local fan-out, plus a final aggregation task.
- An **MCP server** exposing `fanout(task, partitions)` that internally spawns N model calls and concatenates.

**Lab 2 exercise.** "Run a dead-code scan across the monorepo using a 4-way matrix; reducer ranks the top 10 candidates and opens a single PR."

## 3. Adversarial Verify

**Definition.** After a generator agent produces an artifact, a *separate* verifier agent — in a fresh context, with an explicitly adversarial system prompt — tries to break it. The verifier's only success criterion is "find a real flaw". The loop ends when the verifier yields.

**Claude Workflow sketch.**

```js
let patch = await agent({ system: "Implement feature X", input: spec });
for (let i = 0; i < 3; i++) {
  const attack = await agent({ system: "You are a hostile reviewer. Find a real bug or stop.", input: patch });
  if (attack.kind === "approve") break;
  patch = await agent({ system: "Fix the issue raised", input: { patch, attack } });
}
```

**GHCP equivalents.**
- Two chatmodes: `implementer.chatmode.md` and `red-team-reviewer.chatmode.md`. The user explicitly opens a **new chat** for the reviewer — context isolation is the entire point.
- In CI: an Action job `implement` writes a diff to an artifact; a separate job `review` runs in a clean runner and posts blocking review comments. The reviewer **must not** receive the implementer's prompt.
- MCP: a `verify(diff)` tool whose backing agent has a different model temperature and a hostile system prompt baked in.

**Lab 2 exercise.** "Wire an Action that runs implement → review → patch up to 3 cycles; fail the PR if cycle 3 still yields blocking comments."

## 4. Generate-Filter

**Definition.** Generate K candidate outputs (high temperature, diverse prompts, or different models), then filter down to the best — typically with a deterministic filter (compile, tests, lint) before any LLM-based judgement, because deterministic filters are free and infallible.

**Claude Workflow sketch.**

```js
const candidates = await parallel(Array.from({length: 8}, (_,i) => 
  agent({ system: "Implement X. Variant " + i, input: spec, temperature: 0.9 })));
const compiling = candidates.filter(c => tryBuild(c).ok);
const passing  = compiling.filter(c => runTests(c).pass);
return await agent({ system: "Pick the cleanest impl", input: passing });
```

**GHCP equivalents.**
- **Actions matrix** with `seed: [1..8]` injected into the prompt, followed by a deterministic `build && test` gate, followed by a single reducer job.
- Locally: a VS Code task that loops Copilot with N different `.prompt.md` variants and runs `npm test` between each.

**Lab 2 exercise.** "Generate 5 candidate implementations of a small utility, drop the ones that fail unit tests, let a judge agent pick the survivor."

## 5. Tournament (1v1 pairwise vs absolute scoring)

**Definition.** When you have many candidates and no ground truth, asking a judge for an absolute score (0–10) is noisy. Pairwise comparison ("which of these two is better?") is dramatically more reliable, at the cost of O(N²) or O(N log N) comparisons in a bracket.

**Claude Workflow sketch.**

```js
async function pickWinner(a, b) {
  const r = await agent({ system: "Which patch is better, A or B? Reply A|B.", input: { a, b } });
  return r === "A" ? a : b;
}
let bracket = candidates;
while (bracket.length > 1) {
  bracket = await parallel(pairs(bracket).map(([a,b]) => pickWinner(a,b)));
}
return bracket[0];
```

**Trade-off.** Pairwise is more accurate but quadratic; absolute scoring scales linearly but biases toward verbose outputs. For more than ~16 candidates, use a Swiss or single-elimination bracket.

**GHCP equivalents.**
- Actions: a `tournament.yml` workflow with a recursive `workflow_call` that takes a list of artifact IDs and emits a winner.
- MCP: a `compare(a, b)` tool the orchestrator calls in a loop.

**Lab 2 exercise.** "Given 8 PR descriptions for the same commit, run a single-elimination bracket to pick the best one for the changelog."

## 6. Loop-Until-Stable

**Definition.** Re-run the agent on its own output until the output stops changing (or until a budget cap). Useful for iterative refinement: formatting, refactoring passes, doc polish, schema migrations.

**Claude Workflow sketch.**

```js
let prev = null, cur = input;
for (let i = 0; i < 6 && prev !== cur; i++) {
  prev = cur;
  cur = await agent({ system: "Improve this. Return verbatim if already optimal.", input: cur });
}
return cur;
```

**GHCP equivalents.**
- A VS Code task in a `while` loop with a diff check; exits when `git diff --quiet`.
- Actions: a job with `for i in $(seq 1 6); do ... ; done`, breaking on no-op diff.
- The "iterate" pattern in Copilot Agent Mode — but bounded externally, not by the agent's own self-assessment (which would re-introduce Agentic Laziness).

**Lab 2 exercise.** "Loop-format a messy markdown doc until two consecutive runs produce identical output; cap at 5 iterations."

---

## Composition example: a serious code-review pipeline

A real-world code reviewer is rarely a single pattern. Here is the recommended composition we use in Lab 2's capstone:

```
PR diff
  │
  ├─► Fan-out ─┬─► bug-hunter agent
  │            ├─► performance agent      (3 parallel specialists)
  │            └─► security agent
  │                  │
  │                  ▼
  │            findings[]
  │                  │
  ▼                  ▼
Adversarial Verify (independent context tries to invalidate each finding —
                    drops hallucinated ones, demands repro for the rest)
                  │
                  ▼
Reduce (dedupe, rank by severity × confidence, emit a single review comment)
```

Each box is one of the six patterns above. The harness — whether you write it as a Claude Workflow `.js`, a `chatmode` graph, or a GH Actions DAG — is just the wiring between them. Lab 2 walks through implementing this exact pipeline three times: once as chatmodes, once as a workflow file, once as an MCP-backed orchestrator. The point is not to pick a winner, but to internalise that **the pattern is invariant, the substrate is not**.
