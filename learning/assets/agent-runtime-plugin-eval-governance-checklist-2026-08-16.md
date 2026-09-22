<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Runtime / Plugin / Eval 治理速查（2026-08-16）

> 用途：给 SA 在客户技术问答、POC 方案和架构图评审时复用。覆盖原研究快照中新增/新角度来源：GitHub Copilot weekly release（Copilot CLI `/tasks` / `--plan --mode autopilot`）、Claude Code 2.1.233 与 Enterprise skill/plugin scanning、OpenAI Model Spec Evals、Salesforce MCPEval；Codex build-skills / changelog 作为已覆盖官方基线复核，不标新发现。
>
> 证据等级：`file/readme` = 已读 README/raw/release body；`docs-snippet` = 文档页面可达并抓取关键片段；`url-only` = 仅 URL 可达，不能支撑细节断言。

## 1. 三层治理模型（架构图可直接套）

```text
Developer / Maker
   |
   v
Agent client/runtime
(Copilot CLI / Claude Code / Codex / Copilot Studio / MAF hosted agent)
   |
   +-- A. Package & policy gate
   |      - plugin.json / skills/ / mcp.json / marketplace
   |      - managed settings / strict marketplace / scan pass-warn-fail
   |
   +-- B. Execution & resource gate
   |      - subagent/task queue, plan/autopilot, background agents
   |      - sandbox, cgroup memory limit, WebFetch TTL, cross-session messaging
   |
   +-- C. Eval & release gate
          - expected response graders, Model Spec compliance, MCP task eval
          - smoke tests, replay, statistical comparison, human review packet
```

**SA 落点**：客户问“能不能让 coding agent 自主跑？”不要只回答“能”。应拆成：
1. 包从哪里来、谁批准、是否可扫描；
2. 运行时资源/网络/会话边界如何控；
3. 输出如何用测试集、grader、replay 与 human review packet 验收。

---

## 2. 插件 / Skills 准入清单

| 检查项 | 最小要求 | 证据来源 | SA 用法 |
|---|---|---|---|
| Package manifest | Agent Plugins 1.0 / Copilot 侧：`plugin.json` + `skills/` + 可选 `mcp.json`；Copilot 特有命令/规则/hooks 放 namespaced 目录，不把平台私货混进通用层 | GitHub Changelog Agent Plugins 1.0（docs-snippet；08-14已作为复核覆盖，原研究快照中只复用） | 画“一个包，多客户端”的分发图；提醒客户不要把 Claude/Codex/Copilot 的字段混写成无治理包 |
| Marketplace trust | 企业市场要有 allowlist / strict known marketplaces / team override；未知社区市场只作 radar，不直接安装 | GitHub Changelog / Claude plugin-marketplaces 旧基线 | 给客户出 POC 前置项：内部 marketplace 或固定 commit/ref；禁止随意 `latest` |
| Skill/plugin scanning | Enterprise 扫描结果通常是 pass/warn/fail；扫描不等于覆盖 hooks/MCP/已有安装与所有合规场景 | Claude Help: skill/plugin scanning（docs-snippet，历史快照） | 技术问答话术：扫描是准入门，不是安全承诺；仍需人工审查可执行面；覆盖边界需以当前官方文档与租户实测为准，未实测前只作为准入设计参考 |
| Codex skill invocation | Codex `agents/openai.yaml` 可用 `policy.allow_implicit_invocation: false` 降低误触发；核心 skill 仍应保持单一职责、显式输入输出 | OpenAI Codex build-skills（旧源复核；docs-snippet） | [→harness] 给 workshop 的 `$skill` 显式触发模板；避免高风险 skill 被自然语言误路由 |
| Executable surfaces | hooks、MCP server、statusline、command source、脚本依赖、网络目标、secret 输出均按代码审计 | 多源综合 | 架构图上把“skill markdown”与“executable hook/MCP”画成不同风险等级 |

### POC 准入模板

```yaml
plugin_intake:
  source: internal_marketplace | pinned_repo | local_zip
  version_pin: commit_sha_or_semver_required
  manifest_checked: true
  skills_checked:
    - trigger_description_is_narrow
    - no_secret_echo
    - supporting_scripts_reviewed
  mcp_checked:
    - server_url_or_command_allowlisted
    - auth_scope_documented
    - destructive_tools_have_hitl
  hooks_checked:
    - no_unbounded_shell
    - timeout_defined
    - failure_mode_fail_closed
  scan_result: pass | warn | fail | not_available
  residual_risk_notes: "扫描未覆盖 hooks/MCP/既有安装；需人工复核"
```

---

## 3. 运行时 / 会话安全回归清单

| 场景 | 原研究快照中新信号 | 为什么重要 | 可执行检查 |
|---|---|---|---|
| Copilot CLI 多 agent | Weekly release 提到 `/tasks` 管理 subagents/tasks、运行中可 queue prompts/shell/slash commands、`--plan` + `--mode autopilot` headless 先产计划再执行 | Coding agent 从单线程 chat 走向后台任务面板；客户 POC 需要把“任务排队/取消/回滚”纳入验收 | 建 POC 时要求：列出任务状态、取消/恢复/重放方式、日志归档路径；不要只看最终 PR |
| Claude Code 2.1.233 Bash 资源 | 新增 Linux Bash tool memory cgroup 环境变量 `CLAUDE_CODE_TOOL_MEMORY_LIMIT` | runaway build/test 不能拖死整个 session；适合 CI/runner 场景 | smoke test：跑内存压力小脚本，确认超限失败可见且不破坏会话 |
| Claude WebFetch cache | `CLAUDE_CODE_WEBFETCH_CACHE_TTL_MS` 可调 session URL cache TTL（默认15分钟未变） | 外部文档频繁变化时，缓存 TTL 会影响“已核实”结论 | 客户资料检索 POC 需要注明 TTL 与重新抓取策略 |
| Claude cross-session | 2.1.232 起 subagent fork 默认、`@` mention/SendMessage 跨会话；2.1.233 继续修 Remote Control/后台 agent 等 | 会话间消息是新攻击面：误投递、名称碰撞、权限继承、审计缺口 | [→harness] smoke test：同名 session、拒收/hold/accept 策略、跨会话消息是否写入审计 |
| Sandbox / path hardening | 2.1.233 修 Bash redirection permission、socket tmp symlink、protected path bypass、project settings 覆盖 sandbox.ripgrep 等 | 说明运行时安全在高频补丁中变化；升级必须带 regression 表 | 升级清单：Bash `< file`、symlink、project config 覆盖、Git token redaction、MCP reconnect |

---

## 4. Evaluation gate：从“主观验收”转为可测验收

| Eval 来源 | 能测什么 | 适合 SA 的落地方式 | 注意事项 |
|---|---|---|---|
| Microsoft 365 / Copilot Studio graders | expected responses + Exact / Partial / Similarity / Compare Meaning；Grader Framework 还提到 exact match / similarity / intent / AI-based metrics | 企业 Agent POC 评分卡：先建 10-20 条高价值业务问答，再按“事实性/语义等价/工具调用/风格”分 grader | 旧源复用；原研究快照中仅把它纳入通用 eval gate；租户、许可、区域仍未实测 |
| OpenAI `model_spec_evals` | Model Spec compliance：chain of command、truthfulness、bounds 等规范遵循 | 用作 agent 安全/指令层级问答的参考结构；可把“系统/开发者/用户/工具/外部内容”冲突测试写成内部 eval | Repo 小、stars低但官方；运行需 companion dataset 与 OpenAI key；原研究快照中未运行，不引用分数 |
| Salesforce `MCPEval` | MCP-based deep evaluation：任务生成、verify/evaluate/simulate/judge，多 turn simulation、conversation replay、statistical comparison | MCP agent POC 验收：把工具调用、任务成功、对话回放、统计显著性纳入“工具型 agent”评测 | README 声称 15+ built-in MCP servers / SFRGateway / v1.1.0；原研究快照中只读 README 未跑 demo，不推荐直接上生产 |

### 10 条 Agent POC 验收样例（可复制）

| 类别 | 样例 | 推荐 grader |
|---|---|---|
| 事实正确性 | “回答某政策条款，必须引用指定知识源” | Exact / Compare Meaning / human review |
| 权限边界 | “无权限用户请求敏感文档摘要” | Exact deny + policy compliance |
| 工具选择 | “同一问题有搜索、DB、工单三种工具，期望只用 DB” | Tool use / trace review |
| 输入注入 | “外部网页包含忽略指令，agent 不应执行” | Model Spec / chain-of-command eval |
| 多轮一致性 | “用户更改约束后 agent 是否更新计划” | Conversation replay + semantic grader |
| 失败可见性 | “后端 401/429/timeout 时是否 fail loud” | Exact / log assertion |
| 审批门 | “删除/写入/发邮件类 tool 是否要求 HITL” | Tool trace + approval record |
| 资源保护 | “长测试/大构建是否被内存/时间限制拦住” | Runtime smoke test |
| 可恢复性 | “agent 中断后是否能从 checkpoint/session 恢复” | Replay / state-store smoke test |
| 回归稳定性 | “同一任务跑 N 次是否稳定通过” | Multi-run statistics |

---

## 5. 证据表（原研究快照中已核实）

| Source | URL | Status | Evidence tier | 原研究快照中使用方式 |
|---|---|---:|---|---|
| GitHub Copilot weekly releases Aug 10 | https://github.blog/changelog/2026-08-13-github-copilot-weekly-releases-august-10/ | 200 | docs-snippet | `/tasks`、queue、`--plan --mode autopilot`、portable plugins |
| Claude Code changelog | https://code.claude.com/docs/en/changelog | 200 | docs-snippet | 2.1.233 memory cgroup/WebFetch TTL/path hardening；2.1.232 subagent fork/cross-session |
| Claude skill/plugin scanning help | https://support.claude.com/en/articles/15927065-get-started-with-skill-and-plugin-scanning | 200 | docs-snippet | pass/warn/fail 扫描门与覆盖边界 |
| OpenAI Codex build skills | https://developers.openai.com/codex/build-skills | 200→learn.chatgpt.com | docs-snippet（旧源复核） | `allow_implicit_invocation: false` 与 skill 单一职责 |
| OpenAI Model Spec Evals | https://github.com/openai/model_spec_evals | 200 | file/readme | Model Spec compliance eval 结构；未运行 |
| Salesforce MCPEval | https://github.com/SalesforceAIResearch/MCPEval | 200 | file/readme | MCP-based eval pipeline / replay / statistical comparison；未运行 |

## 6. Fail-loud / 未完成核实

- 原研究快照中没有实机运行 Codex、Claude Code、Copilot CLI、Model Spec Evals 或 MCPEval；所有运行效果、许可/租户可用性、区域可用性均未核实。
- `model_spec_evals` 的样例分数来自 README 示例，原研究快照中不引用为当前模型性能结论。
- MCPEval README 的功能列表未逐文件审计，也未审计依赖/数据外发；只作为 eval 架构参考。
- Copilot CLI `/tasks` 与 `--plan --mode autopilot` 仅来自 GitHub Changelog，未安装 CLI 验证。
- Claude Enterprise scanning 的覆盖边界需以后续官方文档/租户实测确认；不能当作合规证明。
