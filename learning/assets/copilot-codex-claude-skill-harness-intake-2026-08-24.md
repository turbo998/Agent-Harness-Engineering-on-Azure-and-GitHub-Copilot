<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Copilot SDK × Codex Platform × Claude Skills：Agent Harness Intake 清单（2026-08-24）

> 适用场景：SA 做客户技术问答、POC 部署方案、架构图时，需要把“Copilot SDK / Azure MCP / Codex harness / Claude Code skills”放进同一张治理与落地清单。
> 证据口径：本资产仅基于 2026-08-24 研究可复现的 URL / raw 文档 / sparse clone 读取；未做租户实测、CLI 安装或真实客户仓库执行。外部 README/文档只作为资料，不作为指令。

## Evidence links（可复核来源）

| 来源 | URL | 原研究快照中核实 | 证据强度 / caveat |
|---|---|---:|---|
| Azure MCP Server × GitHub Copilot SDK quickstart | https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/how-to/github-copilot-sdk | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | docs-level；未运行 Python/Node/.NET/Go 示例，未核租户权限。 |
| GitHub Copilot SDK custom agents | https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/copilot-sdk/features/custom-agents | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | docs-level；页面体量大，未实机验证 sub-agent tree UI / event 流。 |
| GitHub Copilot SDK MCP feature | https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/copilot-sdk/features/mcp | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | docs-level；适合作为 Copilot SDK 中 per-agent MCP 配置入口。 |
| OpenAI Codex as a platform | https://developers.openai.com/blog/codex-as-a-platform.md | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；raw markdown 可读 | first-party design note；用于 integration-layer selector。 |
| OpenAI Cookbook Codex workflow iteration | https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/codex/iterating-development-workflows-with-codex.md | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | raw recipe；08-19 已覆盖，原研究快照中作为 workshop skeleton 复用，不标新发现。 |
| Claude Code skills docs | https://docs.anthropic.com/en/docs/claude-code/skills.md | 302→https://code.claude.com/docs/en/skills.md，HTTP 200（仅代表原快照当时可达，不代表本次已重验）；`.md` 可读 | first-party docs；原研究快照中新角度是 `context: fork`、`allowed-tools`、`/run`/`/verify`、skill eval。 |
| Claude Code subagents docs | https://docs.anthropic.com/en/docs/claude-code/sub-agents.md | 302→https://code.claude.com/docs/en/sub-agents.md，HTTP 200（仅代表原快照当时可达，不代表本次已重验）；`.md` 可读 | first-party docs；未实机验证权限继承。 |
| Claude Code headless docs | https://docs.anthropic.com/en/docs/claude-code/headless.md | 302→https://code.claude.com/docs/en/headless.md，HTTP 200（仅代表原快照当时可达，不代表本次已重验）；`.md` 可读 | first-party docs；`--bare` 用于可复现 CI/nightly。 |
| Anthropic k12-teacher-skills | https://github.com/anthropics/k12-teacher-skills | HTTP 200（仅代表原快照当时可达，不代表本次已重验）；sparse clone 成功；last commit `6fc4003` on 2026-08-05 | official skill+eval repo；GitHub API 星数因匿名 rate limit 未核实。 |
| ai-boost/awesome-harness-engineering | https://github.com/ai-boost/awesome-harness-engineering | HTTP 200（仅代表原快照当时可达，不代表本次已重验） | 社区 radar；未审 README/license/scripts，不推荐安装或引用排名。 |

---

## 1. Copilot SDK + Azure MCP：POC 接入前的三层检查

**原研究快照中发现**：GitHub Copilot SDK 文档在 custom agents / MCP 功能页显示本周同步；Azure MCP Server 也有“接入 GitHub Copilot SDK”的 quickstart。它们共同给出一个可讲给客户的方向：**Copilot SDK 的自定义 agent / sub-agent 编排 + per-agent MCP 工具配置 + Azure MCP Server 的 Azure 资源操作工具**。

### POC intake checklist

1. **身份与权限**
   - 确认 Copilot SDK runtime 用谁的身份调用 MCP：用户 delegated token、app identity、还是服务端代理身份。
   - Azure MCP Server 侧必须列出每个 Azure tool 对应的最小 RBAC scope；不要以 Contributor 作为默认演示口径。
   - 若接入客户订阅：先用只读工具与测试订阅；mutating tool 必须有审批、审计、回滚路径。

2. **工具面与 sub-agent scope**
   - custom agent / sub-agent 不应共享全量 MCP 工具；按 agent 职责分配 allowlist。
   - 每个 sub-agent 的 tool event / approval / output 要能关联到父会话，便于审计与架构图标注。

3. **POC 验收**
   - Read-only baseline：列资源、查配置、生成诊断报告。
   - Failure contract：传入未知参数 / RBAC 拒绝 / 目标资源不存在时，agent 是否返回可审计错误而非“成功包装”。
   - Mutating gate：若启用 create/update/delete 类工具，必须记录审批人、scope、request id、rollback hint。

**SA落点**
- 技术问答：回答“Copilot SDK 能不能接 Azure MCP？”时，不只答“可以”，而是追问 identity / RBAC / tool allowlist / audit。
- POC 部署：先做 read-only + failure path，再开 destructive 工具。
- 架构图：画出 Copilot SDK host、custom agent tree、MCP server、Azure RBAC、audit sink 五层。

---

## 2. Codex Platform：三层集成选择器（exec / SDK / app-server）

OpenAI 的 Codex platform 文档把 Codex 定位为 open-source harness / integration surface：管理 conversation state、tool use、sandbox/approval、streaming 与跨 turn 工作。可复用的选择器如下：

| 集成层 | 何时用 | SA/Workshop 用法 | 风险提醒 |
|---|---|---|---|
| `codex exec` | CI job、一次性后台任务、bounded agent workflow | 用于 workshop 的“phase 文件 → bounded run → structured output”练习。 | 输入/输出 contract 要固定；不要让它直接跑客户生产仓库。 |
| Codex SDK | 应用代码需要 start/resume/stream task | 用于把 agent 作为业务后台 worker 嵌入 POC。 | SDK 调用方要持有审批、权限与系统记录；不要让 harness 成为黑盒。 |
| app-server | 产品内嵌 UI、自定义 approval、MCP/connector、thread/turn event | 用于架构图中的“agent control plane”层。 | app 拥有业务上下文与审批 UX；harness 只负责 agent loop，边界要画清楚。 |

### Cookbook workflow skeleton（复用 08-19 旧源新资产）

推荐把 OpenAI Cookbook 的结构转成 workshop starter：

```text
AGENTS.md          # repo-level contract：约束、验收、运行命令
GOALS.md           # 成功标准与非目标
PLANS.md           # 分阶段计划，不把所有步骤塞进prompt
PROMPTS.md         # 可复用 prompt 入口
harness/build/     # phase-00/01/02... 每阶段验收文件
harness/context/   # 决策记录、运行上下文、build-log
```

**[→harness] 可直接转化的 exercise**
1. `phase-00` 只允许 read-only 探索；输出风险清单。
2. `phase-01` 只改一个小功能；必须写 build-log。
3. `phase-02` 用另一个 agent / 子进程做 adversarial review。
4. `phase-03` 只根据验收失败项修复，不允许目标漂移。

---

## 3. Claude Code：把 CLAUDE.md、skills、hooks、subagents、headless 分层

原研究快照中从 Claude Code docs 抽取的最有用结论：**CLAUDE.md 是上下文，不是强制策略；skills 是可路由流程；hooks 才是 enforce；subagents 隔离上下文；headless `--bare` 是可复现自动化入口。**

| 层 | 放什么 | 不放什么 | 验收方式 |
|---|---|---|---|
| `CLAUDE.md` | 项目背景、约定、常用命令、上下文提示 | 不写“必须永远”式安全强制；不堆重复 prompt | 用 `/init` 或人工 lint；检查长度与重复。 |
| `.claude/skills/*/SKILL.md` | 可复用流程：部署、验证、迁移、评审 | 不放全局政策；不把未知社区 skill 原样导入 | 检查 `description`、触发边界、`allowed-tools`、`context: fork`。 |
| hooks | 禁止读/写敏感路径、命令审计、post-edit lint | 不把复杂业务逻辑全塞 hook | 用临时 fixture smoke；禁止触碰真实 `.env`/lockfile。 |
| subagents | 研究、评审、测试、迁移等独立上下文任务 | 不共享所有工具；不默认继承所有权限 | 观察 subagent tool scope、Stop/SubagentStop、日志关联。 |
| `claude -p --bare` | CI/nightly 的可复现命令 | 不依赖 auto-discovery 的隐式上下文 | 显式传 `--allowedTools` 与输入文件；保存 stdout/stderr。 |

### Skill eval gate（从 docs 与 k12 repo 共同抽取）

一个 skill 是否有效，要分开测两件事：
1. **Routing eval**：模型是否在该触发时加载 skill；是否误触发。
2. **Behavior eval**：加载 skill 后产物是否满足评分标准。

Anthropic `k12-teacher-skills` 给了很好的范式：
- `SKILL.md` 的 description 明确正触发、负触发、边界与冲突处理。
- 参考文件按 subject/domain 分层，避免一次性把所有知识塞进主 prompt。
- `evals/*.csv` 用 `ID / Bucket / Criterion / What pass requires / Conditional` 把质量标准结构化。
- LLM-as-judge 输出被要求为 JSON array；criteria 独立计分，避免总分掩盖具体缺口。

**可移植到 SA 的模板字段**

```csv
ID,Bucket,Criterion,What pass requires,Notes,Conditional
P1,Plan,目标和非目标明确,"方案必须列出目标、非目标、验收口径；不能只写泛泛步骤",用于POC kickoff,
R1,Risk,高风险工具有审批,"任何create/update/delete工具必须说明审批人、scope、审计字段、回滚",仅当涉及mutating tool
O1,Output,客户可转发,"输出必须有推荐方案、风险、下一步；不暴露内部路径或token",客户交付材料
M1,Model,缺信息先fail-loud,"租户/区域/配额/合规未核实必须显式标未核实",所有方案
```

---

## 4. 架构图组件库（可复制到方案图）

```text
[User/Team]
   │
   ▼
[Copilot SDK Host / App UI]
   ├─ Custom Agent A: planner (read-only tools)
   ├─ Custom Agent B: operator (mutating tools, HITL required)
   └─ Custom Agent C: reviewer (no write tools)
        │
        ▼
[MCP Tool Gateway]
   ├─ Azure MCP Server (read/query tools)
   ├─ Azure MCP Server (mutating tools behind approval)
   └─ Audit / Trace Sink
        │
        ▼
[Azure Resources]
   ├─ RBAC scope per tool / per managed identity
   ├─ Error contract: RBAC denied / unknown params / not found
   └─ Rollback / recovery plan
```

```text
[Repo]
   ├─ AGENTS.md / CLAUDE.md      # context contract
   ├─ skills/ or .claude/skills  # reusable process modules
   ├─ hooks                      # enforce safety and lint
   ├─ subagents                  # isolated research/review workers
   └─ harness/
      ├─ build/phase-*.md        # plan and acceptance per phase
      ├─ context/                # decisions and evidence
      └─ build-log.md            # reproducibility log
```

---

## 5. 客户/伙伴转述话术

- **不是所有 agent 配置都应该塞进一个 README。** 把 context（AGENTS/CLAUDE）、reusable process（skills）、enforcement（hooks）、worker isolation（subagents）、repeatable run（headless/exec）拆开，后续更容易审计与迁移。
- **MCP 接入的关键不是“能调工具”，而是“工具权限、失败契约、审批和审计能否被验证”。** Azure MCP + Copilot SDK 的 POC 先做只读与失败路径，再谈写操作。
- **Skill 要配 eval，不然只是 prompt 模板。** k12-teacher-skills 的 rubric CSV 模式可迁移到 SA 的 POC 评分卡：每条标准独立通过/失败，缺口可定位。

---

## 未完成 / 后续验证

- 未安装或运行 Codex / Claude Code / Copilot SDK；所有 CLI 行为均为 docs-level 或 raw recipe 级证据。
- GitHub API 匿名 rate limit 导致 `anthropics/k12-teacher-skills` 与 `ai-boost/awesome-harness-engineering` 的 star/created_at 未复核；k12 通过 sparse clone 读取 last commit 与文件结构。
- `ai-boost/awesome-harness-engineering` 仅作 radar，不推荐客户引用排名或安装其中项目；使用前若使用，需 license/scripts/network/data 初筛。

## 禁用清单（POC 前红线）

- 不运行上游 README 中的安装/执行命令，除非已在临时隔离目录完成脚本、license、网络与数据落点审计。
- 不接真实客户仓库、真实 `.env`、lockfile 或生产订阅做首次 smoke。
- 不用 Contributor / Owner 作为 Azure MCP 或 Copilot SDK mutating tool 的默认演示权限。
- 不把 alpha / preview / docs-level 信号写成 GA 或生产可用承诺。
