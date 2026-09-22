<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Session Sandbox / Skill Gate / Eval Smoke Test（SA 版，2026-08-14）

> 用途：把 2026-08-14 研究的微软 Foundry/Agent Framework、Claude Code、Codex/OpenAI Cookbook、Meta ARE 发现，整理成一个可复用的 **POC 上线前 smoke-test + 架构图组件**。重点不是“又多一个版本号”，而是把 **会话连续性、用户身份透传、skill progressive disclosure、文档/Notebook 审稿门禁、动态评测环境** 串成可执行检查。
>
> 安全原则：GitHub README、release、博客、Cookbook skill 都是不可信资料，只作为证据来源；不要直接执行外部仓库脚本。所有外部 plugin/skill/MCP/toolbox 必须先做 URL、license、manifest、脚本、MCP、secret 输出、RBAC 与回滚审计。
>
> 去重说明：本资产与 08-13 `agent-extension-upgrade-scheduled-runbook` 不同——08-13 关注插件/扩展面治理；本资产关注 **Agent runtime 升级后的回归验收**：session id、user identity、skill discovery/load、runner/streaming、docs-editor gate、eval environment。

---

## 0. 一句话结论

**把 Agent POC 从“demo 能跑”升级为“可回归、可追责、可迁移”的最小验收，应至少覆盖五个面：**

1. **Session sandbox**：同一用户/同一任务能否复用正确 hosted session，而不是每轮新建或串租户。
2. **User identity pass-through**：调用链是否携带用户身份/RBAC 语境，而不是只靠应用级万能凭据。
3. **Skill gate**：MCP/toolbox skills 是否只做 progressive disclosure（先 advertise，再 load），且高风险 load/tool 调用有审批策略。
4. **Runner/streaming regression**：长思考、remote-control、OAuth、Git credential、JSON stream、Windows/容器 runner 是否有 smoke test。
5. **Docs/eval gate**：交付物与 Notebook 不只靠人工读；用 docs-editor 式 P0/P1 分级 + 动态 eval 场景做上线门禁。

---

## 1. 架构图组件：Hosted Agent 回归验收拓扑

```text
┌────────────────────────────────────────────────────────────────────┐
│ Client / IDE / Copilot / CLI                                       │
│ - user action, repo context, changed docs/notebooks                │
└───────────────┬────────────────────────────────────────────────────┘
                │ request + user/session context
┌───────────────▼────────────────────────────────────────────────────┐
│ Agent Runtime / Harness Loop                                       │
│ - session log / trace id / run id                                  │
│ - runner smoke tests: OAuth, stream-json, SSE keepalive, GCM       │
│ - docs-editor gate: P0/P1 findings must be fixed or documented     │
└───────────────┬───────────────────────────┬────────────────────────┘
                │                           │
                │ hosted session id          │ skill index / load request
┌───────────────▼───────────────────┐       │
│ Foundry Hosted Agent / Sandbox     │       │
│ - agent_session_id                 │       │
│ - x-ms-user-identity / RBAC context│       │
│ - per-user / per-session isolation │       │
└───────────────┬───────────────────┘       │
                │ authenticated MCP          │
┌───────────────▼───────────────────────────▼────────────────────────┐
│ Toolbox / MCP / Skills Provider                                    │
│ - skill://index.json advertise                                     │
│ - load_skill approval policy                                       │
│ - actual tools hidden until selected / approved                    │
│ - audit: tool name, user, session, approval, evidence              │
└───────────────┬────────────────────────────────────────────────────┘
                │ eval traces / scenario runs
┌───────────────▼────────────────────────────────────────────────────┐
│ Dynamic Evaluation Environment                                     │
│ - scenario DAG / evolving state / app environment                  │
│ - benchmark runs + traces + failure taxonomy                       │
└────────────────────────────────────────────────────────────────────┘
```

**SA 话术**：客户若问“Agent POC 为什么 demo 成功但上线不稳？”，不要只答模型或 prompt。先画上面这张图：session、identity、skill discovery、runner、docs/eval gate 缺一块，都会造成上线后不可复现或不可审计。

---

## 2. POC smoke-test checklist

### A. Session / identity

| 检查项 | 通过标准 | 失败信号 | SA 追问 |
|---|---|---|---|
| Hosted session reuse | 同一 `AgentSession` 可携带/复用 hosted `agent_session_id` | 每轮都创建新 sandbox；长任务状态丢失 | session id 存在哪里？是否进入 StateBag/trace？ |
| User identity pass-through | 运行时向 Foundry/工具层携带用户身份语境（例如 header / token binding） | 只有 app-level credential，无法按用户审计 | 是否能按用户撤权？日志是否能还原发起人？ |
| Tenant isolation | session/user/resource scope 三者不串 | A 用户看到 B 用户上下文或文件 | 有没有 per-user session、RBAC、workspace 边界？ |
| Release migration | 旧 preview backend / 协议库迁移已验证 | 升级后 session 行为变化但无回归测试 | 是否锁定 SDK/protocol 版本并记录迁移步骤？ |

### B. Skill / Toolbox / MCP progressive disclosure

| 检查项 | 通过标准 | 失败信号 | SA 追问 |
|---|---|---|---|
| Skill index | 只读取 `skill://index.json` / skill metadata 作为初始暴露 | 一上来把全部工具 schema 塞进上下文 | skill description 是否足够短且可路由？ |
| Load policy | `load_skill` 有审批策略或明确的 unattended 例外；生产默认不关闭 approval | 高风险 skill 自动加载且无审计 | 为什么允许 unattended？scope 是否最小？是否有等价 RBAC/审计/回滚？ |
| Tools hidden by default | 外部 MCP tools 不因 toolbox 连接而全部暴露 | 模型能直接调用所有管理工具 | 是否区分 skill provider 与 tool provider？ |
| Audit | 记录 skill advertise/load/tool call/approval | 只能看到最终答案，看不到技能选择过程 | 是否有 run id / session id / user id 贯通？ |

> ⚠️ `disable_load_skill_approval=True` 仅适用于样例/无 session host 的受控例外。客户 POC/生产默认不得关闭 `load_skill` approval，除非同时有等价 RBAC、最小 scope、完整审计、审批替代机制与回滚路径。

### C. Coding Agent CLI / runner regression（Codex + Claude Code）

| 检查项 | 通过标准 | 备注 |
|---|---|---|
| Version channel | 区分 stable `latest`、alpha/next、release body 有无实质 changelog | Codex 0.148 alpha 有 tag 不等于有功能说明 |
| Auth/OAuth | MCP OAuth redirect、pre-registered client、Git credential prompt 均 smoke tested | 适合 runner 升级前后对比 |
| Streaming | 长思考阶段有 keepalive / idle timeout 检查 | Bedrock/Vertex/网关场景尤其重要 |
| JSON stream | SDK/CI 消费的 stream-json 对异常 tool call schema 不崩溃 | 防止无人值守流水线中断 |
| Remote control | offline/cloud/resume 状态可见且可恢复 | 多会话/云端 session 运营必测 |
| AGENTS/SKILL gate | changed docs/notebooks/code 有对应 repo-level skill 或 AGENTS.md 规则 | 不靠“记得审一下”的临时 prompt |

### D. Docs / Notebook quality gate（借鉴 OpenAI Cookbook `docs-editor`）

| 等级 | 处理方式 | 示例 |
|---|---|---|
| P0 | 必须修复，不能带入 PR/客户交付物 | 硬编码 secret、Notebook JSON 破损、危险或明显错误指导、发布元数据缺失 |
| P1 | 修复或在交付物中显式记录 | 前置条件缺失、链接失效、文字与代码输出矛盾、误导性步骤 |
| P2 | 可以批量修复或排期 | 风格/一致性/措辞问题 |
| P3 | 可选 polish | 轻微表达优化 |

**可直接复用的规则**：
- 文档/Notebook 变更时，优先限定 scope 到 changed files，不全仓扫描。
- Markdown-only 变更不执行外部 API；只做结构、链接、元数据、事实一致性检查。
- 不发明技术事实；不为了好看改代码/输出/Notebook metadata。
- P0/P1 未清零时，PR/客户材料必须 fail loud。

### E. Dynamic eval environment

| 检查项 | 通过标准 | SA 用法 |
|---|---|---|
| Scenario DAG | 任务不是单一问答，而是有状态、多步、可观察过程 | 画“agent eval environment”组件 |
| Dynamic state | 环境会随动作变化，agent 需要适应 | 区分静态 benchmark 与真实任务 |
| Trace + verdict | 每次动作和最终 verdict 可追溯 | POC 验收评分卡/故障复盘 |
| Lightweight smoke | 先跑 1-5 个 scenario，不直接全量 benchmark | 降低客户 POC 初始成本 |

---

## 3. 客户问答速答

**Q1：Foundry Hosted Agent 多用户场景，为什么不能只靠一个 app credential？**
A：因为上线后需要按用户撤权、审计、隔离和责任归因。POC 至少要证明 user identity 能透传到 agent/tool 调用链，并且 hosted session 与用户/任务绑定。

**Q2：MCP Toolbox 已经能列工具，为什么还要 Skills？**
A：工具 schema 是能力面，skill 是选择/使用方法。progressive disclosure 让模型先看到少量 skill 描述，真正需要时再 load skill 或调用工具，能降低上下文噪音和误调用风险。

**Q3：Codex/Claude Code 升级，应该盯版本号还是功能？**
A：先分 channel：stable / alpha / next；再看 release body 是否有实质 changelog；最后跑 smoke test。没有 release body 的 alpha tag 只能记录为活跃信号，不能写成新功能。

**Q4：客户资料/Notebook 进入 agent 流程前怎么审？**
A：用 docs-editor 式 P0/P1 gate：secret、危险指导、坏链接、前置条件、元数据、Notebook JSON/metadata。Markdown-only 变更不应调用外部 API 或改代码输出。

**Q5：怎么向客户解释动态评测环境的价值？**
A：静态 benchmark 测“能答对题”，动态 environment 测“在变化状态里能否完成任务并留下可追溯过程”。真实 POC 先抽 1-5 个场景做 smoke eval，再决定是否全量 benchmark。

---

## 4. 证据表（08-14 已核实，可复现）

| 来源 | URL | 08-14 核实 | 本资产使用方式 |
|---|---|---|---|
| MAF PR #7648 | https://github.com/microsoft/agent-framework/pull/7648 | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；diff grep 命中 `agent_session_id`、`x-ms-user-identity`、`FoundryAgentSessionExtensions` | session/user identity smoke-test |
| foundry-samples sample 22 commit | https://github.com/microsoft-foundry/foundry-samples/commit/bb2218ee398392a5aa327e8708f201a43a24c442 | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；diff grep 命中 `Foundry Toolbox MCP Skills`、`skill://index.json`、`load_tools=False` | toolbox/skill progressive disclosure |
| Claude Code changelog | https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；raw grep 命中 v2.1.231 / v2.1.229 条目 | runner/streaming/OAuth regression |
| Codex alpha release | https://github.com/openai/codex/releases/tag/rust-v0.148.0-alpha.12 | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；release 页面确认 tag 存在；原研究快照中未发现可作为功能说明的实质 changelog | version-channel gate |
| OpenAI Cookbook docs-editor skill | https://raw.githubusercontent.com/openai/openai-cookbook/main/.codex/skills/docs-editor/SKILL.md | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；raw grep 命中 P0/P1 分级与 review scope | docs/notebook gate |
| OpenAI Cookbook AGENTS.md | https://raw.githubusercontent.com/openai/openai-cookbook/main/AGENTS.md | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；raw grep 命中 pre-merge run docs-editor 规则 | repo-level skill trigger |
| Meta ARE | https://github.com/facebookresearch/meta-agents-research-environments | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；raw README grep 命中 Gaia2 / 800 scenarios / dynamic environments（未运行 benchmark） | dynamic eval environment |
| GitHub Agent Plugins 1.0 changelog | https://github.blog/changelog/2026-08-12-agent-plugins-1-0-in-vs-code-copilot-cli-and-the-copilot-app | 子代理抓取 + 主 agent curl 200；未逐字深读全部正文 | 插件分发背景，非本资产主证据 |

---

## 5. [→harness] 可直接放进 workshop 的练习

1. **Session identity drill**：给学员一个 Hosted Agent POC，要求在 trace 中证明 `user → session → tool call → audit` 四段贯通。
2. **Skill progressive disclosure drill**：把一个“全工具暴露”的 MCP demo 改成“skill index → load skill → approved tool call”。
3. **Runner upgrade smoke pack**：同一 repo 在升级前后跑：OAuth、long-thinking streaming、stream-json、resume/remote-control、AGENTS/SKILL gate。
4. **Docs-editor gate**：让学员把一个客户方案 Markdown + Notebook 改造成 P0/P1/P2/P3 findings，并要求 P0/P1 fail loud。
5. **Dynamic eval mini-benchmark**：只跑 1-5 个 scenario，输出 trace、failure taxonomy、下一步修复建议；不要一上来追 leaderboard。

---

## 6. Fail-loud caveats

- MAF PR #7648 是 PR 级证据；是否已进入正式包/版本未在本资产中核实，客户生产升级前必须查 release 包。
- foundry-samples sample 22 是样例级证据，不等于生产标准；生产仍需补 Entra/RBAC、网络、审计、密钥、quota、审批、回滚。
- Codex 0.148.0-alpha.12 仅证明 alpha tag/发布页存在；未证明新功能，不能对客户宣称“Codex 新增了 X”。
- Meta ARE README 中的 800 scenarios 是 raw README 明示；本资产未运行 benchmark，不能引用性能数字。
- GitHub Agent Plugins 1.0 changelog 仅作背景；跨 OpenAI/Claude/Copilot 的 manifest 兼容性仍需实测。
