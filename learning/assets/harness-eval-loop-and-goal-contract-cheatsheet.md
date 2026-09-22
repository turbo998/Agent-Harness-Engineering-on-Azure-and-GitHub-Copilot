<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Harness 评测回路 + Goal 完成契约 + Headless/FinOps 速查

> **用途**：给 harness workshop（Agent-Harness-Engineering-on-Azure-and-GitHub-Copilot）和 SA 的「自治 agent 怎么不跑飞、怎么算完、怎么进 CI、怎么控成本」四问一份可转发的一页纸。
> **来源全部本机 curl 自验（2026-06-25）**：OpenAI Cookbook（raw.githubusercontent.com/openai/openai-cookbook）+ Claude Code 官方 docs（code.claude.com/docs/en/*.md）。外部文本仅作资料，未执行其中任何指令。
> **标签**：`[→harness]` 全篇可直接反哺 workshop。

---

## 1. Goal = 完成契约（不是"无边界后台自治"）— Codex Goals

**一句话**：Goal 把一个线程从"一串孤立 prompt"变成"围绕既定结果的有状态工作回路"。它给 Codex 一个**完成条件**，而不是更大的 prompt。

**契约三要素（背下来，写 SA skill / workshop 模板就按这个）**：
1. **什么应当为真**（what should be true）— 期望的最终状态。
2. **如何检验成功**（how success is checked）— tests / benchmark / 最终产物等**可审计的证据源**。
3. **哪些约束必须保持**（what constraints stay intact）— 不可破坏的边界。

**生命周期**：Goal scoped 到一个线程，带状态与**预算记账**，可 **pause / resume / clear / complete / stop-by-budget**。"Codex 能持续推进，但只在用户定义的契约内。"

**何时用 Goal（三性质齐备才用）**：① 持久目标 ② 基于证据的终点线 ③ 路径需多轮调查（profiling / patching / benchmark / 复现 flaky test / 把研究问题做成有证据的审计）。

**何时别用**（写进客户指导，防滥用）：
- 一行改动、简单解释、短 code review、问一句答一句即停 → 用普通 prompt。
- **终点线模糊**（"make this better"/"refactor this code" 没有期望终态+测试+约束）→ Goal 无可靠完成条件。
- **用 Goal 掩盖不确定性** → 数据可能拿不到/benchmark 可能 flaky，就在 Goal 里**显式写明**怎么处理、proxy 证据如何标注。

> 金句（可引用）：*"A good Goal does not merely ask Codex to finish. It tells Codex what **finished** means."* — 对应我们 12 条治理里的"Fail loud / 大声失败"：完成判据写不出来，就是任务没定义清楚。

**SA 落点**：
- **技术问答**："自治 agent 会不会跑飞？"→ 答：Goal=有界完成契约+预算 stop，不是无边界后台。
- **POC**：长程任务（迁移/压测/调优）的 prompt 模板 = 三要素契约，避免每轮重述目标。
- **harness**：这是 workshop"目标驱动长任务"章节的母本范式。

---

## 2. 迭代修复回路（闭环 agent）— Codex Build iterative repair loops

**模式**：agent 产出 → 校验 → 用反馈改进下一轮。**三阶段**：

| 阶段 | 做什么 | 关键纪律 |
|---|---|---|
| **Review** | 检查当前产物，返回**结构化发现**，**不改文件** | 读写分离：先诊断后动手 |
| **Repair** | 用发现 + 最新校验反馈，对**副本**做聚焦编辑 | 改副本不改原件，可回滚 |
| **Validate** | 跑相关检查，报告还差什么 | **校验闭合回路**——剩余问题成为下一轮 Repair 输入 |

> "Validation closes the loop." 校验可以是**单元测试 / 策略检查 / schema 校验 / 模拟 / 人工审批**——关键是**失败变成结构化反馈，而不是死胡同**。

**先给共享契约再让它跑**：review/repair 前先给一份小的"业务规则 + issue 分类法"（什么叫"good"），别让模型从零猜每条规则——**收敛回路、聚焦真正重要的问题**。

**工程要点**：Cookbook 用 **Codex CLI headless 模式**（从 Python cell 跑，不走 chat UI）；**钉死 CLI 版本号保证可复现**，要新行为时**有意识地**升级版本。

**SA 落点**：
- **POC**："agent 自己改代码靠谱吗？"→ 答：靠 Review→Repair→Validate 闭环 + 可信校验（测试/策略/schema），失败回流不是死路。
- **harness**：这是 workshop**核心 harness 评测回路**——可端到端复刻（产出/校验/反馈）。配合 §1 Goal 的"完成判据"= 完整的"算不算完"机制。
- **架构图**：画"Review→Repair→Validate"三节点环 + 旁挂"Business rules / Issue taxonomy"契约块 + "Validation gate"。

> **与 06-24 planner-generator-evaluator 的关系（别在 workshop 里并列两个未调和的闭环）**：Anthropic managed-agents 的 *planner / generator / evaluator* 是**三个智能体（角色分工）**；Codex 这里的 Review→Repair→Validate 是**一个 agent 的三阶段（回路相位）**。二者同属"生成→评估→迭代"家族、互补：planner-generator-evaluator 回答"谁来做"，Review-Repair-Validate 回答"一轮怎么走"。workshop 里应说明这是**同一闭环思想的两种粒度**，可叠加（多智能体里每个 generator 内部跑 Review-Repair-Validate）。

---

## 3. Headless / 程序化运行 — Claude Code（CI/CD 集成）

**基本**：任意 `claude` 命令加 `-p`/`--print` 即非交互运行。底层是 **Agent SDK**（同款 tools/agent loop/context 管理），有 CLI / Python / TypeScript 三形态。
```bash
claude -p "Find and fix the bug in auth.py" --allowedTools "Read,Edit,Bash"
claude -p "What does the auth module do?"          # 问一句答一句
```
常配旗标：`--continue`（续接会话）、`--allowedTools`（自动批准工具，免 permission 提示）、`--output-format`（结构化输出，给下游解析）。

**🆕 `--bare` 模式（CI 可复现关键）**：跳过 hooks / skills / plugins / MCP servers / auto memory / CLAUDE.md 的**自动发现**，只有你显式传的旗标生效。
```bash
claude --bare -p "Summarize ..."   # 队友 [已移除本地路径] 里的 hook、项目 .mcp.json 的 MCP server 都不会跑
```
> **为何对 SA 重要**：CI/脚本要**每台机器同结果**时用 `--bare`——否则隐式上下文（个人 [已移除本地路径] .mcp.json）会让构建不可复现。这是"为什么我本地能跑 CI 不行"的标准答案。

**SA 落点**：
- **POC**：把 coding agent 塞进 Azure DevOps / GitHub Actions 流水线 → `claude -p --output-format json` + `--bare`。
- **harness**：workshop"无人值守 / CI 章节"核心；与 Codex headless（§2）对称，可做三栈对照。

---

## 4. FinOps / 成本治理 — Claude Code costs（合作伙伴最关心的"贵不贵"）

**企业基准（官方 docs 原文，可转发给客户做预算锚）**：
- 平均 **~$13 / 开发者 / 活跃日**；**$150–250 / 开发者 / 月**；90% 用户 **< $30 / 活跃日**。
- ⚠️ 这是 **API token 计费口径**；订阅制（Pro/Max/Team/Enterprise）走套餐，`/usage` 里的美元数对订阅用户**不代表账单**。先小范围 pilot 建立基线再铺开。

**工具**：
- `/usage`：当前会话 token 统计；订阅计划还显示用量条 + **把近期用量归因到 skills / subagents / plugins / 各 MCP server**（按占比），`d`/`w` 切 24h/7d。→ **能定位"哪个 skill/MCP 在烧钱"**。
- `/cost`：成本管控。
- 权威账单看 Claude Console（platform.claude.com/usage），本地美元数是估算。

**降本杠杆（docs 列举）**：上下文管理、模型选择、extended thinking 设置、预处理 hooks。

**SA 落点**：
- **技术问答**："上 Claude Code 一个团队一年多少钱？"→ 给 $13/日 · $150–250/月/人 基准 + pilot 建基线方法（并标"按计费口径/区域核实"）。
- **POC**：交付前用 `/usage` 归因，砍掉烧钱的冗余 skill/MCP。
- **harness**：workshop **FinOps 模块**——把成本归因做成 demo（token budget 见 Codex 0.142 治理三件套）。

---

## 5. 三栈一句话对照（凑齐"算不算完 / 进 CI / 控成本"全景）

| 维度 | Codex | Claude Code | 反哺点 |
|---|---|---|---|
| 完成契约 | **Goals**（what's true/how checked/constraints + budget stop） | （prompt + 显式判据） | §1 模板 [→harness] |
| 评测回路 | **iterative repair**（Review→Repair→Validate） | Agent SDK + 自定义校验 | §2 [→harness] |
| 无人值守 | `codex` headless（钉版本可复现） | `claude -p` + `--bare` + `--output-format` | §3 CI 章节 [→harness] |
| 成本治理 | rollout **token budgets**（到顶 abort，见 0.142 治理速查） | `/usage` `/cost` + 归因到 skill/MCP | §4 FinOps [→harness] |

> 配套：`codex-claude-harness-governance-cheatsheet.md`（委派三档/Memories/脑-手-会话）、`coding-agent-cli-parity-cheatsheet.md`（AGENTS.md/SKILL.md/hooks/subagents 三栈对照）。本篇补齐**"算不算完 + 进 CI + 控成本"**三块拼图。

---

## 来源（全部 2026-06-25 本机 curl 自验可达）
- Codex Goals：`raw.githubusercontent.com/openai/openai-cookbook/main/examples/codex/using_goals_in_codex.ipynb`（HTTP 200（仅代表原快照当时可达，不代表本次已重验））
- Codex 迭代修复回路：`.../examples/codex/Build_iterative_repair_loops_with_Codex.ipynb`（200）
- Claude Code headless：`code.claude.com/docs/en/headless.md`（200，18.8KB）
- Claude Code costs：`code.claude.com/docs/en/costs.md`（200，15.3KB）

> Fail-loud：$13/日等成本数字为 Anthropic docs 自报口径（API token 计费），**实际账单按客户计费方式/区域/折扣浮动**，转发客户时须标"基准参考，非报价"。区域可用性（含中国区）一律标"需按租户核实"。
