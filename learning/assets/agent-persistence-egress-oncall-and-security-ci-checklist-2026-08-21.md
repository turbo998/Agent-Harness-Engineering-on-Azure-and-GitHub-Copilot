<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Persistence / Egress / On-call / Security-CI Checklist（2026-08-21）

> 用途：把原快照中 6 个深挖对象转成 SA 可复用模板：回答客户技术问题、规划 POC、画架构图时，快速覆盖 **会话持久化、长上下文压缩、私网/出站治理、on-call 人机协作、Codex/Claude harness 治理、安全扫描修复闭环**。
>
> 证据等级：
> - **源码/commit diff 已读**：可用于设计建议，但仍需包级/租户级 smoke 才能承诺生产可用。
> - **README/docs 已读**：可作为架构模式和 POC 素材；不得引用未运行的 benchmark/效果数字。
> - **release/changelog 已读**：适合升级回归清单；功能语义仍以实机验证为准。

## Evidence links（本资产证据入口）

- MAF Azure Blob session persistence commit：<https://github.com/microsoft/agent-framework/commit/e6617c407a1d94a9eb8421e1fd3f385ee6da7e13>（commit/diff 200；未做包级 smoke）
- MAF CompactionProvider / IChatReducer commit：<https://github.com/microsoft/agent-framework/commit/cabb21a292cd364cd51421003f9c3e5dac861e03>（commit/diff 200；文档级证据）
- Foundry hosted agent egress guardrails / model-router docs commit：<https://github.com/MicrosoftDocs/azure-ai-docs/commit/afb12848abe3a1cf6a96a0e6a9e832d37b04ef25>（commit/diff 200；租户 trace 字段未实机验证）
- Foundry private endpoint troubleshooting commit：<https://github.com/MicrosoftDocs/azure-ai-docs/commit/dd563cf26615e14f00bc5aa10c76e40959db278d>（commit/diff 200；私网排障顺序文档级证据）
- Google DeepMind Amplio：<https://github.com/google-deepmind/amplio> / <https://raw.githubusercontent.com/google-deepmind/amplio/main/README.md>（repo/raw 200；未运行）
- Anthropic oncall-kit：<https://github.com/anthropics/oncall-kit> / <https://raw.githubusercontent.com/anthropics/oncall-kit/main/README.md>（repo/raw 200；未运行）
- OpenAI Codex platform / Skills / AGENTS.md：<https://developers.openai.com/blog/codex-as-a-platform>、<https://developers.openai.com/codex/build-skills>、<https://developers.openai.com/codex/agent-configuration/agents-md>（页面 200/跳转 200；CLI precedence/truncation 未实机验证）
- Claude Code changelog：<https://code.claude.com/docs/en/changelog>（页面 200；2.1.236/237 未实机 smoke）
- OpenAI Codex Security：<https://github.com/openai/codex-security/releases>、<https://registry.npmjs.org/%40openai%2Fcodex-security>（release/npm 200；`verify-fix` read-only 仅 release note 级证据）


## 1. Agent 会话持久化与上下文压缩（MAF 08-20 commits）

### 1.1 POC 设计默认项
- **开发期**：In-memory session store 可用，但架构图必须标为 ephemeral / dev only。
- **POC/生产候选**：把 session store 外置到 Azure Blob / Cosmos / DB 等可恢复存储；原研究快照中 MAF commit 显示 AgentWebChat 示例已出现 Azure Blob Storage session persistence 线索。
- **长上下文**：区分两层：
  - `CompactionProvider`：请求进入模型前的 pipeline 压缩，不一定改变已持久化历史。
  - `IChatReducer`：更接近 chat history 层的 reducer，对“存储历史/后续恢复”影响更大。

### 1.2 技术问答标准答案片段
> “Agent 会话恢复不是只靠更大上下文窗口。建议把 **session state / conversation history / tool approval state / trace id** 分层持久化；压缩层要说明是否只影响本次模型输入，还是会写回持久历史。否则 crash-resume 后模型看到的历史可能与用户认为的历史不一致。”

### 1.3 架构图组件
```text
User/Channel
  -> Agent Runtime
     -> Request Pipeline: CompactionProvider（模型输入裁剪）
     -> Chat History Layer: IChatReducer（历史裁剪/摘要）
     -> Session Store: Azure Blob/Cosmos/SQL（恢复锚点）
     -> Trace Sink: App Insights/OTel
```

### 1.4 POC 验收项
- [ ] 杀掉 agent 进程后，同一 session 是否能恢复最后一条用户任务？
- [ ] 工具审批/拒绝状态是否随 session 恢复？
- [ ] 压缩后是否保留安全关键事实（租户、权限边界、审批结果）？
- [ ] session store 是否有 tenant/user scope 前缀、TTL、加密、审计？

---

## 2. Foundry Hosted Agent 出站治理与私网排障

### 2.1 设计模式
- Network egress policy 不只是“allow/deny 列表”，还要画出：规则顺序、默认动作、阻断返回、trace 可观测。
- 原研究快照中 diff 证据显示：Foundry hosted agent guardrails 文档强调 egress decision 可在 trace / Application Insights 侧查看，并给出每 policy **480 egress rules** 限制。
- 私有端点 403 排障：不要先假设 RBAC。先查 DNS / 私网路径 / NSG / route，再查身份和角色。

### 2.2 技术问答标准答案片段
> “私网 Foundry 403 不等于一定是权限问题。先做三步：DNS 是否解析到 private IP；从客户端到 private endpoint:443 是否通；Foundry 项目 RBAC 是否满足。出站工具调用被 guardrail 拦截时，应在 trace/App Insights 中能看到 destination host、matched rule、decision 和 enforcement mode。”

### 2.3 架构图组件
```text
Agent Runtime
  -> Tool Call / HTTP Client
  -> Egress Proxy / Guardrail Policy
       -> rule order / default action / 480-rule limit
       -> Allow | Deny | Transform | Rewrite
  -> External endpoint / Private endpoint
  -> Trace + Application Insights（egress decision）
```

### 2.4 POC 验收项
- [ ] 明确默认 deny 还是 default allow；无匹配规则会发生什么？
- [ ] 对 1 个 allow、1 个 deny、1 个 private endpoint 目标分别留 trace。
- [ ] 在网络失败、DNS失败、RBAC失败三类场景下截图/日志可区分。
- [ ] rule 数量超过 480 或接近上限时有拆分/压缩方案。

---

## 3. AI Labs 模式：长程 agent harness 与 On-call 人机协作

### 3.1 Google DeepMind `amplio`：DB-first crash-resume loop
- README 证据：轻量 step model；工具包括 shell/file edit/sub-agent/inter-agent coordination；DB-first persistence；crash 后可恢复；sub-agent session trees 自动恢复。
- SA 吸收点：长程 POC 不应只要求“agent 能连续跑 3 小时”，而要要求 **checkpoint / resume / sub-agent tree recovery / error envelope**。

#### 架构组件
```text
Run Controller
  -> SQLite/data directory（run reports / summaries / compaction / state）
  -> Agent Step Loop
      -> tools: shell / file edit / sub-agent spawn / coordination
  -> Recovery: resume parent + sub-agent session tree
```

### 3.2 Anthropic `oncall-kit`：只读调查 + 人类决策 + skill-as-code
- README 证据：从 incident history 生成 playbooks/templates；skill 是 markdown instruction file；Claude 调查并给每个 claim 链接，人类决定修复；先验证 read-only connection。
- SA 吸收点：客户问“AI 能不能自动值班修复生产故障？”推荐默认答案不是 full-auto remediation，而是：**read-only investigation → evidence-linked diagnosis → human approval → lesson/playbook update**。

#### 架构组件
```text
Alert / Incident Channel
  -> Claude/Agent read-only investigation
      -> metrics / logs / code host / pager / runbook
  -> Evidence-linked diagnosis
  -> Human decision / approval
  -> Optional remediation ticket / command
  -> Lessons learned -> playbook/skill update
```

### 3.3 POC 验收项
- [ ] 只读连接先行：metrics/logs/code/pager 任一缺失时，agent 是否 fail loud？
- [ ] 每条诊断 claim 是否有链接/日志证据？
- [ ] 修复命令是否需要人类确认，且不会默认执行？
- [ ] 事故复盘是否能沉淀成版本化 skill/playbook？

---

## 4. Codex/Claude harness 治理：上下文拥有权、技能打包、输出风格

### 4.1 OpenAI “Codex as a platform” 模式
- 证据：官方博客标题为 “Codex as a platform: build on the open agent harness”，导航/正文指向 SDK、App Server、MCP Server、sandbox、guardrails/approvals。
- SA 抽象：**Application owns context; harness owns loop**。

```text
Customer/Product App
  owns: UI, user intent, business rules, approval surface, audit records, MCP/tool inventory
  -> Codex/Open Agent Harness
      owns: agent loop, streaming events, sandbox execution, session/thread state, approval callbacks
  -> Tool/MCP layer
  -> Evidence/Logs/Evals
```

### 4.2 Codex Skills 与 AGENTS.md 边界
- Skills：目录形态 `SKILL.md + scripts/ + references/ + assets/ + agents/openai.yaml`；描述用于显式/隐式触发；初始 skill list 有上下文预算，过多会截短/省略。
- AGENTS.md：global/project/path 层级；`AGENTS.override.md` 优先；project instructions 默认组合上限 **32 KiB**。

#### 使用建议
| 需求 | 首选载体 | 理由 |
|---|---|---|
| 仓库全局工程约定 | `AGENTS.md` | 就近层级、覆盖整个 repo |
| 可复用工作流 | Skill | progressive disclosure，减少主上下文污染 |
| 连接器/分发/marketplace | Plugin | 可带 MCP/connector/依赖 |
| 强制质量门 | CI/eval/hook | 不要只靠自然语言指令 |

### 4.3 Claude Code 2.1.236/237 回归项
- 2.1.237：LLM gateway/custom base URL prompt caching 修复；新增 Concise output style。
- 2.1.236：`ANTHROPIC_DEFAULT_MODEL`、cross-session `SendMessage notify_when_idle`、macOS wildcard read-deny 优先级修复。

#### POC smoke pack
- [ ] LLM Gateway / custom base URL 下 prompt caching 是否仍命中？
- [ ] `/model` 与 `ANTHROPIC_DEFAULT_MODEL` / `ANTHROPIC_MODEL` 优先级是否符合预期？
- [ ] `notify_when_idle` 是否只发一次、不会轮询刷屏？
- [ ] `**/.env` / `denyRead` wildcard 在 allow 区域内仍 fail-closed？
- [ ] Concise output 是否适合客户群晨报/CI日志；不适合时保留详细证据链接。

---

## 5. Codex Security 0.1.16：安全扫描 → 修复验证 → SARIF 闭环

### 5.1 新增信号
- GitHub release / npm registry 证据：`@openai/codex-security` latest `0.1.16`。
- Release notes 命中：read-only `verify-fix`、improved GitHub SARIF exports、Daybreak pricing fix。

### 5.2 CI / POC 模板
```text
1. Baseline scan / diff scan
2. Export SARIF -> GitHub code scanning / Defender / security backlog
3. Human or agent patch
4. read-only verify-fix（release note 标为 read-only；仍需 fixture 实机验证不得修改代码）
5. CI gate: no new high/critical + verification evidence attached
6. Ticket close / Linear update / audit log
```

### 5.3 安全边界
- 不在真实客户 repo 上首次运行未知扫描器；先用 fixture repo。
- `verify-fix` 即使是 read-only，也要记录文件访问范围和外部网络行为（未实机验证）。
- SARIF export 改进只是 release note 级证据；接入 GitHub code scanning 前需跑一次最小 SARIF schema check。

---

## 6. 快速客户话术（可转发）

> 推荐把企业 agent POC 拆成 4 层验收：
> 1) **状态层**：会话/审批/trace 可恢复，不靠内存；
> 2) **网络层**：出站策略有默认动作、阻断可追踪，私网 403 先查 DNS/路由再查 RBAC；
> 3) **协作层**：on-call / 高风险工具默认“只读调查 + 人类批准”，playbook/skill 像代码一样版本化；
> 4) **安全层**：扫描结果进入 SARIF，修复后用只读 verify-fix 复验，CI/Eval gate 兜底。
>
> 对 Codex/Claude Code 类 coding agent，`AGENTS.md` 管全局规则，Skill 管可复用工作流，Plugin 管分发/连接器，CI/Hook 管强制质量门；不要把四者混在一个大 prompt 里。
