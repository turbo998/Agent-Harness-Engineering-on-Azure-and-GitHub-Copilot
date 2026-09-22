<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Planfile / Source Freshness / Hosted Workflow Gates（2026-09-08）

> 用途：给 SA 在技术问答、POC 部署和架构图设计时复用。本文是证据驱动的检查表，不是安装或执行外部项目的指令。所有命令形态片段均为上游证据摘录或概念名，任何客户环境执行前必须在隔离 fixture/测试租户中验证。
>
> 证据级别：URL/PR/diff/docs 均为 2026-09-08 原快照中核实；未运行 CLI、未安装包、未连 Azure/Foundry/GitHub 企业租户，因此运行时可用性、配额、策略生效范围均不得对客户承诺。

## 1. Evidence links（可复现证据）

| 来源 | URL | 原快照中证据强度 | 关键命中 |
|---|---|---|---|
| MAF PR #8020 | https://github.com/microsoft/agent-framework/pull/8020.diff | diff 200 | `AddAsAIAgent(includeWorkflowOutputsInResponse: true)`；Hosted workflow response 输出回传开关 |
| MAF PR #8082 | https://github.com/microsoft/agent-framework/pull/8082.diff | diff 200 | Hosted-Workflow-Resilient-Long-Running；operation ID / scope 复用以避免恢复时重复副作用 |
| VS Code 1.136 | https://code.visualstudio.com/updates/v1_136 | docs 200 | Agent Merge Preview、multi-root agent sessions、Agent Host Protocol、Copilot SDK |
| GitHub Copilot policy/billing 预告 | https://github.blog/changelog/2026-08-28-upcoming-changes-to-github-copilot-policies-and-billing/ | changelog 200 | cloud agent / github.com Chat / Mobile Chat 收敛；Sandbox；数据保留从 28 天变为账号生命周期（按公告） |
| google-research/envharness | https://raw.githubusercontent.com/google-research/envharness/main/README.md | raw README 200 | static worlds → interactive environments；保留 trusted human-built verifiers |
| Claude Code Skills docs | https://code.claude.com/docs/en/skills | docs 200（BrightData抽正文） | `context: fork`、`disable-model-invocation`、`/skill-doctor`、`/run`/`/verify`/`/run-skill-generator` |
| Codex Best Practices | https://learn.chatgpt.com/guides/best-practices | docs 200（解析到 canonical 内容） | Goal / Context / Constraints / Done when；AGENTS.md；MCP；skills；scheduled tasks |
| Codex ExecPlans | https://cookbook.openai.com/articles/codex_exec_plans | 301→developers.openai.com 200 | `PLANS.md` / ExecPlan；Progress、Decision Log、Retrospective；“goal, work, result, proof” |
| Anthropic long-running harness | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | engineering blog 200 | initializer agent、coding agent、`init.sh`、`claude-progress.txt`、`feature_list.json` |
| Codex alpha sentinel | https://github.com/openai/codex/releases/tag/rust-v0.154.0-alpha.6 | release page 200 + npm registry | npm `latest=0.153.4`、`alpha=0.154.0-alpha.6`；release body 无 user-facing 内容 |

## 2. Release-source freshness gate（避免把“版本跳动”讲成“能力发布”）[→harness]

**问题**：Codex / Claude Code / agent CLI 生态 release 很快，alpha tag、npm dist-tag、docs changelog 三者经常不同步。客户问“现在能不能用某功能”时，不能只看一个版本号。

### 三路证据矩阵

| 检查点 | 可说明什么 | 不能说明什么 | POC 前最低验收 |
|---|---|---|---|
| npm / package registry `latest` | 客户默认安装线的大致版本 | alpha channel 是否生产可用 | 记录 `latest`、`modified`、目标平台包是否存在 |
| GitHub release / tag body | 是否有发布说明或仅空壳版本页 | 功能是否已进官方 docs / 默认启用 | release body 必须有明确 user-facing 条目才可写入“新增功能” |
| 官方 docs/changelog | 对外承诺口径 | preview/alpha 的底层实验变更 | 客户材料优先引用 docs/changelog；docs 缺失则标“release-level only” |
| 本地 smoke / 测试租户 | 目标环境是否真的可用 | GA/合规/配额普遍结论 | 用 disposable repo/tenant 验证，不触碰客户真实 secret |

**原快照中示例**：`@openai/codex` npm `latest` 仍为 `0.153.4`，`alpha` 为 `0.154.0-alpha.6`；GitHub release `rust-v0.154.0-alpha.6` 可达但 body 仅空壳版本页。因此：只记 release sentinel，不写功能更新。

## 3. Planfile continuity gate（长任务 Agent 不靠“记忆”，靠文件协议）[→harness]

把 OpenAI ExecPlans 与 Anthropic long-running harness 合并成一个跨厂商模板：

```text
repo/
  AGENTS.md or CLAUDE.md        # 短：指向方法、约束、何时用 plan
  PLANS.md                      # 长任务 plan 文件规范
  feature_list.json             # 机器可读 feature backlog / 状态
  claude-progress.txt or progress.md
  decisions.md                  # 决策记录，禁止只藏在对话里
  init.sh                       # 可复现启动/验证环境（客户环境需改为安全脚本）
```

### POC 检查表

1. **开工前**：读取 `AGENTS.md/CLAUDE.md` + 当前 plan/progress + 最近提交摘要；具体命令由客户授权环境的 runbook 提供，不在本文中作为执行指令下发。
2. **计划文件**：每个 milestone 写清 `goal / work / result / proof`；proof 必须是可运行验证或可检查状态，不是“我认为完成”。
3. **每轮收尾**：提交或明确不提交；更新 progress；记录未完成项；清理临时 server/process；把失败验证写入 plan。
4. **跨会话恢复**：新 agent 只凭 repo 文件即可接班；如果必须依赖聊天历史，说明 planfile 不合格。
5. **安全边界**：`init.sh`/验证脚本不能默认读取真实 `.env`、生产 token、客户数据库；演示用 fixture。

### SA 落点

- **技术问答**：回答“为什么 agent 做长任务容易断？”→ 因为 context 会断，解决方式是 repo-level plan/progress/decision 文件，而不是更长 prompt。
- **POC 部署**：把 POC 从“一次性演示”变为“可交接的工程状态机”；下一轮 agent/工程师能接着跑。
- **架构图**：画“Agent Session → Repo Plan State → Validator/E2E → Git Checkpoint”的闭环，而不是只画 LLM + tools。

## 4. Claude Skills / Subagent authoring gate（从大 CLAUDE.md 转为按需加载）[→harness]

| 机制 | 适合放什么 | 风险 | Gate |
|---|---|---|---|
| `CLAUDE.md` / `AGENTS.md` | 稳定导航、仓库约束、何时读哪个文件 | 过长导致每轮上下文污染 | 150 行/500 token 级别为目标；只放索引与硬约束 |
| Skill (`SKILL.md`) | 可复用流程、检查表、模板、验证脚本入口 | 描述触发不准；工具权限过宽 | description 写触发条件；必要时加 `disable-model-invocation`；附属文件按需读 |
| `context: fork` skill | 部署、研究、验证这类希望隔离上下文的技能 | 子代理可能拿到过宽工具或误读外部内容 | 明确允许工具、输入输出、停止条件；结果回主会话再合并 |
| Subagent | 读重/并行/审查/triage/测试 | 写入共享文件冲突；子代理自陈不可信 | 子代理只返回结构化摘要；父代理核实关键 URL/文件；独立评审另起 |
| `/run` / `/verify` | 从“测试通过”扩展到“应用真的跑起来” | 启动推断可能错 | 复杂项目用 `/run-skill-generator` 或自定义验证脚本固化启动步骤 |
| `/skill-doctor` | 清理未使用或过重 skills | 只看报告不改 | 每次 workshop/POC 后把无用 skill 禁用或合并 |

## 5. Hosted workflow response / resiliency gate（MAF / Foundry Hosted Agent POC）

原快照中新 PR 信号（commit-level，不代表已发布包）：

- PR #8020：Hosted workflow 可通过 `includeWorkflowOutputsInResponse: true` 把 workflow outputs 纳入 hosted agent response。
- PR #8082：Resilient long-running sample 强调 operation ID / scope 复用，恢复时返回已存结果，避免服务调用重复产生副作用。

### POC 问答模板

客户问：“Hosted Agent workflow 执行完，调用方怎么拿到子步骤输出？”

建议答法：
> MAF 主线已经出现 workflow outputs in hosted responses 的 PR 级信号，说明产品正在把 workflow 结果回传做成显式 response 面。但这还是 commit/PR-level 信号，未确认进入你要用的正式包。POC 里应先固定 SDK 版本，写一个 hosted sequential workflow，验证 response payload 是否包含目标 output，再决定是否把它作为业务契约。

客户问：“长任务失败恢复会不会重复扣款/重复发邮件/重复写数据库？”

建议答法：
> 不能只靠 prompt 保证。要把每个有副作用的服务调用设计为 idempotent operation：用 scope + operation ID 复用，恢复时能返回 stored result 而不是重新执行。MAF resilient LRA sample 的最新 PR 正好把这个模式写进样例，适合做客户 POC 验收项。

### 架构图组件

```text
Client / Channel
   ↓ request
Foundry Hosted Agent / MAF Host
   ↓ invokes
Workflow Runtime ── checkpoint ── Durable Store
   ↓ calls with scope + operationId
Idempotent Service Adapter ── stored result ── Business System
   ↓ outputs
Hosted Agent Response (workflow outputs when supported/verified)
```

## 6. Interactive environment eval gate（EnvHarness 作为评测架构素材）

`google-research/envharness` 的价值不在“直接拿来跑客户 POC”，而在评测思想：把静态 benchmark 改造成可交互环境，同时保留原有人类构造的 verifier。

### 可迁移到 SA 的做法

- **技术问答**：评测 agent 不只看最终文本答案，要看 agent 在环境中的动作路径、失败恢复和约束遵守。
- **POC 部署**：对每个客户场景定义“初始环境 + 可用动作 + 成功谓词”，而不是只写 prompt + 预期答案。
- **架构图**：把 Evaluation Environment / Verifier / Agent Actions 画成闭环，区别于离线 QA benchmark。

### 最小 POC 评测模板

| 字段 | 示例 |
|---|---|
| 初始状态 | 一个含 issue、失败测试、mock API 的 repo fixture |
| 动作空间 | edit file、run tests、query logs、open browser（均在沙箱） |
| 成功谓词 | 指定测试通过 + UI smoke 通过 + 无 secret 读取 |
| 反作弊 | verifier 不暴露给 agent；日志中检查是否越权读取 |
| 输出 | trace + score + failure class + 可复现 command |

## 7. VS Code / Copilot client-agent gate（客户桌面与云 Agent 统一治理）

原快照中证据：VS Code 1.136 提到 Agent Merge Preview、multi-root agent sessions、Agent Host Protocol、Copilot SDK；GitHub Copilot 08-28 changelog 预告 cloud agent、github.com Chat、Mobile Chat 收敛，cloud agent leverages Sandbox，chat data retention 口径变化。

### 客户前置问题

1. 目标是 **本地 IDE agent**、**GitHub cloud agent** 还是 **移动/网页 chat**？策略面即将收敛，但验证路径不同。
2. 是否启用 content exclusions / org policy？这些是治理配置，不是 prompt 能替代。
3. 数据保留、审计、sandbox、网络出站是否满足客户合规？公告不能替代租户实测。
4. Agent Merge 是否只用于低风险 PR，还是会自动处理安全/合规敏感变更？后者需要 required review gate。

## 8. Tonight’s direct workshop cards

- [→harness] **练习1：Release sentinel classifier**：给学员 3 个信号（npm alpha、GitHub release body 空、docs changelog旧），要求分类为“版本信号，不是功能发布”。
- [→harness] **练习2：Planfile handoff**：给一个无 plan 的半成品 repo，要求补 `PLANS.md` + progress + proof，并让第二个 agent 接班。
- [→harness] **练习3：Hosted workflow idempotency**：在 diagram 中标出哪条调用必须带 operation ID，以及恢复时如何避免二次副作用。
- [→harness] **练习4：Skill vs subagent**：把一个 300 行 CLAUDE.md 拆成索引 + 2 个 skills + 1 个审查 subagent brief。

## 9. Fail-loud caveats

- Codex `0.154.0-alpha.6` 只核为 alpha release + npm dist-tag；未发现 user-facing release body，不得写“新增能力”。
- Claude Code 原快照中核实 npm latest 仍为 `2.1.263`，09-07之后无新 user-facing 版本；skills/subagents docs 属旧源新角度提炼。
- MAF PR #8020/#8082 为 PR/diff 级信号；未确认进入正式 release，也未运行 .NET sample。
- EnvHarness 仅 README/论文方向核实；未运行 benchmark，不能引用性能结论。
- Codex ExecPlans、Anthropic long-running harness、Claude Code skills docs 均为旧源复用/新角度；本资产仅做跨厂商 planfile/skill/harness gate 合并，不把它们记为新发现。
- wshobson/agents、awesome 类社区资源仅作为 radar；本资产未直接采用其脚本/安装命令。
