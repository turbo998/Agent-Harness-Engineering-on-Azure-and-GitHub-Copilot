<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent diagnostics / provenance / eval / model-tier gates（2026-09-15）

> 用途：给 SA 在客户技术问答、Agent POC 部署与架构图评审时快速套用。本文是**门禁/清单资产**，不是执行 runbook；出现命令形态字符串仅作为上游工具名或证据片段，不是让读者直接在生产环境运行。

## Evidence links（已核实 URL 可达）

| 证据 | URL | 证据层级 | Caveat |
|---|---|---|---|
| MAF .NET OTel source name commit | https://github.com/microsoft/agent-framework/commit/7a82595cbd9e2efb06356ea81f6a6e4640e537b8.diff | commit diff 200；命中 `OpenTelemetryAgent.DefaultSourceName` / `TracerProviderBuilder.AddSource` | 未确认进入正式 NuGet；未跑 .NET smoke |
| MAF Python function-arguments repair commit | https://github.com/microsoft/agent-framework/commit/216e7616c8846143364dbdcaee66d9853277231c.diff | commit diff 200；命中 argument-repair middleware / security middleware fail-closed | 未确认进入 PyPI；未运行 sample |
| MAF Python tool diagnostics redaction commit | https://github.com/microsoft/agent-framework/commit/4d5c63a46a9e1b044936c3806f97701041f2df1b.diff | commit diff 200；命中 `Content.exception` host-internal / fixed failure marker / redaction tests | 未确认进入 PyPI；未做协议端到端验证 |
| Azure MCP ADME search commit | https://github.com/microsoft/mcp/commit/a96d3cce30b157adf4ab035b9a702216633bfc4c.diff | commit diff 200；命中 ADME Lucene search / snapshot cursor / consolidated tools | 未安装 Azure.Mcp.Server；未连 Azure Data Manager for Energy |
| Azure MCP Azure Files Backup register/inquire commit | https://github.com/microsoft/mcp/commit/8f34877b9fa0bc066c4ec2b4947b00f323363a99.diff | commit diff 200；命中 `azurebackup container register` / `protectableitem inquire` | 备份/发现类控制面需测试 vault、RBAC、审批、审计、回滚 |
| Azure AI Projects 2.6.1 prepare commit | https://github.com/Azure/azure-sdk-for-python/commit/fedc3ab96021c2b0d42496cb4ddf0c476f77b63d.diff | commit diff 200；命中 `## 2.6.1 (2026-09-14)` / samples require `azure-ai-projects>=2.6.1` | PyPI 原快照中仍为 2.6.0；release tag 2.6.1 404；仅 prepare/radar |
| GitHub Copilot auto model selection tier changelog | https://github.blog/changelog/2026-09-14-configure-cost-and-quality-in-copilot-auto-model-selection/ | changelog HTML 200；命中 efficiency / balance / intelligence 三档 | 未做企业租户策略 dry-run；可用性需目标租户核实 |
| NVIDIA-NeMo Gym AutomationBench commit | https://github.com/NVIDIA-NeMo/Gym/commit/e657a59.diff | commit diff 200；命中 `AutomationBench` / headline metric / guardrail violation zero-score | 未安装 Gym；未跑 benchmark；不引用性能数字 |
| NVIDIA-NeMo nemo-platform spec revision commit | https://github.com/NVIDIA-NeMo/nemo-platform/commit/e471dfb.diff | commit diff 200；命中 `spec_revision` / `spec_tracked_revision` / deployment staged revision | 未部署 NeMo Platform；抽象为 provenance 模式 |
| OpenAI Codex npm registry + alpha release | https://registry.npmjs.org/@openai/codex ; https://github.com/openai/codex/releases/tag/rust-v0.155.0-alpha.4 | registry/release page 200；`latest=0.154.0`, `alpha=0.155.0-alpha.4` | alpha release body无详细 user-facing delta；stable POC 继续 pin 0.154.0 |
| Claude Code changelog raw + npm registry | https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md ; https://registry.npmjs.org/@anthropic-ai/claude-code | raw/registry 200；顶部 `2.1.270`；npm latest/next仍2.1.270 | 原快照中无2.1.271；2.1.269/270多数已09-13/14覆盖 |
| OpenAI skills/prompts blog | https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra.md | markdown 200；命中 short description / progressive disclosure / AGENTS.md | 09-14官方最佳实践，非09-15新版本；用于方法论重组 |

---

## A. 技术问答速答：客户问“Agent 工具调用出了错，能不能把详细异常给模型/用户看？”

**建议口径**：默认不要把 host-internal exception 原文暴露给模型响应或持久会话。MAF 的 09-14 diff 明确把 `Content.exception` 视为 host-internal diagnostic state，默认序列化时只保留固定 failure marker；真正要给用户看的错误说明应放在 channel-visible `result`，并且经过脱敏。

**POC 验收门**：
1. 合成一个工具抛出包含路径、token-like 字符串、内部 endpoint 的异常。
2. 检查：本地 trusted logs 可定位；模型下一轮上下文、remote protocol payload、session persistence 只出现固定失败标记，不出现敏感原文。
3. 若开启 detailed error 模式，只允许在指定 channel 中出现脱敏信息；不得改变默认安全姿态。

**架构图组件**：Tool Runtime → Diagnostic Sink（restricted）与 User/Model-visible Result（redacted）分两条线，不要把 exception 直接连到 Model Context。

---

## B. 技术问答速答：客户问“函数调用参数错一点，Agent 能不能自动修？”

**建议口径**：可以做“修复型 middleware”，但必须放在 policy/security middleware 之前；一旦 security middleware 已经基于某组参数做过审批或检查，后续再改参数必须 fail-closed，并重新生成 caller-visible 的待审批请求。

**POC 验收门**：
1. 用 schema-compatible 的 provider 参数偏差做 happy path：repair middleware 归一化后进入最终验证，只执行一次工具。
2. 用 approval-bound call 做 tamper path：审批后改参数，应生成 replacement request 或 fail-closed，旧响应不执行工具。
3. 用 NaN/不可复制对象/隐藏值扩展做边界 path：参数 snapshot 必须稳定，安全策略看到的是最终有效调用。

**架构图组件**：Provider arguments → Repair middleware → Validation → Security/Policy middleware → Approval binding → Tool body。把“repair after security”画成红色禁止边。

---

## C. POC 部署清单：Azure MCP 控制面工具新增时怎么安全接入？

原研究快照中两个 Azure MCP commit 代表两类新增工具域：
- ADME search：更偏 read/query，包含 Lucene query、snapshot cursor、>10,000 results 场景。
- Azure Backup AFS register/inquire：涉及注册容器与触发发现，虽然不是删除/故障转移，但仍改变云控制面状态或触发后台发现流程。

**统一安全红线**：所有 register/inquire/discovery/mutating 类云控制面操作只允许在测试订阅/测试 vault 或 mock 中验证，必须有 RBAC scope、human approval、audit 与 rollback/cleanup；不得直连生产。

**统一验收门**：
1. **工具分区**：inventory/read/search、background discovery、mutating control-plane 三类分别审批。
2. **大输出控制**：ADME search 必须验证分页、cursor、output budget、敏感字段脱敏。
3. **云控制面安全**：Azure Backup register/inquire 只接测试 vault/storage account，记录审批人、RBAC scope、operation id、审计日志与 rollback/cleanup。
4. **错误包络**：403、not found、timeout、partial results、cursor expired 都要有稳定 envelope，不能把 SDK/CLI raw exception 直接喂回模型。

**架构图组件**：Agent → MCP Gateway → Tool Router（read/search/discovery/mutating lanes）→ Azure RBAC + Audit Sink + Approval Store。

---

## D. Foundry / SDK release-source freshness gate

Azure SDK for Python 中 `azure-ai-projects` 已有 2.6.1 prepare commit，但原快照中 PyPI 仍显示 `info.version=2.6.0`，GitHub release tag `azure-ai-projects_2.6.1` 返回 404。因此：

- 对内可记录为 **prepare/radar**：Agent Insights samples、WebIQ sample、cancelled run poller、preview header polling 等值得追踪。
- 对客户不能写成“2.6.1 已发布可安装”。客户 POC 基线仍应 pin 已发布包，并用 mock 或测试订阅 smoke 新能力。

**验收门**：package registry latest / GitHub release tag / raw CHANGELOG / sample import smoke 四条 evidence lane 分开记录，任一缺失不得被另一条 URL 200 代替。

---

## E. Eval harness gate：AutomationBench / guardrail-aware scoring

NeMo Gym 新增 AutomationBench 的价值不在“分数”，而在结构：任务目标、评分函数、guardrail violation 直接归零或影响 partial credit。这适合迁移到客户 Agent POC 验收：

1. 每个任务必须拆成 objective metric 与 guardrail metric。
2. objective 成功但触发禁区（越权工具、PII外泄、未经审批写操作）应判 fail 或 severe downgrade。
3. 输出 evidence JSONL：prompt、tool calls、objective score、guardrail events、grader reason、artifact links。
4. 不引用未复算的公开 benchmark 数字，只复用“评分结构”。

**架构图组件**：Agent Run → Artifact Store → Objective Grader + Guardrail Grader → Score Aggregator → POC Scorecard。

---

## F. Deployment provenance gate：记录“部署时到底用了哪个 commit”

NeMo Platform 的 `spec_revision` / `spec_tracked_revision` 模式可抽象为所有 Agent 平台的部署可追溯性门禁：

- `spec_revision`：实际 staged 的不可变 revision（如 commit SHA）。
- `spec_tracked_revision`：部署时跟踪的 mutable ref（如 `main`），如果直接 pin immutable id 则为空。

**客户 POC 验收门**：
1. 每次部署记录 repo URL、branch/ref、resolved commit、artifact digest、builder identity。
2. UI/API 同时显示 mutable ref 与 resolved commit，避免“部署 main”这种不可复现描述。
3. 回滚时必须可选择某个 resolved commit，而不是只选 branch。
4. 审计日志把 prompt/skill/plugin bundle revision 与 runtime image digest 关联。

**架构图组件**：Source Repo → Build/Staging → Deployment Record（tracked ref + resolved revision + artifact digest）→ Runtime。

---

## G. Copilot Auto Model Selection：成本/质量/延迟三档不是强制模型锁

GitHub Copilot 09-14 changelog 表明 auto model selection 增加三档：Efficiency、Balance、Intelligence。客户话术应精确：

- 这是对“auto 如何在可用模型集合中为每个 prompt 选择模型”的偏好配置，不等于固定某个模型，也不等于所有租户立即可见。
- 做企业治理时，要与 model allowlist、预算/AI credits、usage metrics、IDE/CLI/app 覆盖范围一起验证。

**POC 验收门**：
1. 在测试 org 中设置三档，记录相同任务的模型选择、延迟、token/credit 口径（如可见）。
2. 验证受管策略优先级：enterprise/team/user default 是否覆盖或冲突。
3. 给客户交付时写“策略偏好/路由行为”，不要写“强制使用低价/高智模型”。

---

## H. Codex / Claude release-source classifier（原快照中 sentinel）[→harness]

- Codex：npm `latest=0.154.0`，alpha lane 到 `0.155.0-alpha.4`；GitHub release page 200 且标题/页面正文仅能支持“alpha release 存在”，未抽取到详细 user-facing delta。客户/工作坊稳定线继续 pin 0.154.0；alpha 只用于隔离 fixture 的 diff/radar。
- Claude Code：raw changelog 顶部仍是 2.1.270，npm latest/next 未见 2.1.271。原快照中只把 2.1.270 的 read-only git permission regression 当回归用例，不重复包装 2.1.269 的大量功能。
- OpenAI skills blog：把“短 description、progressive disclosure、AGENTS.md 去膨胀”固化为 skill/AGENTS/CLAUDE.md authoring gate：长期短规则留根文件，长流程进 skill/reference，验证动作放脚本或 Stop hook。

---

## 可直接反哺 harness workshop 的练习卡

1. **Tool error redaction lab**：构造含 secret/path 的 tool exception，断言 model context 与 persisted session 不含原文，只含 fixed marker。[→harness]
2. **Argument repair vs approval tamper lab**：先 repair 再 policy 可通过；审批后改参必须 replacement/fail-closed。[→harness]
3. **Azure MCP tool lane lab**：同一 MCP server 中把 search/discovery/mutating 三类工具映射到不同 approval/RBAC/audit 策略。[→harness]
4. **Release-source classifier lab**：比较 raw changelog、registry latest、alpha tag、release body、package smoke 五层，避免把 alpha/body-empty 写成客户功能。[→harness]
5. **Deployment provenance lab**：部署记录必须包含 mutable ref 与 resolved commit；回滚只允许选 resolved commit。[→harness]
6. **Eval scorecard lab**：objective grader 与 guardrail grader 并行，guardrail violation 可覆盖 objective success。[→harness]
