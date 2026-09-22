<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent release / routing / eval gates — SA reusable checklist (2026-08-23)

> 用途：把原快照中的 MAF/Copilot Studio/MCP SDK/ProEval/Switchyard/Codex/Claude 发现，转成 SA 可复用的 POC 验收清单、技术问答口径与架构图组件。外部 README/Release 仅作资料；未运行真实包、CLI 或租户 smoke 的条目标为未实机验证。

## Evidence links

| Source | URL | Evidence level | Caveat |
|---|---|---|---|
| MAF .NET 1.19.0 | https://github.com/microsoft/agent-framework/releases/tag/dotnet-1.19.0 | release 页面 200；页面正文命中 `session-persisted chat client routing`、`agent-hooks`、`Azure Blob Storage session persistence`、`MCP long-running task support to the 2026-07-28 Tasks extension`；原快照中曾通过 GitHub release API 读取，后续匿名 API 可能限流 | 未跑 NuGet/API smoke |
| MAF Python 1.15.0 | https://github.com/microsoft/agent-framework/releases/tag/python-1.15.0 | release 页面 200；页面正文命中 `A2UI`、`MiddlewareFailure`、`steering, retry, and recovery`、`OpenTelemetry GenAI semantic-convention` breaking；原快照中曾通过 GitHub release API 读取，后续匿名 API 可能限流 | 未跑 Python package smoke |
| Copilot Studio what’s new | https://learn.microsoft.com/en-us/microsoft-copilot-studio/whats-new | Learn page 200；正文命中 Entra Agent ID、GitHub Copilot harness、MCP server as tool、MCP certification preview、skills/memory/files | 需租户级实测可用性/区域 |
| Copilot Studio model lifecycle guidance | https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/plan-agent-model-lifecycle | Learn page 200；正文命中 inventory/evaluate/migrate/monitor lifecycle | 指导性文档，非 API 变更 |
| MCP Python SDK v2 | https://github.com/modelcontextprotocol/python-sdk | GitHub page 200；README 命中 v2 stable、2026-07-28 spec、`pip install mcp` now installs 2.x、v1.x branch | 未读 migration guide 全文 |
| Google DeepMind ProEval | https://github.com/google-deepmind/proeval | repo/raw README 200；README 命中 proactive failure discovery、cost up to 100x claim | `100x` 为 README/论文自述，未复算；不对客户引用为保证 |
| NVIDIA NeMo Switchyard | https://github.com/NVIDIA-NeMo/Switchyard | repo/raw README 200；README 命中 OpenAI/Anthropic/Responses translation、multi-backend routing、stage/escalation routing | 未安装；代理会接触全量 prompt/响应，需安全审计 |
| Claude Code changelog 2.1.239/240 | https://code.claude.com/docs/en/changelog | docs 200；正文命中 `2.1.239`、`/claude-api upgrade`、`metadata.pluginRoot`、synced plugin 命名；2.1.240 为 reliability fixes | 未本地升级 smoke |
| Codex 0.150.0-alpha.6 release | https://github.com/openai/codex/releases/tag/rust-v0.150.0-alpha.6 | release page 200；API 因匿名限流 403，未读 release body | 只记录版本信号；不宣传具体功能 |

## 1. 微软 agent release intake gate

**触发条件**：MAF / Copilot Studio / Azure MCP / Foundry 发布新版本、Learn 文档出现 GitHub Copilot harness、MCP、model lifecycle 等关键词。

**POC 验收门**
1. **包级证据分层**：`release tag 200` ≠ `NuGet/PyPI 已可用` ≠ `样例可跑`。客户材料中分开写 release-level、package-level、smoke-level。
2. **状态持久化**：MAF .NET 1.19 的 Azure Blob session persistence 与 session-persisted chat routing，应做 kill/restart、用户隔离、审批状态与 trace continuity fixture。
3. **长任务协议**：MCP long-running tasks 迁到 2026-07-28 Tasks extension 后，验证旧 client 是否 break、task status/cancel/result envelope 是否与 Azure MCP/自建 MCP 一致。
4. **A2UI/AG-UI**：Python 1.15 A2UI/streaming tool-call indices 适合演示“agent 生成 UI”，但生产 POC 需检查前端渲染 sandbox、XSS/HTML 注入、文件产物权限。
5. **OTel breaking**：OpenTelemetry GenAI semantic convention 从默认/实验模式切换时，先比较字段名、assistant_response 是否落日志、PII 脱敏与成本标签是否丢失。
6. **Copilot Studio model lifecycle**：对生产 agent 建立 model inventory、baseline eval、migration plan、rollback owner、post-deploy monitor；不要把“改模型”当单个配置变更。

**SA 技术问答口径**：
- “MAF 的状态/恢复能力在快速补齐，但我会把 release、包、smoke 三层证据分开；需要客户 POC 才能承诺 kill/restart 恢复。”
- “Copilot Studio GitHub Copilot harness 正把 skills、memory、files、MCP server、workflow 引入低代码 agent；身份与认证从 Entra Agent ID 和 MCP certification 角度治理。”

## 2. MCP SDK v2 migration gate

**触发条件**：客户 Python MCP server 从 `mcp<2` 升级，或 agent runtime 使用 2026-07-28 MCP spec / Tasks extension。

**检查项**
- `requirements.txt` 是否无意从 `mcp>=1.x` 变成安装 2.x；若未准备迁移，显式 pin `mcp>=1.28,<2`。
- 若要迁移，先读 v2 migration guide，验证 transports、session lifecycle、tool schema、long-running tasks、client/server compatibility。
- 对每个 MCP tool 建立 contract tests：unknown parameters、type mismatch、business error、auth error、cancel/timeout、large output truncation。

**架构图组件**：Agent Runtime → MCP Client → SDK v2 Server → Tool Adapter；旁路画 Contract Test / Audit Sink / Policy Gate。

## 3. Eval budget / failure discovery gate（ProEval）

**可复用模式**：把客户 Agent POC 的评测从“抽 20 条人工看”升级为“在预算内主动找失败模式”。

**落地模板**
1. 先准备 baseline traces / Q&A / tool-call transcripts。
2. 定义业务维度：正确性、工具选择、合规、引用证据、响应格式、成本/延迟。
3. 用低成本采样或主动采样挑最可能失败的样本；所有“降低成本 up to 100x”只作为未复算自述，不对客户承诺。
4. 输出 failure clusters：instruction gap、tool contract gap、retrieval/data gap、model migration gap。
5. 失败 cluster 回灌到 AGENTS.md / skill / eval set / architecture guardrail。

**[→harness] workshop exercise**：给一个 30 条 synthetic trace 集，要求学员用主动采样选 8 条最值得人工复核，并写出为什么比随机抽样更节省评测预算。

## 4. Multi-model routing / gateway gate（Switchyard）

**可复用模式**：Claude Code / Codex 等 client 保持原生 API 形状，代理层做 OpenAI/Anthropic/Responses 转换与多后端路由。

**安全边界**
- 代理层会看到完整 prompt、tool output、响应、可能的 secrets；必须有日志脱敏、租户隔离、egress allowlist、key vault、retention policy。
- “弱模型先跑，强模型升级”需要定义 judge 标准与误判处理；不能只画成成本优化。
- stage router 使用 tool errors / conversation signals 做路由时，要避免用户通过 prompt 注入伪造“需要强模型/需要外网”的信号。

**架构图组件**：Coding Agent CLI → Switchyard / AI Gateway → Route Policy → vLLM/NIM/Ollama/OpenAI/Anthropic；旁路画 Trace/Eval、Secret Scrubber、Cost Meter。

## 5. Codex / Claude Code nightly release gate

**Claude 2.1.239/240 本晚吸收**
- `/claude-api upgrade` 可成为“SDK migration skill”的范例：命令化迁移 + reference 更新 + smoke fixture。
- marketplace `metadata.pluginRoot` 修复提醒：plugin catalog 路径解析必须进入 CI，尤其 synced plugin / bare source name。
- 2.1.240 为 reliability fixes；未看到强用户功能，不夸大。

**Codex 0.150 alpha 本晚吸收**
- release page 可达，但 API body 403 未读，因此仅标“alpha line active”；不写 dashboard/queue/plugin 的具体新增功能，除非后续验证时拿到 release body / diff。

**[→harness] release-note hygiene exercise**
1. 给学员一条 release tag、一个 changelog、一个 API 403 情况。
2. 要求输出三层结论：可确认、不可确认、需要下一步 smoke。
3. 若 body 未读，禁止把搜索摘要里的功能点写进客户材料。

## 6. 晚班 takeaways → 四类日常落点

- **技术问答**：遇到“MAF/Copilot Studio/MCP 有什么新能力”时，先按 release/package/smoke 三层回答，避免把 release note 当生产承诺。
- **POC 部署**：优先把 session persistence、MCP contract、model lifecycle、eval budget 写成验收门，不只搭 demo。
- **架构图**：新增四个组件：Agent State Store、MCP Tasks/Contract Test、Eval Budget Optimizer、Model Routing Gateway。
- **[→harness]**：把 Codex/Claude release-note hygiene 与 ProEval failure discovery 做成 workshop 两个 exercise：一个训练证据分层，一个训练评测预算。
