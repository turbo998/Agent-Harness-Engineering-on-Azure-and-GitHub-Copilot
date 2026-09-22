<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent 自体检 + 容器化收敛（Containment）速查

> 一句话主旨：**"agent 能力越强，越需要①运行时能自己审计自己的配置成本 ②厂商在环境层收敛能力边界（containment），而不是只靠 prompt 约束。"** 本篇合并两个 2026-07 新发现，直击"这套 skill/subagent/MCP 体系会不会越堆越乱""自治 agent 到底怎么被管住"两类客户高频追问。
> ⚠️ 全部来源已 curl 核实可达；行为随 CLI 版本演进，落地前按当前版本复核。

---

## 一、Claude Code `/doctor`（别名 `/checkup`）—— 运行时自体检工具

> ⚠️ **旧源复用**：本篇聚焦 `/doctor` 的交互模式（先报告→询问→用户确认才执行）与未使用 skill/MCP 的 token 成本诊断，不将其包装为首次发布。

来源：`code.claude.com/docs/en/whats-new/2026-w28`（curl 200 已核实，覆盖 2026-07-06~07-10，v2.1.202→v2.1.206）

**能做什么（逐条）**：
1. 诊断安装健康度（版本/依赖/权限配置）
2. **发现未使用的 skills / MCP servers / plugins，并报告它们占用的上下文 token 成本** —— 这是原研究快照中最值钱的一条：客户堆了一堆 skill/MCP 却不知道哪些从没被路由到、又在每次启动时白烧 token
3. 对 `CLAUDE.md` 给出"去重/瘦身"建议（内容冗余检测）
4. 标记运行慢的 hooks
5. **行为模式：先报告 → 询问是否修复 → 用户确认才执行**（不是自动改配置）

**SA 落点**：
- **技术问答**："我们上了很多 skill，会不会拖慢/费钱？" → 直接演示 `/doctor`，给出量化的"未使用 skill 的 token 成本"报告，比空泛建议更有说服力。
- **POC 部署**：交付验收清单里加一项"跑一次 `/doctor`，清理未用 skill/MCP"，作为上线前的标准动作。
- **反哺 harness workshop**：可设计“skill 库健康审计”练习，对比文件数量、路由命中和上下文成本；演示前先验证目标版本。
- 关联：可与 obra/superpowers 的 `verification-before-completion`（07-03 已固化进 `skill-quality-tdd-and-verification.md`）形成组合拳——那个管"完成声明要有证据"，这个管"配置本身要定期体检"。

---

## 二、Anthropic《How we contain Claude across products》—— Containment 设计的最新延续


**核心论点**：随着 agent 能力增强，"爆炸半径控制"（containment）问题变得更突出——不能只靠 prompt 层约束，要在**环境层**先做能力边界收敛，再叠加模型层引导。三条产品线（claude.ai / Claude Code / Cowork）各有不同的容器化/沙箱实现，但共享同一条设计哲学：**"先环境层隔离，再模型层引导"**。

**SA 落点**：
- 直接反哺 harness workshop 安全章节：客户问"自治 agent 跑 CI/生产会不会失控"，现在有三篇 Anthropic 官方一手文章可以连续引用（3/25→10/20→本篇），讲清楚这是一个持续在迭代的产品级问题而非一次性方案。
- 与 06-30 已固化的 `agent-command-execution-authz-tristack-cheatsheet.md`（OS层/运行时分类器层/云IAM层）互补——那篇讲"命令执行授权"的三层拆解，本篇讲"为什么需要 containment 这件事本身"的产品叙事视角。
- **未核实**：本篇具体的技术实现细节/数字未逐字比对（原研究快照中时间有限，仅确认文章存在、可达、是最新置顶内容），后续验证时可安排逐字深挖，比对是否有新于 06-27 已覆盖三产品隔离模型文章的具体技术差异点。

---

## 三、关联但原研究快照中仅轻触：Codex 并入 ChatGPT 桌面应用

来源：`developers.openai.com/codex/changelog`（308→200 已核实，最新头条 2026-07-09）

Codex 正式并入 ChatGPT 桌面 App（macOS/Windows），可作为默认视图；应用内直接编辑 Markdown/代码+行内批注；侧边栏直接看 GitHub PR review（含 reviewer 评论+diff）；单项目跨仓库工作；Computer Use 用 GPT-5.6 加速。

**SA 落点**：桌面 App 化是三大编码 CLI（Codex/Claude Code/Copilot）共同趋势，"PR review 内嵌侧边栏"可对标 Claude Code 的类似能力做 harness workshop 横向对比素材（具体差异尚需核实）。

---

## Fail-loud 声明
- `/doctor` 的具体报告格式/输出示例未实机跑一遍验证，仅依据官方 changelog 文字描述。
- `how-we-contain-claude` 一文的具体技术实现（沙箱类型/审批流数字）原研究快照中未逐字核实，仅确认文章存在且可达、当前为 Anthropic engineering 页面置顶内容。
- Codex 桌面 App 功能面未实机体验，仅依据官方 changelog 文字描述。

来源核实表：
| 来源 | URL | 状态 |
|---|---|---|
| Claude Code Week 28 | code.claude.com/docs/en/whats-new/2026-w28 | 200 |
| Codex changelog | developers.openai.com/codex/changelog | 308→200 |
| Anthropic containment 文章 | anthropic.com/engineering/how-we-contain-claude | 未逐字二次核实(仅访问确认存在) |
