<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Memory / Secure MCP Tunnel / Cross-Agent Config Gates — 2026-08-25

> 用途：给 SA 在三类日常任务中复用：①技术问答快速定位“该用哪层 agent 运行/记忆/隧道能力”；②POC 部署前做 smoke gate；③画架构图时把 identity / memory / tool tunnel / observability 放进正确层级。
>
> 证据等级：`DOC/RELEASE`=官方文档或 release 页面已 HTTP 200（仅代表原快照当时可达，不代表本次已重验）；`README`=仓库 README 已 HTTP 200（仅代表原快照当时可达，不代表本次已重验），仅作资料（claim, not guarantee）；`NOT RUN`=未安装/未部署/未租户实测；`API LIMITED`=GitHub API 匿名限流，star 或 release body 无法二次 API 复核。
>
> **全局安全红线**：所有第三方 CLI / npm / pip / repo 工具只允许在 disposable fixture、无真实 secret、无客户代码的临时环境验证；禁止直接在客户仓库运行 `init` / `install` / setup 脚本。README 中关于“无遥测”“只读”“本地绑定”等安全声明必须用源码/网络抓包/运行时日志复核后才能对客户推荐。

## 1. 本晚选中的 5 个可复用模式

| 模式 | 来源 | 证据 | 适合回答的问题 | POC gate | 架构图组件 |
|---|---|---|---|---|---|
| Foundry Projects SDK 工具调用/A2A 权限面 | Azure SDK `azure-ai-projects_2.5.0` | `DOC/RELEASE`，未跑包 | “Foundry agent 怎么做 A2A / programmatic tool calling / allowed callers？” | Python>=3.10；`openai>=3.0.0` 依赖影响；A2A tool 与 allowed_callers 最小样例 | Agent runtime → Tool policy → A2A peer |
| Foundry Responses durable checkpoint 修复 | Azure SDK `azure-ai-agentserver-responses_2.1.0b2` | `DOC/RELEASE`，未跑包 | “长任务中断/容器重启后 checkpoint、identity、history 会不会错？” | checkpoint JSON round-trip；durable task 内 `get_request_context()`；history limit newest-item 语义 | Durable state store / session recovery |
| 私有 MCP Secure Tunnel | `openai/tunnel-client` | `README+ARCH`，未部署 | “内网 MCP server 能否安全暴露给 ChatGPT/Codex/AgentKit？” | outbound-only；无 inbound firewall；strict-local-auth 不适用；静态 header/mTLS 边界 | Product runtime ↔ tunnel control plane ↔ customer network MCP |
| Cross-agent repo instruction bridge + subagent lint | Codex AGENTS/Subagents + Claude CLAUDE.md/Subagents | `DOC`，未跑 CLI | “一套 repo 规则怎么同时给 Codex/Claude Code 用？subagent 怎么管权限？” | AGENTS 32KiB；CLAUDE.md `@AGENTS.md`；Codex TOML / Claude YAML frontmatter 必填项、sandbox/read-only 默认 | Repo policy layer / agent manifest / verifier subagent |
| Coding-agent observability map | `sodiumsun/agenttrail` | `README+source excerpt`，未安装 | “agent 跑半小时，怎么知道它是不是在绕圈？” | local-only 127.0.0.1；PLAN.md durable map；hooks 只观察不控制；不发送 prompt、不编辑代码 | Plan map + file watcher + hook relay + local dashboard |

## 2. Microsoft / Azure POC intake gates

### 2.1 Azure AI Projects SDK 2.5.0（Foundry Projects）

已核实 release 页面：`https://github.com/Azure/azure-sdk-for-python/releases/tag/azure-ai-projects_2.5.0`（HTTP 200（仅代表原快照当时可达，不代表本次已重验））。关键变更摘录（页面文本）：

- 依赖变更：`openai>=3.0.0`，且最低 Python 版本变为 3.10。
- 新增稳定 A2A tools：`A2ATool`、`A2AToolboxTool`，可选 `A2AProtocolVersion` 1.0。
- 新增 programmatic tool calling：`ProgrammaticToolCallingParam`、`SpecificProgrammaticToolCallingParam`、`ToolType.PROGRAMMATIC_TOOL_CALLING`。
- 多类 tool 参数新增 `allowed_callers`；`CallableToolAllowedCaller` 包含 `direct` 和 `programmatic`。
- Reasoning 扩展 `mode`、`context`、`max_effort` 等属性。

**SA 落点**
- 技术问答：把“agent 调 tool”拆成 direct vs programmatic 两条路径，别只谈 tool allowlist。
- POC：升级前加三条 smoke：依赖锁 `openai>=3.0.0`、A2A 1.0 工具最小 round-trip、`allowed_callers` 对高风险 tool 的拒绝路径。
- 架构图：在 Tool Policy 层标 `allowed_callers: direct/programmatic`，在横向委派边标 A2A protocol version。

**Fail-loud**：未安装 SDK、未运行 A2A / programmatic tool calling 示例；不能向客户承诺具体 API 调用片段可直接运行。

### 2.2 Azure Agentserver Responses 2.1.0b2（durable checkpoint 修复）

已核实 release 页面：`https://github.com/Azure/azure-sdk-for-python/releases/tag/azure-ai-agentserver-responses_2.1.0b2`（HTTP 200（仅代表原快照当时可达，不代表本次已重验））。关键变更：

- 恢复 response-level `internal_metadata` 的 JSON-string 编码，使 resilient response checkpoints 可 round-trip through Foundry storage。
- 恢复 durable tasks 内 stored Responses handlers 的 `get_request_context()` identity values。
- `get_history_item_ids` 应用 limit 时保留 newest item IDs。

**POC smoke gate**
1. 创建一个带 internal_metadata 的响应，写入 Foundry storage 后读取，断言 metadata JSON 字符串 round-trip 不丢字段。
2. 在 durable task 内读取 `get_request_context()`，断言 acted-for identity / tenant / user 不为空且与入口请求一致。
3. 构造超过 limit 的 history，断言保留最新 item，而不是旧 item。

**Fail-loud**：这是 beta 包 release 信息，未包级 smoke；生产材料应写“需在目标版本实测”。

## 3. Secure MCP Tunnel 架构边界（openai/tunnel-client）

已核实：
- `https://github.com/openai/tunnel-client` HTTP 200（仅代表原快照当时可达，不代表本次已重验）；raw README HTTP 200（仅代表原快照当时可达，不代表本次已重验）。
- `docs/architecture.md` raw HTTP 200（仅代表原快照当时可达，不代表本次已重验）。

从 README/architecture 抽取的可用事实：

- `tunnel-client` 由客户运行；通过 outbound HTTPS 连接 OpenAI tunnel service；把 OpenAI 产品发来的 MCP JSON-RPC 请求转发到私有/localhost MCP server。
- MCP server 不需要公网 listener；内部 URL 仅 tunnel-client 能访问。
- final hop 可是 Streamable HTTP、stdio 或 in-memory MCP。
- 控制面 URL 形如 `/v1/mcp/{tunnel_id}`；产品 runtime / tunnel service / client / private MCP 是四段链路。
- `CONTROL_PLANE_API_KEY` 只用于 tunnel-client 到 OpenAI 控制面的 bearer auth，不转发给 MCP server。
- `MCP_EXTRA_HEADERS` 是静态配置，只注入到最终 MCP server hop，不是动态短期 per-request token 生成。
- 文档明确：如果所有 bearer token / auth artifact 必须完全不离开客户环境，则 **strict-local-auth is not supported by Tunnel**；这种场景不应使用 Secure MCP Tunnel。
- 对 Codex，本地可达 MCP 优先用 direct local MCP config；Tunnel适合需要把私有 MCP 暴露给 ChatGPT/Responses/AgentKit 等 OpenAI-hosted runtime 的场景。

**SA 使用方式**
- 技术问答：先问“数据/凭据能否经过 OpenAI product/tunnel queue？”如果答案是否，直接推荐私网内自托管 agent/runtime，不推荐 Tunnel。
- POC：用 sidecar / dedicated deployment / VM systemd 三种部署形态画清楚，不要把 tunnel-client 和 MCP server 混为一个信任边界。
- 架构图：必须画出 control-plane API key、MCP-side auth、MCP payload 三种不同数据流。

## 4. Cross-agent repo instruction + subagent lint gate

### 4.1 Canonical repo instructions

已核实：
- Codex AGENTS.md docs：`https://developers.openai.com/codex/agent-configuration/agents-md.md` → `learn.chatgpt.com/...` HTTP 200（仅代表原快照当时可达，不代表本次已重验）。
- Claude memory docs：`https://docs.anthropic.com/en/docs/claude-code/memory.md` → `code.claude.com/...` HTTP 200（仅代表原快照当时可达，不代表本次已重验）。

**推荐 repo 结构**

```text
repo/
  AGENTS.md                 # canonical: 所有 agent 通用规则
  CLAUDE.md                 # bridge: 只写 @AGENTS.md + Claude-specific delta
  .codex/agents/*.toml      # Codex custom subagents
  .claude/agents/*.md       # Claude Code subagents
  .github/copilot-instructions.md  # 若客户使用 GitHub Copilot，保持与 AGENTS.md 同源或自动生成
```

**Lint checks**
- Codex discovery：`~/.codex/AGENTS.override.md` 优先，否则 `~/.codex/AGENTS.md`；项目从 repo root 到 cwd 逐层读 `AGENTS.override.md` / `AGENTS.md` / fallback；默认 `project_doc_max_bytes=32 KiB`。
- Claude bridge：`CLAUDE.md` 可写 `@AGENTS.md`；相对路径相对当前文件；递归 import 最大 4 hops；Windows 优先 import 而非 symlink。
- 禁止：同一规则在 AGENTS.md 与 CLAUDE.md 双写冲突；把大量 runbook 全塞进启动上下文；把 secret 或 token 写进规则文件。

### 4.2 Subagent manifest lint

已核实：
- Codex Subagents docs：`https://developers.openai.com/codex/agent-configuration/subagents.md` HTTP 200（仅代表原快照当时可达，不代表本次已重验）。
- Claude Subagents docs：`https://docs.anthropic.com/en/docs/claude-code/sub-agents.md` → `code.claude.com/...` HTTP 200（仅代表原快照当时可达，不代表本次已重验）。

**Codex `.codex/agents/*.toml` 必检**
- 必填：`name`、`description`、`developer_instructions`。
- 默认：若未设置 `sandbox_mode`、`mcp_servers`、`skills.config`，继承父会话；高风险 reviewer 默认应显式 read-only / limited tool surface。
- 全局并发：`agents.max_concurrent_threads_per_session` 需与 CI/预算匹配。
- 交互 CLI 里 inactive agent thread 也可能弹 approval；审批前确认 source thread label。

**Claude `.claude/agents/*.md` 必检**
- frontmatter 字段：`description`、`tools`、`disallowedTools`、`model`、`permissionMode`、`mcpServers`、`hooks`、`maxTurns`、`skills`、`initialPrompt`、`memory`、`effort`、`background`、`isolation`。
- `isolation: worktree` 用于隔离子代理写操作；若 worktree 被删且命令路径回到主 checkout，应 fail。
- managed subagents 由管理员通过 managed settings 下发，优先级高于项目/用户同名定义。
- v2.1.233+ 可用 `claude plugin validate` 检查 agent 目录 frontmatter（仍需本地 fixture 实测）。

## 5. Codex Security deep scan 模式（0.1.20）

已核实 changelog：`https://developers.openai.com/codex/security/plugin/changelog` → `learn.chatgpt.com/...` HTTP 200（仅代表原快照当时可达，不代表本次已重验）。

0.1.20（August 17, 2026）的可迁移模式：

- deep scan workers 不再只做局部发现，而是各自跑完整 standard scan end-to-end audit：threat modeling、validation、attack-path analysis、coverage reporting。
- reducer 合并 completed worker reports，同时保留 time limit、partial coverage、restart recovery、cancellation。
- 默认 4 concurrent workers；连续 4 次 completed scan 没有新增 findings 后停止；上限 40 worker runs。
- hosted scans 前检查 Trusted Access for Cyber；状态不可验证时给 warning/enrollment link。

**迁移成 SA 安全 review harness**

```text
security-review/
  scope.md              # 本次要审哪些 assets / repos / MCP tools
  workers/              # 每个 worker 一份完整审计，不是切碎 checklist
    threat-model.md
    validation.md
    attack-paths.md
    coverage.md
  reducer.md            # 合并 findings，按 P0/P1/P2 去重
  stop-condition.md     # 连续 N 轮无新增发现即停；记录 partial coverage
  evidence-log.md       # 每条 finding 必带文件/URL/命令/时间戳
```

**Fail-loud**：本晚未运行 Codex Security plugin，不引用其扫描效果数字；只借鉴“并行完整审计 + reducer + 停止条件”的 harness 形态。

## 6. Agent observability：agenttrail 的轻量模式

已核实：`https://github.com/sodiumsun/agenttrail` 与 raw README HTTP 200（仅代表原快照当时可达，不代表本次已重验）；`bin/agenttrail.mjs` raw HTTP 200（仅代表原快照当时可达，不代表本次已重验）。

可借鉴点：
- 本地开源 observability layer：展示 plans、tool calls、file changes、progress；不以 token/latency 为中心，而以 repo work map 为中心。
- `npx agenttrail --open` 在 localhost 打开；README 声称无账号、无全局安装、无 telemetry。
- `init` 会修改 `CLAUDE.md` / `AGENTS.md`、创建 `PLAN.md`、安装 additive local Claude Code hooks；因此不能在客户仓库盲跑。
- 源码片段显示 hook relay 发到 `http://127.0.0.1:<port>/hook`，CLI 注释称 “fs watcher on the repo + PLAN.md convention；hooks optional fidelity adapter”。
- README 声称只绑定 `127.0.0.1`，只观察、不发送 prompt、不编辑代码。

**SA 落点**
- 技术问答：可把“LLM observability（trace/token/cost）”与“coding work observability（计划/文件/组件状态）”区分开。
- POC：先在临时 repo 跑，只允许修改 fixture 的 `AGENTS.md/CLAUDE.md/PLAN.md`，验证它是否真的不外发遥测。
- 架构图：作为“开发者工作台可观测层”，放在 coding agent 与 git workspace 旁边，不放在生产 runtime 监控层。

## 7. OpenViking：context database 的设计启发（不作为推荐组件）

已核实：`https://github.com/volcengine/OpenViking` 与 raw README HTTP 200（仅代表原快照当时可达，不代表本次已重验）；GitHub API 受限，star 数未独立复核。

可借鉴的结构：
- 用 `viking://` 虚拟文件系统统一 memories/resources/skills。
- 写入时处理成 L0 abstract、L1 overview、L2 details；按任务需要分层加载，降低 token。
- 先命中目录，再层层 drill down；保留 retrieval trajectory 方便解释“为什么召回了这条”。
- session commit 后异步抽取 user preference / agent experience 为长期 memory。

**Fail-loud**：README 中关于 LoCoMo / tau2-bench 的提升数字未复算，不能写入客户承诺；本晚只采纳“分层上下文 + 可解释召回轨迹”设计模式。

## 8. 可直接拿去用的 POC 前置清单

### 8.1 Cross-agent repo config preflight

```yaml
repo_config_preflight:
  canonical_file: AGENTS.md
  claude_bridge:
    required: CLAUDE.md contains '@AGENTS.md'
    max_import_depth: 4
    windows_symlink: avoid
  codex:
    project_doc_max_bytes_default: 32768
    check_override_shadowing: true
    check_fallback_names: true
  forbidden:
    - secrets_or_tokens_in_instruction_files
    - duplicated_conflicting_rules
    - long_runbooks_loaded_at_startup
```

### 8.2 Subagent permission preflight

```yaml
subagent_permission_preflight:
  default_policy: read_only_until_task_requires_write
  codex:
    required_fields: [name, description, developer_instructions]
    inspect: [sandbox_mode, mcp_servers, skills.config, model_reasoning_effort]
  claude:
    inspect: [tools, disallowedTools, permissionMode, mcpServers, hooks, skills, memory, background, isolation]
    recommended_for_writes: isolation: worktree
  approvals:
    require_source_thread_label: true
    forbid_blind_approval_from_inactive_thread: true
```

### 8.3 Secure MCP Tunnel decision gate

```yaml
secure_mcp_tunnel_gate:
  use_when:
    - private_or_local_mcp_server_needs_openai_hosted_product_access
    - outbound_https_allowed
    - mcp_payloads_can_cross_openai_runtime_and_tunnel_queue
  do_not_use_when:
    - strict_local_auth_required
    - bearer_tokens_or_auth_artifacts_must_never_leave_customer_environment
  verify:
    - control_plane_api_key_not_forwarded_to_mcp
    - mcp_extra_headers_static_only
    - mcp_side_mtls_if_required
    - audit_log_separates_product_runtime_tunnel_client_mcp_server
    - payload_and_metadata_logging_policy_reviewed
    - data_residency_and_region_compliance_reviewed
```

### 8.4 Agent work observability fixture

```yaml
agent_work_observability_fixture:
  environment: temporary_repo_only
  expected_files: [AGENTS.md, CLAUDE.md, PLAN.md]
  checks:
    - dashboard_binds_127_0_0_1_only
    - hook_payload_contains_no_secret
    - tool_shows_plan_vs_observed_file_changes
    - uninstall_restores_instruction_files_or_diff_is_reviewed
  non_goals:
    - production_runtime_monitoring
    - token_cost_tracing
    - automatic_agent_control
```

## 9. 原快照中关键 takeaways

- [→harness] **Repo 指令文件要“一主多桥”**：AGENTS.md 做 canonical，CLAUDE.md 用 `@AGENTS.md` 导入并只放 Claude-specific delta，减少跨工具漂移。
- [→harness] **Subagent manifest 应进入 CI/lint**：不是“写几个 persona 文件”就完事；要检查必填字段、最小权限、read-only 默认、worktree isolation、MCP/skills trust。
- [→harness] **安全审计并行化不能把 checklist 切碎**：Codex Security 0.1.20 的有用模式是每个 worker 都做完整审计，再由 reducer 合并，而不是把 threat modeling/validation/coverage 分给互不理解上下文的不同 agent。
- **Secure MCP Tunnel 是“私有网络入口”不是“本地数据不出域”**：无 inbound firewall 是优点，但 MCP payload / tool args / responses 仍经过 OpenAI product runtime 与 tunnel queue；严格本地 auth 场景不要用。
- **Foundry durable agent POC 要测恢复语义**：checkpoint JSON、request identity、history limit 是 long-running agent 最容易“看起来成功、恢复后错乱”的三类回归点。
- **Agent observability 要分两层**：生产 LLMOps 看 trace/token/cost；coding-agent 工作台要看 plan/file-change/component map。agenttrail 给了一个轻量模式，但必须先审 init 对 AGENTS/CLAUDE/PLAN 的修改。
