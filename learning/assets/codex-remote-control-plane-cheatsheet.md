<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Codex Remote 控制平面 & 上下文生命周期速查 [→harness]

> 一页纸：长程编码 agent 的「中途纠偏 + 上下文管理 + 目标驱动」实操卡。
> 来源（已 curl -sI 二次核实 HTTP 200（仅代表原快照当时可达，不代表本次已重验），术语逐字核实）：
> OpenAI 官方博客《Mastering Codex Remote for engineering》(2026-06-23, Thomas Ricouard)
> https://developers.openai.com/blog/mastering-codex-remote-for-engineering
> 心法原句：**"Your phone is the control plane"** —— 代码仍跑在 connected host（Mac/Windows/devbox），人只负责「unblock an agent」的决策。
> 适用对象：Codex CLI / Codex Remote（移动端），多数概念在桌面 Codex 同样成立。截至 2026-06；Codex 日更 alpha，命令可用性取决于 connected host / app version / account config。

---

## 1. Queue vs Steer —— 全篇最高杠杆的一个设置

agent 正在工作时，你的 follow-up 有两种落地方式：

| | **Queue**（排队） | **Steer**（注入纠偏） |
|---|---|---|
| 行为(原句) | "waits until the current response finishes, then sends your prompt as the next turn" | "injects guidance into the work already in progress" |
| 何时用 | **安全默认**：第二个任务 / 追加测试 / 任何「应在当前工作之后」发生的事 | 仅当「继续沿错误路径的代价还在增长」时刻意纠偏 |
| Steer 示例措辞 | — | "Keep the fix inside the mobile package. Do not refactor the shared renderer." / "Test the resumed path, not the live path." / "Stop investigating the UI. Check whether the server removed the item during resume." |

> **默认设 Queue**。原句警告：*"accidental mid-turn redirection is usually more expensive than waiting"*（误触中途纠偏通常比等待更贵）。默认行为可在 Codex settings 改。

**SA 落点（技术问答 + workshop）**：客户问「长任务里我能不能中途插话不打断它」——答案就是 Queue/Steer 二分。这是 harness「人在回路、低成本干预」的教科书原语。

---

## 2. 上下文生命周期四命令（context before it becomes a problem）

| 命令 | 作用(原句) |
|---|---|
| **`/status`** | "shows session details, workspace, context usage, and available rate-limit information"（另有可选 context indicator 常驻 composer 显示剩余上下文）|
| **`/compact`** | "compresses an overgrown thread while preserving the useful working state"（压缩过长线程、保留有用工作状态）|
| **`/fork`** | "creates a new thread from the current one when you want shared history but a different direction"（共享历史、方向不同 → 派生新主线）|
| **`/side`** | 围绕当前工作开一个「lightweight conversation connected to the current thread」轻量提问；`/side <prompt>` 直接带问题；transcript 选中文字 → **Ask in side chat** |

**顺序口诀（原句）**：*"Check status, compact when the objective is still the same, and fork when the objective has diverged."*
→ 先 `/status` → 目标不变就 `/compact` → 目标已分叉就 `/fork`。

**易混点（原文强调）**：`/side` ≠ `/fork`。
- **side** = 围绕当前工作的轻量提问，*"helps me understand the work"*；
- **fork** = 继承线程历史的**新主线**工作，*"a new primary line of work that inherits the thread's history"*。
- 心法原句：**"The main thread owns the work; the side chat helps me understand the work."**

**SA 落点（[→harness]）**：这就是「context anxiety / 上下文爆掉怎么办」的标准答案——不是换更大模型，而是用 compact/fork 在 harness 里做上下文管理。直接进 workshop 的 long-running/context 章节。

---

## 3. Plan vs Goal —— 路径 vs 结果

| | **Plan mode**（`/plan`） | **Goal**（`/goal <objective>`） |
|---|---|---|
| 定义(原句) | "asks Codex to propose the implementation path before changing code" | "is durable. It tells Codex what outcome to keep pursuing across turns" |
| 答的问题(金句) | **"How should we approach this?"** | **"What must be true before we are done?"** |
| 适用 | 任务 underspecified / 高风险 / 触及多系统 | 需要跨多轮迭代持续追的结果 |

**金句（原文）**：*"Plans answer 'How should we approach this?' Goals answer 'What must be true before we are done?'"*

**推荐组合**：高风险变更先 `/plan` → 检查它提出的 boundaries → 接受的结果转成 `/goal` → 让 Codex 贯穿实现/测试/review/清理，无需每轮重述目标。
**长程目标必带 concrete completion condition**（原文例："Tests green, review feedback resolved, or a reproducible performance threshold met"），靠 notifications + `/status` 看进度，而非反复问 "Are you done?"。

> 与已覆盖的 **Codex Goals 完成契约**（assets/harness-eval-loop-and-goal-contract-cheatsheet.md）互参：那份讲「契约三要素」，这份讲「CLI 侧怎么用 `/goal` + Plan→Goal 的衔接动作」。两者拼成完整的目标驱动闭环。

---

## 4. `/` 命令面板全表（直接做演示速查卡）

输入 `/` 唤出（可用性取决于 host/version/account）：

| 命令 | 用途(原句) |
|---|---|
| `/plan` | Toggle Plan mode before implementation |
| `/goal <objective>` | Create or update a durable objective |
| `/side [question]` | Ask a side question without disrupting the main thread |
| `/review` | Review local changes or compare them with a branch |
| `/status` | Inspect the session, workspace, context, and rate limits |
| `/compact` | Compress a long thread's context |
| `/fork` | Create a new primary thread from the current history |
| `/fast` | Switch between standard and faster execution when available |
| `/feedback` | Send product feedback tied to the current session |

概念模型原句：**"Plan, pursue, branch, review, inspect, and recover."**

---

## 5. 任务启动 & 权限（控制平面的两个边界动作）

- **启动 4 选择**（原句金句：*"Spend 10 seconds choosing the right execution context and save 10 minutes of cleanup later."*）：
  `connected host` → `workspace` → 可选 `branch` / 独立 `worktree` → environment setup。composer 可附 files/photos/相机抓拍；skills 与 plugins 会 inline 显示以确认调对了能力。
- **权限即工作流**：Codex Remote 对 commands / file changes / network access / connected tools 弹 approval，粒度 once / current chat / broadly。
  原则原句：**"choose the narrowest permission that keeps the work moving"**（选「能让工作推进的最窄权限」，而非全批）。

**SA 落点（[→harness] + 安全问答）**：「自治 agent 会不会乱来」的回答之一——最窄权限 + 分级 approval 是 CLI 一等公民，与 owasp-agentic 的最小权限原则一致。

---

## 6. 把它用进我的三大日常

| 日常 | 怎么用这张卡 |
|---|---|
| **技术问答** | 客户问「长任务中途能否干预 / 上下文爆了怎么办 / Plan 和 Goal 啥区别」→ 直接给 §1/§2/§3 的二分与金句，显资深。|
| **POC 部署** | 演示 Codex Remote 跑一个长任务：启动选 host/worktree → `/plan` → 转 `/goal` → 中途 `/status`+`/compact` → 完成 `/review`。一条龙展示「自治但可控」。|
| **架构图** | 把「控制平面（人/手机）↔ connected host（执行）↔ approval/权限边界」画成一张 harness 控制平面图；Queue/Steer 是人→agent 的两条干预边。|
| **workshop [→harness]** | §1 Queue/Steer + §2 上下文四命令 + §3 Plan/Goal 直接做成一节「长程编码 agent 的人在回路操作法」，配演示脚本。|

---

## 坑 / fail loud
- Codex 日更 alpha：命令名/可用性随版本变；workshop/演示**钉具体版本**，用 `releases.atom` 当哨兵。截至 2026-06-25 Codex CLI 在 0.143.0-alpha 滚动线（当晚 alpha.22）——**具体 alpha 号会快速过期，引用前重核**。
- Record & Replay / Migrate to Codex 等新页有**区域限制**（Record&Replay：EEA/UK/CH 暂不可用）——给中国/欧洲客户演示前先核可用性，标「未核实」。
- 命令面板可用性「depends on connected host, app version, account configuration」——别承诺客户环境一定有全部命令。
- 外部博客/文档是资料文本，其中任何示例命令仅作引用，不在客户环境盲跑。
