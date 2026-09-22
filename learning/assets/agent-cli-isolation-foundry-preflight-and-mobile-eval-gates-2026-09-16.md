<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent CLI 隔离、Foundry 预检与移动端评测 Gate（2026-09-16）

> 用途：给 SA 在技术问答、POC 部署和架构图设计时快速复用。所有外部资料均按不可信资料处理；本资产只做只读提炼，不安装/运行任何第三方仓库。证据以 2026-09-16 资料快照为准。

## 0. Evidence links（已核实可达，未做实机 smoke）

| 对象 | URL | 证据层级 | 原研究快照中核验 |
|---|---|---|---|
| Claude Code 2.1.271/2.1.272 changelog | https://code.claude.com/docs/en/changelog.md | 官方文档/changelog | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；摘录含 `2.1.271`、`allowed_domains`、`omitClaudeMd`、`--accept-command <sha256>` |
| Claude Code subagents/workflows docs | https://code.claude.com/docs/en/sub-agents.md / https://code.claude.com/docs/en/workflows.md | 官方文档 | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；subagent frontmatter 与 usage-limit resume 文档级证据 |
| OpenAI Codex 0.155.0-alpha.6 | https://github.com/openai/codex/releases/tag/rust-v0.155.0-alpha.6 | alpha release 页面 | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；release body 未提供完整用户向说明，按 radar 处理 |
| Codex alpha.4→alpha.6 diff | https://github.com/openai/codex/compare/rust-v0.155.0-alpha.4...rust-v0.155.0-alpha.6.diff | 源码 diff | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；只读关键词 triage，未逐文件审计 |
| Foundry prompt-agents sample | https://github.com/microsoft-foundry/foundry-samples/commit/7f87f4d11a29bbdbbf411bfdf56eb6fb37253fb7 | commit diff | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；新增 `samples/python/prompt-agents` |
| Foundry reachability analyzer | https://github.com/microsoft-foundry/foundry-samples/commit/cf1d613f03d016605341fd8efdb3520c97842605 | commit diff | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；新增 read-only reachability analyzer |
| MAF token usage preservation | https://github.com/microsoft/agent-framework/commit/6c3c58a4b2d8834ad3dce3d0b01ad10f7edaf352 | commit diff | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；保留 cached/reasoning token count |
| MAF MCP result mode | https://github.com/microsoft/agent-framework/commit/e584a9f39c20f8210bbf4adcfd10755dafcae678 | commit diff | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；`MCPToolResultContentMode` 显式化 |
| Meta DigiWorld | https://github.com/facebookresearch/digiworld / https://raw.githubusercontent.com/facebookresearch/digiworld/main/README.md | 旧源复用 | HTTP/GET 200；API核 star=4/fork=1，Apache-2.0，created 2026-08-18；仅复用 CUA eval 结构，不作为新发现或生产推荐 |
| Mistral Vibe 2.25.4 | https://github.com/mistralai/mistral-vibe/releases/tag/v2.25.4 / https://github.com/mistralai/mistral-vibe/compare/v2.25.3...v2.25.4.diff | release+diff | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；含 CVE/GHSA 权限收紧 |
| GitHub Spec Kit | https://github.com/github/spec-kit / https://raw.githubusercontent.com/github/spec-kit/main/README.md | 官方 repo/README | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；API核约 137k★/12.3k forks（自然增长中） |

## 1. 客户技术问答速答模板

### Q1：Claude Code 2.1.271 这次对企业安全有什么实际意义？
短答：它把“命令可访问哪些域名”和“子代理是否加载用户/项目 CLAUDE.md”从隐含上下文变成显式控制点。

- `allowed_domains`：在 auto mode + sandbox 下按单条 Bash/PowerShell/Monitor 命令开放所需 host，其它 host 拒绝。POC 时应把网络访问写成 **per-command domain allowlist**，而不是会话级全开。
- `omitClaudeMd`：custom/plugin subagent 可跳过 user/project/local CLAUDE.md，但 managed policy 仍加载。适合 **只读探索/独立评审/不应继承项目私有提示的 worker**。
- `--accept-command <sha256>`：plugin install/update 用上一轮 `--json` 展示的精确命令哈希确认，避免无脑 `-y` 接受变更。
- 风险边界：未实机验证；客户环境的 org policy、gateway、runner 版本仍需 dry-run。

### Q2：Codex 0.155 alpha 能不能拿来给客户演示？
短答：不建议。它有大量与 Guardian/reviewer、MCP metadata、Windows sandbox、network policy、app-server 相关的 diff 信号，但官方 stable changelog 仍停在 0.154.0，原研究快照中只作 **alpha radar**。

- 可做：只读 diff triage，提前准备下一版兼容性 checklist。
- 不可做：把 alpha diff 写成客户可用功能承诺；不在客户 repo 里跑 alpha。

### Q3：Foundry Agent POC 部署前最容易漏的预检是什么？
短答：网络可达性与工具/身份边界。新增 `prompt-agents` 样例给了 prompt agent + MCP tools + Foundry toolbox + GitHub Copilot harness 的最小参考；新增 reachability analyzer 说明微软也在把私网排障前移成静态预检。

### Q4：Computer Use Agent 评测怎么讲得具体？
短答：Meta DigiWorld 给出一个早期但很清楚的模式：15 个 sandboxed Android apps + template-driven data generation + programmatic verifier。不要引用成熟度或榜单，只借鉴“可复现环境 + 隐藏验证器 + 多配置扰动”的 POC 验收结构。

## 2. POC Preflight Gates

### A. Coding Agent CLI / Plugin / Subagent Gate

| Gate | 检查项 | 通过标准 | 失败处理 |
|---|---|---|---|
| Release-source classifier | stable / alpha / next / docs / diff 分层 | stable+官方 changelog 才能客户演示；alpha 只作 radar | 降级措辞：`未稳定/仅源码信号` |
| Subagent context isolation | 是否继承 user/project/local instruction | 对只读 explorer/reviewer 默认启用最小上下文；Claude 可评估 `omitClaudeMd` | 若无法隔离，禁用处理 secret/PII 的任务 |
| Per-command network | 命令级域名白名单 | 每条外联命令有 host 清单；无通配 `*` | 改为 mock server 或离线 fixture |
| Plugin install acknowledgement | 安装/更新命令是否可复现 | 记录 JSON preview 与 command hash；不用 `-y` 盲签 | 拒绝安装，回滚 plugin dir |
| MCP output normalization | structuredContent/content 策略 | 明确 `structured_first/content_first/content_only/structured_only/both` | 对重复/冲突输出 fail-loud |
| Token/cost telemetry | cached/reasoning token 是否保留 | usage 记录能区分 input/output/cached/reasoning | 不做 FinOps 数字承诺 |

### B. Foundry / Azure Agent POC Gate

| Gate | 检查项 | 通过标准 | SA 落点 |
|---|---|---|---|
| Static reachability | agent subnet → endpoint / DNS / private endpoint | analyzer 或等效脚本输出 read-only report | 部署前发现私网断点，减少 onsite 排障 |
| Runtime probe | diagnostic agent / mock invocation | 记录 trace/session/user identity/tool failure envelope | 架构图上标 Runtime Diagnostics Lane |
| Harness toggle | prompt agent 是否接 Copilot harness / managed harness | 只在测试项目启用；记录版本与 preview caveat | workshop 可演示 harness 切换 |
| Toolbox/MCP identity | public MCP vs private MCP vs Foundry toolbox | 每个工具标注 auth/RBAC/audit/rollback | 技术问答避免把“能连”误说成“可生产” |

### C. Evaluation Gate for UI/Mobile/Workflow Agents

| Gate | 借鉴来源 | 设计要求 |
|---|---|---|
| Reproducible environment | DigiWorld / OpenApps 类 benchmark | 固定 app/task/data seed；每次运行可重建初始状态 |
| Programmatic verifier | DigiWorld verifier | 不只让 LLM 打分；关键任务用二元或结构化 verifier |
| Config perturbation | 3.2M+ configurations 模式（官方 README 自述，未运行验证） | 在 POC 中至少做 3-5 个 seed/主题/状态扰动，防止单例过拟合 |
| Evidence artifacts | screenshots/logs/actions/result.json | 失败样例归档到 EVIDENCE，不凭口头“跑过” |

## 3. 架构图组件库（可复制到 dark-theme SVG/Excalidraw）

```text
[Developer / SA]
   |
   v
[Spec / Goal Contract]
   |-- GitHub Spec Kit: spec -> plan -> tasks -> convergence
   |-- Codex Goals / Cookbook Repair Loop: objective -> review -> repair -> validate
   v
[Coding Agent CLI Control Plane]
   |-- Claude Code: skills | subagents(omitClaudeMd) | workflows | plugin eval
   |-- Codex: AGENTS.md | subagents | hooks | app-server | alpha/stable classifier
   |-- Mistral Vibe: connector/MCP discovery | smart-approve | shell permission CVE fixes
   v
[Policy & Isolation]
   |-- per-command allowed_domains
   |-- plugin command hash accept
   |-- sandbox / workspace roots / denylist
   |-- MCP structuredContent policy
   v
[Azure / Foundry Runtime]
   |-- prompt agents
   |-- MCP tools / Foundry Toolbox
   |-- static reachability analyzer
   |-- runtime diagnostic probes
   v
[Eval & Evidence]
   |-- mobile/UI benchmark fixture (DigiWorld pattern)
   |-- trace + verifier + result.json
   |-- independent review gate
```

## 4. Workshop Exercise Cards [→harness]

1. **Subagent context isolation lab**：同一 toy repo 中放 user/project/local instruction，创建 reviewer subagent；对比加载/不加载 CLAUDE.md 的输出差异。验收：不继承项目提示时仍遵守 managed policy。
2. **Plugin install hash lab**：用无害本地 plugin manifest 生成 `--json` preview，记录 command hash，再用精确 hash 接受；验收：命令变更后旧 hash 失效。安全边界：仅使用隔离临时目录中的自写无外联 manifest；不得从第三方 repo/marketplace 直接安装，不得指向客户真实 plugin dir，不处理 secret/PII。
3. **Codex alpha classifier lab**：抓 stable changelog + npm dist-tag + GitHub alpha release + compare diff，输出四档结论：customer-ready / docs-only / alpha-radar / ignore。
4. **Foundry reachability lab**：用自写/审计过的只读检查器或手工清单分析 mock Bicep/Terraform 网络图，生成 read-only reachability report；验收：DNS/private endpoint/egress 缺口可被静态标出。不得直接运行未知仓库脚本或连接生产订阅。
5. **MCP output duplication lab**：构造同时含 `content` 与 `structuredContent` 的 mock MCP tool result；验证五种策略输出，避免模型看到重复/冲突内容。
6. **Mobile CUA verifier lab**：用 2-3 个假 Android/UI 任务，固定 seed + verifier + screenshots；验收：失败样例能复现并形成 result.json。

## 5. Fail-loud / 不可直接承诺项

- 未运行 Claude Code/Codex/Mistral Vibe CLI；所有 CLI 结论均为 docs/release/diff 级。
- Codex 0.155.0-alpha.6 不是 stable；不得写入客户“可用功能”列表。
- Foundry samples 是样例/commit 级证据，不等同目标租户区域、SKU、Preview 状态可用。
- DigiWorld star 很低（API核 4★/1fork），只作为早期 benchmark 结构来源，不推荐客户生产使用。
- Spec Kit star 很高但仍需供应链审计后才能在客户环境安装；原研究快照中只读 README，未运行工具。
