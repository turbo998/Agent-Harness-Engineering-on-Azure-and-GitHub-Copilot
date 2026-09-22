<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 多 Agent Provider 收敛 + Containment 架构 Cheatsheet
> 07-15 新建。整合三条本周证据链：①GitHub Copilot 把 Codex/Claude 并列为可插拔 agent provider；②Claude Code `/doctor` 从只读诊断升级为主动修复；③Anthropic《How we contain Claude across products》三层隔离架构（05-25 发布，07-13起置顶为 engineering 首页 featured 文章）。三者共同回答 SA 客户常问的一个问题：**"我们已经买了 Copilot license，能不能同时用 Codex 和 Claude Code 的能力，而不用切换整套工具链？"** + **"自治 agent 长跑安全吗？"**

## 一、GitHub Copilot 作为多 agent 统一前端（07-15 新发现，已核实可达）

来源：`github.blog/changelog/2026-07-07-codex-as-agent-provider-and-agentic-enhancements-in-jetbrains-ides/`（200核实，2026-07-07）

- JetBrains IDE 中的 Copilot Chat 面板**新增可选 Codex 作为 agent provider**（需本机装 Codex CLI 并配置路径），与此前已支持的 Claude agent provider **并列**。
- 同批更新：Claude agent 会话新增 permission modes 选择 + debug logs；Copilot CLI 会话新增 **Approval 三档设置**（`Default` / `Bypass` / `Autopilot`）。
- **SA 落点**：这是"多 agent 互操作性"最直接的一手证据——Copilot 生态正把 Codex/Claude 作为可插拔后端，暴露统一的 permission-mode/审批策略概念。可反哺 harness workshop 新增案例"Copilot 作为多 agent 统一前端"，并做一张三方审批模式对比表：

| 审批策略维度 | Copilot CLI | Claude Code Auto Mode | Codex `writes` 审批 |
|---|---|---|---|
| 档位 | Default / Bypass / Autopilot | 分层护栏(PreToolUse gate+注入探测+分类器) | 只读放行/写操作需确认 |
| 默认行为 | Default(需确认) | 需 opt-in(部分平台已默认开启) | 只读默认放行 |
| 无人值守适配 | Autopilot | Auto Mode | 需显式配置 |

**⚠️ fail-loud**：三方审批模式的具体权限粒度（如是否支持按工具/按路径细分）未逐字对照核实，仅做概念层面对比。

## 二、Claude Code `/doctor` 主动修复升级（Week 28, v2.1.202→v2.1.206）

来源：`code.claude.com/docs/en/whats-new/2026-w28`（200核实）

- `/doctor`（别名`/checkup`）从**只读诊断**升级为**主动修复**：检测未用 skills/MCP/plugins 造成的上下文开销、去重 CLAUDE.md、提出精简建议、揪出慢 hooks。
- Auto Mode 新增：会话记录**防篡改** + 对无法解析变量的 `rm -rf` 二次确认；后台任务通知明确声明"未发生任何人工输入"防止伪造批准被执行。

**SA 落点**：可把“上下文成本审计 + CLAUDE.md 去重”设计为**仓库健康检查流程**：经授权检查 `.claude/`/`AGENTS.md`/`CLAUDE.md` 冗余、未用 MCP 配置，作为“agent 配置体检”POC 的检查清单。自动修正前应展示差异并取得确认；本篇未验证该流程。

## 三、Anthropic《How we contain Claude across products》三层隔离架构（07-15 再确认为置顶重点文章）

来源：`www.anthropic.com/engineering/how-we-contain-claude`（200核实，原发布 2026-05-25，07-13起确认为 engineering 首页 featured）

三层防御模型（金句：**"先环境层隔离，再模型层引导"**）：

| 层 | claude.ai | Claude Code | Claude Cowork |
|---|---|---|---|
| 隔离机制 | ephemeral gVisor 容器 | Seatbelt(macOS)/bubblewrap(Linux) HITL 沙盒 | 密封本地 VM |
| 人工介入 | 无 | 批准疲劳→Auto Mode 降本83%误报 | 无 |
| 已披露真实漏洞 | — | trust-prompt前hook执行 | 员工钓鱼凭证外泄、白名单域名被滥用做数据渗出、EDR无法可见VM内部 |

关键数字（博客自述，**未复算**）：93%批准率、84%减少弹窗、83%拦截率（漏17%）、注入成功率0.1%~5-6%。

**三坑（逐字核实）**：
1. `settings.json` 在信任建立前就可能执行 hook；
2. 用户本身可作为注入向量（员工钓鱼→凭证外泄案例）；
3. allowlist 授予的是**能力**而非**目的地过滤**——即便域名在白名单，仍可能被滥用做数据渗出通道。

**SA 落点**：这是回答"自治 agent 跑 CI/POC 安全吗"的结构化模板——先讲清楚客户场景对应哪一层隔离（临时容器 vs HITL沙盒 vs 密封VM），再讲护栏（分类器/批准疲劳缓解），最后用三个真实漏洞案例做风险提示。**[→harness]**：可直接改写为 workshop 的"Agent 安全护栏"章节案例研讨题。

## 四、三条证据的组合叙事（面向客户的一页纸讲法）

1. **多 vendor 收敛**：Copilot/Claude Code/Codex 正在暴露相似的 permission-mode 抽象——客户不必押注单一厂商，"harness 抽象层可插拔多 agent 后端"是可信的架构原则。
2. **自我体检成为标配**：`/doctor` 证明"agent 配置需要定期审计"不是内部纪律而是产品化能力——POC 交付物应包含类似的配置健康检查步骤。
3. **隔离先于引导**：Anthropic 官方给出的三层模型是回答客户安全疑虑的最权威一手素材，环境层隔离（容器/沙盒/VM）永远排在模型层引导之前。

## 引用来源（全部已 curl 核实 200）
- https://github.blog/changelog/2026-07-07-codex-as-agent-provider-and-agentic-enhancements-in-jetbrains-ides/
- https://code.claude.com/docs/en/whats-new/2026-w28
- https://www.anthropic.com/engineering/how-we-contain-claude
