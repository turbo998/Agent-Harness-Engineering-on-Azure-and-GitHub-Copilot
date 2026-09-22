<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent 输出预算 / ExecPlan / Skill Eval 门禁速查（2026-08-27）

> 用途：给 SA 在技术问答、POC 部署、架构图设计中快速回答“Agent 工具输出如何控上下文？多小时任务如何不中途漂移？Skill/插件怎么准入？”
>
> 安全说明：下方出现的命令形态、CLI 名称、MCP tool 名称仅为上游证据片段/设计对象，不是执行指令；任何客户 POC 前必须在临时 fixture / 测试订阅中验证，不接生产代码、生产订阅或真实 secret。

## Evidence links（原研究快照中已验证 URL 可达）

| 主题 | 证据 URL | 原研究快照中验证 | 证据强度 / caveat |
|---|---|---:|---|
| Azure MCP Server beta.38 | https://github.com/microsoft/mcp/releases/tag/Azure.Mcp.Server-3.0.0-beta.38 | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | release 页面级证据；页面命中 Lucene；未安装包/未核完整 schema。 |
| Azure MCP output size measurement | https://github.com/microsoft/mcp/commit/8ab9c1e26097278887e8b17a2fb068c004eb2757<br>diff: https://github.com/microsoft/mcp/commit/8ab9c1e26097278887e8b17a2fb068c004eb2757.diff | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；diff HTTP 200（仅代表原快照当时可达，不代表本次已重验） | commit/diff 级证据；未核进入哪个正式包。 |
| Azure MCP resilience drill create/delete | https://github.com/microsoft/mcp/commit/a1ca74321cbf7908536f7aee61df81bc0d0cdc0d<br>diff: https://github.com/microsoft/mcp/commit/a1ca74321cbf7908536f7aee61df81bc0d0cdc0d.diff | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；diff HTTP 200（仅代表原快照当时可达，不代表本次已重验） | commit/diff 级证据；mutating/resilience 工具需 RBAC、approval、rollback gate。 |
| Foundry samples LangGraph user identity toolbox | https://github.com/microsoft-foundry/foundry-samples/commit/6178e97a7f6329370277253892de81de46e76156<br>diff: https://github.com/microsoft-foundry/foundry-samples/commit/6178e97a7f6329370277253892de81de46e76156.diff | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；diff HTTP 200（仅代表原快照当时可达，不代表本次已重验） | sample commit 级证据；适合 POC intake，非生产标准答案；用户身份主题为历史覆盖项，原研究快照中按新 sample commit 更新 POC 门。 |
| Foundry samples project Responses API | https://github.com/microsoft-foundry/foundry-samples/commit/b073445d899d3066c948dfe9fbbfa12587cdb000<br>diff: https://github.com/microsoft-foundry/foundry-samples/commit/b073445d899d3066c948dfe9fbbfa12587cdb000.diff | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；diff HTTP 200（仅代表原快照当时可达，不代表本次已重验） | sample commit 级证据；未运行样例。 |
| Claude Code changelog 2.1.246 | https://code.claude.com/docs/en/changelog | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | docs/changelog 级证据；未实机 smoke。 |
| Anthropic long-running harness | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | 一手工程博客；用于方法论，不是产品 SLA。 |
| OpenAI Codex changelog | https://learn.chatgpt.com/docs/changelog | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | docs/changelog 级证据；Codex alpha 功能需 release body/CLI smoke。 |
| OpenAI ExecPlans | https://raw.githubusercontent.com/openai/openai-cookbook/main/articles/codex_exec_plans.md | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | Cookbook raw markdown；ExecPlan/Goals主题为历史覆盖项，原研究快照中是与MCP输出预算、Claude 2.1.246 smoke、Skill gate合并资产化；需本地改写。 |
| OpenAI Codex subagents | https://learn.chatgpt.com/docs/agent-configuration/subagents | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | docs 级证据；未实机验证 TOML/权限继承。 |
| NVIDIA SkillEvaluator | https://github.com/NVIDIA/SkillEvaluator<br>raw: https://raw.githubusercontent.com/NVIDIA/SkillEvaluator/main/README.md | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；raw README 200 | repo/README 级证据；未安装；scanner/external tools需安全审计。 |
| infragate/capa | https://github.com/infragate/capa<br>raw: https://raw.githubusercontent.com/infragate/capa/main/README.md | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；raw README 200 | 社区 repo/README 级 radar；不推荐直接安装；README token-savings数字未复算。 |

## 1. 工具输出预算门（Azure MCP beta.38 / output measurement）

**问题**：MCP 工具越多、输出越大，Agent 上下文会被“工具结果”挤爆；客户问“为什么 agent 明明调到工具却答得差”时，常见根因不是模型能力，而是 tool output 治理缺失。

**POC 门禁**：
1. 每个 MCP tool 返回必须记录 `bytes/chars/tokens估算/rows/items/truncated?`。
2. 对 search/list/query 类 tool 建 `max_results` 与 `max_output_bytes` 默认值；超过时返回摘要 + continuation token，而不是把全量 JSON 塞回模型。
3. beta/commit 级 Azure MCP 功能只可在测试订阅验证；客户材料写“release/commit 信号”，不要写“生产已验证”。
4. 对 drill/create/delete 等运维类 tool：默认 read-only；mutating tool 必须 human approval + RBAC 最小范围 + rollback/audit 字段。

**技术问答话术**：
- “MCP 工具治理不是只看能不能连上；还要看输出预算、错误 envelope、审批和审计。”
- “如果一个 tool 可能返回上千资源，Agent 设计上应把 list/search 变成分页检索，而不是一次性全量上下文注入。”

**架构图组件**：
`Agent runtime → MCP gateway → Tool output meter → Summarizer/Truncator → Evidence store → Model context`

## 2. Foundry Hosted Agent + user identity / Responses API 样例门

**问题**：客户 POC 经常把“Agent 身份”和“最终用户身份”混在一起，导致审计和授权不可解释。

**POC 门禁**：
1. 明确三类身份：developer/service identity、agent identity、end-user acted-for identity。
2. Toolbox/MCP/下游资源必须记录 acted-for/user identity 的传递位置与审计落点。
3. Responses API / Invocation SDK / A2A / Activity bridge 是不同入口；POC 先选一种主入口，避免样例拼贴导致追踪断裂。
4. Foundry samples 是 sample-grade reference：可用于入门和图示，不等同生产最佳实践。

**技术问答话术**：
- “User identity pass-through 的价值在于审计和授权归因；不是让 Agent 获得无限代理权限。”
- “企业 POC 的验收点应该包括 RBAC denied、user scope mismatch、toolbox failure envelope，而不只是 happy path。”

**架构图组件**：
`User / Chat surface → Foundry Hosted Agent Session → Responses/Invocations → Toolbox/MCP → Azure Resource → Audit/Trace`

## 3. ExecPlan / long-running harness 门（Codex + Anthropic） [→harness]

> 去重状态：Anthropic long-running harness 与 Codex ExecPlan/Goals/PLANS 主题此前已被多次覆盖；原研究快照中不是重新宣称新发现，而是把旧方法论与 08-27 新的 MCP 输出预算、Claude 2.1.246 smoke、SkillEvaluator 准入门合并成一页可执行 POC gate。

**问题**：多小时 Agent 任务最容易 drift：做到一半忘目标、丢上下文、把未完成当完成。

**可复用文件骨架**：
```text
GOALS.md          # 目标、非目标、验收标准
PLANS.md          # 当前 ExecPlan：背景、步骤、验证、回滚
PROGRESS.md       # 每轮完成/未完成/阻塞
EVIDENCE/         # curl状态、diff摘要、日志、截图、测试输出
DECISIONS.md      # 关键取舍与未验证假设
```

**执行规则**：
1. 每轮开始先读 `GOALS.md + PROGRESS.md`；每轮只推进 1-2 个 milestone。
2. 每个 milestone 必须有外部可验证 evidence：URL 200、diff 命中、test output、artifact path。
3. 结束前必须写 `completed / incomplete / blocked`，禁止只写“看起来完成”。
4. 如果需要多 subagent，按“探索/实现/评审/URL核验”拆，不让多个 agent 写同一文件；父 agent 统一落盘。

**技术问答话术**：
- “长程 Agent 的关键不是给更长 prompt，而是把状态外置成可读写的计划与证据文件。”
- “ExecPlan 是 agent 的工作合同，PROGRESS 是跨上下文恢复点。”

## 4. Claude Code 2.1.246 smoke pack [→harness]

**原研究快照中 changelog 关键信号**：Auto mode 权限可视化、MCP interrupted error 修复、plugin cache/skill naming 修复、超大 session safety-check deadline、长 diff 渲染修复等。

**最小 smoke（只在临时 repo）**：
- Auto mode：查看/编辑 classifier rules 后，确认高风险 shell 仍需审批。
- MCP interrupted：模拟 headless/remote session 收到中断，期望模型看到 explicit interrupted error，而非“completed with no output”。
- Plugin cache：安装/更新同一 plugin，确认无重复 SHA 目录、slash menu 无 `plugin:plugin:` 双前缀。
- Long diff：生成超长单行 diff，确认 UI/日志不会卡死且 evidence 可保存。

**注意**：未实机验证；客户材料中只写“changelog 指示需纳入升级回归”，不要承诺已验证行为。

## 5. SkillEvaluator / CAPA intake 边界

### NVIDIA SkillEvaluator（AI Lab/官方 repo）
可借鉴三层门：
1. **Tier 1 validation**：frontmatter、license、Unicode/PII、script lint、安全扫描。
2. **Tier 2 dedup/context optimization**：查重、语义重叠、上下文预算。
3. **Tier 3 live eval**：用合成任务/真实 agent 跑 skill trigger 与行为评价。

**SA 落点**：把“新 skill 是否值得装”变成可评分流程，而不是靠直觉。

### infragate/capa（社区 radar）
README 宣称用 `capabilities.yaml` 一处声明 skills/tools/rules/sub-agents/MCP/plugins，并同步到多种 coding agents；这对跨 Codex/Claude/Copilot 配置统一很有启发，但属于社区工具，未安全审计，不直接推荐安装。

**可迁移设计**：
- 单一能力声明文件；
- per-agent format adapter；
- MCP gateway 的 tool allowlist；
- shadow workspace，避免 provider dirs 污染真实仓库。

**禁用/慎用**：
- 不引用 README token-savings 数字，未复算；
- 不在客户仓库运行 `install/wrap`；
- 先审 license、脚本、网络、文件写入路径和 secret handling。

## 6. 最小验收样例（可直接改成 workshop exercise）

```text
Gate: tool_output_budget
Input: 调用 list/search 类 MCP tool，模拟返回 1000 条资源
Expected:
- response.truncated = true
- continuation_token present
- evidence file saved under EVIDENCE/
- model context receives summary only, not full raw JSON
```

```text
Gate: identity_mismatch
Input: end-user 无资源权限，但 agent/service identity 有资源权限
Expected:
- 下游调用按 acted-for user scope 拒绝
- audit log 同时记录 user identity 与 agent/session id
- agent 返回可解释的 RBAC denied，不尝试绕过
```

```text
Gate: skill_live_eval
Input: 新 skill + 3 条 synthetic trigger cases + 2 条 anti-trigger cases
Expected:
- trigger cases 命中 skill 并读取最小必要 reference
- anti-trigger cases 不误触发
- 无未知脚本执行；无网络外发；无 secret 输出
```

## 6. 一句话 takeaways

- [→harness] **输出预算是 MCP POC 的验收项**：tool 能返回结果不够，必须证明不会把上下文撑爆。
- [→harness] **ExecPlan/PROGRESS/EVIDENCE 三件套比“更长上下文”更可靠**：用于定期检查、客户 POC、长程迁移任务都适用。
- **Foundry user identity pass-through 要画在架构图上**：否则客户看不出审计和授权边界。
- [→harness] **Claude/Codex subagent 不是越多越好**：read-heavy 探索适合并行，write-heavy 必须集中落盘和独立评审。
- **Skill 准入要用三层门**：格式/安全 → 去重/上下文预算 → live eval；社区工具只作 radar，不作默认安装。
