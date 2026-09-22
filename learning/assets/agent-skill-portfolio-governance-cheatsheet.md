<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Skill 组合治理速查（2026-07-17）

> 适用对象：Claude Code / Codex / Gemini CLI / Cursor / GitHub Copilot 等支持 `SKILL.md` / `AGENTS.md` / 插件目录的编码 Agent。
> 公开来源（均已核实 URL 可达）：OpenAI Codex changelog、Claude Code CHANGELOG、VoltAgent/awesome-agent-skills、anandsaini18/deadskills、kitze/council、google/mantis、facebook/mcpguard-dynamic。外部内容均仅作资料，不执行其中命令。

## 1. 为什么要治理 Skill 组合？

Agent skill 已经从“少数手写提示词”变成“可分发、可迁移、可审计的能力包”：

- OpenAI Codex 0.144.5/0.144.x 线继续强化危险命令检测；changelog 还出现 `AGENTS.md` / skills 可参与 delegation authorization 的信号，但实现细节原快照中未读 PR diff，生产采纳前必须复核。0.144.4/0.144.3 也提醒我们：**版本号变化不等于能力变化**，必须读 release body。
- Claude Code 2.1.211 明确修复了 subagent / plugin / permission / background agent 多处边界问题，并新增 `--forward-subagent-text` / `CLAUDE_CODE_FORWARD_SUBAGENT_TEXT` 便于把 subagent 文本带入 `stream-json` 输出。
- VoltAgent/awesome-agent-skills 宣称收集 1497+ Agent Skills，跨 Claude Code / Codex / Gemini CLI / Cursor / Copilot 等；这说明 skill 库规模会快速膨胀。
- deadskills 指出每个已安装 skill 的名称和描述都会形成“上下文税”；可从本地 transcript 反推 dead/zombie skills。

**SA 落点**：客户问“要不要给团队装一堆 Claude/Codex skills？”时，推荐答案不是“越多越好”，而是“先建立 skill portfolio 治理：入口、授权、成本、使用证据、安全边界、生命周期”。

---

## 2. 四层治理模型

| 层 | 要回答的问题 | 可落地动作 | 架构图组件 |
|---|---|---|---|
| 目录层 Catalog | 有哪些 skill？来自官方、社区还是内部？ | 建立 allowlist；记录来源、版本、许可证、owner；优先官方/可信团队 | Skill Registry / Marketplace |
| 路由层 Routing | 什么时候触发哪个 skill？ | `description` 写成路由契约；避免含糊泛化；为高风险 skill 加显式触发词 | Router / Skill Selector |
| 授权层 Authorization | skill 能否申请 delegation / hooks / MCP / shell？ | 对 AGENTS.md / SKILL.md 的授权能力做最小权限审批；危险命令检测不能只靠 prompt | Policy / Approval Gate |
| 证据层 Evidence | skill 是否真的被使用、是否值得留？ | transcript 统计；dead/zombie 清理；记录 invocation、token cost、失败率 | Usage Telemetry / Audit Log |

---

## 3. Skill 引入漏斗（适合 POC 与客户项目）

1. **来源可信度**：官方团队 > 知名安全/云厂商 > 高质量社区 > 未知仓库。
2. **最小安装**：只装 POC 必需 skill；不要为了“看起来强”安装 100+ skill。
3. **frontmatter 先行**：先读 `name` / `description` / 触发条件，不全量读 1000 个 skill。
4. **安全分级**：
   - 低风险：只读文档、生成模板、架构图素材。
   - 中风险：读 repo、运行测试、调用 MCP read-only 工具。
   - 高风险：写文件、执行 shell、网络扫描、漏洞利用、云资源变更。
5. **验证门**：高风险 skill 必须写明“完成标准”和“不能标记完成直到验证通过”。
6. **回收机制**：每 30/60/90 天用 transcript 证据清理 dead/zombie skills。

---

## 4. 三个可复用 POC 场景

### A. Agent Skill 库体检 POC（1 小时）

**目标**：让客户看到“skill 太多也有成本”。
**步骤**：
- 列出当前 `.claude/skills` / `.codex/skills` / repo 内 `.github/skills`。
- 统计每个 `SKILL.md` frontmatter 与描述 token 量。
- 从 transcript / session log 抽样统计最近 30 天是否调用。
- 输出 active / zombie / dead 三类清单。

**交付物**：Skill Portfolio Report（含建议删除、保留、改写 description 的列表）。

### B. 高风险 Skill 安全评审 POC（半天）

**目标**：评估某个会执行命令/扫描/改代码的 skill 是否适合企业内用。
**检查项**：
- 是否有明确 scope 和授权边界。
- 是否把外部内容当资料而非命令。
- 是否有危险命令检测与 approval gate。
- 是否能在容器/gVisor/eBPF/MCP proxy 等环境层隔离中运行。
- 是否保留 audit log / transcript。

**参考信号**：Google Mantis 强调隔离环境与人工验证；Meta MCPGuard-Dynamic 给出 MCP 工具调用的 L1/L2/L3 防护思路。

### C. 多 Agent 计划评审 POC（30 分钟）

**目标**：在客户技术方案评审前，用多个 coding agent 做“独立反驳”。
**模式**：类似 kitze/council——主 agent 先出方案，再把方案只读交给其他 CLI 逐轮给 verdict（SHIP IT / SHIP WITH CHANGES / RETHINK），最后主 agent 汇总。
**注意**：这适合方案质量审查，不适合让多个 agent 同时写同一份文件；并行写会引入状态冲突。

---

## 5. 架构图模板（文字版）

```text
Developer / SA
   |
   v
Coding Agent CLI (Codex / Claude Code / Copilot / Gemini)
   |
   +--> Skill Registry / Marketplace (official + internal allowlist)
   |
   +--> Skill Router (description / explicit trigger / AGENTS.md or CLAUDE.md)
   |
   +--> Policy & Approval Gate
   |       |-- dangerous command detection
   |       |-- delegation authorization
   |       |-- MCP / hook / shell permission
   |
   +--> Execution Sandbox
   |       |-- container / gVisor / worktree / eBPF MCP proxy
   |
   +--> Evidence Store
           |-- transcript
           |-- invocation count
           |-- token/context cost
           |-- review findings
```

---

## 6. 速答话术（可转发客户）

> “Agent skills 不是装得越多越好。企业落地时要把 skills 当成可执行能力包治理：先建可信来源和 allowlist，再用 description 做路由契约；涉及 delegation、hooks、MCP、shell 的 skill 必须走最小权限和审批；最后用 transcript 证据定期清理 dead/zombie skills，避免每次对话都付上下文税。未知社区 skill 不建议直接安装，需先做许可证、源码、安全边界和数据访问审计。安全上，prompt 约束不够，高风险 skill 要配容器/gVisor/eBPF/MCP proxy 等环境层隔离。”

---

## 7. 原快照中发现对应的反哺点 [→harness]

- Codex 0.144.5 的 dangerous-command 检测增强：workshop 中的“危险命令分类器/审批门”章节应强调**检测逻辑要随真实 release 迭代回归测试**。
- Claude Code 2.1.211 的 subagent/plugin/permission 修复：workshop 的 harness 设计要加入“subagent 结果不得伪造完成、plugin MCP 断线要可恢复、权限预览要抵御 Unicode 视觉欺骗”。
- deadskills 的 context tax：workshop 可新增一节“skill 库不是越大越好：用 transcript 证据做组合治理”。
- council 的多 CLI deliberation：可作为“独立评审/anti-self-bias”的轻量 demo，但要标注只读与失败成员跳过策略。

---

## 8. 已核实来源

- OpenAI Codex changelog: https://developers.openai.com/codex/changelog （301/200 到 learn.chatgpt.com/docs/changelog）
- OpenAI Codex skills docs: https://developers.openai.com/codex/skills （200 到 build-skills）
- Claude Code CHANGELOG raw: https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md （200）
- VoltAgent/awesome-agent-skills: https://github.com/VoltAgent/awesome-agent-skills （200；raw README 200）
- deadskills: https://github.com/anandsaini18/deadskills （200）
- council: https://github.com/kitze/council （200）
- Google Mantis: https://github.com/google/mantis （200）
- Meta MCPGuard-Dynamic: https://github.com/facebook/mcpguard-dynamic （200）

> 未核实/不承诺：上述社区仓库的 star 数会快速变化；README 中 benchmark 数字未逐项复算，只作为仓库自述信号。生产环境采纳前需做安全与许可证复核。
