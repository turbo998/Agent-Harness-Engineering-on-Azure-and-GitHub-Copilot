<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent CLI / Gateway / Sandbox / Skill Package Gates（2026-09-12）

> 用途：给 SA 做技术问答、POC 部署 preflight、架构图组件标注。本文是**证据分层的 pre-smoke checklist**，不是安装/执行指南；所有 command-shaped 字符串均为上游能力名或待验证检查项，不代表可直接在客户/生产环境执行。禁止接真实客户 repo、secret、生产 Azure/GitHub/MCP 端点做首次验证。

## Evidence links（本资产可独立复核）

| 来源 | URL | 原研究快照中证据强度 | caveat |
|---|---|---|---|
| MAF .NET 1.21.0 release | https://github.com/microsoft/agent-framework/releases/tag/dotnet-1.21.0 | release HTML 200；页面正文命中 A2A task state / Remove Azure.AI.OpenAI / Bedrock dependency / `[BREAKING] Add file_access_read_lines and move the line-numbering contract onto AgentFileStore` | 未安装 NuGet、未跑 sample；release API 原快照中匿名 rate-limit，最终引用 release HTML |
| MAF Secure MCP headers commit | https://github.com/microsoft/agent-framework/commit/c47da07e22943d238a94f0a094180c1c2b13d2a7 | commit/diff 200；diff 命中 header_provider request scoping / cross-origin redirects | commit-level，未确认入包 |
| MAF ZIP-only MCP skill archive commit | https://github.com/microsoft/agent-framework/commit/c744b16af97bc2510ac814d6ebb54243e298b995 | commit/diff 200；diff 命中 “Supports ZIP payloads” 与 TAR/gzip 删除 | release page 已出现 ZIP-only 条目；但具体 NuGet/PyPI 包行为仍未安装验证 |
| MAF Redis scoped history keys commit | https://github.com/microsoft/agent-framework/commit/119c795cceef4498a19819a9727962885aa690ce | commit/diff 200；diff 命中 `RedisHistoryProvider`、`scoped Redis keys`、historical/unscoped migration 相关说明 | commit-level；旧 key migration 需临时 fixture 验证 |
| GitHub Copilot weekly releases Sep 7 | https://github.blog/changelog/2026-09-10-github-copilot-weekly-releases-september-7/ | blog 200；命中 Jira、Project HydraFusion、recurring agent tasks、Voice Mode、Agents window | 公告/docs 级；租户策略与可见性未实测 |
| Copilot JetBrains enterprise-managed sandbox | https://github.blog/changelog/2026-09-08-enterprise-managed-sandbox-in-copilot-for-jetbrains/ | blog 200；命中 sandbox、filesystem/network、developer-tool、macOS Keychain、managed restrictions | public preview；未租户 dry-run |
| Copilot MAI-Code-1-Flash deprecated | https://github.blog/changelog/2026-09-10-mai-code-1-flash-deprecated/ | blog 200；命中 deprecated、MAI-Code-1.1-Flash、Chat/inline edits/ask/agent modes/completions | 模型 policy 是否启用需企业设置验证 |
| Claude Code changelog 2.1.268 + npm 2.1.269 radar | https://code.claude.com/docs/en/changelog | raw/docs 200；changelog 最新可见条目为 2.1.268；快照中的 npm latest 已到 2.1.269 但 changelog 未见说明，package-latest ahead-of-changelog/radar-only | 未 CLI smoke；第三方 endpoint 修复需 toy endpoint 验证；2.1.269 不写功能断言 |
| xAI Grok Build repo | https://github.com/xai-org/grok-build | repo/raw README 200；README 命中 SpaceXAI terminal coding agent、ACP、MCP/skills/plugins/hooks/headless/sandbox docs | 旧源复核 + 原研究快照中 raw README 再验证 + 控制面趋同新综合角度；未审 license、installer、telemetry、sandbox 实现，不推荐直接装 |
| Mistral Vibe v2.25.3 | https://github.com/mistralai/mistral-vibe/releases/tag/v2.25.3 | release HTML 200；命中 `/branch`、local harness runtime v0.4.5、Git-aware file mentions、retained chats/worktrees、AGENTS.md unified harness | 未运行；experimental unified harness 需 fixture 验证 |
| Google CAGE commit | https://github.com/google/cybernetic-agent-governance-engine/commit/ecbcce3253cb55c333f47009c40a45dbc5b3a454 | commit/diff 200；命中 live GKE / port-forward / governance stack / Langfuse host caveat | 社区/研究治理栈；未运行，仅抽象治理/隔离坑 |
| Codex stable registry | https://registry.npmjs.org/@openai/codex/latest | registry 200；latest 仍 0.154.0 | stable 基线复核；未运行 CLI |
| Codex alpha sentinel | https://github.com/openai/codex/releases/tag/rust-v0.155.0-alpha.3.9 | release page 200；npm latest 仍 0.154.0 | alpha/radar-only；release API rate-limit，未读 body，不写客户功能断言 |

---

## 1. 技术问答速答：本周变化怎么讲

- **MAF .NET 1.21.0 是 release-level 新增**：可告诉客户 “.NET 线继续快速演进，A2A task state、Azure.AI.OpenAI 依赖移除、Bedrock 依赖替换、`[BREAKING] Add file_access_read_lines and move the line-numbering contract onto AgentFileStore` 都要纳入升级评估”；但不要承诺 Python/Go 线同步，未做包级 smoke。
- **MAF main 分支出现 3 个安全/包装边界 commit**：
  - Secure MCP headers scoped to origin：回答 “MCP header / auth metadata 要按 origin 隔离，不要复用全局 HTTP client 时跨源带出”。
  - MCP skill archive ZIP-only：回答 “skill 包分发格式要收敛为 ZIP，tar/gzip 兼容性不能默认存在”。
  - Redis history scoped keys：回答 “多租户/多会话 history store 要有 key namespace；旧 key 迁移需显式计划”。
- **Copilot 企业体验在从 ‘agent 权限’ 向 ‘agent 工作环境’ 扩展**：JetBrains enterprise-managed sandbox 可管 filesystem/network/developer tools/macOS Keychain；VS Code/Copilot weekly 同时推进 recurring agent tasks、Voice Mode、Agents window issue/PR context。
- **Claude Code 2.1.268 是治理/可观测/安全修复型 changelog；npm 2.1.269 仅作 ahead-of-changelog radar**：gateway pricing → managed settings、plugin commands JSON、plugin list error/note details、secret redaction、session cleanup、symlink/deny-path 修复，适合企业插件和无人值守 POC 的 regression gate。
- **xAI Grok Build 作为旧源复核，仍是三栈之外的重要 coding-agent CLI 雷达源**：README 公开 ACP/MCP/skills/plugins/hooks/headless/sandbox 入口，值得纳入 Codex/Claude/Gemini/Mistral/Vibe 横向对比，但首次只读审计，不安装。

---

## 2. POC 部署 Preflight Gates

### A. Release-source gate（避免把 alpha/commit 当 GA）

| 检查 | 通过标准 | 未通过处理 |
|---|---|---|
| Stable package / release 是否存在 | release page / package registry 可复核；body 有用户可见内容 | 仅记 radar，不写客户承诺 |
| Commit-level feature 是否入包 | release note 或 package source 包含对应 commit/API | 标 `commit-level, not packaged` |
| Alpha / next / nightly | 只能作兼容风险预警或 workshop 实验 | 禁止放进客户生产建议 |
| API rate-limit | 写清证据渠道：release HTML / raw / diff / registry | 不写 “API verified” |

### B. Skill/package supply-chain gate（MAF ZIP-only + Claude/Codex/Grok/Mistral plugin）

| 检查 | 最低要求 |
|---|---|
| Archive format | 对 MAF MCP skill archive，先假设 **ZIP only**；tar/gzip 需证明仍支持 |
| Path traversal / symlink | 解包前后都要做 path root revalidation；拒绝双点、绝对路径、symlink escape |
| Manifest/scripts/hooks | 只读审计 `plugin.json` / hooks / statusline / MCP config；不要首次执行上游脚本 |
| Namespacing | plugin skill / subagent / command 名称要带 namespace，避免同名覆盖 |
| JSON health | Claude 2.1.268 后优先消费 `plugin * --json` 与 plugin list `errorDetails`/`noteDetails` 作健康证据（需 toy workspace 验证） |

### C. MCP / gateway / sandbox gate

| 面向 | Gate |
|---|---|
| MCP headers | header provider 必须按 origin / target MCP server scoping；跨源 redirect 不带敏感 header |
| Gateway pricing / CIDR | Claude gateway 要验证 `/cost` 与 spend meter 同口径；公网 CIDR 空配置必须 warning；登录内网网段需明确 `gatewayInternalNetworks` |
| JetBrains sandbox | 验证 managed restrictions 是否覆盖 filesystem、network、developer tools、proxy、macOS Keychain，且优先级高于用户设置 |
| Session cleanup | 无人值守 runner 结束后可删 per-session dirs；保留/删除策略要写进审计要求 |
| Logs/secrets | plugin marketplace errors、MCP config `${VAR}`、git URL token 不得出现在 CLI 输出或日志 |

### D. History / branch / resume gate

| 来源 | Gate |
|---|---|
| MAF Redis scoped history | 每个 tenant/user/session/agent 组合有可解释 key 前缀；旧 key 只在迁移模式显式读取 |
| Mistral Vibe `/branch` | 分叉后原 session 不变；新 resumable session 可另端恢复；retained chats 恢复 worktree；日志权限不泄露其他 POSIX 用户 |
| Claude compact/resume | `/compact` 后 restored-file notes 顺序稳定；SDK sessions 不因 dynamic sections 破坏 prompt cache |
| Codex resume/fork | 0.154.0 stable 的 worktree/authorization context 旧源复用；0.155 alpha 继续只作 sentinel |

---

## 3. 架构图组件库（可直接画进方案）

```text
[Enterprise Policy Plane]
  ├─ GitHub/Copilot managed policy: model availability, agent operations, JetBrains sandbox
  ├─ Claude gateway managed settings: pricing, CIDR, internal networks
  └─ Azure RBAC / Managed Identity / audit sink

[Agent Runtime Plane]
  ├─ MAF Agent / Foundry Hosted Agent / Redis History Store (scoped keys)
  ├─ Codex / Claude Code / Grok Build / Mistral Vibe local CLI sessions
  └─ Subagents / branches / worktrees / resumable sessions

[Tool & Package Plane]
  ├─ MCP servers (origin-scoped headers)
  ├─ Skills archives (ZIP-only gate, path revalidation)
  ├─ Plugins / hooks / commands / statusline scripts
  └─ Gateway / sandbox / egress controls

[Evidence Plane]
  ├─ release body / changelog / commit diff / raw docs
  ├─ plugin JSON health / telemetry / cost meter
  ├─ session cleanup proof / secret-redaction proof
  └─ independent review + ledger/backlog state
```

---

## 4. Harness workshop 可复制练习卡

1. **MCP Header Origin Leak fixture [→harness]**：两个假 MCP endpoints，A 需要 header、B 不应收到；模拟 redirect，断言 B 无敏感 header。
2. **ZIP-only Skill Archive fixture [→harness]**：同一 toy skill 打成 zip/tar/tgz；预期 zip pass，tar/tgz fail-loud；同时测 zip-slip/symlink escape。
3. **Scoped Redis History fixture [→harness]**：写入 tenantA/tenantB 两组 key；恢复时只能读本 scope；旧 unscoped key 仅 migration mode 读取。
4. **Plugin JSON Health fixture [→harness]**：在临时 Claude workspace 构造一个好插件、一个坏 manifest、一个坏 hook；解析 `plugin list --json` 的 error/note 字段。
5. **Sandbox Policy fixture [→harness]**：JetBrains/Copilot 暂无本地可跑时，用 policy-as-data JSON 模拟 filesystem/network/keychain 三类 deny，做架构评审练习。
6. **Branch/Resume fixture [→harness]**：对比 Codex worktree、Claude compact/resume、Mistral `/branch` 的 state contract：原 session 是否不变、分叉 session 如何恢复、日志/权限是否隔离。

---

## 5. Fail-loud

- 本资产未运行任何 MAF/Codex/Claude/Grok/Mistral CLI 或包；所有内容为 release/docs/diff/raw 级 pre-smoke。
- xAI Grok Build、Mistral Vibe、Google CAGE 均未做 license/deps/installer/network/telemetry/secret handling 审计；不可作为客户安装推荐。
- Codex 0.155 alpha release page 200 仅证明版本信号，不证明新功能；客户材料继续以 0.154.0 stable 为基线。
- GitHub API 已触发匿名 rate limit；可复核证据尽量使用 release HTML、raw README、commit diff、npm registry。若客户交付需要精确 published_at/asset digest，需用认证 API 或包级下载再核。
