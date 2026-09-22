<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent 委派授权治理速查（Codex vs Claude Code）— 2026-07-18

> 目的：跨厂商编码 Agent CLI 的"何时允许 subagent/委派/并行工作"治理模式对比，供 SA 技术问答、POC 设计话术、架构图使用。所有信源已实测核实（curl/scrape 返回 200），未核实内容单独标注。

## 一、核心问题
企业客户普遍关心："Agent 会不会未经允许就自己去 fork 子任务/调用工具/花费预算？" 两大编码 Agent CLI 给出了两种不同哲学的答案：

| 维度 | OpenAI Codex CLI | Anthropic Claude Code |
|---|---|---|
| 授权载体 | **AGENTS.md 自然语言约定** + skill 文件指令 | **SKILL.md frontmatter 字段**（`context: fork`, `allowed-tools`, `disable-model-invocation`, `user-invocable`）+ **运行时配额环境变量** |
| 委派门禁默认值 | 默认禁止 spawn sub-agent，除非"用户显式请求" | 默认允许 subagent，但受配额与权限继承约束 |
| 07-17 后的变化 | PR #30274：委派授权来源从"仅用户显式请求"扩展为"用户 **或** AGENTS.md/skill 指令显式请求" | v2.1.212：`/fork`语义变为"整会话复制为独立后台会话"；新增会话级委派配额 |
| 治理粒度 | 项目级（AGENTS.md 一次写好，全仓库生效） | 会话级+skill级双层（配额是会话级硬上限，权限是 skill 级细粒度） |
| 失控防护机制 | 无独立配额，靠文本约定+ code review | `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`(默认200)、`CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`(默认200)、MCP 工具调用超2分钟自动转后台 |

**已核实来源**：
- Codex PR#30274 diff：https://github.com/openai/codex/pull/30274.diff — 实测抓取到具体diff：`multi_agent_mode_instructions.rs` 中 `EXPLICIT_REQUEST_ONLY` 常量文案从 `"unless the user explicitly asks"` 改为 `"unless the user or applicable AGENTS.md/skill instructions explicitly ask"`。纯文本策略层改动，无新技术执行通道。
- Claude Code CHANGELOG（v2.1.212）：https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
- Claude Code Skills 官方文档：https://docs.anthropic.com/en/docs/claude-code/skills （**注：该URL会301跳转至新域名 code.claude.com/docs/en/skills，最终可达，但域名已迁移，建议直接引用新域名**）

## 二、Auto Mode 三层放行架构（Anthropic 官方一手案例）
来源：https://www.anthropic.com/engineering/claude-code-auto-mode （已验证可访问）

替代 `--dangerously-skip-permissions` 的安全设计：
1. **内置安全工具白名单**（只读/低风险操作直通）
2. **项目内文件操作直通**（沙箱边界内的写操作）
3. **Transcript 分类器兜底**：两阶段（①快速单token过滤 ②仅对flag项做CoT推理），且对**assistant文本和工具结果做"推理盲"处理**（只看user消息+工具调用参数本身，不看模型自己的输出），防止 agent 说服分类器放行自己的越权请求。
   - Subagent 委派时双向过分类器：委派时可**拒绝**，结果回传时仅**警告**（非对称设计，宁可多拦委派，少拦结果）
   - 实测指标：FNR 17%、FPR 0.4%（**未核实**是否为生产环境长期稳定值，来自官方博客单次披露）

**SA 落地话术**：当客户问"Agent 自主执行会不会失控"，可用这个三层模型 + 分类器"推理盲"设计作为标准答案框架，说明"不是简单开关，而是分层放行+异步兜底"。

## 三、Claude Code Skills 规范关键字段（POC/答疑直接可用）
来源：https://docs.anthropic.com/en/docs/claude-code/skills

- `context: fork` — skill 在独立 subagent 中运行，配合 `agent: Explore/Plan` 等预设角色
- `allowed-tools` / `disallowed-tools` — 按 skill 粒度授予/禁止工具，而非全局权限
- `disable-model-invocation` / `user-invocable` — 精细控制"模型能否自主调用此skill" vs "用户能否手动调用"
- 嵌套 `.claude/skills/` 支持 monorepo 命名空间（如 `apps/web:deploy`）
- `skill-creator` 插件自带 eval 循环：`evals.json → grading.json → benchmark.json`，做 skill 有效性的 A/B 测试

**SA 落地话术**：客户问"如何保证内部写的 skill 不会被滥用/误触发"，直接引用 `disable-model-invocation` + `allowed-tools` 两个字段做权限矩阵设计。

## 四、Codex AGENTS.md 双重职责（上下文锚点 + 委派授权载体）
来源：https://github.com/openai/openai-cookbook/blob/main/examples/codex/code_modernization.md（已验证）+ PR#30274

AGENTS.md 现在同时承担两个角色：
1. **任务上下文锚点**：官方 Cookbook 示例中，Codex 先生成 AGENTS.md + PLANS.md 锚定长任务上下文与计划，再分阶段执行
2. **委派授权载体**（PR#30274 新增语义）：项目维护者可在 AGENTS.md 中预先写明"允许对XX类任务使用sub-agent并行"，模型据此可在无用户当场明确要求时主动委派

**架构图素材**：可画一张"AGENTS.md 生命周期"图——创建（锚定上下文）→ 演化（记录委派授权规则）→ 审计（作为 policy-as-code 文档纳入代码评审）。

## 五、跨厂商 CLI 生态对照（新增信号，未深挖，仅供参考）
- **xai-org/grok-build**（07-14新建，Rust实现，支持MCP/Skills/插件/Hooks/ACP协议，16k★/2.9k fork）：xAI 首个开源编码Agent CLI，https://github.com/xai-org/grok-build （已核实可达）
- **facebookresearch/TUA-Bench**：Terminal-Use Agent 基准，120个真实任务，含 Claude Code/Codex/OpenHands SDK/Terminus-2/Mini-SWE-Agent 排行榜，https://github.com/facebookresearch/TUA-Bench （已核实可达）— 可直接引用为第三方权威横向对比数据支撑"选哪个编码Agent框架"的客户决策。

## 六、SA 快速应答模板
**Q: 客户问"给 Agent 自主委派权限，风险怎么控？"**
> A: 参考业界两种成熟模式——① Codex 用 AGENTS.md 项目级自然语言约定（谁能委派、什么场景），门槛低但需靠 code review 治理；② Claude Code 用运行时硬配额（会话级 subagent/websearch 调用上限）+ skill 级细粒度权限字段（allowed-tools/disable-model-invocation），门槛高但更适合企业合规场景。建议 POC 阶段先用 Claude Code 的配额模式做护栏，成熟后再引入 AGENTS.md 类自然语言治理降低维护成本。

**Q: 客户问"Agent 会不会自己突破权限审批"？**
> A: 参考 Claude Code Auto Mode 的"分类器推理盲"设计——审批分类器只看用户原始意图和工具调用参数，**不给模型自己的输出任何影响分类结果的机会**，从架构上杜绝"Agent 说服审批系统放行自己"的攻击面。

---
*[→harness] 本cheatsheet核心内容（委派授权对比表 + Auto Mode三层架构 + Skills字段矩阵）建议整体反哺 Agent-Harness-Engineering-on-Azure-and-GitHub-Copilot workshop repo，作为"跨厂商Agent治理模式对比"独立章节。*
*未核实项：Auto Mode FNR/FPR 数值为官方单次披露，未做多环境复现验证；xai-org/grok-build、facebookresearch/TUA-Bench 仅确认可达+机制描述，未做功能实测。*
