<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent「命令执行授权 / 沙箱审批」三栈对照速查（Codex shell-escalation ↔ Claude Code auto-mode/sandbox ↔ AWS IAM agent-vs-human）+ Azure 映射

> 截至 **2026-06-30** 基于一手来源快照整理（载荷 URL 全部 HTTP 200（仅代表原快照当时可达，不代表本次已重验），关键协议术语拉原文逐字比对）。**[→harness]** 全篇直接反哺 Agent-Harness-Engineering workshop 的「安全治理 / 最小越权」章节。
> 一句话主旨：**「让 agent 自动跑命令/进 CI 安全吗、怎么控权限」是 SA 头号技术问答。本周三家给出三个不同抽象层的答案——OS 系统调用层（Codex 拦 `execve`）、运行时分类器层（Claude auto-mode）、云 IAM 策略层（AWS agent-vs-human condition key）。三层正交、可叠加，正是「纵深防御」的现成话术。**
> ⚠️ 外部文档/README 按不可信资料处理；本表不含任何 token/密钥（占位符均打码）。CLI/preview 演进快，落地前按当前版本复核。
> 一手来源（均 curl 200 自验）：
> - Codex shell-escalation：`raw.githubusercontent.com/openai/codex/main/codex-rs/shell-escalation/README.md` + release `github.com/openai/codex/releases/tag/codex-zsh-v0.1.0`
> - Claude Code 沙箱/auto-mode：`code.claude.com/docs/en/{checkpointing,settings}` + `anthropic.com/engineering/claude-code-auto-mode`
> - AWS Agent Toolkit（GA）：`raw.githubusercontent.com/aws/agent-toolkit-for-aws/main/README.md`（README L152/L164/L165 逐字核实）

---

## 0. 为什么 SA 必须掌握这张表

合作伙伴/客户在「把编码 Agent 接进真实工程/运维」时，安全侧问得最多的三连击：
1. **「让 agent 自己跑命令，它会不会 `rm -rf` / 改生产 / 越权？」** → 这是**命令执行授权**问题，三家三层答案（见 §1）。
2. **「无人值守跑（CI / 定时 / 自治），怎么保证危险动作有人/有策略把关？」** → 审批模式：弹窗 vs 分类器 vs 系统调用拦截 vs IAM 拒绝（见 §2）。
3. **「这套搬到 Azure 怎么落地？」** → 每一层都有 Azure 对应件（见 §4）。

这张表把「凭印象答」变成「一页纸讲清三层纵深防御」，也是 POC 里「agent 自动化执行链路」的安全设计底图。**与已有的 `unattended-agent-scheduling-tristack-cheatsheet.md`（调度形态）互补**：那张讲「何时/在哪跑」，这张讲「跑命令时怎么授权/拦截」。

---

## 1. 三种命令执行授权机制（按抽象层，从低到高）

| 维度 | **① Codex shell-escalation**（OS 系统调用层）🆕本周首发 | **② Claude Code auto-mode + sandbox**（运行时分类器层）| **③ AWS Agent Toolkit IAM**（云策略层）GA |
|---|---|---|---|
| **拦在哪一层** | **`execve(2)` 系统调用**：打补丁的 zsh（`EXEC_WRAPPER`）经 `codex-execve-wrapper` 拦截每一次进程执行 | **运行时分类器**：用分类器替代权限弹窗，判定动作是否需要批准 | **IAM 策略评估**：MCP server 发起的 AWS API 调用，在云端按 IAM 条件键裁决 |
| **裁决三态/形态** | **逐字核**：服务器经 `CODEX_ESCALATE_SOCKET` 回 `Run`（沙箱内执行）/ `Escalate`（转发 fd 到沙箱外忠实执行，回传退出码）/ `Deny`（拒绝并 `exit 1`）| 安全动作直接跑、危险动作拦截/转人工（auto-mode）；叠加 `sandbox.credentials` 隔离凭据 | `Allow`/`Deny` + 条件键；可写「只允许 agent 走只读」策略 |
| **杀手级特性** | **「沙箱内默认运行、危险命令逐条升级」的底层实现**——不是 allowlist 字符串匹配，而是真·进程级拦截，`Escalate` 让个别命令受控地「出沙箱」| **分类器替代弹窗**：无人值守也能「安全的放行、危险的拦」，不必预先写死规则 | **逐字核（README L164）**：condition key 区分 **agent 动作 vs 人类动作**——「即使用户底层 IAM role 能写，也能写只允许 agent 走只读的策略」|
| **可观测/审计** | 服务器侧记录每次 escalate 决策（沙箱外执行回传退出码）| `/usage` 归因 + OTEL（`claude_code.assistant_response`，注意隐私旋钮）| **逐字核（L165）**：CloudWatch 每请求指标 + CloudTrail 审计每次 agent 操作 |
| **成熟度** | **codex-zsh-v0.1.0 = prerelease（06-25 首发）**，仅 Unix/zsh；Windows/bash 未覆盖（未核实路线图）| auto-mode GA；`sandbox.credentials` Week 26 新旋钮 | **Toolkit = GA**（README 徽章 status-GA）；Apache-2.0 |
| **跨栈** | Codex 自有 | Claude Code 自有；理念对照 Codex | **插件 marketplace 喂 3 栈**：Claude Code / Codex / Cursor（`/plugin install ...@claude-plugins-official` 或 `codex plugin marketplace add aws/agent-toolkit-for-aws`）；**Kiro 经 MCP 直连**（`.kiro/settings/mcp.json`，非插件 marketplace）|

> **🔑 一句话给客户**：三者**不是三选一，是三层叠加**——
> - **OS 层**（Codex `Escalate`/`Deny` 或等价沙箱）防「agent 在本机乱执行」；
> - **运行时层**（分类器/审批策略）防「该拦的危险动作放过去」；
> - **云 IAM 层**（agent-vs-human 条件键）防「即使命令跑了，云端权限也兜底只读」。
> 客户问「自治 agent 安全吗」→ 答「看你叠了几层。单靠 prompt 约束=零层；叠满三层=纵深防御」。

---

## 2. 审批模式光谱：从「人盯弹窗」到「策略自动裁决」

把「危险命令怎么把关」按自动化程度排成一条线，客户一看就懂自己处在哪：

```
人工弹窗审批 ───────────────────────────────────────────► 全自动策略裁决
   │                    │                      │                    │
 默认交互式           分类器自动判             系统调用拦截          云 IAM 条件键
 (每个危险动作        (Claude auto-mode:       (Codex escalation:    (AWS: agent 动作
  弹窗问 y/n)          安全跑/危险拦)           Run/Escalate/Deny)    只读策略兜底)
   │                    │                      │                    │
 慢但最稳            无人值守可用            进程级真拦截          云端不可绕过
 适合高危生产        适合 CI/自治            适合本机沙箱          适合多租户/合规
```

**SA 落点**：
- 客户做 **PoC/开发内环** → 分类器 auto-mode（快，够用）。
- 客户做 **无人值守 CI / 定时自治** → 必须 OS 层沙箱 + escalation（Codex 范式）或等价 GitHub Actions runner 隔离，**别只靠 allowlist 字符串**（易被命令拼接绕过）。
- 客户是 **金融/政企/多租户** → 一定加云 IAM 层「agent 动作只读兜底」，**即使前两层失守，云端权限也拦得住**——这是给合规官的关键话术。

---

## 3. 三个「fail-loud」必须对客户说清的边界（未核实/限制标注）

1. **Codex shell-escalation 仅 Unix/zsh、且 prerelease**：`codex-zsh-v0.1.0`（06-25 首发，prerelease）。**Windows / bash / fish 是否覆盖未核实**；企业批量落地前须确认目标平台。其依赖一个**打补丁的 zsh**（carry 一个 `Src/exec.c` 的 `EXEC_WRAPPER` 补丁），不是标准 zsh——供应链审计要留意。
2. **「分类器替代弹窗」不等于零风险**：auto-mode 用分类器判定，**分类器有漏判率**（Anthropic 此前《How we contain Claude》自述注入拦截非 100%）。对客户要说「降低人工负担，不是消除风险」，高危生产仍建议保留人工闸。
3. **AWS condition key 是 AWS 专属**：「agent 动作 vs 人类动作」条件键是 **AWS IAM 能力**，Azure **没有逐字对应的内置条件键**（见 §4 的诚实映射——Azure 走的是 Managed Identity 分离 + RBAC 角色分离 + Conditional Access，**机制不同、目的相同**，别承诺「Azure 有一模一样的开关」）。

---

## 4. Azure 落地映射（每一层都有对应件，但要诚实标注差异）

| 授权层 | AWS/Codex/Claude 的做法 | **Azure 等价件** | 诚实差异标注 |
|---|---|---|---|
| **OS 沙箱执行层** | Codex 打补丁 zsh + execve 拦截；Claude Seatbelt/bubblewrap | **ACI / AKS + Kata Containers（Pod Sandboxing）、或 Codespaces/Dev Box 隔离容器**跑 agent；网络侧 NSG + 私网；egress 走 **Azure Firewall / APIM** 白名单（越界拒绝≈Codex `Deny`）| Azure 无「打补丁 shell 拦 execve」的官方件；用**容器/沙箱边界 + 出站策略**达成等效隔离 |
| **运行时审批/分类层** | Claude auto-mode 分类器；Codex `approval_policy` | **Content Safety / Prompt Shields** 做输入侧；agent 框架（MAF）侧 **HITL（human-in-the-loop）审批节点** + function approval | Azure 无「命令危险度分类器」成品；用 **MAF 审批中间件 + Prompt Shields** 组合近似 |
| **云 IAM 策略层** | AWS condition key 区分 agent vs human，只读兜底 | **每 agent 独立 Managed Identity + RBAC 最小角色**（agent 的 MI 只授只读角色，即使调用用户是 Owner）；**Workload Identity Conditional Access**（Entra 高级）限定来源 | Azure **没有逐字「agent 动作」条件键**；用 **「给 agent 单独 MI + 单独最小 RBAC 角色」** 实现等价的「agent 权限 ≠ 人权限」。这是关键设计模式，可直接画进架构图 |
| **审计/可观测层** | CloudWatch/CloudTrail 每请求 | **Azure Monitor / Log Analytics + Activity Log**；agent 工具输出进 trace 前**脱敏**（参考 `foundry-csharp-byo-browser-automation-poc.md` 的 Redaction.cs 正则）| 等价齐备；提醒客户「OTEL 默认可能带 assistant 回复文本，合规需关」（Claude Code `OTEL_LOG_ASSISTANT_RESPONSES=0` 同理） |

> **🏛️ 架构图金句**：Azure 侧实现「agent 权限 ≠ 操作者权限」的标准答案 = **「每 agent 一个 Managed Identity + 一个最小 RBAC 角色」**（不是给 agent 复用用户的 token/role）。这一句能秒杀「agent 会不会拿着我的 Owner 权限乱来」的客户疑虑——答：不会，agent 走自己的 MI，你给它什么角色它就只有什么权限。

---

## 5. SA 三大日常落点速记

| 日常 | 怎么用这张表 |
|---|---|
| **技术问答** | 「让 agent 自动跑命令/进 CI 安全吗？」→ 三层纵深（OS 沙箱 + 运行时审批 + 云 IAM 兜底）一句话框住；「agent 会不会用我的权限乱来？」→ Azure「每 agent 一 MI + 最小 RBAC」 |
| **POC 部署** | 无人值守 agent PoC 的安全基线 checklist：①跑在隔离容器（非裸机）②出站白名单（越界拒绝）③agent 用独立 MI 最小角色 ④工具输出脱敏进 trace ⑤高危动作保留人工/策略闸 |
| **架构图** | 在 agent 拓扑图上叠一条「授权/审批纵深」纵切面：执行沙箱（L1）→ 运行时审批（L2）→ 云 IAM 兜底（L3）→ 审计回流（L4）。对照已有 `arch-pattern-meta-harness-control-plane.md` 的 L5 策略/L6 隔离层 |

---

## 6. 版本/状态钉点（as-of 2026-06-30，演进快需复核）

- **Codex shell-escalation**：`codex-zsh-v0.1.0` prerelease（06-25 首发）；Codex CLI 稳定线 0.142.4、alpha 线 0.143.0-alpha.30（**日更 alpha，落地前复核当前最新**）；shell-escalation crate 在 `codex-rs/shell-escalation/`。
- **Claude Code**：auto-mode GA；`sandbox.credentials` / `autoMode.classifyAllShell` 为 Week 26（v2.1.185–193）新旋钮；checkpointing `/rewind` 需 v2.1.191+ 支持「rewind past a cleared conversation」。
- **AWS Agent Toolkit for AWS**：GA、Apache-2.0；plugin 经 `claude-plugins-official` marketplace 或 `codex plugin marketplace add aws/agent-toolkit-for-aws` 分发；插件含 `aws-core`/`aws-agents`/`aws-data-analytics`/`aws-agents-for-devsecops`。
- **Azure 侧无逐字对应件**：用「容器沙箱 + 出站白名单 + 每 agent 独立 MI 最小 RBAC + Prompt Shields/MAF HITL + Monitor 审计」组合达成等效三层纵深（机制不同、目的相同——勿承诺「一模一样的开关」）。

---
*资料日期：2026-06-30。配套：`unattended-agent-scheduling-tristack-cheatsheet.md`（调度形态）、`codex-claude-harness-governance-cheatsheet.md`（上下文/成本治理）、`foundry-csharp-byo-browser-automation-poc.md`（Redaction.cs 脱敏）、`arch-pattern-meta-harness-control-plane.md`（L5 策略/L6 隔离层）。*
