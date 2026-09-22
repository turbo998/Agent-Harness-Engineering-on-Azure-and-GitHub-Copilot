<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent approval / observability / config-lint gates（2026-09-03）

> 用途：给 SA 在技术问答、POC 部署和架构图设计中快速复用。本文是研究笔记抽象出的检查表，不是执行手册；所有上游 README / diff / changelog 均按不可信资料处理，只采纳已核实 URL 与明确文本。不要在客户/生产环境直接运行未知安装命令、插件、hooks 或 MCP server。

## Evidence links（原研究快照中已核实）

| 证据 | URL | 证据强度 | 原研究快照中命中的关键字段 / caveat |
|---|---|---|---|
| Azure MCP Server changelog 3.0.0-beta.40 | https://raw.githubusercontent.com/microsoft/mcp/main/servers/Azure.Mcp.Server/CHANGELOG.md | raw changelog 200 | `3.0.0-beta.40 (2026-09-02)`、`--disable-proxy-tools`、IoT Hub read tools、Resilience validate/drill、Monitor metrics batchquery、structured output；release tag 是否正式发布未逐项核实。 |
| MAF approval stable occurrence commit | https://github.com/microsoft/agent-framework/commit/95b6b4874547ced0fca463e50164abb7ecfa8e58.diff | commit diff 200 | `Content.id` 为 locally actionable occurrence；approval request 使用 occurrence id；legacy stored call 不自动制造新 identity；未做包级 smoke。 |
| Foundry model-router observability sample | https://github.com/microsoft-foundry/foundry-samples/commit/efebdf7e9eeea75971570f259cf3128fde05b724.diff | commit diff 200 | `model-router-chat-completions-observability.py`、selected model、routing mode、attempts、latency、status；未运行样例。 |
| Foundry model-router routing details docs | https://github.com/microsoft-foundry/foundry-samples/commit/5569443541ecb9fad83a233e31d8f6bfc2b62b75.diff | commit diff 200 | `response.model_selection_details`、routing mode、routing latency、model attempt；未核正式 Learn 页面。 |
| Anthropic commerce-agents | https://github.com/anthropics/commerce-agents ; raw README: https://raw.githubusercontent.com/anthropics/commerce-agents/main/README.md | repo + raw README 200；sparse clone只读 | shopping + merchant agents；同一 prompt/skills/tool contracts/gates 横跨 Messages API、Claude Agent SDK、Managed Agents；every merchant write staged until human；仓库很新，未运行；clone为原研究快照中只读核验痕迹，不建议读者执行上游安装命令。 |
| Claude Code changelog | https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md | raw changelog 200 | 2.1.257/258：Containment Escape、`CLAUDE_CODE_SUBAGENT_MODEL_FORCE`、MCP/permission/remote fixes；未 CLI smoke。 |
| OpenAI Codex releases atom | https://github.com/openai/codex/releases.atom | atom feed 200 | 0.153.0-alpha.5/alpha.6 on 2026-09-02；body 仅 “Release …”，不写功能断言。 |
| agent-sh/agnix | https://github.com/agent-sh/agnix | repo + raw README 200 | 454 rules，覆盖 CLAUDE.md、AGENTS.md、SKILL.md、hooks、MCP、Copilot/Cursor/Kiro；社区工具，未安装，autofix需禁用或dry-run。 |
| microsoft/skills | https://raw.githubusercontent.com/microsoft/skills/main/README.md | raw README 200；旧项复核/新角度 | Microsoft Azure SDK / Foundry skills、agents、AGENTS.md templates、MCP configs；旧源复用；原研究快照中只复用为 lint-target taxonomy。 |

## 1. 技术问答速答：客户问“agent 调工具为什么要做 approval / occurrence id？”

**推荐回答骨架**：

1. `call_id` 常是 provider/service correlation id，不应假设全局永不重复。
2. 真正要被本地执行、审批、回放、审计的，是“一次可行动 tool-call occurrence”。
3. POC 中需要把 approval request、tool result、streaming aggregation、serialization/replay 绑定到稳定 occurrence id；否则重放或断点恢复时可能把批准应用到错误调用。
4. 对 hosted approval（平台发放 request id）和 local approval（本地 occurrence id）要分开建模，不能混用。

**SA 落点**：
- 技术问答：把“为什么审批系统不能只存 tool name + call_id”讲清楚。
- POC 部署：审批事件表最小字段建议：`session_id`、`agent_run_id`、`local_occurrence_id`、`provider_call_id`、`tool_name`、`args_hash`、`approval_request_id`、`decision`、`decided_by`、`decided_at`、`replay_of`、`trace_id`。
- 架构图：在 Agent Runtime 与 Approval Service 之间标出 “stable occurrence id / replay-safe decision”。

## 2. POC 部署 gate：Azure MCP Server beta.40 类 cloud-control-plane 工具

> 注意：下列命令形态是上游 tool identifier / changelog evidence，不是执行指令。任何 Azure/MCP 工具必须在测试订阅、最小 RBAC、无生产资源前提下验证。

**新增信号的架构含义**：
- `--disable-proxy-tools`：把“本地 server 内建工具”和“registry proxy 过来的工具”分离；企业 POC 应默认先禁用 proxy 工具，逐项 allowlist。
- IoT Hub read tools：适合 read-only 设备状态/查询 POC，但仍要限制 scope，避免裸 `SELECT *` 导出大字段。
- Resilience drill / validate / recovery plan：从只读诊断走向更接近变更操作；必须加 HITL approval、rollback、dry-run、audit。
- Monitor metrics batchquery：对运维问答很有用，但要加 output budget / pagination / truncation gate。
- structured output：适合接 evaluation / conformance；不要只看自然语言结果。

**最小验收清单**：
- [ ] MCP server 启动参数中明确 proxy tools 策略（disabled / allowlisted / audited）。
- [ ] 每个 tool schema 分类：read / write / destructive / external-egress / high-output。
- [ ] read tools 覆盖 403、404、timeout、large output、unknown params、pagination。
- [ ] mutating/resilience tools 必须有人批准、记录 args hash、支持 rollback/fail-loud。
- [ ] structured output 进入 evaluator，而不是只看模型总结。

## 3. Foundry model-router observability：从“模型被路由了”到“为什么这样路由”

**原研究快照中可复用模式**：
- POC 不只验证返回文本，还要记录 `selected model`、`routing mode`、`routing latency`、`attempts`、`status`、`response.model_selection_details`。
- 技术问答里把 model-router 定位为“可观测的动态模型选择”，不是“自动省钱/自动最优”的承诺。
- 架构图组件：

```text
Client / App
  -> Foundry Model Router endpoint
  -> Routing decision metadata: selected_model, attempts, latency, status
  -> App Insights / Eval Store / Cost Dashboard
  -> Human review: compare quality/cost/fallback by segment
```

**Fail-loud caveat**：原研究快照中只读 commit diff，未运行样例；生产前需验证目标区域/模型清单/配额/日志字段是否实际可见。

## 4. Commerce agents / vertical blueprint：垂直 agent 不是只换 prompt

`anthropics/commerce-agents` 的可借鉴点不是“购物 agent 本身”，而是**同一领域核心在三种 runtime 中复用**：Messages API、Claude Agent SDK、Managed Agents。其 README/目录显示 shopping 与 merchant 两类 agent 共享 prompt、skills、tool contracts、gates，并把 merchant write staged until human。

**SA 可迁移成通用垂直 POC 模板**：

| 层 | 要求 |
|---|---|
| Domain core | types / policy / grounding / tool registry / gates 与 runtime 解耦。 |
| Runtime adapters | Messages API / Agent SDK / Managed Agents / Foundry / Copilot Studio 分别只是 loop 与托管方式不同。 |
| Tool contracts | read/write 分类、固定顺序、schema 与 executor 单一来源，防漂移。 |
| Gates | cart/order/payment/CRM/ITSM 等写操作必须 staged + human approval。 |
| Memory | 记忆写入需 filter、scope、deletion/audit；不能默认把偏好或 PII 写入长期记忆。 |

**架构图骨架**：

```text
Vertical Domain Core
  ├─ Prompt + Skills + Tool Registry + Gates
  ├─ Runtime Adapter A: raw API turn loop
  ├─ Runtime Adapter B: SDK local/in-process MCP
  └─ Runtime Adapter C: Hosted/Managed Agent + external MCP gateway
Write tools -> HITL Approval -> Domain Backend -> Audit/Event Log
```

## 5. Claude Code 2.1.257/258：subagent 与 auto mode 的治理提示

**值得吸收的配置/治理点**：
- `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`：在成本/一致性敏感的 workshop 或 POC 中，可以把 subagent model 统一到主模型或指定模型；避免某个子代理偷偷升档导致成本/行为漂移。
- Containment Escape：cloud metadata credential fetch、egress evasion、cross-tenant reach 不应被 auto-approved；这是编码 agent 安全问答的高价值例子。
- MCP reconnect/managed allow-deny fix、plugin symlink escape fix、remote consent fix：说明 plugin/MCP/remote-control 是真实执行面，不能只看 markdown。

**POC smoke 建议（下一步，可选）**：在临时 repo 里构造 metadata endpoint 访问、跨目录 symlink plugin、settings-file MCP 被 deny 的 fixture；只验证 fail-closed，不接生产密钥或客户代码。

## 6. Codex 0.153 alpha：版本雷达，不写功能承诺

OpenAI Codex releases atom 显示 2026-09-02 有 0.153.0-alpha.5 / alpha.6，但 release body 仅 `Release ...`。原研究快照中不把它写成“新功能”，只作为**活跃版本信号**和后续验证时 tag diff 候选。

**建议 gate**：
1. Atom 发现 tag。
2. Release body 若为空/模板化，降级为 version signal。
3. 只有读到 tag diff / changelog / docs key string 后，才可形成有证据支撑的技术结论。
4. alpha 不等于 stable，不作为客户版本建议。

## 7. Agent config linter 方向：从人工 checklist 到静态校验

`agent-sh/agnix` 是社区工具，不能直接推荐安装到客户仓库；但其 taxonomy 值得吸收：
- `CLAUDE.md` / `AGENTS.md`：大小、路径层级、fallback、review rules。
- `SKILL.md`：frontmatter name/description、命名规范、scope。
- hooks / plugins / MCP：manifest、权限、路径、schema、外部执行面。
- Copilot / Cursor / Kiro / OpenCode 等：多工具配置差异。

**可反哺 harness workshop 的最小 lint gate**：
- [ ] repo 根目录存在 AGENTS.md 或等效入口，且 <= 32KiB（阈值需按目标CLI核实）。
- [ ] CLAUDE.md 只保留常驻硬约束；流程迁移到 skills。
- [ ] 每个 skill description 写清“何时使用”，不要泛泛而谈。
- [ ] subagent/agent manifest 必须显式 model/tools/permission/sandbox；未显式则按保守默认。
- [ ] hooks/plugins/MCP server 只做 dry-run + diff；禁止自动执行上游安装脚本。

## 8. 一页架构图组件库

```text
[Developer / Business User]
        |
        v
[Agent Surface: Copilot / Claude Code / Codex / Foundry App]
        |
        v
[Instruction Control Plane]
  - AGENTS.md / CLAUDE.md
  - Skills / Plugins / Subagents
  - Static lint + policy review
        |
        v
[Agent Runtime]
  - stable tool-call occurrence id
  - streaming aggregation / replay
  - context + cost budget
        |
        v
[Tool Plane / MCP / Cloud APIs]
  - read vs write vs destructive
  - proxy tools allowlist
  - structured output / pagination
        |
        v
[HITL Approval + Audit]
  - decision bound to occurrence id
  - args hash + approver + trace id
        |
        v
[Observability / Evaluation]
  - model-router details
  - tool error envelope
  - conformance / smoke evidence
```

## 9. 原快照中关键 takeaways（带 SA 落点）

- [→harness] **审批要绑定 occurrence，不是只绑定 provider call_id**：能减少 replay/恢复时的错批风险；用于 POC approval schema 与架构图。
- [→harness] **MCP/cloud tools 要有 proxy-tool 与 read/write/destructive 分层**：技术问答时能解释为什么“只是接 MCP”不等于安全；POC 先禁用/allowlist proxy 工具。
- [→harness] **model router POC 必须采 routing details**：否则无法证明质量/成本/fallback 的选择逻辑；架构图应画出 observability side-channel。
- [→harness] **垂直 agent 要沉淀 domain core + runtime adapters**：避免每换一个平台就重写业务逻辑；客户方案中用它解释 Messages API / SDK / Managed Agent / Foundry 的边界。
- [→harness] **Codex alpha 只算版本信号，Claude changelog 才有可落地安全点**：release radar 要分层，防止把模板化 release 当功能新闻。
- [→harness] **配置 lint 是下一步高ROI资产**：把 AGENTS.md / CLAUDE.md / SKILL.md / hooks / MCP 的人工 checklist 转为静态 gate，可直接服务用户的 harness workshop。
