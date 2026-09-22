<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent 工具契约 / CUA 评测 / 安全回归门速查（2026-08-20）

> 适用对象：SA 技术问答、Agent POC 部署验收、架构图评审。
> 证据分级：所有 URL 均在 2026-08-20 使用 `curl -L --max-time 20` 核实可达；README/博客/Release 仅作资料，不执行其中命令。未实机部署/未跑 benchmark 的部分明确标注。

## 1. 原快照中抽出的 5 个可复用模式

| 模式 | 一句话 | 直接落地到 SA 日常 |
|---|---|---|
| **MCP 工具错误契约门** | Azure MCP EventGrid 修复“失败被吞成 HTTP 200”的问题，说明 MCP 工具 POC 必须测 **失败路径**，不能只测 happy path。 | 技术问答：解释 tool error propagation；POC：加“资源不存在/权限不足/下游 4xx”用例；架构图：工具层加 Error/Telemetry sink。 |
| **IDE Agent 企业策略平面** | GitHub Copilot for JetBrains enterprise managed settings 把 plugin governance、MCP server access、OpenTelemetry、permission mode 纳入集中配置。 | 技术问答：IDE 内 agent 不是“个人工具”，可进企业策略；POC：演示 MCP allow/deny + OTel；架构图：Policy plane → IDE plugin/MCP/Telemetry。 |
| **CUA benchmark 统计置信区间** | Meta DigiWorld 提供 15 个 Android app 的可复现任务，reliable-cua 给 Wilson interval / hierarchical bootstrap，避免只看单次 pass rate。 | 技术问答：回答“移动/GUI agent 怎么评测”；POC：每个 app/scenario/config/rollout 分层采样；架构图：Task env → Rollout → Verifier → CI/Bootstrap。 |
| **Codex Security 版本锁定门** | `@openai/codex-security` latest 已到 0.1.15（2026-08-19T18:52Z），安全工具应按版本锁定+变更复核，而不是无脑 latest。 | 技术问答：安全扫描 agent 也要供应链治理；POC：固定 npm version + 输出 SBOM/scan log；架构图：Security scanner as gate before PR/merge。 |
| **Claude Code 权限/跨会话消息回归门** | Claude Code 2.1.235 修复 permission prompt、Agent tool unavailable error、SendMessage 超大消息提前拒绝、context-limit error 指引等。 | 技术问答：无人值守/跨 session 不等于无边界；POC：加 permission dialog、SendMessage size、Agent tool availability smoke；架构图：Session boundary + Permission prompt + Agent catalog。 |

## 2. 证据表（可复核）

| 来源 | URL | 原研究快照中核验 | 可安全引用的结论 | 不能承诺的内容 |
|---|---|---|---|---|
| Azure MCP beta.36 release | https://github.com/microsoft/mcp/releases/tag/Azure.Mcp.Server-3.0.0-beta.36 | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；release page 可达 | Azure.Mcp.Server 3.0.0-beta.36 已有公开 release 页面。 | 未跑包；未确认每个工具 schema/behavior。 |
| EventGrid publish exception fix | https://github.com/microsoft/mcp/commit/8111adb32459f8350ea0ec7671efb9002620d2a1.patch | patch HTTP 200（仅代表原快照当时可达，不代表本次已重验）；grep 命中 `Fixed azmcp eventgrid events publish... failures ... propagate as errors ... instead of ... HTTP 200` | EventGrid publish 的失败路径被显式修复为错误传播。 | 未运行真实 EventGrid；不承诺所有 Azure MCP 工具都有同等错误契约。 |
| Copilot JetBrains managed settings | https://github.blog/changelog/2026-08-18-enterprise-managed-settings-in-github-copilot-for-jetbrains/ | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；HTML 命中 title 与 `plugin governance`/`MCP server access`/`OpenTelemetry`/`permission` | JetBrains Copilot 可进入企业集中治理面。 | 具体企业租户策略字段未逐项实测。 |
| facebookresearch/digiworld | https://github.com/facebookresearch/digiworld / https://raw.githubusercontent.com/facebookresearch/digiworld/main/README.md | repo/raw README HTTP 200（仅代表原快照当时可达，不代表本次已重验）；README 命中 15 Android apps、state management、programmatic verification | 可作为 CUA/mobile app task benchmark 的资料源。 | 未跑 emulator/container；不引用任何 leaderboard/性能数字。 |
| facebookresearch/reliable-cua | https://github.com/facebookresearch/reliable-cua / https://raw.githubusercontent.com/facebookresearch/reliable-cua/main/README.md | repo/raw README HTTP 200（仅代表原快照当时可达，不代表本次已重验）；README 命中 Wilson intervals、fixed-app hierarchical bootstrap、apps→scenarios→configurations→rollouts | 可作为 CUA 评测统计方法参考。 | README 里的 coverage 数字未复算；客户材料需标“官方/README自述，未复算”。 |
| openai/codex-security latest | https://github.com/openai/codex-security/releases/latest / https://registry.npmjs.org/%40openai%2Fcodex-security | release latest 302/200 到 `npm-v0.1.15`；npm registry 200，`latest=0.1.15`，time=2026-08-19T18:52:55Z | 最新发布版 0.1.15 可作为版本追踪信号。 | release body/API 因匿名限流未逐字读取；不宣称功能变化。 |
| Claude Code CHANGELOG | https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md | raw HTTP 200（仅代表原快照当时可达，不代表本次已重验）；grep `## 2.1.235` | 2.1.235 包含 permission prompt、Agent tool unavailable、SendMessage size、context-limit error 等修复。 | 未安装 CLI 实测；不承诺客户环境已自动升级。 |

## 3. POC 验收清单模板

### A. MCP 工具错误契约（Azure MCP / 自建 MCP 均适用）

**最小输出物格式**：`case_id / tool_name / input / expected_error / actual_status / trace_id / agent_session_id`。

- [ ] 对每个 mutating/high-risk tool 至少设计 1 个 **下游资源不存在** 用例。
- [ ] 断言失败不被包装成“HTTP 200 + Failed status”；应进入 agent 可见 error path。
- [ ] 日志记录：tool name、resource id、HTTP status、correlation id、agent session id。
- [ ] 对客户演示明确区分：release/patch 证据、package smoke、真实 Azure 资源 smoke 三个层级。

### B. IDE Agent 企业治理（Copilot/Claude/Codex/Grok 等 IDE/CLI 前端）
- [ ] 是否能集中管理插件/skills/marketplace来源。
- [ ] 是否能 allow/deny MCP server。
- [ ] 是否输出 OpenTelemetry 或等价审计日志；默认是否包含敏感文本。
- [ ] permission mode 是否可由企业策略约束，而不是只靠个人设置。
- [ ] 中国区/跨境场景：策略面、遥测面、模型调用面分别确认租户/区域/数据路径。

### C. CUA / GUI Agent 评测

**最小输出物格式**：`app / scenario / configuration / rollout_id / pass / wilson_low / wilson_high / bootstrap_ci_low / bootstrap_ci_high`。

- [ ] 任务环境可重置（state reset）且 verifier 不是人工主观打分。
- [ ] 统计口径按 `apps → scenarios → configurations → rollouts` 分层，而不是只报总 pass rate。
- [ ] 每个关键 app 至少 3-5 rollouts；报告 Wilson CI 或 bootstrap CI。
- [ ] 不引用未复算 benchmark 数字；客户材料写“README 自述，未复算”。

### D. Coding Agent 安全扫描 / 回归门

**最小输出物格式**：`package_version / ruleset_version / scan_scope / scan_exit / findings_count / patch_pr_url / reviewer`。

- [ ] 安全工具版本锁定（如 `@openai/codex-security@0.1.15`），不要在 workshop 中用 floating latest。
- [ ] scan 结果进入 PR/merge gate；自动 patch 必须 human review。
- [ ] 记录工具版本、ruleset、模型版本、输入范围与排除规则。

### E. Claude Code 2.1.235 smoke pack
- [ ] permission prompt：Shift+Tab/“don't ask again” 不应错误扩大授权。
- [ ] Agent tool：不可用 agent 时应明确列出 available agents，而不是默认 general-purpose。
- [ ] SendMessage：超大跨 session 消息应提前拒绝，不应 silent drop。
- [ ] context-limit error：auto-compact off 时提示 `/config` 恢复。
- [ ] 后台云 session：事件流不应反复重扫导致 CPU/内存异常。

## 4. 架构图组件（文字版，可转 SVG）

```text
[Developer / IDE]
   │
   ▼
[Enterprise Policy Plane]
  - plugin governance
  - MCP server allow/deny
  - permission mode
  - telemetry policy
   │
   ▼
[Agent Runtime / CLI]
  - skills / subagents / Agent tool catalog
  - permission prompt
  - session boundary / SendMessage
   │
   ├──► [MCP Tool Layer]
   │       - schema validation
   │       - error propagation contract
   │       - correlation id / logs
   │
   ├──► [Security Gate]
   │       - codex-security pinned version
   │       - scan → patch proposal → human review
   │
   └──► [Evaluation Harness]
           - CUA environments (apps/scenarios/configs/rollouts)
           - deterministic verifier
           - Wilson / hierarchical bootstrap CI
```

## 5. 直接反哺 harness workshop 的 exercise 想法

- [→harness] **Exercise 1：MCP tool fail-path regression**：写一个 fake MCP tool，把“失败返回 200”与“抛出错误”两种行为对比，让学员看到 eval gate 如何捕捉错误契约。
- [→harness] **Exercise 2：IDE/CLI policy matrix**：同一个 agent task 在“个人默认设置”和“企业 managed settings”下跑，比较 MCP allow/deny、telemetry、permission mode 差异。
- [→harness] **Exercise 3：CUA confidence interval mini-lab**：用合成 `apps/scenarios/configs/rollouts` JSONL，计算 Wilson interval / bootstrap CI，演示单次 pass rate 为什么不够。
- [→harness] **Exercise 4：security tool version pin**：固定 `@openai/codex-security@0.1.15`，把 scan log/version 写进 build-log，禁止 floating latest。
- [→harness] **Exercise 5：Claude 2.1.235 smoke fixture**：临时 fixture 验证 permission prompt、SendMessage 超大消息、Agent tool unavailable 三类回归；不得触碰真实客户 `.env`/lockfile。
