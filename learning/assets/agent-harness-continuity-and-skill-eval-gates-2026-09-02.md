<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent Harness Continuity & Skill Eval Gates（2026-09-02）

> 用途：给 SA 定期检查、客户 Agent POC、以及 `Agent-Harness-Engineering-on-Azure-and-GitHub-Copilot` workshop 复用的一页式检查表。
> 安全说明：本文中出现的命令形态、hook 名称、配置名均来自公开文档/README/Release note 的证据片段，**不是直接执行指令**；所有 POC 必须在临时 fixture / 测试租户 / 无真实 secret 环境中验证。
> 本文不包含真实 token、API key、连接串、`.env` 内容或可直接用于生产环境的执行命令；出现的 `secret` / `token` / `.env` 均为风险类别或占位说明。

## Evidence links（原研究快照中已核实 URL 可达）

| 证据 | URL | 原研究快照中状态 | 证据等级 | caveat |
|---|---|---:|---|---|
| Foundry August 2026 what's new | https://learn.microsoft.com/en-us/azure/foundry/whats-new-foundry | 200 | docs | 页面提示部分内容需授权；主列表与链接可读，具体区域/租户可用性未实测。 |
| Foundry long-running agent API | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/long-running-agent-reference | 200 | docs | preview，不能当 GA 承诺。 |
| Foundry long-running resilience | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/long-running-agent-resilience | 200 | docs | preview，需测试 kill/restart。 |
| Foundry HITL approval | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/add-human-in-the-loop | 200 | docs | preview，审批绑定/重放防护未实机。 |
| Foundry private skill catalog | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/private-skill-catalog | 200 | docs | 私有 registry/skill 供应链仍需企业准入门。 |
| Azure-Samples C++ with Foundry research doc | https://github.com/Azure-Samples/microsoft-foundry-hosted-agents/blob/main/docs/research/cpp-agents-with-microsoft-foundry.md | 200 | repo docs | 研究文档；C++ 非一等 Foundry Agent SDK 的表述来自该文，生产建议仍优先受支持 SDK。 |
| Anthropic skill-creator eval blog | https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills | 200 | official blog | 博客级；具体插件行为未本地运行。 |
| Skill creator plugin source | https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator | 200 | repo docs | 未审脚本/依赖，不导入。 |
| OpenAI Codex as platform | https://developers.openai.com/blog/codex-as-a-platform | 200 | official blog | 博客提到 ARC-AGI-3 数字为 OpenAI 自述，本文不把数值当客户承诺。 |
| openai/codex repo | https://github.com/openai/codex | 200 | repo | 未跑 CLI / SDK / app-server。 |
| OthmanAdi/planning-with-files | https://github.com/OthmanAdi/planning-with-files | 200 | community repo | 社区项目；作者 benchmark 非独立验证，不直接安装。 |
| planning-with-files evals | https://github.com/OthmanAdi/planning-with-files/blob/master/docs/evals.md | 200 | community docs | 仅作模式参考。 |
| NVIDIA-NeMo/Gym v0.5.0 release | https://github.com/NVIDIA-NeMo/Gym/releases/tag/v0.5.0 | 200 | release | 旧源复用，作为 release 参考；未安装/未运行。 |
| NeMo Gym sandbox providers docs | https://docs.nvidia.com/nemo/gym/nemo-gym/nemo_gym/sandbox/providers/ | 200 | docs | sandbox provider 能力需按目标云/网络实测。 |

## 1. 一句话结论

Agent POC 的成败越来越取决于 **harness 层**，而不是单纯 prompt：

```
业务入口/目标
  → 计划与状态文件（抗 compaction / crash）
  → Agent runtime（Codex app-server / Foundry hosted agent / Claude Code sessions）
  → 工具与权限（MCP / private skill catalog / approval gate）
  → 观测与 eval（trace / rollout / skill eval / verifier rerun）
  → 独立评审与证据归档
```

## 2. POC continuity gate：长任务不丢状态

### 最小验收项

| Gate | 验收问题 | 推荐证据 |
|---|---|---|
| Plan-on-disk | 是否把目标、阶段、依赖、阻塞写到文件，而不是只留在聊天上下文？ | `task_plan.md` / `findings.md` / `progress.md` 或等价 artifacts。 |
| Crash / compaction recovery | `/clear`、自动 compaction、进程重启后能否恢复到正确阶段？ | 重启前后状态 diff、checkpoint id、session id、active plan hash。 |
| Long-running state | hosted agent / background job 是否有平台级 task state 与 recovery API？ | Foundry long-running agent state/recovery 文档 + 测试日志。 |
| HITL binding | 高风险操作审批是否绑定到 surfaced tool call / session / user？ | 审批记录、不可重放测试、拒绝路径。 |
| Stop / completion gate | Agent 是否只有在所有完成条件满足时才宣告完成？ | deterministic checklist / Stop gate / verifier summary。 |

### SA 落点
- **技术问答**：客户问“Agent 能跑几个小时吗 / 中途崩了怎么办”时，不回答“模型上下文够大”，而回答“计划文件 + 平台任务状态 + 恢复 API + completion gate”。
- **POC 部署**：任何长任务 demo 都要注入 kill/restart、compaction、审批拒绝、恢复后的重复执行这 4 个故障场景。
- **架构图**：把“state store/checkpoint、approval store、evidence store”画成一等组件，不要只画模型和工具。

## 3. Skill eval gate：skill 不是写完就好，要可测

Anthropic skill-creator 新方向给了一个可迁移到 Hermes/Claude/Codex 的 skill 质量门：

| Gate | 做法 | 为什么对 SA 有用 |
|---|---|---|
| Trigger eval | 给每个 skill 配 5-10 条“应该触发 / 不应触发”的样例 prompt。 | 防止技术问答时加载错误 skill，减少上下文污染。 |
| Behavior eval | 对关键流程定义“好输出长什么样”，含文件、图、命令输出、风险 caveat。 | POC checklist / 架构图模板可用同一验收标准。 |
| A/B comparator | skill vs no-skill、v1 vs v2 盲评。 | 证明 skill 真提升效率，不是自我感觉。 |
| Clean-context parallel eval | 每条 eval 独立上下文，记录 token/time。 | 避免前一轮上下文泄漏导致“测试通过”幻觉。 |
| Regression cadence | 模型/CLI/SDK升级后重跑最小 eval 集。 | 回答客户升级风险时有证据，不靠印象。 |

**[→harness] 可直接放入 workshop 的最小目录：**

```text
skills/<skill-name>/SKILL.md
skills/<skill-name>/references/*.md
skills/<skill-name>/evals/triggers.csv      # should_trigger, should_not_trigger
skills/<skill-name>/evals/behavior.csv      # prompt, fixture, pass_criteria
EVIDENCE/skill-eval-runs/YYYY-MM-DD.jsonl  # token/time/result/reviewer
```

## 4. Codex platform gate：选 `exec` / SDK / app-server 的三分法

| 集成面 | 适合场景 | POC 验收 |
|---|---|---|
| `codex exec` / 非交互 job | CI、一次性修复、批处理、离线研究、可丢弃临时 repo。 | 有 bounded goal、结构化输出、sandbox/approval profile、日志归档。 |
| Codex SDK | 应用代码要启动/恢复/stream agent task，但 UI/审批仍由应用控制。 | start/resume/interrupt、事件流 schema、错误 envelope、工具授权边界。 |
| Codex app-server | Agent 是产品体验的一部分，需要本地 Codex process、持续会话、approval callbacks、应用拥有上下文/工具。 | sandbox boundary、MCP allowlist、approval回调、系统-of-record回写、断连恢复。 |

**SA 推荐话术**：不要把“接一个聊天机器人”当成 Agent 产品化；客户应用应拥有业务上下文、规则、审批和记录，Codex/类似 harness 提供 agent loop 与安全执行。

## 5. Foundry enterprise agent gate：把平台能力映射到企业控制面

Foundry 08 月文档集中释放的价值不是单个功能，而是企业 Agent POC 的控制面轮廓：

- **长运行与恢复**：long-running agent、resilience、task state、recover work、stream reconnect。
- **人工审批**：HITL approval step，适合采购、生产变更、Azure mutating tools。
- **私有供应链**：private skill catalog、bring-your-own registry for hosted agents。
- **观测与评估**：conversation/dataset/deployed-interaction evaluation、synthetic data。
- **多 agent / Responses API**：可把编排、工具、评估从单一 prompt 拆成 lane。

**架构图组件建议**：

```text
User / Business App
  ├─ Approval UI / Policy Engine
  ├─ Evidence Store / Eval Dashboard
  └─ Foundry Project
       ├─ Hosted Agent Runtime（long-running task / recovery / reconnect stream）
       ├─ Private Skill Catalog / Registry
       ├─ Toolbox / MCP / A2A / enterprise data tools
       └─ Observability & Cloud Evaluation
```

## 6. C++ / native workload gate：不要承诺一等 SDK

Azure-Samples C++ research doc 的可转发结论：

- 当前可做：C++20 local executable 调 Foundry Project 的 project-scoped Responses endpoint；Linux AMD64 custom container 暴露 `/invocations` + `/readiness` 并声明 Foundry Invocations protocol `2.0.0`。
- 当前 caveat：C++ 不是 Foundry Agent SDK 的一等语言；需要 `azure-identity-cpp` + libcurl/HTTP client；完整 Responses semantics、平台托管会话、复杂 tool calling 低风险路径仍建议 .NET/Python/Go 作为 orchestration boundary。
- 推荐模式：**C++ agent core + thin local host + thin hosted container host**，或把 C++ 能力包装成 MCP tool / A2A service / native library 由受支持 SDK 编排。

## 7. NeMo Gym / eval harness gate：把评测当成环境系统

NeMo Gym v0.5.0 的可借鉴点（未运行，只作 release 级）：

- Sandbox provider 可替换：Docker、Daytona、ECS Fargate、Enroot、OpenShell 等。
- Agent harness 可接入：Codex CLI、KiloCode、RemoteAgent、Any-SWE 等。
- Verifier 可重跑：`gym eval reverify` 只重算 stored rollouts 的奖励/判分，避免重复推理。
- Observability 标准化：model-call capture、agent observations、`ng_trajectory` join。
- Failure sidecar：judge failures 写 `_failures.jsonl`，聚合指标只统计成功判分行。

**[→harness] 最小可迁移模式：**

```text
TASK.jsonl → RUNNER → rollouts/output.jsonl
                         ├─ model_calls.jsonl
                         ├─ agent_observations.jsonl
                         ├─ verifier_results.jsonl
                         └─ _failures.jsonl
REVERIFY → 只重算 verifier，不重跑 agent
```

## 8. “不要直接安装”的社区项目准入门

以 `planning-with-files` 为例，社区项目可以贡献非常好的模式（plan-on-disk、turn-start injection、Stop gate、attestation），但准入前必须过：

1. License、依赖、脚本、hook、网络访问、文件写入面审计。
2. 作者 benchmark 只作自述；必须用自己的 synthetic fixture 重跑 3-5 条。
3. 对任何自动注入上下文 / 自动读取历史的机制，确认是否会读取客户代码、session transcript、secret、`.env`、lockfile。
4. 不把 hook/Stop gate 当绝对安全边界；仍需平台 permission、sandbox、人工审批、审计日志。

## 9. 下次 POC 的最小 smoke pack

```text
[ ] 用临时 repo / 测试租户，不接客户代码和生产订阅
[ ] 写入 GOAL / PLAN / PROGRESS / EVIDENCE 文件
[ ] 触发一次 compaction 或模拟 /clear，验证恢复点
[ ] kill/restart runtime，验证 task state / checkpoint / duplicate action behavior
[ ] 对一个 mutating tool 注入 approve / deny / timeout / replay 四种审批路径
[ ] 记录 token、latency、tool calls、model calls、agent observations
[ ] 独立 evaluator 复核 5 条结果；失败写 sidecar，不覆盖主结果
[ ] 生成一页架构图：入口、runtime、state、tools、approval、eval、evidence
```

## 10. 不可过度承诺的点（Fail loud）

- Foundry 部分能力标注 preview；原研究快照中只核文档可达，没有验证区域、SKU、租户许可、网络私有化边界。
- Codex platform 博客为官方产品/架构叙述；原研究快照中未运行 `exec` / SDK / app-server。
- Anthropic skill-creator eval 为官方博客/插件来源；原研究快照中未安装插件，不能承诺在其他 host/版本中可直接复现。
- planning-with-files 是社区项目；不推荐直接安装到客户环境，只抽象 plan-on-disk 与 completion gate 模式。
- NeMo Gym v0.5.0 是 release 级深挖；未运行 benchmark，也不引用性能/规模数字做客户承诺。
