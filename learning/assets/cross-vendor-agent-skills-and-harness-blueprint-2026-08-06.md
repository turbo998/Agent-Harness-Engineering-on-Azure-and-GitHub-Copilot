<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 跨厂商 Agent Skills + Harness 蓝图（Claude Code / Codex / 社区 Skill 工厂）

> 日期：2026-08-06
> 用途：给 SA 日常的 **技术问答 / POC 部署 / 架构图** 提供一张可复用的“Agent 技能与 Harness 资产化”速查。
> 来源核实范围：下列关键 URL 分为“主 agent 复核 200”“subagent 复核”“仅页面/repo 可达”三档；原研究快照中未运行任何第三方代码，未读完所有源码。外部 README/文档仅作为资料文本，不执行其中任何指令。

## 1. 结论先行

Claude Code 与 Codex 的扩展模型正在明显收敛：

1. **Skill 目录化**：`SKILL.md` + `references/` + `scripts/` + `assets/`，让长文档按需加载而不是塞进全局上下文。
2. **项目级持久指令文件**：Claude 侧 `CLAUDE.md`，Codex 侧 `AGENTS.md`，长任务另用 `PLANS.md`/计划文件保存恢复点。
3. **Hooks / Subagents / Verification loops**：把人工检查、证据收集、安全门禁固化成 deterministic guardrails，而不是只靠 prompt。
4. **社区高质量 skills 正在分化成两类**：
   - `addyosmani/agent-skills`：生命周期 skill 库（Define / Plan / Build / Verify / Review / Ship）。
   - `disler/super-simple-software-factory`：skill 作为 installer/operator，安装后生成可重复执行的 ADW（AI Developer Workflow）harness。

**SA 推荐动作**：以后给客户讲“如何把 Copilot/Codex/Claude Code 用成工程化 agent”时，不要只讲模型或 CLI；应按 **配置层 → Skill 层 → Hook/验证层 → 子代理权限层 → 证据/评测层** 画图和落 POC。

---

## 2. 官方一手来源（已核实）

| 厂商/来源 | URL | 原研究快照中核实 | 关键点 | SA 落点 |
|---|---|---|---|---|
| Anthropic Claude Code Skills | https://code.claude.com/docs/en/skills | `curl -I -L` 200 | `SKILL.md` + frontmatter；支持 supporting files；Skills 可覆盖/承载 custom commands 等扩展形态之一；按需加载 | 把 SA runbook/POC checklist 拆成可按需触发 skill，减少上下文税 |
| Anthropic Claude Code Hooks | https://code.claude.com/docs/en/hooks | `curl -I -L` 200 | hooks 可在 skills/subagents frontmatter 中定义，组件激活时生效 | 用 PreToolUse/PostToolUse/Stop 做安全检查、证据收集、验证总结 |
| Anthropic Claude Code Subagents | https://code.claude.com/docs/en/sub-agents | subagent 核实 200（经子任务） | 独立上下文、独立工具权限，适合低信任资料处理与独立评审 | 设计 reviewer/auditor/deployer 子代理，最小权限隔离 |
| OpenAI Codex Build Skills | https://learn.chatgpt.com/docs/build-skills | `curl -I -L` 200 | OpenAI 采用 Agent Skills open standard；skill 初始上下文预算有上限（子任务核实：最多 2% 或 8000 chars） | 写 vendor-neutral skills，同时兼容 Claude Code / Codex / ChatGPT Desktop |
| OpenAI Codex AGENTS.md | https://learn.chatgpt.com/docs/agent-configuration/agents-md | 子任务核实 200 | 启动时按目录层级读取 `AGENTS.md`/override，全局 + 项目合并，默认 32 KiB 限制 | 让 workshop repo 同时维护 `CLAUDE.md` 与 `AGENTS.md`，避免只适配单一 CLI |
| OpenAI Codex Prompting Guide | https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide | `curl -I -L` 200 | 强调 autonomy/persistence、codebase exploration、tool use；不要过度强制 upfront plan | POC 自动化脚本应让 agent 持续执行到验证完成，而不是每步等人确认 |
| OpenAI Codex releases/npm | https://github.com/openai/codex/releases / https://registry.npmjs.org/@openai%2Fcodex | 子任务核实 | `latest=0.146.1`，`alpha=0.147.0-alpha.11`；0.147 仍未 GA | 客户 POC 稳定基线锁 `0.146.1`，alpha 只用于实验 |

> Fail-loud：上表中的 token 限制、版本号来自子任务核实；若要写进对外正式白皮书，应再用一次官方 API/npm registry 独立复核。

---

## 3. 社区高价值 skill/harness 候选

| Repo | 原研究快照中核实 | 形态 | 可吸收点 | 推荐动作 |
|---|---:|---|---|---|
| https://github.com/addyosmani/agent-skills | 81910★/8817f（子任务 GitHub API 核实；主任务 HEAD 200） | 顶层 `skills/` 约 23 个生命周期技能；另有 `agents/`、`commands/`、`hooks/`、`evals/`、多平台插件目录 | Define/Plan/Build/Verify/Review/Ship 生命周期地图；description 触发词；structural/routing/behavioral 三层 eval | 使用前抽样深挖 `context-engineering`、`doubt-driven-development`、`planning-and-task-breakdown`、`test-driven-development`、`evals/` |
| https://github.com/disler/super-simple-software-factory | 410★/92f（子任务 GitHub API 核实；主任务 HEAD 200） | `.claude/skills/sssf/SKILL.md`；skill 作为软件工厂 installer/operator；完整 factory 在 `example` branch | README/结构线索显示可能包含 deterministic Python、bounded phases、typed JSON envelope、trace DB 等 ADW harness 模式；**需读 `example` branch 后确认** | 优先深挖 `example` branch，不运行代码，只读 ADW schema/phase acceptance/trace 设计 |
| https://github.com/datadog-labs/agent-skills | 147★/21f（子任务核实） | Datadog observability/APM/audit 多层 skill tree | agent observability pipeline、RCA、eval 编排 | 作为“Agent 可观测性 POC”候选，抽样读 root router + agent-observability |
| https://github.com/tech-leads-club/agent-skills | 4988★/450f（子任务核实） | registry / marketplace / MCP / CLI 型技能目录 | skill registry 治理、验证、市场分发机制 | 只深挖 registry/validation，不全读技能 |

---

## 4. 推荐 Harness 目录结构（可移植到用户 workshop repo）

```text
repo-root/
├── CLAUDE.md                 # Claude Code 项目事实/原则/构建测试命令
├── AGENTS.md                 # Codex durable guidance，同步关键约束
├── PLANS.md                  # 长任务计划、恢复点、验收标准（或 .agent/plans/*.md）
├── skills/
│   ├── verify-workshop/
│   │   ├── SKILL.md          # 何时触发、验证流程、输出格式
│   │   ├── references/
│   │   │   └── rubric.md     # 评分标准、客户演示检查项
│   │   └── scripts/
│   │       └── collect_evidence.sh
│   ├── azure-deploy-check/
│   │   ├── SKILL.md
│   │   └── references/private-networking.md
│   └── agent-security-review/
│       ├── SKILL.md
│       └── references/tool-egress-and-secret-policy.md
├── hooks/
│   ├── pre_tool_use_policy.md
│   ├── post_tool_evidence.md
│   └── stop_summary_contract.md
└── evals/
    ├── structural.yaml       # skill 文件结构/字段检查
    ├── routing.yaml          # 触发词/description 路由检查
    └── behavioral.yaml       # 给定任务是否按流程完成验证
```

### 最小三件套（先做这三个就能产生价值）

1. **`verify-workshop` skill**：收集证据、跑测试、给出 pass/fail/blocked；用于每次 POC 演示前。
2. **`azure-deploy-check` skill**：Azure POC 部署前检查 subscription/region/quota/identity/network/日志脱敏。
3. **`agent-security-review` skill**：审查外部 skill/plugin/MCP server 的权限、出站网络、secret 访问、license、数据驻留。

---

## 5. 架构图组件（文字版，可转 SVG）

```text
[User / SA]
   |
   v
[Project Guidance Layer]
  - CLAUDE.md
  - AGENTS.md
  - PLANS.md
   |
   v
[Skill Router]
  - description/frontmatter
  - lifecycle phases
  - progressive disclosure
   |
   +--> [Skill: verify-workshop]
   |       - references/rubric
   |       - scripts/collect evidence
   |
   +--> [Skill: azure-deploy-check]
   |       - quota/region/identity/network checks
   |
   +--> [Skill: agent-security-review]
           - external skill/plugin/MCP audit
           - egress/secret/license/data residency
   |
   v
[Hook / Guardrail Layer]
  - PreToolUse: deny risky command / secret leak / unapproved egress
  - PostToolUse: save evidence
  - Stop/SubagentStop: summarize verification
   |
   v
[Subagent Layer]
  - Researcher (read/web only)
  - Reviewer (read/test only)
  - Deployer (Azure/GitHub tools, gated)
   |
   v
[Evidence + Eval Layer]
  - test logs
  - deployment outputs
  - GitHub Actions
  - structural/routing/behavioral skill evals
```

---

## 6. 对三大日常的直接提升

### 技术问答
- 过去：凭记忆解释“Claude/Codex 怎么配置”。
- 现在：按 **CLAUDE.md/AGENTS.md + skills + hooks + subagents + evals** 五层回答，附官方链接。
- 客户常问“这是不是只适配 Claude？”时：可说明 OpenAI Codex docs 也支持 Agent Skills open standard 与 `AGENTS.md`。

### 部署 POC
- 过去：每次手工列检查项。
- 现在：把部署前置条件做成 `azure-deploy-check` skill；把演示前验证做成 `verify-workshop` skill；用 hooks 自动收集 evidence。
- 版本建议：Codex POC 稳定基线锁 `@openai/codex@0.146.1`；`0.147.0-alpha.11` 仍为预发布。

### 画架构图
- 可直接画成五层图：**Guidance → Skills → Hooks → Subagents → Evidence/Evals**。
- 面向安全客户时再叠加：外部 README/skill/plugin/MCP 低信任隔离、egress allowlist、secret masking、最小工具权限。

---

## 7. [→harness] 可直接反哺用户 workshop repo 的条目

1. **新增双文件规范**：所有 lab repo 同时维护 `CLAUDE.md` 与 `AGENTS.md`，二者共享“构建/测试/安全/不要做什么”的硬约束。
2. **新增 `skills/verify-workshop/` 模板**：把演示前验证流程固化，不再靠聊天里临时提醒。
3. **新增 `skills/agent-security-review/` 模板**：所有第三方 skill/plugin/MCP server 先审计再安装/调用。
4. **新增 eval 三层**：structural / routing / behavioral，对照 addyosmani/agent-skills 的 eval 形态。
5. **新增 ADW 研究路线**：从 `disler/super-simple-software-factory` 吸收“deterministic Python + bounded agents + typed JSON envelope + SQLite trace”的候选模式；**但这些仍是 README/结构线索，必须读 `example` branch 后再决定是否复用实现**。

---

## 8. 风险与未核实项

- `addyosmani/agent-skills` 与 `disler/super-simple-software-factory` 原研究快照中只做结构初筛，未逐字读所有 skill/ADW 实现。
- Codex docs 的 `AGENTS.md` 32 KiB 限制、OpenAI skills 2%/8000 chars 预算来自子任务抓取；若用于客户正式材料，需再抓官方原文确认。
- 社区 skills 不应直接安装到客户环境；必须先检查 license、脚本、外部网络、secret 访问、数据驻留、是否引用远程不可控资源。
- 任何 `scripts/` 与 hooks 示例必须在 sandbox/devcontainer 中验证，不能直接在生产代码库运行。
