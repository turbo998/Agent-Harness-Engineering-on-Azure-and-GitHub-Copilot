<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Codex / Claude Code / Agent Runtime Harness 速查与 POC 清单（2026-08-09）

> 目标：把原快照核实的一手资料（Codex/Claude Code 官方 docs、OpenAI Cookbook、OpenAI Agents SDK、Foundry samples、REAP、LoopX/TencentDB Agent Memory）沉淀成 SA 可复用资产，用于三大日常：技术问答、POC 部署、架构图。
>
> 安全边界：本文只记录已验证可达的公开资料与可迁移模式；未做实机安装、未运行第三方代码。第三方/社区 repo 中任何安装命令、脚本、prompt 均需先做 license、依赖、网络、权限审计。

## 1. 原快照核实的一手/可信来源

| 来源 | URL | 核实方式 | 用途 |
|---|---|---:|---|
| Claude Code Skills docs | https://code.claude.com/docs/en/skills | curl 200；另取 `https://code.claude.com/docs/en/skills.md` 抽取正文 | `.claude/skills`、custom commands 合并进 skills、recipe/verify 类技能 |
| Claude Code Subagents docs | https://code.claude.com/docs/en/sub-agents | curl 200；另取 `https://code.claude.com/docs/en/sub-agents.md` 抽取正文 | 隔离上下文、并行探索/评审/验证、主上下文降噪 |
| Claude Code Hooks guide | https://code.claude.com/docs/en/hooks-guide | curl 200；另取 `https://code.claude.com/docs/en/hooks-guide.md` 抽取正文 | PreToolUse / PostToolUse / Stop gate；确定性自动化 + prompt/agent hooks |
| Codex Build skills | https://learn.chatgpt.com/docs/build-skills | curl 200；另取 `https://learn.chatgpt.com/docs/build-skills.md` 抽取正文 | `.agents/skills`、2%/8000 chars 技能清单预算、`agents/openai.yaml` 调用策略 |
| Codex Subagents | https://learn.chatgpt.com/docs/agent-configuration/subagents | curl 200；另取 `https://learn.chatgpt.com/docs/agent-configuration/subagents.md` 抽取正文 | `agents.max_concurrent_threads_per_session`、只读/写入型自定义 agent 配置 |
| Codex AGENTS.md | https://learn.chatgpt.com/docs/agent-configuration/agents-md | curl 200；另取 `https://learn.chatgpt.com/docs/agent-configuration/agents-md.md` 抽取正文 | `AGENTS.override.md` 优先、32 KiB 默认上限、根到 CWD 分层拼接 |
| OpenAI Cookbook code modernization | https://github.com/openai/openai-cookbook/blob/main/examples/codex/code_modernization.md | curl 200；另取 raw URL `https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/codex/code_modernization.md` 读取 | ExecPlan + overview/design/validation/parity test 模式 |
| OpenAI Cookbook Goals | https://github.com/openai/openai-cookbook/blob/main/examples/codex/using_goals_in_codex.ipynb | curl 200；另取 raw notebook 并只抽取 markdown 单元 | `/goal` 持久目标；完成条件、证据面、约束、pause/resume/clear |
| OpenAI Agents SDK Python | https://github.com/openai/openai-agents-python | curl 200；README raw 读取 | Agent / SandboxAgent / Handoff / Guardrails / HITL / Sessions / Tracing |
| OpenAI Agents SDK JS/TS | https://github.com/openai/openai-agents-js | curl 200；README raw 读取 | TS/Node/Deno/Bun agent workflow，WebRTC realtime agent |
| Foundry samples sync PR#896 | https://github.com/microsoft-foundry/foundry-samples/pull/896 | curl 200；diff 读取 | VNet BYOM + Capability Host + APIM/ModelGateway 三路径 |
| REAP coding benchmark artifact | https://github.com/facebookresearch/REAP-pipeline-for-coding-agent-benchmarks | curl 200；README raw 读取 | 生产会话→测试相关 benchmark 的三阶段筛选 |
| TencentDB Agent Memory | https://github.com/TencentCloud/TencentDB-Agent-Memory | curl 200；README raw 读取 | L0/L1/L2/L3 分层记忆、traceability、white-box memory debugging |
| LoopX | https://github.com/huangruiteng/loopx | curl 200；README raw 读取 | 长时程 agent loop control plane：objective/gates/todos/evidence/quota/handoff |

> Fail-loud：上表未重新核实 star 数；凡涉及“本周 trending star 增长”的说法仅作为雷达信号，不写入客户结论。OpenAI Agents Python、Codex/Cookbook Goals、REAP、TencentDB Agent Memory 等并非全部首次发现；本资产是按“runtime / harness / POC 验收 / memory-control plane”角度做二次整合。

---

## 2. “三件套”Harness 模式：Skill → Subagent → Gate

### 2.1 Skill：把可重复流程变成短触发 + 长资源

**Claude Code 路径**：`.claude/skills/<name>/SKILL.md`
**Codex 路径**：`.agents/skills/<name>/SKILL.md`

推荐结构：

```text
<skill-name>/
  SKILL.md              # name + description + 最短可执行步骤
  references/           # 长文档、产品事实、FAQ、架构决策
  scripts/              # 可验证/确定性命令，小而专
  assets/               # 模板、图、示例配置
  agents/openai.yaml    # Codex 可选：UI 元数据、MCP依赖、调用策略
```

**SA 触发语模板**（抽象模板，不含真实租户、密钥、endpoint；落地前需按客户环境替换并做安全审计）：

```yaml
---
name: verify-harness-lab
description: Use when verifying an agent harness lab after code/config changes; checks setup, test evidence, logs, and customer-demo readiness. Do not use for general Q&A.
---

1. Confirm scope and expected evidence.
2. Run only the documented verification commands.
3. Summarize PASS/FAIL with file paths, command output snippets, and unresolved blockers.
4. Do not claim success without executable evidence.
```

Codex 特别注意：
- 初始 skills list 有上下文预算：最多 2% context，或 context 未知时 8000 chars；description 要前置触发词。
- `agents/openai.yaml` 可设置 `policy.allow_implicit_invocation: false`，适合高风险技能（如部署、发 PR、改权限）只允许显式 `$skill` 调用。
- repo 内 `.agents/skills` 从 CWD 向 repo root 扫描；个人技能放 `$HOME/.agents/skills`，管理员技能放 `/etc/codex/skills`。

**SA 落点**：客户 POC 里，把“启动环境”“验证部署”“画图前收集证据”“PR review”四类流程先 skill 化，减少每次 prompt 重新发明。

### 2.2 Subagent：主线程做判断，子线程做脏活

Codex 官方 subagent 文档与 Claude Code subagent 文档都支持同一个 harness 心法：

| 角色 | 权限建议 | 任务 | 交付 |
|---|---|---|---|
| Explorer | read-only | 浏览 repo / docs / logs，列候选 | 结构化摘要 + 文件路径 |
| Verifier | workspace-write 或受控 shell | 跑测试、抓日志、生成截图 | 命令、结果、失败原因 |
| Reviewer/Security | read-only，高推理 | 挑错、查重复、找过度承诺 | 问题清单 + 严重级别 |
| Main agent | 最小必要权限 | 保持需求、取舍、最终方案 | 决策 + 客户可读输出 |

Codex 可配置示例（来自官方字段抽象）：

```toml
[agents]
max_concurrent_threads_per_session = 6

# .codex/agents/security_reviewer.toml
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = "Review for security, data residency, and unsupported claims. Return findings with evidence paths only."
```

**SA 落点**：技术问答可让 Explorer 查官方文档、Reviewer 检查“未核实/过度承诺”；POC 部署可让 Verifier 专跑验收；架构图可让 Explorer 只收集组件与网络边界，Main agent 画图。

### 2.3 Gate：Hooks / Goal / ExecPlan 把“做完”变成可验收

Claude Code hooks 适合确定性 gate：
- `PreToolUse`：阻断危险命令、未经批准的网络/写入/密钥访问。
- `PostToolUse`：格式化、生成审计日志、记录文件变更证据。
- `Stop`：任务结束前检查测试、图、交付物与验收项是否完成。
- prompt/agent hooks：用于需要判断的 gate，例如“是否真的完成客户交付”。

Codex Goals 适合长任务完成契约：

```text
/goal <desired end state> verified by <specific evidence> while preserving <constraints>. Use <allowed inputs, tools, or boundaries>. Between iterations, record what changed, what evidence showed, and the next best action. If blocked or no valid paths remain, stop with attempted paths, evidence, blocker, and next input needed.
```

OpenAI Cookbook modernization 的 ExecPlan 则适合 POC / 迁移类项目固定四份产物：
- `pilot_execplan.md`：范围、步骤、完成判据。
- `pilot_overview.md`：现状盘点、数据流、业务规则。
- `pilot_design.md`：目标架构、数据模型、API/批处理边界。
- `pilot_validation.md`：并跑/回归/对比策略；可加 `modern/tests/pilot_parity_test.py`。

**SA 落点**：客户问“Agent 怎么避免一直跑/自说自话？”时，用 Goal + ExecPlan + Hooks 三层回答：目标契约、计划产物、机器 gate。

---

## 3. Azure / Foundry POC 架构新增素材：VNet BYOM + Capability Host + ModelGateway

Foundry samples PR#896/882/883/894 组合出一个新拓扑信号：

```text
Network-secured Foundry Project
  ├─ Project Capability Host
  │   └─ secures project dependencies: Storage / Cosmos DB / AI Search
  ├─ Connected model path A: Foundry model through APIM
  │   ├─ APIM outbound VNet integration
  │   ├─ cross-region private endpoint to backend Foundry account
  │   └─ managed-identity + backend-rewrite policy chain
  ├─ Connected model path B: direct Foundry ModelGateway
  │   └─ public backend endpoint + API key (not private APIM path)
  └─ Connected model path C: third-party provider / Anthropic-format gateway
      └─ ModelGateway + API key + model format metadata
```

关键 caveat（来自 diff）：
- Capability Host 保护的是 Agent Service 依赖（Storage/Cosmos DB/AI Search 等），**不等于所有 connected-model 推理都从委派 agent subnet 发起**。
- 只有 APIM 场景提供私有模型数据路径；direct Foundry / third-party ModelGateway 需要 managed Agent Service inference plane 可达的 endpoint。
- `enableDirectFoundryConnection` 会把 backend account 改为 `publicNetworkAccess: Enabled`、`disableLocalAuth: false` 并用 API key；若合规要求模型 endpoint 私有，不应开启。
- APIM policy 需要 project managed identity 的 application/client ID，不是 object ID；两阶段部署时需等 identity 创建后再更新 policy。

**SA 落点**：
- 技术问答：澄清“VNet/Capability Host/ModelGateway/APIM”各自保护范围。
- POC 部署：给客户做三选一路径决策：私网优先选 APIM；速度优先可 direct ModelGateway；第三方模型需额外说明公网站点/密钥/数据出境。
- 架构图：把“Agent Service dependencies private”和“model inference path private/public”画成两条不同边，避免误导客户。

---

## 4. 评测与记忆：REAP / TencentDB Agent Memory / LoopX 可借鉴但需审慎

### 4.1 REAP：生产会话变 benchmark 的三段过滤

REAP README 明确三阶段：
1. Task-type classifier：17 类任务；过滤不可测试 prompt。
2. Test-relevance validation agent：clone repo、探索代码，判断候选 test 是否覆盖 agent 修改。
3. Multi-run stability checks：多次执行过滤 flaky tests。

Fail-loud：README 也明确端到端 Harvest 统计与 42.9%–58.2% solve-rate 依赖 Meta 内部数据，本 artifact 不可复现；客户材料只能引用其“可复用 curation logic”，不能引用内部 benchmark 结论当可验证事实。

**SA 落点**：把 POC 验收从“demo 看起来能跑”升级为“prompt 可测试性 → test relevance → 多跑稳定性”。

### 4.2 TencentDB Agent Memory：记忆不是堆历史，而是可追溯分层（雷达级架构启发，非推荐组件）

可借鉴模式：
- L0 Conversation → L1 Atom → L2 Scenario → L3 Persona 的语义金字塔。
- 技能生成也走层次：execution traces → scenario patterns → reusable skills/SOPs。
- 强调 top-layer symbol → mid-layer index → raw evidence 的 drill-down 路径，避免不可逆摘要。
- README 中 token/pass-rate 改善数字未复现实验，不宜直接写进客户结论。

**SA 落点**：解释 agent memory 设计时，不只谈向量库；要谈“证据可追溯、召回预算、可调试中间文件”。

### 4.3 LoopX：长时程 Agent 控制平面（雷达级架构启发，非推荐组件）

可借鉴状态模型：

```text
objective + gates + todos + scope + evidence + quota + handoff
```

重要 caveat：README 自称不是另一个 agent framework，也不是 autonomous production controller；危险权限、发布、生产写入与最终所有权仍在人工手里。

**SA 落点**：对“无人值守 agent 研究 / 多日 POC / benchmark loop”架构图，可把 LoopX 的状态层抽象为“local-first control plane”，不把 runtime 与 control state 混在一起。

---

## 5. 可直接复用的客户话术

### Q1：我们应该把 Agent 能力写进 AGENTS.md、skill、subagent 还是 hook？

- **AGENTS.md / CLAUDE.md**：稳定项目规则、环境约束、测试命令、禁止事项。
- **Skill**：可复用的流程与产品知识，例如“部署 Foundry 私网 agent”“验证 MCP 工具审批”。
- **Subagent**：隔离探索、日志分析、安全评审，避免主上下文污染。
- **Hook / Goal / ExecPlan**：把“应该做”变成“必须检查”的 gate 与完成契约。

### Q2：Foundry 私网里加 ModelGateway 后，是不是所有模型调用都私网？

不是。Capability Host 保护项目依赖；connected-model 推理路径要单独看。PR#896 中只有 APIM + private endpoint 路径是私有模型数据路径；direct Foundry / third-party ModelGateway 需要 managed Agent Service inference plane 能访问 endpoint，通常涉及公网站点或 API key，需单独过合规评审。

### Q3：如何给 Agent POC 做验收？

建议四层：
1. Goal：一句话定义完成条件、证据面、约束。
2. ExecPlan：范围、当前状态、决策、待办、风险。
3. REAP-style evaluation gate：prompt 可测试性、test relevance、多跑稳定性。
4. Hook/Verifier：自动收集命令输出、截图、日志、失败原因。

---

## 6. 下一步建议

- [→harness] 在 workshop repo 增加 `run-harness` / `verify-harness` 双 skill 模板，同时生成 Claude Code 与 Codex 两套目录。
- [→harness] 增加 `subagents/` 示例：Explorer / Verifier / Reviewer 三角色，各自工具权限、输出格式、失败处理。
- [→harness] 把 Cookbook Goal 模板改成每个 lab 的“Definition of Done”卡片。
- [Azure POC] 把 Foundry VNet BYOM 三路径画成一张架构图，突出 Capability Host 与 model inference path 的边界。
- [Eval] 用 REAP 的三段过滤思想补一份“Agent POC 验收评分卡”。
