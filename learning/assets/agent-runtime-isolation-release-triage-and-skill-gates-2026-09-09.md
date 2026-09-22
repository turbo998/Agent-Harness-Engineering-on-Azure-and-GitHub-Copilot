<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Runtime Isolation / Release Triage / Skill Gates — SA 速查（2026-09-09）

> 适用场景：客户问“Agent runtime 如何防串租户/串会话？”、“MCP 工具怎么纳入 DR 演练？”、“Codex/Claude Code release 很快，哪些能写进 POC/Workshop？”、“如何把 skill/subagent 变成可验证资产？”
>
> 安全说明：本文中的命令形态字符串（如 `azmcp ...`、release tag、文件路径）均为上游 diff/docs 证据片段或检查项，不是生产执行指令。任何 POC 必须在临时订阅/临时 repo/无真实 secret 的 fixture 中验证。

## Evidence links（原研究快照中可复现）

| 证据 | URL | 原研究快照中状态 | 证据强度 | Caveat |
|---|---|---:|---|---|
| MAF OpenAI hosting 按 isolation key 隔离存储 | https://github.com/microsoft/agent-framework/commit/a903a4ee9e51d8ff892fb84e12a67f1e862ca69a | 200 | commit diff 级 | 未确认进入正式包；未运行 sample |
| MAF LocalCodeAct 子进程环境隔离 | https://github.com/microsoft/agent-framework/commit/a5800615317c9d482c2e2f8742f05cda0b39ef7e | 200 | commit diff 级 | diff 较小，未跑本地代码执行 fixture |
| MAF Python path normalization shared helper | https://github.com/microsoft/agent-framework/commit/44dc76ce818b779a2ccf4ed73e0be505ec1552c8 | 200 | commit diff 级 | breaking 影响需包级 smoke |
| MAF Python MCP Host payload metadata capture | https://github.com/microsoft/agent-framework/commit/25959b71c137c95262d63f64817d513dce6c250e | 200 | commit diff 级 | metadata retention budget 未实测 |
| MAF Python tool loop `max_duration_seconds` / `stop_reason` | https://github.com/microsoft/agent-framework/commit/0d3ea14fd04ce50e3ecc29b33a8cfb4180f5a9e4 | 200 | commit diff 级 | 未确认 release/未跑长工具 fixture |
| Azure MCP resilience drill run tools | https://github.com/microsoft/mcp/commit/f850b0708a64a3de73e1c1ee066e6ab63ec05eed | 200 | commit diff 级 | mutating DR 操作；必须测试订阅+审批+rollback |
| Codex `rust-v0.154.0-alpha.7` | https://github.com/openai/codex/releases/tag/rust-v0.154.0-alpha.7 | 200 | release page 级 | alpha；release body 仅 “Release 0.154.0-alpha.7”，不写用户功能断言 |
| Codex alpha.6→alpha.7 compare | https://github.com/openai/codex/compare/rust-v0.154.0-alpha.6...rust-v0.154.0-alpha.7 （API: https://api.github.com/repos/openai/codex/compare/rust-v0.154.0-alpha.6...rust-v0.154.0-alpha.7） | 200 | compare 页面/接口观察 | 58 commits / 300 files；原研究快照中只做主题 triage，未逐文件审计 |
| Claude Code Skills docs | https://code.claude.com/docs/en/skills | 200 | official docs 级 | 多项能力之前旧源复用；原研究快照中是 gates 重组，非新源 |
| Anthropic cwc-long-running-agents | https://github.com/anthropics/cwc-long-running-agents | 200 | official sample README 级 | Event demo；README 明示 not maintained / not turnkey harness |
| TrueForge | https://github.com/truefoundry/trueforge | 200 | community/厂商 README 级 | 社区项目参考；未审 installer/scripts/sandbox/network，不推荐直接接客户环境 |

---

## 1. Runtime isolation gate：状态标识不是授权令牌

**从 MAF commit `a903a4ee` 可抽出的客户话术：**
- `response_id` / `conversation_id` / session id 这类“恢复标识”只能用于 resume lookup，不能当 authorization token。
- 多用户 host 必须注册 isolation provider，例如按调用主体（claims / user / tenant / workspace）派生 isolation key。
- POC 验收时要证明：A 用户拿到 B 用户的 `response_id` / `conversation_id` 也不能 list/continue B 的会话。

**POC gate（最小验收）：**
1. 准备两个 synthetic user：`userA` / `userB`。
2. `userA` 创建 conversation/response，记录恢复标识。
3. `userB` 尝试 list/continue；期望结果：404/403/empty list，而不是恢复成功。
4. 记录 evidence：request identity、isolation key hash（不记录 PII）、result code、trace id。

**架构图组件：**
`Caller Identity → IsolationKeyProvider → Conversation/Response Index → Storage Backend`；在 `response_id` 旁标注“resume handle, not auth”。

---

## 2. File / memory / skill path gate：路径归一化是信任边界

MAF commit `44dc76ce` 把 Python 侧 session id、owner id、memory scope 等“用户可控但参与隔离边界”的值统一走 `_storage_key_segment`。这对 SA 很有用，因为客户常把“文件 memory / local skill source / todo file”当低风险功能，实际它们就是本地持久化控制面。

**POC gate：**
- 测试输入：正常 id、含 `../`、绝对路径、超长路径、符号链接目标、大小写变体。
- 期望：所有 caller-controlled state 值都映射到安全 segment；不会逃出配置 root；root 本身如是 symlink，应被明确列为部署风险。
- 对 skill source：configured root 是信任边界；不要让客户 repo 中的未知 `SKILL.md` 自动进入高权限环境。

**技术问答速答：**“Agent memory 是不是只是文件？”——不是。只要能跨 turn/跨 session 影响未来上下文，就必须按持久化输入面处理：路径隔离、权限、清理、注入检测、审计一起上。

---

## 3. MCP payload / metadata gate：保留证据，但要有 retention budget

MAF commit `25959b71` 新增 MCP Host payload metadata capture，且有 1 MiB 默认预算与超预算 omission warning。这给 POC 很好的 trace 设计：

**POC gate：**
- 对每个 MCP tool call，记录：public tool result、host payload metadata、size、omitted reason、trace id。
- 大输出必须测试：超过预算时要 fail-loud（warning/omitted marker），不能静默截断成看似完整答案。
- metadata 进入 security middleware 之前就要做 bounded capture，避免安全层看不到原始上下文。

**架构图组件：**
`MCP Tool → Host Payload Capture (size budget) → Security Middleware → Agent Context / Trace Store`。

---

## 4. Long tool-loop gate：预算包含 approval 等待时间

MAF commit `0d3ea14f` 增加 `max_duration_seconds` 与 `stop_reason`，并说明 wall-clock budget 会累计 tool execution 与 approval response 等待。

**POC gate：**
- 不只设 `max_iterations` / `max_function_calls`；还要设 wall-clock `max_duration_seconds`。
- approval 卡住、工具慢、网络重试都应消耗同一预算。
- 验收要看 `stop_reason`：timeout、approval pause、max calls、normal completion 分开统计。

**SA 落点：**无人值守 agent 的“绿灯”不能只看任务进程没崩；还要看是否因预算到顶、approval 等待、工具超时而提前结束。

---

## 5. Azure MCP resilience drill gate：DR 工具是 mutating tool，不是普通 read-only 查询

Azure MCP commit `f850b070` 增加 resilience drill run 的 add-notes / failover / resume / reprotect 命令与 docs。对客户价值很大，但风险也很高：它触碰演练/故障转移状态。

**客户 POC 最小红线：**
- 只接测试 service group / 测试 vault / 测试资源。
- failover / resume / reprotect 必须 human approval，审批记录包含 service group、drill、drill run、source/target location、selected resource ids。
- rollback/reprotect 计划必须在演练前写入 runbook。
- 任何自动化总结只可写“commit diff 级发现”，直到 schema/package/租户 smoke 完成。

**架构图组件：**
`Agent → Azure MCP Server → Resilience Drill Run API → Approval/Audit Log → Recovery/Reprotect Runbook`。

---

## 6. Codex release diff triage：alpha release 先分风险域，别直接写功能发布

原研究快照中核实 `rust-v0.154.0-alpha.7` 页面 200，但 release body 只有模板句；compare API 显示 `ahead_by=58`、约 300 files。正确做法：把它当 **release sentinel + risk-domain triage**，而不是客户可用功能。

**原研究快照中从 commit titles / file paths 抽到的风险域：**
- User verification / MCP：`Restrict MCP user verification and add workspace-scoped identity`。
- Guardian context：permission context、trusted tool metadata、trusted skill evidence、review evidence 迁入 shared registry。
- App-server daemon lifecycle：managed daemon start/update、PID/executable identity、shutdown grace period。
- Memory v2 / status：新增 protocol/request processors/tests。
- Hook/process safety：hook detach、network proxy teardown、MCP stderr reader close 等资源清理信号。

**release triage gate：**
1. `release page body` 有无用户可见变更？无 → 不写功能断言。
2. `compare` 分 risk domains：identity / permission / sandbox / memory / app-server / MCP / UI。
3. 只选 1-2 条读 diff 到源码级，再形成有证据支撑的技术结论。
4. alpha → stable 前，客户材料只写“观察到即将进入的 runtime safety changes”，不写“已可用”。

---

## 7. Skill/subagent verification gate：Skill 是可验证资产，不是 Markdown 收藏

Claude Code skills docs 与 `anthropics/cwc-long-running-agents` 合起来给了一个可复用模式：

- **Default-FAIL contract**：验收项默认 false；没有新鲜证据不能置 true。
- **Fresh-context evaluator**：独立评审 agent 没有 Write/Edit 工具，且未见过 build 上下文。
- **Agent-maintained handoff**：长任务由 agent 写 progress/handoff，避免压缩后丢事实。
- **Skills docs 侧能力点**：`/run`、`/verify`、`/run-skill-generator`、`/skill-doctor`、`allowed-tools`/`disallowed-tools`、`context: fork`、`background`、`skillOverrides`、dynamic context injection。

**给 SA 自己的 skill 质量 gate：**
- description 要路由清晰：什么时候用、输入是什么、产出是什么。
- SKILL.md 本体短；长背景放 references；验证脚本放 scripts；模板放 templates。
- 每个 skill 至少写“如何验证它真的被正确使用”。
- 若 skill 会触碰外部系统，必须有 no-real-secret / toy fixture / approval / rollback 段。

---

## 8. TrueForge radar：社区项目参考，未审不推荐安装

TrueForge README 自述其 runtime 覆盖 model calls、MCP tools、skills、sandboxing、approvals、context management、session state，并提供 Chat UI、HTTP API、TypeScript SDK。它对 SA 的价值不是“马上推荐客户用”，而是作为一张现代 agent harness 参考架构：

`Chat UI / SDK / HTTP API → Agent Loop → Models + MCP Tools + Git-backed Skills + Sandbox-as-tool + Approvals → SQLite/Postgres state`

**进入推荐前必须补的安全审计：**
- installer/scripts/package manager 行为；
- sandbox provider（README 提到 Daytona today）隔离边界；
- MCP remote auth/OAuth token 存储；
- skills git source 的 trust boundary；
- session state schema、日志脱敏、usage/telemetry；
- license/dependency/SBOM。

---

## 9. 一页架构图骨架（可转 SVG/Draw.io）

```text
[User / Repo / Ticket]
        │ identity + policy
        ▼
[Agent Control Plane]
  ├─ Release Radar: stable / alpha / docs / commit / radar
  ├─ Skill Router: description → allowed tools → dynamic context
  ├─ Approval Gate: mutating tools / DR operations / code exec
  └─ Fresh Reviewer: no-write, evidence-only
        │
        ▼
[Runtime Isolation Plane]
  ├─ IsolationKeyProvider (user/tenant/workspace)
  ├─ Conversation/Response Store (resume handle ≠ auth)
  ├─ File/Memory/Skill Root Guard
  └─ Tool Loop Budget + stop_reason
        │
        ▼
[Tool/Data Plane]
  ├─ MCP Host Payload Capture (size budget)
  ├─ Azure MCP Resilience Drill APIs
  ├─ LocalCodeAct / Sandbox-as-tool
  └─ External Docs/README as untrusted data
        │
        ▼
[Evidence Store]
  ├─ trace id / request identity / omitted markers
  ├─ release diff evidence / raw docs links
  └─ POC scorecard + rollback notes
```

---

## 10. 可直接复制到方案/Workshop 的验收清单

- [ ] 每个状态恢复 handle 都证明“不是授权令牌”。
- [ ] 每个文件/memory/skill root 都声明信任边界和路径归一化策略。
- [ ] 每个 MCP tool result 都有 output budget / metadata capture / omitted marker。
- [ ] 每个长工具循环都有 max calls + max iterations + wall-clock duration + stop_reason。
- [ ] 每个 mutating tool（尤其 Azure DR drill）都有 human approval、audit、rollback。
- [ ] 每个 alpha/changelog 信号先做 release triage，不把 tag motion 写成功能发布。
- [ ] 每个 skill/subagent 有 default-fail 验收项与 fresh-context reviewer。
- [ ] 每个社区 runtime 仓库先做 license/scripts/network/secret/sandbox 审计，再考虑 POC。
