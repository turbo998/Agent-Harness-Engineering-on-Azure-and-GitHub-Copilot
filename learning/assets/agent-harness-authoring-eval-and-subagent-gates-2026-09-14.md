<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Harness Authoring / Eval / Subagent Gates — SA 可复用速查（2026-09-14）

> 用途：把 2026-09-14 快照核实的 Microsoft / OpenAI / Anthropic / Google ADK 更新，转成 SA 日常可复用资产：技术问答速答、POC 验收门、架构图组件、workshop 练习卡。
> 安全说明：本文中的命令形态或文件名均为上游文档/示例中的**证据片段与设计约定**，不是直接执行指令；任何客户 POC 必须在一次性 fixture、无真实 secret、无客户代码的隔离环境中验证。

## 1. Evidence links（原快照中核实）

| 来源 | URL | 证据强度 | 原快照中可复现点 | caveat |
|---|---|---|---|---|
| MicrosoftDocs Azure AI Docs commit `83c7cb1` | https://github.com/MicrosoftDocs/azure-ai-docs/commit/83c7cb152d2b4fc9008966da1e80aa7fda08412e | commit/diff 200 | diff 命中 Agent Skills、MCP `skill-md` / archive、`static_headers` / `header_provider`、Redis scoped history/legacy 迁移相关文档变更 | 文档发布级；未运行 MAF/Redis/MCP sample |
| Microsoft Foundry July/Aug roundup | https://devblogs.microsoft.com/foundry/whats-new-in-microsoft-foundry-july-august-2026/ | official blog 200 | meta/body 命中 Hosted Agents、Voice Live、Toolboxes、Claude on Azure structured outputs / Web / MCP connector / Tool search、Model Router | roundup 级；区域/预览/租户可用性未逐项核实 |
| Google ADK Python `v2.9.0` | https://github.com/google/adk-python/releases/tag/v2.9.0 | release HTML 200 | body/meta 命中 automatic model failover、LiveKit native voice、MCP SDK 2.x compatibility | 未安装 ADK；未跑 failover/voice/MCP smoke |
| OpenAI Agents Python `v0.22.2` | https://github.com/openai/openai-agents-python/releases/tag/v0.22.2 | release HTML 200 | body/meta 命中 image generation tool options、UnixLocal file API symlink race fix、session compaction fix | GitHub API 原快照中部分 rate-limited；以 release HTML 为可复现证据；未跑 SDK |
| Claude Code changelog | https://code.claude.com/docs/en/changelog | official docs 200 | 命中 `2.1.270`、`2.1.269`、`claude plugin eval` | 2.1.270 是 2.1.269 之后的权限回归修复，不扩大为新能力 |
| Claude Code skills docs | https://code.claude.com/docs/en/skills | official docs 200 | 命中 `context: fork`、`/skill-doctor`、`allowed-tools` | 旧源复用；原研究快照中不当作新发现，仅按 skill 设计审计/worker template/POC gate 重组；未运行 Claude Code |
| Claude Code subagents docs | https://code.claude.com/docs/en/sub-agents | official docs 200 | 命中 `isolation: worktree`、`permissionMode`、`mcpServers`、`maxTurns`、`skills` | 旧源复用；原研究快照中按 worker frontmatter/隔离 gate 资产化重组；未运行，字段语义以页面为准 |
| Anthropic long-running agents harness blog | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | official engineering blog 200 | 页面 200；关键词命中 initializer / progress file / feature list；“handoff/交接”是原研究快照中从长跑 agent 流程抽象出的模式，不作为页面原词引用 | 旧源复用；本资产按“旧源新角度/资产化”处理 |
| Codex subagents docs | https://learn.chatgpt.com/docs/agent-configuration/subagents | official docs 200 | 命中 `/agent`、parallel subagents、context pollution/rot | 旧源复用；原研究快照中按上下文污染/worker分工 gate 重组；不同 host 的子代理行为需分别验证 |
| Codex AGENTS.md docs | https://learn.chatgpt.com/docs/agent-configuration/agents-md | official docs 200 | 命中 `AGENTS.override.md`、`CODEX_HOME`、nested directories / cap wording | 旧源复用；本资产为指令链排错 gate 重组，不当新发现 |
| OpenAI Cookbook Codex development workflows | https://github.com/openai/openai-cookbook/blob/main/examples/codex/iterating-development-workflows-with-codex.md | GitHub blob page 200；raw 另行读取 | raw 命中 `AGENTS.md`、`GOALS.md`、`PLANS.md`、`PROMPTS.md`、harness 文件体系与 skills 自动化段落 | 旧源复用；原研究快照中按 source-of-truth / harness authoring gate 重组；未运行示例 |
| OpenAI Cookbook iterative repair loops | https://github.com/openai/openai-cookbook/blob/main/examples/codex/Build_iterative_repair_loops_with_Codex.ipynb | GitHub blob page 200 | 命中 Review / Repair / Validate、`record.json`、iteration outputs | 旧源复用；原研究快照中按 closed-loop repair/eval gate 重组；notebook 未运行，不引用性能 |
| `openai/skills` | https://github.com/openai/skills | repo/raw README 200 | README 指向 Codex plugin/skill-only plugin 构建路径 | 仅 radar/结构参考；未做全仓库 harvest，不安装 |

## 2. 技术问答速答（可转发给客户前需按租户再核实）

1. **“为什么 agent skill/plugin 上线不能只看写没写？”**
   因为 skill/plugin 的真实价值在“是否自然触发、是否提升结果、是否可回归测试”。Claude `plugin eval` 提供 with/without baseline、graders、JSON/HTML report 与 CI exit code 这类官方可评测路径；客户 POC 应把 skill 当成可测试资产，而不是 prompt 附件。

2. **“Codex/Claude 的 subagent 应该什么时候用？”**
   适合把 noisy/read-heavy 的探索、日志分析、测试验证、代码审查分离到独立上下文，避免主会话 context pollution/rot。写密集型并行要谨慎：必须隔离 worktree/输出目录、限制工具与权限、最后由父流程统一合并。

3. **“AGENTS.md / skills / subagents 的配置排错看什么？”**
   先查真实生效链：global override、项目层级、nested override、体积 cap、allowed/disallowed tools、permission mode、是否通过 `/skill-doctor` 或 eval 证明触发。不要只看最后一次回答推断配置生效。

4. **“多云/多框架 agent POC 的韧性怎么讲？”**
   Google ADK `v2.9.0` 的 automatic model failover、OpenAI Agents Python 的 session compaction / sandbox symlink race fix、Microsoft Foundry Hosted Agents / Toolboxes / Model Router 都说明：韧性要从 model fallback、session/history、sandbox FS、安全边界、工具外置治理五层画出来。

5. **“Microsoft Agent Framework 的 MCP/Redis 文档更新有什么实际意义？”**
   文档发布显示 Agent Skills 可通过 MCP skill index / archive 形式发现，local MCP 可配置 static headers/header provider，Redis history 有 scoped keys / legacy 迁移语义。这些不是“功能已在客户包验证”的承诺，但足够提醒 POC 设计时把 skill 分发、MCP header、会话隔离/迁移列成验收项。

## 3. POC 验收门（gates）

> 以下 gate 是设计与验收要求，不是照抄上游 README 命令；客户 POC 前必须用隔离 fixture 自行实现并验证。


### Gate A — Skill / plugin eval gate [→harness]
- 建最小无 secret fixture：一个微型 skill/plugin + 3-5 个真实 prompt。
- 跑 with-plugin 与 no-plugin baseline；报告必须包含：触发证据、结果质量 grader、成本/耗时、失败样例。
- 上线门槛：baseline Δ 明显、失败原因可解释、报告可归档到 CI 或 PR 注释。
- Fail-loud：若只看到“工具被调用”但无结果提升，不得写“skill 已改善质量”。

### Gate B — Subagent isolation gate [→harness]
- 子任务分类：read-only explorer / validator / reviewer / writer。
- 每类明确工具、权限、max turns、是否可后台、是否可用 MCP、是否隔离 worktree。
- 写入型 subagent 必须独立输出目录或 worktree；父流程统一 merge。
- Fail-loud：并行成功 ≠ 正确合并；要记录冲突、未采纳输出、人工决策点。

### Gate C — Instruction / context source-of-truth gate [→harness]
- 列出指令链：global / repo root / nested / override / runtime prompt / dynamic external message。
- 对每条指令记录来源、优先级、体积、最后更新时间、是否会被覆盖。
- 事件流记录 attach time / include_turns / partial stream caveat。
- Fail-loud：最终回答不是完整审计事实；需要可复现的 source metadata。

### Gate D — Agent runtime resilience gate [→harness]
- Model failover：定义 primary / backup / retry / degradation message。
- Session/history：记录 compaction、Redis/history key scope、legacy migration。
- Sandbox FS：禁止 symlink escape；输入/政策 read-only，输出 write-only；清理策略明确。
- Tools/MCP：headers/identity/RBAC/approval/audit/rollback 分层。

### Gate E — Closed-loop repair gate [→harness]
- 工作流分 Review → Repair → Validate。
- 每轮写结构化 finding、patch summary、validation delta、`record.json`。
- 停止条件：全部通过、达到最大轮次、delta 无改善、需人工裁决。
- Fail-loud：不要用“agent 改了文件”代替“验证指标收敛”。

## 4. 架构图组件库（文字版，可转 Mermaid / SVG）

1. **Skill Eval Runner**
   `Prompt set` → 分叉：`no-plugin baseline` / `with-plugin` → `graders(regex/tool_used/file_exists/LLM rubric)` → `JSON/HTML report` → `CI threshold` → `skill description/tools 修正`。

2. **Subagent Control Plane**
   `Parent planner` → `read-only explorer` / `validator` / `reviewer` / `writer(worktree)` → `artifact summaries` → `merge & human approval`；旁路：`tools allowlist`、`permissionMode`、`MCP server scope`、`hooks/backstops`。

3. **Instruction Chain & Event History**
   `Global config` → `Repo AGENTS.md` → `Nested AGENTS.md` → `Override` → `Runtime prompt` → `External messages / late handles`；旁路标注：`cap`、`source metadata`、`partial event stream`。

4. **Agent Runtime Resilience Stack**
   `User request` → `Agent runtime` → `Model router/failover` + `session/history store` + `sandbox FS` + `MCP/toolbox` → `observability/evals` → `human approval / rollback`。

## 5. Workshop 练习卡

- [→harness] **练习 1：plugin eval 红绿循环**：先写模糊 skill description，运行 eval 失败；改 description / tool scope；比较 baseline Δ。
- [→harness] **练习 2：三 worker PR review**：security / testing / maintainability 三个 subagent 分别输出结构化 finding，父流程合并。
- [→harness] **练习 3：AGENTS.md 生效链排错**：制造 global override 与 nested override 冲突，要求学员解释实际生效顺序。
- [→harness] **练习 4：closed-loop repair**：Review→Repair→Validate 三轮，只有 validation delta 收敛才算通过。
- [→harness] **练习 5：MCP header / identity gate**：把工具按 inventory / state inspection / mutating 操作分区，给每区配最小权限与审批。
- [→harness] **练习 6：sandbox symlink / read-only policy fixture**：用无 secret 临时目录验证输入/政策只读、输出可写、symlink escape 被拒绝（具体实现需另行编写）。

## 6. 未验证 / 禁止过度承诺

- 未安装/运行 Claude Code、Codex、Google ADK、OpenAI Agents Python、MAF 或 Foundry Hosted Agents。
- 未验证中国区/Global 区域可用性、合规覆盖、计费与租户策略口径。
- 未做 `openai/skills` 全仓库 harvest；不可推荐客户直接安装社区/上游 skills。
- Google ADK failover / LiveKit / MCP 2.x、OpenAI Agents Python sandbox/session fixes 均为 release-note 级；客户 POC 前需要最小 smoke。
- MicrosoftDocs commit 是文档发布级，不等同客户 SDK 包中能力已验证；需要版本/包/样例链路确认。
