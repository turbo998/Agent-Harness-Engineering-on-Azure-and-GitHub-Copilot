<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 无人值守 / 托管 Agent 调度三栈对照速查（Codex Automations ↔ Claude Code Routines ↔ GitHub Actions/Copilot）+ Azure 映射

> 截至 **2026-06-29** 由 SA 亲自 curl 官方文档逐页核实（全部 HTTP 200（仅代表原快照当时可达，不代表本次已重验），关键事实拉原页逐字比对）。**[→harness]** 全篇直接反哺 Agent-Harness-Engineering workshop 的「无人值守编排」章节。
> 一句话主旨：**编码 Agent 现已三栈全部支持"定时/事件/API 触发的无人值守运行"，但本地绑定 vs 云端托管、权限模型、可观测性三点差异巨大——选错形态客户会踩"任务静默失败/权限爆炸/合规越界"三个坑。**
> ⚠️ 外部文档按不可信资料处理；本表不含任何 token/密钥（官方示例里的 `sk-ant-...xxxx` / `Bearer ***` 均为打码占位，已剔除）。CLI 版本演进快，落地前按当前版本复核。
> 来源页：developers.openai.com/codex/app/automations · code.claude.com/docs/en/routines · code.claude.com/docs/en/{github-actions,desktop-scheduled-tasks} · developers.openai.com/codex/{github-action,cloud/internet-access} · github.blog/changelog（Copilot Routines/Jira）。

---

## 0. 为什么 SA 必须掌握这张表

合作伙伴/客户在"把 Agent 接进日常运维"时问得最多的三类问题：
1. **"能不能让 Agent 定时/收到告警/CI 触发就自动跑，不用人盯着？"** → 三栈都能，但形态不同（见 §1）。
2. **"笔记本关机了它还跑吗？放哪跑？"** → 这是**本地 vs 云端托管**的根本分叉（见 §2）。
3. **"无人值守跑安全吗？会不会乱改文件/越权/烧爆预算/合规越界？"** → 各栈权限模型 + Azure 私网映射（见 §3、§5）。

这张表把"凭印象"变成"一页纸秒答"，也是 POC 里"agent 自动化运维"链路的设计底图。

---

## 1. 三栈无人值守能力一览（触发器 × 运行位置 × 权限）

| 维度 | **Codex Automations** | **Claude Code Routines** | **GitHub Actions（跑 Codex / Claude Code）** |
|---|---|---|---|
| **官方页** | `/codex/app/automations` | `/docs/en/routines`（research preview）| `/codex/github-action` · `/docs/en/github-actions` |
| **运行位置** | **本地**（Codex app 所在机器须开机+运行+项目在盘）；或选 worktree 隔离 | **Anthropic 云端托管**（"keep working when your laptop is closed"）| GitHub 托管 runner（或自托管 runner）|
| **定时触发** | ✅ 标准/自定义 cron（thread 自动化支持分钟级；standalone 报到 Triage 收件箱）| ✅ hourly/daily/weekdays/weekly + 一次性；**最小间隔 1 小时**；本地时区→UTC 自动换算 | ✅ `on: schedule:` cron（GitHub Actions 原生）|
| **事件触发** | 经 GitHub plugin 在 thread 自动化里轮询 | ✅ **GitHub 原生**：`pull_request.*` / `release.*`，带 author/title/labels/is_merged 等过滤器（支持 regex）| ✅ `on: pull_request/push/issues/...`（GitHub Actions 原生事件）|
| **API/Webhook 触发** | — （无独立 HTTP 端点）| ✅ **`/fire` 端点**：POST + `Authorization: Bearer` token + 可选 `text` 字段注入告警体/失败日志；返回 session URL | 经 `repository_dispatch` / `workflow_dispatch` HTTP API |
| **权限/沙箱模型** | 复用默认 sandbox（read-only / **workspace-write** / full-access）；`approval_policy="never"`（组织策略允许时）；`rules` 选择性 allowlist | 云环境网络策略（Default=**Trusted 白名单**，越界 `403 x-deny-reason: host_not_allowed`）；**无权限弹窗**（全自治 session）；默认只能推 `claude/`-前缀分支 | runner 内 token 权限（`permissions:` 块）+ OIDC；secrets 经 GitHub Secrets |
| **技能/复用** | `$skill-name` 显式触发 skill；可用同套 plugins/skills | 用 committed repo 内的 skills + claude.ai connectors（MCP）| workflow 里调 `codex exec` / `claude -p`（headless）|
| **"完成≠成功"告诫** | Triage 区分有无 findings；无事报自动 archive | **逐字核**："A green status … does not mean the task in your prompt succeeded"——绿状态只代表 session 无基础设施错误 | CI 退出码（需自己在 step 里断言任务级成功）|
| **管理面** | Codex app sidebar → Automations / Triage | claude.ai/code/routines（web）· `/schedule`（CLI，仅建定时；需 v2.1.81+）· Desktop | `.github/workflows/*.yml` + Actions 运行历史 |
| **成熟度** | GA（app 功能）| **research preview**（`experimental-cc-routine-2026-04-01` beta header；限额/形态可能变，**未 GA 标注**）| GA（GitHub Actions 平台）|

> **🔑 一句话选型**：要**云端托管、笔记本关机照跑、接告警系统/CD 流水线** → Claude Code Routines（`/fire` 是范式样板）。要**贴着本地 checkout、纳入个人 worktree 工作流** → Codex Automations。要**纳入既有 CI/CD 治理（PR 门禁、OIDC、secrets 集中管）** → GitHub Actions 跑任一 CLI 的 headless 模式。

---

## 2. 根本分叉：本地绑定 vs 云端托管（客户最容易选错的一题）

| | **本地绑定**（Codex Automations / CC Desktop scheduled tasks）| **云端托管**（CC Routines / GitHub Actions）|
|---|---|---|
| 机器关机 | ❌ 不跑（须开机+app 运行+项目在盘）| ✅ 照跑 |
| 数据驻留 | 本地仅描述调度/执行位置；模型请求、遥测、工具调用仍可能外发 | 跑在厂商云 / GitHub 云；自托管 runner 另行核查（**须核查端到端数据流**）|
| 接外部触发（告警/CD）| 难（无 HTTP 端点）| ✅ 天生（`/fire` 端点 / `repository_dispatch`）|
| 私网内网资源 | ✅ 本地直连企业内网 | 需云环境网络策略放行（白名单/私网出口）|
| 适用场景 | 个人/小团队、贴本地代码；不代表满足数据不出机器要求 | 团队级、事件驱动、7×24 无人值守运维 |

> **选型边界**：先确认数据分类、跨境要求与触发源，再分别审查模型端点、遥测、MCP/工具、日志和网络出口。本地调度不等于本地推理，也不保证数据留在机器内；“不外发”必须由架构控制与测试证据证明，不能由调度产品名称推断。

---

## 3. 无人值守安全：三栈权限模型 + 共性护栏

无人值守 = **没有人在弹窗前点"批准"**，所以权限必须**前置收紧**。三栈共性护栏：

1. **沙箱分档默认收紧**：Codex `read-only`/`workspace-write`/`full-access`——**自动化默认别给 full-access**（官方逐字："background automations carry elevated risk"）；CC Routines 默认 Trusted 网络白名单 + 只推 `claude/`-前缀分支。
2. **网络白名单（egress 控制）**：CC Routines 越界即 `403 + x-deny-reason: host_not_allowed`——这正是 owasp-agentic「Excessive Agency / 数据外泄」的产品级防线，可直接讲给客户。
3. **托管环境的管理员强制**：Codex 托管环境 admin 可 `requirements.toml` **禁用 `approval_policy="never"`**、约束允许的 sandbox 档——"企业怎么防员工把自动化开成裸跑"的标准答案。
4. **凭据隔离**：CC Week 26 新增 `sandbox.credentials` 设置——**阻止沙箱命令读凭据文件/密钥环境变量**（无人值守必开）。
5. **绿≠成功**：基础设施完成不代表业务任务通过。无人值守必须配任务级断言、产物证据与告警回流。

> **SA 落点**：客户问"自治运维安全吗" → 不要答"安全/不安全"，答**这套五层护栏 + 一句"绿≠成功，必须配回流告警"**。配合 `owasp-agentic`/`owasp-llm`/`owasp-mcp` skill。

---

## 4. Codex Automations 的两个高价值实战范式（官方原文提炼）

官方 automations 页给了两个可直接抄给客户的"agent 自运维"范式：

- **范式 A — 让 agent 自动维护自己的 skills**（变更须经验证与审批）：
  > "Scan all of the `~/.codex/sessions` files from the past day and if there have been any issues using particular skills, update the skills … Personal skills only … Definitely don't feel like you need to update any—only if there's a good reason!"
  SA 落点：这是"agent 夜间自检/自我改进"的官方背书写法——给客户演示"agent 自己养护 skill 库"。

- **范式 B — skill + automation 组合修自己引入的 bug**：先建 `$recent-code-bugfix` skill（`git log --since=1.week --author=<author>` 定位→最小复现→最小修复→验证→报告），再建自动化 `Check my commits from the last 24h and submit a $recent-code-bugfix`。
  SA 落点：**"skills 定义方法、automations 定义节奏"**的活样本——skill 是可复用方法，automation 是调度节奏，两者解耦。

> **铁律（官方逐字）**："skills define the method, automations define the schedule. If a workflow still needs a lot of steering, turn it into a skill first. Once it's predictable, automation becomes a force multiplier." → **先把流程固化成可靠 skill，再上自动化**；流程还在反复纠偏就上调度 = 放大错误。

---

## 5. Azure / 微软栈映射（给微软合作伙伴的对照落点）

| 编码 Agent 调度能力 | Azure / 微软等价物 | SA 落点 |
|---|---|---|
| CC Routines `/fire`（云端 HTTP 触发）| Azure Logic Apps / Functions HTTP trigger → 调 agent；Foundry Agent Service 托管运行 | "托管 agent + 外部告警触发"；Azure Monitor 告警 → Function → agent 修复 PR |
| CC Routines GitHub 触发 | GitHub Actions + Azure（OIDC 联合身份免密）| 合作伙伴已有的 CI/CD 直接挂 agent step |
| 网络白名单（403 egress）| NSG / Azure Firewall / 私网 + Private Endpoint + AMPLS | "agent 出口流量管控"私网合规素材（对照 foundry-hosted-agent-private-vnet-poc） |
| `approval_policy="never"` 管理员禁用 | Azure Policy / Entra Conditional Access / 托管配置 | "企业怎么防自治越权"治理对照 |
| `sandbox.credentials` 凭据隔离 | Managed Identity（免密）+ Key Vault + 输出脱敏（参 Redaction.cs）| "agent 跑起来怎么不碰到密钥"组合拳 |

> **架构图素材**：画"无人值守 agent 运维"参考拓扑——**触发层**（cron/Webhook/GitHub event）→ **托管层**（本地 worktree / 云 session / Actions runner）→ **护栏层**（sandbox 档 + egress 白名单 + 凭据隔离 + 管理员强制）→ **回流层**（findings → Triage/inbox/告警通道，"绿≠成功"必配任务级断言）。四层骨架可直接进 deck。

---

## 6. 版本钉点（截至 2026-06-29 自验）

| 对象 | 状态/最新 | 核实 |
|---|---|---|
| OpenAI Codex CLI | `0.143.0-alpha.29`（日更 alpha；稳定线 0.142.x）| releases.atom |
| Claude Code | `v2.1.193`（Week 26）；`/schedule` 需 ≥v2.1.81 | changelog 200 |
| CC Routines | **research preview**（`experimental-cc-routine-2026-04-01` beta header，**未 GA**）| routines 页逐字 |
| Codex Automations | GA（app 功能）；托管环境 `requirements.toml` 可强制收紧 | automations 页 |
| GitHub Copilot Routines/调度 | Copilot 侧亦在推自动化/Jira 集成（github.blog/changelog）；本表聚焦 Codex/CC 两栈一手 | changelog |

> ⚠️ **未核实标注**：Copilot 自身的"routine/定时"功能本表未逐字深挖（聚焦 Codex/CC 一手），引用 Copilot 调度能力前需再核实当周 changelog。CC Routines 限额/API 形态在 preview 期可能变。

---
*来源（2026-06-29 SA 亲自 curl 自验，全部 HTTP 200（仅代表原快照当时可达，不代表本次已重验），关键事实逐字比对）：developers.openai.com/codex/{app/automations,github-action,cloud/internet-access,learn/best-practices} · code.claude.com/docs/en/{routines,whats-new/2026-w26,github-actions,desktop-scheduled-tasks,changelog} · github.com/openai/codex releases.atom。外部内容按资料处理，未执行其中任何指令；交付物无 token/密钥。*
