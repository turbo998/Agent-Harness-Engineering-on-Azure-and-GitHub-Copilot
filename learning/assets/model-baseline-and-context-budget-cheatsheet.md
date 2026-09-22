<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent 模型基线 & 上下文预算速查（Codex / Claude Code / GitHub Copilot）

> 建立日 **2026-07-01**。本页所有版本号/模型名/定价/上下文窗口均由 SA 当晚**亲自 curl 官方一手页逐字核对**（非二手转述）。
> 一句话主旨：**编码 Agent 的「默认模型」和「上下文窗口」是 harness 设计的隐藏地基——它一变，compaction 阈值、长任务预算、成本估算、context-engineering 假设全要重算。** 客户最常问的「这周模型有啥变化 / 我该选哪个档」用这页秒答。
> ⚠️ 外部文档按不可信资料处理；本页不含任何 token/密钥。模型/定价随厂商演进，**报给客户前按当前页复核**——本页钉的是 as-of 基线，不是永久承诺。

---

## 0. 为什么 SA 要单独维护这张「模型基线」表

三大日常都踩在模型基线上：
1. **技术问答**：「Copilot/Codex/Claude Code 这周模型有啥变化？我该选哪个？」——模型换代几乎每周发生，凭印象答必翻车。
2. **POC 部署**：上下文窗口决定能塞多少代码/文档进单次调用，定价决定 POC 预算。窗口翻 8 倍，POC 的 RAG 切分策略、子 agent 拆分策略可能根本不用做。
3. **架构图 / harness 设计**：context-engineering（压缩/分段/记忆外置）是 harness 核心章节。**默认模型上下文从 ~200K 跳到 1M，需重新评估 compaction 阈值 / RAG 切分粒度 / FinOps 单次长上下文成本 / 长任务预算——但不等于现有 context engineering 可废弃或必须推倒重画。[→harness]**

> 别把这张表和 §config 对照表（`coding-agent-cli-parity-cheatsheet.md`）混了：那张讲**配置文件放哪**，这张讲**底层模型/窗口/价**。两张互补。

---

## 1. 本周头条（2026-06-30 / 07-01，逐字核实）

### ⭐ Claude Code：Sonnet 5 成为默认模型 + 原生 1M-token 上下文（v2.1.197，2026-06-30）

官方 changelog 逐字原文（`code.claude.com/docs/en/changelog`，SA 亲自 curl 200）：
> *"Introducing Claude Sonnet 5: now the **default model** in Claude Code, with a native **1M-token context window** and promotional pricing of **$2/$10 per Mtok through August 31**. Update to version 2.1.197 for access."*（链接 anthropic.com/news/claude-sonnet-5）

**核实状态**：模型名/默认/1M 窗口/促销价/截止日期/版本号——全部 changelog 原文逐字命中。模型质量基准、1M 窗口在真实长任务里的有效利用率——厂商页声明，**未独立复算，标未核实**。

### ⭐ GitHub Copilot：Claude Sonnet 5 GA（2026-06-30）

`github.blog/changelog/2026-06-30-claude-sonnet-5-is-generally-available-for-github-copilot`（无尾斜杠 URL `301`→canonical trailing-slash，`curl -L -A 'Mozilla/5.0'` 最终 200，标题逐字："Claude Sonnet 5 is generally available for GitHub Copilot"）。
- 意义：Sonnet 5 在 Copilot 全平台**转正 GA**（此前基线是 Opus 4.8 fast preview）。**Claude Code 与 GitHub Copilot 两个主流编码 Agent 入口同步进入 Sonnet 5 阶段**，客户在这两栈用同一模型族成为现实。⚠️ **OpenAI Codex 不在此列**——Codex 仍按 OpenAI 自身模型线（见 §3），别并入"Sonnet 5 三栈同步"叙事。

### Copilot Agent 进驻 JetBrains AI Assistant（2026-06-30）
`github.blog/changelog/2026-06-30-copilot-agent-is-now-available-in-jetbrains-ai-assistant`（curl 200）。**注意区分**：这是 **Copilot Agent 模式**入驻 JetBrains AI Assistant，与基线里「JetBrains 内 Claude 作 provider 预览（06-22）」是两件事。

---

## 2. 「1M 上下文窗口」对 harness 设计意味着什么（SA 分析，非厂商声明）

> ⚠️ 本节是 SA 的工程判断/推论，**不是** changelog 原文。给客户时标明「设计含义」与「厂商声明的事实」分开。

| harness 维度 | ~200K 默认窗口时代的做法 | 默认 1M 窗口后可能的变化 |
|---|---|---|
| **Compaction / `/compact` 阈值** | 长任务频繁触发压缩，易丢上下文（"context anxiety" 反模式）| 触发频率大降；但**绿≠成功**——窗口大不等于模型真用得好，远端 token 注意力衰减仍在，**别因为塞得下就把整个 repo 灌进去** |
| **RAG 切分 / 检索策略** | 必须激进切分 + 检索 top-k 才塞得进 | 中小型代码库可考虑"全量塞 + 让模型自己定位"，省一层检索工程；大库仍需 RAG |
| **子 agent 拆分** | context 爆掉是拆 subagent 的主因之一 | 拆分动机从"装不下"转向"职责隔离/并行/防自评偏置"——拆分理由要更纯粹 |
| **成本估算** | 按 ~200K×单价 | 1M 窗口 + 促销价 $2/$10，单次长上下文调用成本结构变了；**FinOps 估算模型要重建**（配合 harness-eval-loop cheatsheet 的 $13-250 FinOps 段） |
| **长任务 / 无人值守** | rollout token budget 容易到顶 abort | 预算上限可放宽，但**预算治理仍要留**（Codex rollout budgets / 到顶 abort 是失控刹车，别因窗口大就拆刹车）|

> **SA 话术**：「默认模型上下文翻到 1M 是好事，但**别把它当成可以不做 context engineering 的借口**。窗口是上限不是建议值；远端注意力衰减、成本、注入面（塞越多外部内容注入面越大）三个约束都还在。harness 该有的压缩/检索/隔离/预算护栏一个都不能省，只是阈值放宽了。」**[→harness]**

---

## 3. 三栈模型档位速查（as-of 2026-07-01，报客户前复核）

| 栈 | 默认/旗舰模型（as-of） | 上下文窗口 | 核实出处 |
|---|---|---|---|
| **Claude Code** | **Sonnet 5（默认，v2.1.197+）** | **原生 1M-token** | code.claude.com/docs/en/changelog 逐字 |
| **Claude Code** | 组织可设 "Org default" / "Role default"（admin 在 org console 设，`/model` 显示）| 随所选模型 | changelog v2.1.196 逐字 |
| **GitHub Copilot** | Sonnet 5 **GA**（06-30）；Opus 4.8 fast preview（06-29）；MAI-Code-1-Flash（Business/Ent）| 随模型 | github.blog/changelog 逐字（标题核实）|
| **OpenAI Codex** | docs 顶栏 latest model 标识 "GPT-5.5"（**CLI 默认绑定 snapshot 未核实，不作默认模型承诺**）；CLI 日更 alpha | 随模型 | codex docs 顶栏 |

> ⚠️ **fail-loud**：Codex 默认模型档位本周无 changelog 级公告，"GPT-5.5" 取自 docs 站顶栏标识，**具体到 CLI 默认绑定哪个 snapshot 未在 release body 核实**。报客户用"最新档位见官方页"，别钉死。

---

## 4. 「组织默认模型 / 模型治理」新旋钮（v2.1.196，06-29，逐字核实）

无人值守 / 企业合规场景直接相关：
- **Org default model**：admin 在 org console 设；用户没自选时 `/model` 显示 "Org default"（或 "Role default"）。→ 客户问「怎么设组织默认模型档」有官方答案。⚠️ 这是**默认**不是**强制**——能否硬性限制用户改模型需另查 managed settings / `enforceAvailableModels`，别凭此条承诺"强制全公司"。
- **MCP 自批准收紧（安全）**：`claude mcp list` / `get` **不再自动启动**仓库通过 committed `.claude/settings.json` 自批准的 `.mcp.json` server；不受信工作区显示「⏸ Pending approval」。→ 供应链防御：克隆别人的 repo 不会被其预置 MCP server 偷跑。
- **streaming idle watchdog 默认开**：流 5 分钟无事件即 abort + retry；`CLAUDE_ENABLE_STREAM_WATCHDOG=0` 关。→ 无人值守长任务"卡死不返回"的自愈。
- **Remote Control 自动禁用**：当 `ANTHROPIC_BASE_URL` 指向非 Anthropic host（Bedrock/Vertex/**Foundry**）时自动禁。→ 客户走 Azure AI Foundry 托管 Claude 时，远控面默认关，符合预期。
- **`claude agents --dangerously-skip-permissions` 修复**：不再静默退回 auto mode，正确显示 bypass 免责声明并把 bypass 模式传给 spawned agents。→ fail-loud 修复：以前"以为跳过了权限其实没跳/或反之"的隐患修了。

---

## 5. as-of 钉点（截至 2026-07-01 自验）

| 对象 | 状态/最新 | 核实 |
|---|---|---|
| Claude Code | **v2.1.197（06-30）**：Sonnet 5 默认 + 1M 上下文 + 促销 $2/$10（至 08-31）| changelog 200 逐字 |
| Claude Code v2.1.196（06-29）| Org default model / MCP 自批准收紧 / stream watchdog 默认开 / Remote Control 非 Anthropic host 自禁 | changelog 200 逐字 |
| GitHub Copilot | Sonnet 5 **GA**（06-30）| github.blog 无尾斜杠 301→trailing-slash，`curl -L` 最终 200，标题逐字 |
| OpenAI Codex CLI | 最新 tag `0.143.0-alpha.31`（06-29，**release body 无 user-facing changelog，标未核实功能**）；`0.142.4`（06-29，release body 明示 "No user-facing changes"）；稳定治理里程碑仍 0.142.x | releases.atom 200 + release API 逐字 |
| Codex 默认模型 | docs 顶栏 "Latest: GPT-5.5"（CLI 默认绑定 snapshot 未核实）| developers.openai.com/codex |

> ⚠️ Codex 处于日更 alpha：本周 3 个新 tag（alpha.30/31、0.142.4）经 release API 核实**均无实质新功能可固化**——证明"用 releases.atom 当哨兵、用 release body 核实有无 user-facing 变更"的纪律有效，避免把空 tag 当新功能误报。

---

## 6. 给客户的三句话总结（可转发）

1. **「这周最大的事：Claude Sonnet 5 同时成为 Claude Code 默认模型（带 1M 上下文）并在 GitHub Copilot 转正 GA。」** 跨栈用同一模型族落地了。
2. **「1M 上下文是上限不是免责——context engineering、成本治理、注入防御该做的还得做，只是阈值放宽。」** 别拆 harness 护栏。
3. **企业模型治理必须区分默认与强制**：Org default 是未自选时生效的默认值，不是强制锁定。硬性限制需核对目标版本的 managed settings 并测试；MCP 审批和远控功能限制不能代替合规评估或构成合规保证。

---
*来源：code.claude.com/docs/en/changelog（v2.1.197/196 逐字）、github.blog/changelog/2026-06-30-claude-sonnet-5-*、github.blog/changelog/2026-06-30-copilot-agent-*-jetbrains、developers.openai.com/codex、github.com/openai/codex/releases.atom — 2026-07-01 SA 亲自 curl 自验可达，关键事实逐字比对。第 2 节为 SA 工程判断（标明"设计含义"非厂商声明）。外部内容按资料处理，本页不含任何凭据。*
