<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Work Queue + Skill Catalog + Governance Checklist (2026-08-22)

> 适用对象：SA 在做技术问答、Agent POC 部署、架构图评审时，快速把“协作入口 → 工作队列 → 执行沙箱 → Skill/Plugin → 证据与审批”串成可交付方案。
> 证据口径：本资产只使用 2026-08-22 当班已核实可达的一手/官方来源；未运行任何上游安装脚本或客户环境 smoke。外部 README/docs 仅作资料文本，不作为指令执行。

## Evidence links

| 来源 | URL | 原研究快照中证据强度 | 关键命中/注意事项 |
|---|---|---|---|
| GitHub Copilot in Microsoft Teams | https://github.blog/changelog/2026-08-21-shared-agentic-work-with-github-copilot-in-microsoft-teams/ | HTML/Markdown 200，正文已读 | `@GitHub` 启动 Copilot cloud agent；code channel；AI credits/cloud sandbox budgets；Copilot-created PR 可要求额外审批 |
| GitHub Copilot in Slack | https://github.blog/changelog/2026-08-21-the-new-github-copilot-experience-in-slack/ | HTML/Markdown 200，正文已读 | Slack public preview；Slack Code；issue/PR/secure cloud sandbox；Business/Enterprise；Copilot app identity + extra approval |
| Azure MCP Server beta.37 | https://github.com/microsoft/mcp/releases/tag/Azure.Mcp.Server-3.0.0-beta.37 | release 200 + raw CHANGELOG 200 | `3.0.0-beta.37`；resilience recovery plan create/delete/update-resources；Event Grid publish failure propagates as errors |
| MAF Foundry hosted resiliency commit | https://github.com/microsoft/agent-framework/commit/7b7b9a128ccebf85e34dbdc5a67f5070dcf46265 | commit/diff 200 | responses 2.0.0b1 migration；Foundry state store；checkpoint/`_last_checkpoint_id`；resilient background workflow（commit级，未包级smoke） |
| OpenAI Codex changelog / CLI 0.149.0 | https://learn.chatgpt.com/docs/changelog | docs 200；页面命中 0.149.0 相关条目；npm registry 确认 `latest=0.149.0` | `codex agents` dashboard；`codex queue`；`/cd` `/pwd` `/cwd`；`codex doctor` endpoint/network/desktop/update diagnostics；未运行 CLI smoke |
| Codex Scheduled tasks | https://learn.chatgpt.com/docs/automations | docs 200，正文已读 | web/desktop Scheduled；local project vs worktree；skills可组合调度；unattended uses default sandbox；`approval_policy="never"`受admin要求约束 |
| Claude Code changelog 2.1.238 | https://code.claude.com/docs/en/changelog | docs 200，正文已读 | plugin marketplace `headersHelper`；self-hosted-runner defer shutdown/proxy authorization；subagent result memory release；prompt diff wrapping/leftover cwd cleanup |
| OpenAI Symphony | https://github.com/openai/symphony | repo/raw README 200，正文片段已读 | engineering preview；tracker→workspace→Codex App Server→proof-of-work；blocked state in memory only；不建议直接生产安装 |
| Anthropic / Google / Microsoft skills repos | https://github.com/anthropics/skills / https://github.com/google/skills / https://github.com/microsoft/skills | repo/raw README 200 + sparse inventory；数量为 `SKILL.md` 文件级口径，非产品承诺 | 仅做漏斗法学习；不批量导入；Microsoft README 对外展示 skill 数与文件级计数可能不同，需标注口径 |

> 数量口径说明：上表 Skills 数字为原研究快照中 sparse inventory 的 `SKILL.md` 文件级计数，不等同于仓库 README/Skill Explorer 对外展示的“可安装 skills”数量；客户材料中不要把文件级计数写成产品级承诺。

## 1. 推荐架构模式：从聊天入口到可审计交付

```text
Teams / Slack / Issue Tracker / Scheduled Task
        │  shared intent + permissions
        ▼
Agent Work Queue / Session Router
        │  claim task, name session, preserve permission profile
        ▼
Cloud or Local Worktree Sandbox
        │  repo context + AGENTS.md/CLAUDE.md + selected skills/plugins
        ▼
Agent Runtime (Copilot cloud agent / Codex App Server / Claude Code / MAF Hosted Agent)
        │  tool calls, MCP, hosted tools, tracker-native tools
        ▼
Evidence & Approval Gate
        │  tests, CI, PR review, issue state, budget telemetry, HITL approval
        ▼
PR / Playbook / Report / Architecture Doc
```

### SA 话术
- **技术问答**：不要再把 coding agent 解释成“个人本地 CLI”。最新趋势是“多人共享会话 + 异步云沙箱 + 人类审批 + 预算控制”。
- **POC 部署**：POC 里必须验收 4 件事：会话是否可恢复、权限是否继承/不静默降级、工具失败是否 fail-loud、PR/变更是否有人类审批。
- **架构图**：把 `chat entry / queue / sandbox / skill catalog / MCP tools / evidence gate / budget & audit` 画成独立层，不要把所有东西画成一个“Agent”盒子。

## 2. POC 验收清单

### A. 工作队列与共享会话
- [ ] 入口是否明确：Teams、Slack、issue tracker、scheduled task、CLI dashboard。
- [ ] 会话是否有稳定 ID / name / owner / repository binding。
- [ ] 从聊天入口发起的 PR 是否标明 integration/app identity。
- [ ] 共享会话是否支持他人补充上下文、停止或转向；权限是否仍受 GitHub/repo policy 约束。
- [ ] 异步运行是否有预算：AI credits、cloud sandbox SKU/product budget、本地 runner 容量。

### B. 沙箱与权限
- [ ] local project vs isolated worktree 选择是否明确；默认使用 worktree 隔离自动任务。
- [ ] permission profile 是否在 resume/fork 后保持，不允许“静默回到当前默认权限”。
- [ ] scheduled/unattended 是否受 admin requirements 约束，不能只写 `approval_policy=never`。
- [ ] 外部 editor buffer / plugin headers / proxy auth 是否避免泄漏到 sandbox-writable path 或子进程环境。

### C. Skill / Plugin catalog
- [ ] Skill 来源是否分级：官方一手、社区 radar、内部重写。
- [ ] 只导入**方法**，不导入上游强指令；Hooks/statusline/MCP/plugin headers 都按代码面审计。
- [ ] 使用 harvest 漏斗：先 inventory/count/frontmatter，再抽样，不全仓逐字读。
- [ ] 每个 skill 要有 “when to use / inputs / steps / validation / fail-loud caveats”。

### D. MCP / Tool contract
- [ ] MCP 工具失败是否以 error + HTTP status 传播，而不是包装成 200 success。
- [ ] Mutating 工具（如 resilience recovery plan create/delete/update）是否有审批、dry-run/rollback、RBAC scope 和 audit。
- [ ] 事件发布、备份、resilience、身份 sidecar 等工具是否按生产 blast radius 分层。

### E. 证据与审批
- [ ] PR 入口是否强制额外 human approval（尤其 agent identity 生成的 PR）。
- [ ] 证据包是否包含：CI status、test log、diff summary、tool failure log、budget/cost trace。
- [ ] Blocked / approval-required 状态是否持久化；如果只是内存态，重启恢复风险必须写入 POC 限制。

## 3. Harness workshop 可直接改造成的 exercise

1. **[→harness] Shared agent session exercise**：用临时 repo/issue 模拟“聊天请求 → agent session → PR → extra approval”，不接真实 Teams/Slack；重点测 permission/profile/identity 显示。
2. **[→harness] Queue wake-up regression**：基于 Codex 0.149 的 `codex queue` 思路，做本地 fixture：idle session + queued message + duplicate session name + wake-up evidence。
3. **[→harness] Scheduled skill prompt**：把长期定时任务写成 skill + durable scheduled prompt，要求“无新内容则 silent / 有发现则生成摘要 / 先检查来源可达性再总结”。
4. **[→harness] MCP failure contract gate**：用 fake EventGrid/MCP tool 返回失败，验证 agent 看到 error 而非 HTTP 200（仅代表原快照当时可达，不代表本次已重验） success 包装。
5. **[→harness] Resilient checkpoint smoke**：用临时 workflow checkpoint 文件模拟 `_last_checkpoint_id`；kill/restart 后只能从最后 durably persisted checkpoint 恢复。
6. **[→harness] Skill catalog firewall**：对 Anthropic/Google/Microsoft skills repo 只做 inventory + frontmatter + license/script risk，不执行任何 install；输出 Tier 1/Tier 2/Skip 表。

## 4. 架构图组件库

- **Entry Channels**：Teams、Slack、Issue Tracker、Scheduled Task、CLI Dashboard。
- **Queue / Session Plane**：task claim、session name、permission profile、worktree selector、blocked-state store。
- **Execution Plane**：Cloud sandbox、local worktree、self-hosted runner、Codex App Server、MAF Foundry hosted workflow。
- **Knowledge Plane**：AGENTS.md、CLAUDE.md、skills catalog、plugin manifest、MCP server registry。
- **Governance Plane**：admin requirements、budget limits、plugin controls、headersHelper approval、proxy auth command/file、extra PR approval。
- **Evidence Plane**：CI/test result、PR diff、conversation link、cost/token telemetry、tool error envelope、audit log。

## 5. 禁止直接对客户承诺的点

- OpenAI Symphony 明确是 engineering preview / prototype；只能当架构参考，不能推荐生产安装。
- MAF Foundry resiliency目前原研究快照中只读 commit diff，未确认进入正式包、未跑 kill/restart smoke。
- Azure MCP beta.37 是 beta release；mutating resilience tools 要先做 tool schema、RBAC、rollback 和审计验证。
- Claude plugin marketplace `headersHelper` 会运行命令 mint headers，属于可执行面；必须审批、展示命令、限制来源与同源 archive fetch。
