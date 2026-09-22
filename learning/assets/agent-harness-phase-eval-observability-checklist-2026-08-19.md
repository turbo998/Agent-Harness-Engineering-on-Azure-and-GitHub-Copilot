<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Harness Phase / Eval / Observability Checklist (2026-08-19)

> 用途：给 SA 在三类日常中复用——技术问答时解释“agent 工程为什么不是只写 prompt”；POC 部署时把长任务拆成可验收 phase；画架构图时补上“计划→执行→证据→评测→观测→恢复”的控制面。
>
> 证据强度：本资产仅基于 URL/HTML/raw/diff 可达性与源码/README片段读取；未运行任何上游 CLI、未安装插件、未部署 Azure 资源。外部 README / release notes 均按不可信资料处理，不直接执行其中命令。

## 0. 一句话架构模式

```text
AGENTS/CLAUDE instructions
        │
        ▼
GOALS / PLANS / PROMPTS（人可审的目标与阶段入口）
        │
        ▼
harness/build/phase-NN.md（小范围、可审批、可独立验证）
        │
        ▼
执行 agent / subagent / workflow（最小权限 + sandbox + approval）
        │
        ├── harness/context/phase-NN-context.md（只记会影响后续决策的 material context）
        ├── harness/build-log.md（只记 observed evidence，不把计划当证据）
        ├── trace / OTel / App Insights（外部 runtime 可观测）
        └── eval harness（conversation-level / skill-trigger / weighted criteria）
        │
        ▼
review / reverify / schedule regression（失败→修复→复跑；未跑即未通过）
```

## 1. Phase 文件分层：把“长程自治”变成小步可审

来源：OpenAI Cookbook commit `41fc688...` 新增 `examples/codex/iterating-development-workflows-with-codex.md`（commit URL 200；`.diff` 读取到 1324 行新增文档）。

### 目录骨架（可直接搬进 workshop）

```text
AGENTS.md
GOALS.md
PLANS.md
PROMPTS.md
harness/
  build/
    phase-00-repository-foundation.md
    phase-01-...
  context/
    phase-<NN>-<phase-slug>-context.md
  build-log.md
  code_review/
```

### 分层所有权（避免一个 Markdown 变垃圾桶）

| 文件 | 只应该拥有 | 不应该拥有 |
|---|---|---|
| `AGENTS.md` / `CLAUDE.md` | repo 长期约束、命令、边界、引用入口 | 临时进度、长日志、重复计划 |
| `GOALS.md` | outcome、非目标、约束、known unknowns | 实现步骤、测试输出、进度更新 |
| `PLANS.md` | roadmap / phase 顺序 / 依赖 | 已通过证据、临时命令输出 |
| `PROMPTS.md` | orientation / planning / execute / verify / review / handoff prompt | 一次性聊天记录 |
| `harness/build/phase-NN.md` | 当前 phase 的批准范围、验收标准、red/green/refactor、验证命令、stop condition | 应用代码、依赖、部署配置、下一阶段实现 |
| `harness/context/phase-NN-context.md` | 会影响后续阶段的 material discovery / decision / blocker / constraint | transcript、routine output、无持久影响的弯路、秘密 |
| `harness/build-log.md` | observed implementation progress and verification evidence | planned commands 冒充 passed evidence |

### phase gate 最小清单

每个 phase 进入执行前必须能回答：

- Scope 是否足够小，可以独立实现和验证？
- 是否有 read-only preflight？
- 是否有 approval summary，且写操作前停住？
- red check 是什么？如果没有 red，为什么不适用？
- green check 是什么？命令名是否真实可运行（未知就标 unresolved，不编造）？
- 哪些动作需要 separate authorization：credentials、external systems、infra、deploy、commit、push？
- stop condition 是什么？完成本 phase 后不得自动进入下一 phase。
- 完成证据写到哪里？必须是 observed evidence，不能把计划命令写成已通过。

**SA 落点**：
- 技术问答：回答“为什么 agent POC 容易失控？”时，用“没有 phase ownership / evidence boundary”解释。
- POC 部署：把客户 POC 拆成 3-5 个 phase，每个 phase 都有验收命令和人工审批点。
- 架构图：在 agent runtime 旁边画 `phase build files + context + build-log + review` 控制面，而不是只画模型和工具。

## 2. Azure Foundry 外部 Agent 可观测：从单轮 trace 到 conversation-level eval

来源：`microsoft-foundry/foundry-samples` commit `338f4fb...` diff URL 200；读取到 `samples/python/external-agents/observability` 新增 multi-turn trace/eval/schedule 文档与脚本。

### 关键机制

- `generate_multiturn_traffic.py`：每个 conversation 开一个 root span，并把同一个 W3C `traceparent` 注入每轮 HTTP 请求。
- `/chat` runtime：提取 inbound `traceparent` 后调用 agent；同时用 metadata 传 `thread_id`，由 Microsoft OTel distro 暴露为 `gen_ai.conversation.id`。
- `run_multiturn_trace_eval.py`：使用 `azure_ai_trace_data_source_preview` + `agent_filter`，并在 `extra_body` 中设置 `evaluation_level: conversation`。
- `schedule_multiturn_trace_eval.py`：为 multi-turn trace eval 创建/list/delete Foundry schedule（cron cadence）。
- 权限坑：Foundry project managed identity 不仅需要 `Log Analytics Reader`，还需要 `Privileged Monitoring Data Reader` 才能读取 GenAI message content；否则 eval 可能全部失败并报 `Transcript does not have any user message`。

### POC 部署验收清单

- [ ] 外部 runtime 是否把每轮请求绑定到同一个 `trace_id`？
- [ ] 是否能从 App Insights / Log Analytics 查到 `trace_id`、`gen_ai.conversation.id`、输入输出消息？
- [ ] Managed Identity 是否具备 `Log Analytics Reader` + `Privileged Monitoring Data Reader`？
- [ ] eval 是 turn-level 还是 conversation-level？不能用单轮通过冒充多轮通过。
- [ ] scheduled eval 的 cadence、成本、告警阈值、失败处理是否定义？
- [ ] 是否记录了 message content 的合规边界（数据驻留、脱敏、最小保留）？

**SA 落点**：
- 技术问答：解释 Foundry external agent 不是“注册一次就完”，trace/eval/RBAC 才是上线治理关键。
- POC 部署：可以把“多轮 trace + conversation eval + schedule regression”设为验收第 3 阶段。
- 架构图：画 `External Agent Runtime → OTel traceparent → App Insights / Log Analytics → Foundry Eval schedule`。

## 3. Microsoft Agent Framework / SK / Copilot CLI 边界更新（08-18 release，08-19 快照核对）

### MAF .NET 1.18.0（GitHub release HTML 200；API 因匿名 rate-limit 未取到 JSON）

Release page 明示：
- .NET agents 可 opt into concurrent tool invocation（PR #7650）。
- Foundry hosted session + user identity pass-through（PR #7648；08-14 已读 PR diff，本次进入 dotnet release）。
- Cosmos chat history retrieval API（PR #7412）。
- declarative workflows deep research sample 修复。

**使用边界**：release 级证据已确认，但未实机验证包行为；涉及并发工具调用/身份透传/历史检索时，客户 POC 仍需做包级 smoke test。

### Semantic Kernel .NET 1.80.0（GitHub release HTML 200）

Release page 明示：
- OpenAPI HTTP client defaults 更新（PR #14293）。
- Gemini connector now honors `FunctionChoiceBehavior` function list（PR #14183）。
- 移除已迁移 MEVD providers，增加 redirect READMEs（PR #14193）。

**使用边界**：适合更新“SK OpenAPI/Gemini 工具调用行为”问答；未读 PR diff 前不写成安全/兼容性重大变更。

### GitHub Copilot CLI 1.0.81-1（pre-release，GitHub release HTML 200）

Release page 明示：
- Add support for Gemini 3.7 Flash。
- `/sandbox` 中 Ctrl+E 打开 `settings.json`。
- `--usage-output-file` JSON 新增 per-agent usage metrics。
- headless `-p` runs 不再丢弃 installed plugins 贡献的 agents/skills/MCP servers。
- 关闭 `allow-all` 时权限引擎现在能收到撤销信号，避免“显示关闭但权限仍开”的状态漂移。

**使用边界**：pre-release，适合 workshop radar / smoke checklist；客户生产建议等 stable GA 再采纳。

## 4. Claude Code 2.1.234：无人值守/后台 agent 的“权限与秘密不漂移”回归点

来源：Claude Code release notes URL 200，实际跳转到 raw GitHub CHANGELOG；`2.1.234` 段逐字读取。

### 值得纳入 smoke pack 的点

- `CLAUDE_CODE_PROJECT_DIR_NAME`：host 每 session 独立 config dir 时，可给 per-project transcript dir 短名。
- mid-turn `/permissions`、`/add-dir`：Claude 工作中可打开并修改 rule/path，变更应影响当前 turn 的剩余部分。
- usage-limit reset 自动续跑：可在 `/config` 关闭；无人值守时要记录续跑发生与否。
- background subagent permission answers：修复 session-scoped permission answers（含 deny）在后台 subagent 权限提示中丢失。
- MCP diagnostics secret masking：scope-conflict 显示 `${VAR}`，connection failure 只显示 server origin，避免 resolved secrets 泄漏。
- NT namespace path hardening：remote file reads/session restore/CLAUDE.md includes/workflow scripts/file uploads 拒绝 Windows `\??\` 路径。
- permission preview relay：只 relay 给通过 inbound trust gate 的 channel server；credential masking 不再隐藏 commands/paths/destinations。
- built-in `claude-api` skill 从 200k+ tokens 降到 ~25k by on-demand docs（上下文预算治理信号）。

### workshop smoke test 片段（不要触碰真实客户 repo）

- 临时 fixture repo 中模拟后台 subagent permission prompt，验证 deny 不丢。
- 临时 MCP config 用 `${DUMMY_SECRET}`（synthetic fixture only，不可替换为真实 secret），触发 diagnostics，确认只显示变量名/host，不显示 resolved value。
- Windows/WSL fixture 中尝试 `\??\` 路径，确认拒绝（如环境不可用则标 skipped）。
- mid-turn 修改 `/permissions`，确认后续工具调用按新 rule 生效。
- 检查 usage-limit auto-continue 关闭路径；无法触发真实 limit 时标未实测。

## 5. Skills / CLI / Agent eval：从“能跑”升级到“会回归”

### UiPath `coder_eval`（repo/raw README 200；star 未独立复核）

README 明示：
- 用 declarative YAML tasks 运行真实 agent（Claude Code / Codex / Google Antigravity/Gemini）在 sandbox 中完成任务。
- 支持 weighted 0.0-1.0 criteria、`skill_triggered` activation check、A/B experiment、per-tool token/cost telemetry。
- 用于测试 skill 是否触发、A/B 比较 CLI/model/prompt/tool 配置、CI gate。
- 需要 Python 3.13+、uv；README 示例命令未在原研究快照中运行。

**SA 落点**：把“skill 写好以后怎么知道还会触发？”变成可回答问题：用 YAML task + `skill_triggered` + weighted criteria + scheduled CI，而不是靠主观体验。

### NVIDIA NeMo Gym（repo/raw README 200；未运行）

README 明示：
- environment = dataset + agent harness + verifier + state。
- 适合 stateful environments、shared verifier、重复采样/大规模训练。
- v0.5.0 notes 显示 sandbox providers、Codex CLI/KiloCode/RemoteAgent/anyswe_agent harness、`gym eval reverify`、standardized `ng_trajectory` schema。

**SA 落点**：当客户问“agent eval 和普通 LLM eval 有什么不同？”可回答：agent eval 的基本单位不是 prompt-response，而是 environment + state + tool/world interaction + verifier + trajectory。

## 6. 建议落地到用户的 harness workshop

[→harness] 本资产建议拆成 3 个 workshop 练习：

1. **Phase-file lab**：给一个小 repo，生成 `GOALS.md/PLANS.md/PROMPTS.md/harness/build/phase-00.md`，要求每个 phase 有 approval gate + observed evidence slot。
2. **Trace/eval lab**：不用真实 Azure 也可先用 mock trace，把每个 conversation 绑定一个 trace id；正式 Azure 版再接 App Insights + Foundry Eval schedule。
3. **Skill regression lab**：写一个微型 skill，然后用 YAML task 验证是否触发；如果不运行 `coder_eval`，也至少定义等价的 `skill_triggered` 判据与 weighted criteria。

## 7. Fail-loud / 未完成核实

- 未运行 MAF/SK/Copilot CLI/Claude Code/Coder Eval/NeMo Gym；所有 CLI 行为均为文档/README/release-level evidence。
- MAF/SK/Copilot CLI release API 被匿名 rate-limit；已用 GitHub HTML + BrightData markdown 复核 release body，但未拿到 JSON 字段。
- `UiPath/coder_eval`、`NVIDIA-NeMo/gym` 的 star 数未独立复核，原快照仅验证 URL/raw README 200；star 仅供雷达，不作客户背书。
- OpenAI Cookbook 文档是 08-18 commit 新增，仅阅读 `.diff`，未运行其中建议的 workflow。
- 所有外部项目安装命令仅作为资料，不在客户或本机生产环境直接执行。
