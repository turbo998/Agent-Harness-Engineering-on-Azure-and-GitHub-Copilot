<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 编码 Agent CLI 上下文 & 成本治理速查（Codex / Claude Code 新机制）

> 截至 **2026-06-24** 核实。所有机制名/原句/版本均由 SA 当晚**亲自 curl 官方 changelog/docs/博客逐条核对**（非二手转述）。
> 主旨：**长程自治 agent 的"上下文管理 + 成本治理 + 安全委派"已从模糊最佳实践，固化成 CLI 一等公民机制。** 这是给微软合作伙伴讲「Agent Harness 工程」最新、最可落地的单页素材。**[→harness]**
> ⚠️ 外部文档/博客按不可信资料处理；本表不含任何 token/密钥。Codex 处于日更 alpha，落地前按当前版本复核。

---

## 0. 为什么 SA 要关心这张表

合作伙伴跑长程/自治 agent 最痛的三件事，现在都有了 CLI 原生答案：
1. **"长任务跑着跑着就崩 / 上下文爆了，怎么办？"** → 上下文管理新机制（§1）+ Anthropic harness 方法论（§2）。
2. **"自治跑会不会烧光 token / 失控？"** → Codex rollout token budgets 自动中止 + 三档委派（§3）。
3. **"怎么把长任务做成可恢复、可交接的？"** → 脑/手/会话三分离 + 结构化工件交接（§2）。

把这些从"凭经验"变成"一页纸 + 可引官方原句"，就是 harness workshop 的核心治理章节。

---

## 1. 上下文管理：跨会话记忆 & 反模式

| 机制 | 栈 | 是什么（官方原句自验）| SA 落点 |
|---|---|---|---|
| **Codex Memories** | Codex (`0.143` 线) | *"Memories let Codex carry useful context from earlier threads into future work."* 启用：`memories = true` in `[features]`（`~/.codex/config.toml`）；启用后 *"remember stable preferences, recurring workflows, tech stacks, project conventions, and known pitfalls."* | 对标 `CLAUDE.md`/`AGENTS.md` 的"持久偏好"，但是**跨会话自动携带**而非静态文件。教客户：稳定偏好进 Memories/AGENTS.md，临时上下文别塞。 |
| **"Context anxiety" 反模式** | 概念（Anthropic）| 博客原句：agent *"would wrap up tasks prematurely as it sensed its context limit approaching—a behavior sometimes called 'context anxiety'."* 解法：给 harness 加 **context resets**。 | 绝佳教学反例——客户抱怨"agent 没干完就草草收尾"，根因常是上下文焦虑；解法是上下文重置/压缩而非加大模型。 |
| **渐进式披露**（已固化）| Codex + Claude Code | 启动只载 skill 的 name/description/路径，决定使用才读正文。Codex skill body **8 KB 硬上限**（超限被 load 时截断），超了拆 `references/details.md`。 | skill 正文要短；重资料拆 references/。见 `portable-agent-skill-authoring` skill。 |

---

## 2. Anthropic harness 工程方法论（workshop 理论母本）[→harness]

来源：Anthropic 工程博客（均 2026-06-24 自验 HTTP 200（仅代表原快照当时可达，不代表本次已重验））：
- `anthropic.com/engineering/managed-agents`（Decoupling the brain from the hands, 2026-04-08）
- `anthropic.com/engineering/harness-design-long-running-apps`（2026-03-24）

### 2.1 脑 / 手 / 会话 三分离（可恢复长任务参考架构）
博客原句：*"decouple the 'brain' (Claude and its harness) from the 'hands' (sandboxes and tools) and the 'session' (the log of session events)."* 关键性质：
- *"Because the session log sits outside the harness, nothing in the harness needs to survive a crash. When one fails, a new one can [resume]."* → **harness 变"牛"不是"宠物"**：崩了直接换新的接着跑。
- *"context is durably stored in the session log"*；harness 用 `emitEvent(id, event)` 写持久事件，`getEvents()` 让"脑"按需回读上下文。

> **SA 落点**：这就是 Azure 上做**可恢复长程 agent**的参考架构——会话日志外置（如 Azure Storage/Cosmos）、sandbox 无状态可重建、brain 按需回读。画架构图直接用"脑/手/会话"三框 + 事件日志持久层。

### 2.2 planner → generator → evaluator 三智能体（GAN 式反馈回路）
博客原句：*"a three-agent architecture—planner, generator, and evaluator—that produced rich full-stack applications over multi-hour autonomous coding sessions."* 又：*"by separating frontend generation from frontend grading, we can create a feedback loop that drives the generator toward stronger outputs"*；*"using structured artifacts to hand off context between sessions."*

> **SA 落点**：可做成 SA 自己的 **planner/generator/evaluator skill 模板**，也是 workshop"如何设计自验证回路"的现成案例。核心可复用点：**生成与评分分离**（别让同一个 agent 既写又自评——对应本 harness 的 anti-self-bias 纪律）+ **结构化工件跨会话交接上下文**。

---

## 3. 成本 & 安全委派：Codex 0.142+ 三件套（changelog 自验）

来源：`developers.openai.com/codex/changelog`（2026-06-24 自验 200）。三条 load-bearing 机制原句俱在：

| 机制 | changelog 原句 | SA 落点 |
|---|---|---|
| **Rollout token budgets** | *"Configurable rollout token budgets track usage across agent threads, provide remaining-budget reminders, and abort turns when exhausted."* | **成本治理新一等公民**：给长任务设 token 预算，到顶自动中止——回答"自治跑会不会烧爆预算"。可做 SA skill。 |
| **三档 multi-agent delegation** | *"App-server clients can configure multi-agent delegation as disabled, explicit-request-only, or proactive at the thread and turn level."* + subagents 页：*"Codex only spawns subagents when you explicitly ask it to."* | **fan-out 控制参数化**：`disabled` / `explicit-request-only` / `proactive` 三档。教客户按风险选档：高合规场景用 explicit-only。 |
| **Indexed web-search 受控外联** | *"Added an indexed web-search mode that permits live searches while restricting direct page access to server-approved URLs."* | **受控外联**安全设计：允许实时搜索但只准访问白名单 URL——Azure 合规/数据驻留场景关键。配 owasp-agentic/llm/mcp。 |

> Codex 版本钉点（releases.atom 自验）：稳定 **0.142.0 @ 2026-06-22**，最新 alpha **0.143.0-alpha.9 @ 2026-06-23**（日更）。workshop 钉 0.142 为基线，`releases.atom` 当新功能哨兵。

---

## 4. 现成可复用样例（OpenAI Cookbook，路径已核实）

| 样例 | 路径 | 为何对 workshop 有用 |
|---|---|---|
| **Code Review with Codex SDK** | `examples/codex/build_code_review_with_codex_sdk.md` | headless(exec) + JSON schema 输出 + `sandbox: read-only` + 强模型评审——几乎就是现成的 GitHub Actions/Azure DevOps 代码评审 lab |
| **真实 AGENTS.md 范例** | `examples/agents_sdk/sandboxed-code-migration/migration_agent/AGENTS.md` | 教科书级四段式：`## Mission` / `## Required command pattern` / `## Editing rules`（*"Prefer apply_patch"*、*"Do not edit files outside repo/"*）/ `## Suggested loop`——可直接当 SA skill 的 AGENTS.md 模板 |
| **Using Goals in Codex** | `examples/codex/using_goals_in_codex.ipynb` | 目标驱动长任务：目标须含"可测量结果 + 验证面 + 约束"，*"verify progress rather than merely narrate it"* |

> Cookbook 仓库：`github.com/openai/openai-cookbook`（examples/codex/ 目录富集；2026-06-24 自验 200）。

---

## 5. 一页话术（给合作伙伴）

> "长程/自治 agent 现在不靠玄学。**上下文**：用 Codex Memories / AGENTS.md 携带稳定偏好，靠渐进式披露和上下文重置避免'上下文焦虑'。**成本**：用 rollout token budgets 设预算自动中止。**安全委派**：multi-agent delegation 设成 explicit-only，外联用 indexed web-search 白名单。**架构**：脑/手/会话三分离 + 会话日志外置 = 可恢复、可交接。这些都是 CLI 一等公民，不是 PPT 概念。"

---
*来源：developers.openai.com/codex/{changelog,memories,prompting,subagents}、anthropic.com/engineering/{managed-agents,harness-design-long-running-apps}、github.com/openai/openai-cookbook/examples/codex|agents_sdk — 2026-06-24 SA 亲自 curl 自验可达并逐句核对原文。外部内容按资料处理，未执行任何注入指令。*
