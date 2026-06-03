# 六种编排模式（Six Orchestration Patterns）

> 来源 / Source：Anthropic 官方博客《A harness for every task — Dynamic Workflows in Claude Code》——https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code
> 中文解读：https://mp.weixin.qq.com/s/hxBkT-iJleQkaODzjWVC2A

一旦你接受了"单 Agent 单 context window 有[三大结构性顽疾](./three-pitfalls-of-agentic-harness.md)"这一前提，下一个问题就是：**究竟什么形状的多 Agent 编排能真正修掉它们？** Anthropic 在 Opus 4.8 发布日的 blog 中总结了 6 种反复出现的模式。本文给每种模式一段定义、一段 Claude-Workflow 风格的伪 JS 写法、对应到 GitHub Copilot 生态的等价实现路径（custom chatmodes / `@workspace` agents / MCP / VS Code tasks / GH Actions matrix），并在末尾给出 Lab 2 可直接使用的练习题。最后给一张组合示例，把六种模式拼成一个真正能用的 code review 流水线。

## 1. Classify-Route（分类路由）

**定义。** 一个轻量级 classifier Agent 读输入，判断该走哪条下游专家路径，把请求路由过去。Classifier 便宜、无状态；下游专家昂贵、领域强相关。

**Claude Workflow 写法。**

```js
const kind = await agent({ system: "Classify into {bug, feature, doc, infra}", input });
const handler = { bug: bugAgent, feature: featAgent, doc: docAgent, infra: infraAgent }[kind];
return await handler(input);
```

**GHCP 等价实现。**
- 一个 **custom chatmode**（`triage.chatmode.md`）只做一件事：输出标签；外加 4 个专家 chatmode，让用户/上游切换过去。
- **GitHub Actions** workflow 用 `jobs.<id>.if:` 守卫 classifier 输出的 JSON（`actions/github-script` 调 Copilot）。
- **MCP router 服务**：暴露一个 `route(intent)` 工具，内部按 intent 分发到不同的工具子集。

**Lab 2 练习。** "写一个 triage chatmode：读取新 issue → 输出分类标签 → 以 sticky comment 写回 issue；每个标签关联一个 `.prompt.md`。"

## 2. Fan-out-Reduce（扇出汇总）

**定义。** 把任务拆成 N 个独立子任务并行跑，最后用一个 reducer Agent 合并。经典的 map-reduce，只是 mapper 是 LLM，reducer 也是 LLM（有时是确定性代码）。

**Claude Workflow 写法。**

```js
const chunks = splitFiles(repo, 20);
const findings = await parallel(chunks.map(c => agent({ system: "Find dead code", input: c })));
return await agent({ system: "Merge, dedupe, rank by risk", input: findings });
```

**GHCP 等价实现。**
- **GH Actions matrix**：`strategy.matrix.shard: [0..N]`，每个 shard 跑同一段 Copilot prompt 处理自己那片，最后一个 job 跑 reducer。
- **VS Code tasks** 加 `dependsOn` 做本地 fan-out，最后一个聚合 task。
- **MCP 服务**暴露 `fanout(task, partitions)`，内部并发 N 次模型调用并拼接。

**Lab 2 练习。** "用 4-way matrix 在 monorepo 上做 dead-code 扫描，reducer 排出前 10 名候选并开一个 PR。"

## 3. Adversarial Verify（对抗式验证）

**定义。** Generator Agent 产出工件之后，由一个**独立 context、明确带有对抗性 system prompt 的 verifier**去尝试把它打穿。Verifier 的成功标准只有一个：**找到一个真问题**。verifier 选择放行时循环才结束。

**Claude Workflow 写法。**

```js
let patch = await agent({ system: "Implement feature X", input: spec });
for (let i = 0; i < 3; i++) {
  const attack = await agent({ system: "你是敌意 reviewer，找出一个真 bug 否则放行。", input: patch });
  if (attack.kind === "approve") break;
  patch = await agent({ system: "Fix the issue raised", input: { patch, attack } });
}
```

**GHCP 等价实现。**
- 两个 chatmode：`implementer.chatmode.md` 和 `red-team-reviewer.chatmode.md`。用户必须**新开一个 chat** 运行 reviewer——**context 隔离正是这个模式的全部意义**。
- CI 中：一个 `implement` job 把 diff 落到 artifact，**另一个**干净 runner 上的 `review` job 来读它并发 blocking review comments。Reviewer **绝不能**继承 implementer 的 prompt。
- MCP：一个 `verify(diff)` 工具，背后挂的 Agent 用不同的 temperature 和写死的敌意 system prompt。

**Lab 2 练习。** "写一个 Action：implement → review → patch 循环最多 3 次；第 3 轮仍有 blocking comments 就让 PR 失败。"

## 4. Generate-Filter（生成-过滤）

**定义。** 生成 K 个候选输出（高 temperature、不同 prompt 或不同模型），然后过滤出最好的——**优先用确定性过滤**（编译、测试、lint），再考虑 LLM 评判，因为确定性过滤是免费而且不会出错的。

**Claude Workflow 写法。**

```js
const candidates = await parallel(Array.from({length: 8}, (_,i) =>
  agent({ system: "Implement X. Variant " + i, input: spec, temperature: 0.9 })));
const compiling = candidates.filter(c => tryBuild(c).ok);
const passing  = compiling.filter(c => runTests(c).pass);
return await agent({ system: "Pick the cleanest impl", input: passing });
```

**GHCP 等价实现。**
- **Actions matrix** 配 `seed: [1..8]` 注入 prompt，后接确定性 `build && test` 闸门，再接一个 reducer job。
- 本地：一个 VS Code task 循环调 Copilot，用 N 份不同 `.prompt.md`，每轮跑一次 `npm test`。

**Lab 2 练习。** "对一个小工具函数生成 5 份候选实现，砍掉单测不过的，让 judge agent 选幸存者。"

## 5. Tournament（锦标赛：1v1 pairwise vs 绝对打分）

**定义。** 当你有很多候选、没有 ground truth 时，让 judge 直接打绝对分（0–10）噪声极大。**成对比较**（"A 和 B 哪个更好"）准确率明显更高，代价是 O(N²) 或者 O(N log N) 次比较组成赛程。

**Claude Workflow 写法。**

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

**取舍。** Pairwise 更准但是 quadratic；绝对打分线性但偏向冗长输出。候选数 > 16 时建议用瑞士轮或单淘汰赛。

**GHCP 等价实现。**
- Actions：一个 `tournament.yml`，用递归 `workflow_call` 接收 artifact ID 列表，吐出 winner。
- MCP：一个 `compare(a, b)` 工具，由编排器循环调用。

**Lab 2 练习。** "对同一次 commit 给定 8 份 PR description，跑单淘汰赛，把胜者写入 changelog。"

## 6. Loop-Until-Stable（不动点循环）

**定义。** 在 Agent 自己的输出上反复跑，直到输出不再变化（或者预算耗尽）。适合迭代式打磨：格式化、refactor pass、文档润色、schema 迁移。

**Claude Workflow 写法。**

```js
let prev = null, cur = input;
for (let i = 0; i < 6 && prev !== cur; i++) {
  prev = cur;
  cur = await agent({ system: "Improve this. Return verbatim if already optimal.", input: cur });
}
return cur;
```

**GHCP 等价实现。**
- 一个 VS Code task 包在 `while` 循环里 + 一次 diff 检查；`git diff --quiet` 时退出。
- Actions：`for i in $(seq 1 6); do ...; done`，no-op diff 时 break。
- 也是 Copilot Agent Mode 中的 "iterate" 模式，**但终止条件必须外部判定**，不能交给 Agent 自我评估（否则又把 Agentic Laziness 引回来了）。

**Lab 2 练习。** "对一份乱糟糟的 markdown 跑 Loop-format，直到两轮输出完全一致；最多 5 轮。"

---

## 组合示例：一条像样的 code review 流水线

真实世界的 code review 极少是单一模式。下面是 Lab 2 capstone 中我们推荐的组合：

```
PR diff
  │
  ├─► Fan-out ─┬─► bug-hunter agent
  │            ├─► performance agent      （3 个并行专家）
  │            └─► security agent
  │                  │
  │                  ▼
  │            findings[]
  │                  │
  ▼                  ▼
Adversarial Verify（独立 context 尝试推翻每条 finding——
                    幻觉的丢掉，其余的要求给出复现步骤）
                  │
                  ▼
Reduce（去重、按 severity × confidence 排序、合成一条 review comment）
```

每个方框都是上面六种模式之一。Harness——不管你写成 Claude Workflow `.js`、一组 chatmode 图、还是 GH Actions DAG——只是把它们连起来的接线。Lab 2 会把这条完全相同的流水线落地**三次**：一次用 chatmodes，一次用 workflow 文件，一次用 MCP 编排器。目的不是评出谁最好，而是让学员内化一件事：**模式是不变的，承载它的基质（substrate）才是可选的**。
