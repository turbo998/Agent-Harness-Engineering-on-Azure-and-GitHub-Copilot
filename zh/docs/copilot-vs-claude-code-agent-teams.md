# Multi-Agent 编排对比：GitHub Copilot vs Claude Code Agent Teams

> 视角：从 GitHub Copilot 出发，对照 Claude Code 2026-05 推出的实验特性 **Agent Teams**，回答合作伙伴最常问的两个问题：「我已经有 Copilot 了，还需要看别人怎么做多智能体吗？」「Copilot 自己的 multi-agent 路线对应到哪一层？」
>
> 参考来源：微信公众号「鲁工」《Claude Code + Agent Teams，并行任务的最佳实践》https://mp.weixin.qq.com/s/_qlK7sP3V_5P-z6XaHc2sA

---

## TL;DR

GitHub Copilot 与 Claude Code 在多智能体方向上走的是 **同一类工程化路线**（本地编排 + 共享制品 + 质量门），但产品形态和成本曲线不同：

| 维度 | GitHub Copilot | Claude Code Agent Teams |
|------|----------------|------------------------|
| 单机本地协作 | Custom Agents（`.github/agents/*.md`）+ handoff | Agent Teams（实验特性，需 flag 打开） |
| 云端并行 | **Coding Agent + Mission Control / Agent HQ** | 无原生云端编排，靠本地 tmux/iTerm2 分窗 |
| 触发方式 | `@agent-name` 显式调用 | prompt 关键词 `agent team` / `teammate` 隐式触发 |
| 队友通信 | 通过共享文件 / PR / Issue（异步） | **队友之间直接收发消息**（同步） |
| 任务面板 | Mission Control / Agent HQ UI | 终端内 `Ctrl+T` 共享任务列表 |
| 成本模型 | 按席位 + Coding Agent 任务数 | 每个队友独立 API 实例，**3–4× 单会话 token** |
| 治理 / 审批 | `copilot-instructions.md` + branch protection + PR review | Plan 审批 + 三个新 hook（`TeammateIdle` / `TaskCreated` / `TaskCompleted`） |
| 推荐场景 | 跨仓库并行交付、CI/CD 驱动的自动化 | 单仓库内的研究、审查、带竞争假设的调试 |

**一句话**：Copilot 更偏 **企业级云端编排**（Mission Control + Coding Agent 是真正的多仓库并行），Claude Code Agent Teams 更偏 **开发者本地深度协作**（同一 repo 内的「同事讨论」）。两者不是替代关系，落地时按任务边界选。

---

## 1. 概念映射：把 Claude Code 的词翻译成 Copilot 的词

| Claude Code 概念 | GitHub Copilot 对应物 | 说明 |
|------------------|----------------------|------|
| Subagents | **Custom Agents** in `.github/agents/*.md` | 各自有专用 system prompt、工具、模型；通过 `@agent-name` 调用 |
| Agent Teams（lead + teammates） | **Mission Control / Agent HQ** + 多个 Coding Agent | Copilot 的「team lead」是 Mission Control 这个编排面，「teammates」是云端 Coding Agent 实例 |
| Shared task list（`Ctrl+T`） | Mission Control 任务面板 + GitHub Issues / Projects | Copilot 这边任务状态天然 first-class 在 GitHub 上 |
| Plan approval | PR review + branch protection rules | Copilot 走的是 GitHub 原生审批，更适合企业治理 |
| Hooks（`TaskCreated` 等） | GitHub Actions / Repository rulesets / Branch protection | Copilot 把硬约束放到仓库治理层，不是 agent 运行时层 |
| `~/.claude/teams/` 本地目录 | Mission Control 云端状态 / GitHub UI | Copilot 的协作状态在云端，多人可见；Claude Code 在本地 |

**关键差异**：Claude Code 把多智能体当作**进程内 / 终端内**的协作来设计；Copilot 把多智能体当作 **跨仓库、跨 PR、可审计**的工程流程来设计。这决定了两者各自的甜蜜点。

---

## 2. 从 Copilot 视角看 Agent Teams 的核心创新

即使你只用 GitHub Copilot，也值得了解 Agent Teams 带来的三个工程化想法：

### 2.1 队友之间能直接讲话

Copilot 当前的 Custom Agents 之间是**通过文件和 PR 间接通信**的（A 改代码 → 提 PR → B 在 PR 里 review）。Claude Code Agent Teams 让队友可以**同步对话**，更适合：

- **带竞争假设的 Bug 调试**：3 个队友各拿一个理论并行测试，发现互相矛盾时直接讨论
- **多角度审查**：安全 / 性能 / 测试覆盖 3 个角度同时跑，互相质疑后给出综合结论

**Copilot 当前的近似实现**：在 Mission Control 中跑 3 个 Coding Agent，每个负责一个角度，最后由人或一个「synthesizer agent」聚合 PR / Issue 评论。同步性弱一些，但**审计性强**——所有讨论都是 PR/Issue/commit。

### 2.2 显式的「Plan → Approve → Execute」闭环

Claude Code Agent Teams 鼓励 lead 在队友动手前要求 plan 审批，并把准则写进 prompt（「必须含测试覆盖」「必须有回滚方案」）。

**Copilot 对应玩法**：
- 在 `.github/copilot-instructions.md` 里写明 plan 标准
- 用 **Spec-driven workflow**（参考本 workshop lab4）让 agent 先产 SPEC + ADR，人或自动化 review 通过后再实现
- 用 **GitHub Actions** 在 PR 阶段强制跑安全扫描、测试覆盖率门槛——这就是 Copilot 版的「hook 硬约束」

### 2.3 团队规模的甜蜜点：3–5 人 × 5–6 任务

这是个**跨产品都成立**的工程经验。在 Copilot Mission Control 里同样适用：

- 一次性派 15 个 Coding Agent 跑 15 个 repo？协调成本爆炸，PR 评审挤爆 reviewer
- 3–5 个 Agent 各处理 5–6 个相关任务，是「人能审完 + 模型不会超限」的平衡点

合作伙伴落地时这是关键的「容量规划」数字。

---

## 3. 成本与限额对比

| 项目 | GitHub Copilot | Claude Code Agent Teams |
|------|----------------|------------------------|
| 计费模型 | 按席位 + Coding Agent 任务数（业务/企业版含配额） | API token 直接消耗（Pro/Team/Max 订阅含配额） |
| 多 agent 倍率 | 每个 Coding Agent 任务独立计费 | **3–4× 单会话 token** |
| 限额风险 | Coding Agent 任务超出后排队 / 拒绝 | Max 20x 用户也容易触发 **5 小时窗口限额** |
| 企业可预测性 | 高（按席位） | 中（受任务复杂度影响大） |

**给合作伙伴的话术**：Copilot 的多智能体在企业财务侧更可控；Claude Code Agent Teams 的极限并发能力强，但需要为「token 黑洞」做预案。两者都建议先在**研究 / 审查**类无写入任务上试水。

---

## 4. 场景选型矩阵（四档方案）

| 任务画像 | 推荐方案 | 理由 |
|---------|---------|------|
| 单会话、顺序依赖强 | **VS Code Copilot Chat (默认 Agent 模式)** | 不需要协调开销 |
| 单仓库、可拆分子任务 | **Copilot Custom Agents handoff**（本 workshop lab3） | 团队共享 `.github/agents/`，配置即代码 |
| 单仓库、需要「同事讨论」 | **Claude Code Agent Teams** | 队友同步通信对带竞争假设的调试有优势 |
| 跨仓库、跨 PR 并行 | **Copilot Coding Agent + Mission Control / Agent HQ** | 云端原生编排 + GitHub 治理 |
| 几百 sub-agent 大规模分解 | **云端 Swarm（Kimi K2.6 / 自建）** | 单机本地编排已不适用 |

---

## 5. 给合作伙伴的实操建议

1. **不要用「替代」框架对话**：客户问「Agent Teams 是不是要替代 Copilot」时，先把任务拆成上面四档，按边界给方案。
2. **Copilot 的护城河在治理层**：PR 审批、branch protection、Coding Agent 与 GitHub Actions 的集成，是 Claude Code 暂时没有的企业级能力。
3. **可借鉴的工程经验**：3–5 人甜蜜点、Plan 审批准则、研究 / 审查类任务先行——这些不分产品都成立，直接写进合作伙伴的 enablement 材料。
4. **混合方案是合理的**：开发者本机用 Claude Code Agent Teams 做单 repo 深度协作，团队级 / 跨 repo 走 Copilot Mission Control，互不冲突。

---

## 6. 关联到本 Workshop

- **Lab 3 — Multi-Agent 协作**：Custom Agents handoff 对应 Claude Code subagents；本文档可作为 lab3「进阶讨论」的延伸阅读。
- **Lab 4 — Spec-Driven / Multi-Role Code Review**：对应 Agent Teams 的「Plan 审批」和「多角度审查」模式。
- **Lab 5 — Ship and Release**：Coding Agent + Mission Control 对应「云端编排」，可作为对比 Claude Code 本地方案的真实落地案例。

---

## 参考资料

- 原文：https://mp.weixin.qq.com/s/_qlK7sP3V_5P-z6XaHc2sA
- Claude Code Agent Teams 官方文档（实验特性，需开启 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`）
- GitHub Copilot Coding Agent / Mission Control / Agent HQ 官方文档
- 本 workshop Lab 3 / Lab 4 / Lab 5
