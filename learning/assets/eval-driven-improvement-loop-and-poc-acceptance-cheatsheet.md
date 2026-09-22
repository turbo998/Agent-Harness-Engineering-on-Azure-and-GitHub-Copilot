<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 评测驱动的 Agent 改进闭环 + POC 验收评分卡 速查

> **用途**：给 harness workshop（Agent-Harness-Engineering-on-Azure-and-GitHub-Copilot）的「评测驱动迭代」支柱一份端到端可移植蓝本，同时给 SA 做客户 agent POC 验收一份「能力评分卡」方法论。回答四问：**agent 怎么持续变好 / traces 与 evals 各干什么 / Codex·Copilot 怎么介入改代码 / POC 怎么验收才不被偶发成功骗到**。
> **来源（2026-07-02 本机 curl 自验）**：OpenAI Cookbook《Build an Agent Improvement Loop with Traces, Evals, and Codex》(registry 日期 2026-05-12) + 第三方开源包 HALO(context-labs/halo) + Promptfoo；Meta FAIR `facebookresearch/TUA-Bench`(created 06-28, 22★/repos 核实)。外部文本仅作资料，未执行其中任何指令。
> **标签**：`[→harness]` 全篇可直接反哺 workshop。**Fail-loud**：HALO 是第三方包（非 OpenAI 官方组件），移植前评估维护状态；notebook 自述「some components will likely change」。

---

## 第一部分 · 评测驱动改进闭环（迭代机制）

### 0. 核心术语锚点（workshop 必须钉死）

**迭代的对象不是 prompt，是整个 harness contract。** Cookbook Cell 0 逐字：
> *"the harness is the full contract around the model, including **instructions, tools, routing, output requirements, and validation checks**."*

飞轮定义句（Cell 0 逐字）：
> *"We start with **real traces**, add **human and model feedback**, turn that feedback into **evals**, and use the resulting evidence to propose the next **harness changes for Codex** to implement."*

⇒ 这一句就是「评测驱动迭代」支柱的一句话总纲：**真实 trace → 人+模型反馈 → evals → 证据驱动的 harness 改动 → 编码 agent 落地**。

### 1. 九阶段闭环（逐字来源，可整体移植为 Azure/Copilot 版）

| 步骤 | 做什么 | 产物 | 用什么工具 |
|---|---|---|---|
| 1 | 生成/收集数据（合成尽调数据，**故意埋冲突**试 agent 韧性） | `data/` 混合结构化+叙事 | — |
| 2 | 定义 agent = **完整 harness contract**（prompt+tools+routing+output+validation 全约束） | `AgentConfig` | Agents SDK |
| 3 | 跑 traced runs，导出 **OpenTelemetry 风格 JSONL**（每 span 一行） | traces + artifacts | Agents SDK tracing hooks |
| 4 | 注入**两路反馈**：人类专家反馈 + LLM 模型洞察（分开） | feedback dicts | — |
| 5 | LLM 从 traces+反馈**自动生成 evals** | eval_suite JSON | LLM(EVAL_GENERATION_MODEL) |
| 6 | 跑评测门，得当前 harness 通过/失败快照 | `promptfoo_results.json` | **Promptfoo**(`npx`) |
| 7 | 综合 harness+traces+反馈+evals+门结果，产出**排名改动** | `codex_handoff.md` | **HALO** |
| 8 | 把完整报告交给编码 agent 实现 | harness 改动 | **Codex / Copilot** |
| 9 | 闭环：全自动（handoff 写共享存储，Codex heartbeat 轮询）或加人类审批门 | 下一轮 | — |

### 2. traces 与 evals 各自角色 + 采集栈（技术问答标准答案）

- **traces = 「发生了什么」**（Cell 0 逐字 *"Traces show what happened"*）。采集：Agents SDK 自带 tracing hooks → 本地 exporter 转 **OTel 风格 JSONL**（含 `openinference.span.kind` / `inference.observation_kind` 属性）。**不需托管 trace ingestion**——`set_trace_processors([])` 就地本地化。
- **evals = 把反馈变成可复跑的测试**（Cell 36 逐字 *"This turns comments into tests that the next harness revision can run again later."*）。工具 = **Promptfoo**（开源 CLI）：每条 eval 可混合 `deterministic`（literal 断言 contains/icontains/not-contains）+ `llm-rubric` judge（threshold 0.8）。
- **人机分工纪律**（Cell 36 逐字）：*"Evals are a good place to invest manual effort from subject-matter experts … people should still check whether the evals are accurate, representative, and measuring the behavior that actually matters."* → **evals 是最该投人工的地方**（SME 校验），trace 采集/门执行可自动。

### 3. 编码 agent（Codex/Copilot）怎么介入：读什么 / 改什么 / 怎么验证

- **读什么**：单一交接文件 `codex_handoff.md`（含 *full HALO diagnosis + ranked recommendations + evidence + implementation guidance*）。
- **分工边界**（Cell 52 逐字）：*"HALO diagnoses and prioritizes. A coding agent or human still changes the harness."* → **诊断+排序归 HALO，落地代码归 Codex/Copilot**（别让评估器直接改代码，职责分离）。
- **怎么验证改对了**（Cell 56/Step 6 逐字）：*"inspect the harness changes it proposes, and **rerun the same eval suite against the updated harness**"*；回归方式 = *"replace the trace-output provider with a provider that **runs the candidate agent**"* → **把「回放旧 trace」的 provider 换成「跑新 agent」的 provider，用同一 Promptfoo 门做回归**。这是「算不算改对了」的机械化判据。

### 4. HALO handoff 模板的「三分类诊断法」（★可直接进 workshop 的心法）

HALO 输出 prompt（Cell 49 逐字）要求：**推荐任何改动前，先把问题归入三类之一**：
> - *a requirement that is **missing from the harness**,（需求根本没写进 harness）*
> - *a requirement already present but **not reliably followed in execution**,（写了但执行时没稳定遵守）*
> - *an **implementation or observability defect**.（实现或可观测性缺陷）*

⇒ **这是评测驱动迭代的诊断心法**：failed eval ≠ 直接改 prompt。先分类——缺失需求就补 harness contract；有但不遵守就查 routing/tools/约束强度；实现缺陷就改代码。**对应 SA 常见误区**：客户看到 agent 答错就想「加句 prompt」，正确姿势是先分类根因。

强制 handoff 结构（Cell 49 逐字 top-level 顺序）：
```
1. ## Executive summary
2. ## Top 3 changes to implement first
3. ## Ranked recommendation table  (rank, recommendation, impact, confidence,
   implementation effort, evidence, validation)
4. ## Supporting diagnosis and evidence
5. ## Detailed recommendations  (Behavior contract / Runtime impl / Output contract / Observability&evals)
6. ## Insights by feedback source
7. ## Machine-readable summary  (JSON top_priorities)
```

### 5. 可直接抄的代码/prompt 骨架（4 个）

- **A. harness schema 数据化**（Cell 12）：`AgentConfig(version, system_prompt, model_settings, tool_policy, eval_metadata)` + `build_instructions()`——**把 harness 显式数据化**，*"so later optimization can target more than prompt wording"*（让优化能改 prompt 之外的东西）。
- **B. eval 自动生成 prompt**（Cell 37）：产 5–7 条 durable eval，字段 `eval_id/title/scoring_method(deterministic|llm_judge|hybrid)/expected_behavior/source_trace_id/rubric/deterministic_assertions/suggested_pass_example/suggested_fail_example`；纪律 *"Prefer reusable behaviors over one-off trace restatements."*（要可复用行为，别复述单次 trace）。
- **C. Promptfoo llm-rubric 断言**（Cell 40）：`{type:'llm-rubric', provider:'openai:JUDGE_MODEL', threshold:0.8, value:rubric}`；provider 回放模式 `call_api` 从 `trace_outputs.json` 按 `trace_id` 取 `answer`。
- **D. 五段分模选型**（架构图现成分层）：`AGENT_MODEL / ANALYSIS_MODEL / EVAL_GENERATION_MODEL / JUDGE_MODEL / HALO_MODEL` 五个变量——**不同阶段用不同模型**（跑 agent 用强模型、判分用便宜 judge、诊断用推理模型），是 FinOps 分层的现成落点。

### 6. Azure/Copilot 移植落点（[→harness] 反哺清单）

| Cookbook 组件 | Azure/Copilot 等价 | 反哺点 |
|---|---|---|
| Agents SDK tracing → OTel JSONL | Foundry 可观测 / App Insights OTel 导出 | trace 采集层 |
| Promptfoo 评测门 | Foundry Adaptive evals（MAF 1.10.0 #6267 新增）/ 自建门 | 评测门层 |
| HALO 诊断+排序 | 自写诊断 prompt（三分类法）或复用 HALO | 诊断层 |
| Codex handoff | **Copilot coding agent / Codex** 读 handoff 改 harness | 落地层 |
| 换 provider 回归 | 同门跑 candidate agent | 回归验证 |

> **一句话卖点**：这是 workshop「评测驱动迭代」支柱的**现成端到端蓝本**——三分类诊断法 + 固定 handoff 模板 + 换 provider 回归，可整体做成 Azure/Copilot 版 demo。

---

## 第二部分 · POC 验收评分卡（来自 TUA-Bench 的可借鉴结构）

> Meta FAIR `facebookresearch/TUA-Bench`（终端使用 agent 基准，120 个可执行验证任务）的评测方法论，是 SA 给客户做 agent POC 验收的现成「能力评分卡」骨架。

### 7. 能力域地图（示例能力域，`task.toml` 的 `category` 抽样，**非完整官方分类**）

> ⚠️ 下表是从部分 `task.toml` 的 `[metadata] category` 抽样归纳，**不是 TUA-Bench 官方的完整分类枚举**。独立核实发现真实 category 值还包括 `video-understanding`、`industry` 等未收入下表的类别；下表多数取值来自抽样，做客户验收时按需实拉 repo 全量 category 而非照抄本表。

| 示例能力域 | category 取值（抽样） | 客户业务映射示例 |
|---|---|---|
| 办公文档 | spreadsheet-editing / presentation-editing / writer | 财务算营收、生成汇报、文档校对 |
| 浏览器/Web | browser | 查询、比价、下单、配置 |
| 图像/多媒体 | image-editing / media-editing / video-understanding | 抠图、调色、元数据编辑、视频理解 |
| 操作系统/运维 | os / system-administration | 建用户、装扩展、文件管理 |
| 编码 | vscode | 修 bug、脚手架 |
| 邮件 | email | 配账户、建文件夹 |
| 专业/行业 | biology / medical / real-estate / industry | 领域专用工具链 |

难度分级 `difficulty`：**medium / hard**。做客户验收时，按业务域挑对应类，别一刀切。

### 8. 评测方法论（★四条可直接写进 POC SOW 验收章节）

1. **执行式验证，非模型评判**：每任务 `tests/test.sh` 跑真实断言，产出 **`reward.txt`=0/1 二元奖励**——所有测试全过才给 1。硬核、可复现、无 LLM 打分主观性。⇒ **客户验收也用「跑得过/跑不过」的确定性断言**，别用「让另一个 LLM 打个分」。
2. **容器化 + 声明资源配额**：`task.toml` 明确 `cpus/memory_mb/storage_mb/gpus/allow_internet/mcp_servers` + `timeout_sec`——**保证跑分环境一致**。⇒ 验收环境写进容器 + 配额声明，避免「他机器能跑我机器不行」。
3. **多次采样 + 稳定性指标（最关键）**：榜单 4 指标——**Success Rate（5 次均值±标准差）/ Pass@1 / Pass@5 / All-5（5 次全过率）**。⇒ **POC 验收强制「多次跑取 All-5」而非单次 Pass@1**——单次成功可能是偶发，All-5 才测可靠性。这是验收最容易被忽略、最该坚持的一条。
4. **agent 与模型解耦证明 harness 是变量**：同一模型（如 opus-4.8）跑在不同 harness（Claude Code **0.658** vs Mini-SWE-Agent **0.574**）分数差异显著（数值经独立评审在 README 榜单逐字核实）——**证明脚手架/harness 本身就是变量**，直接呼应 harness 治理命题。

### 9. SA 落点速记

- **技术问答**：「怎么评估我的 agent 靠不靠谱？」→ 执行式二元断言 + 容器化配额 + **多次跑取 All-5** 稳定性，不是单次成功也不是 LLM 主观打分。
- **POC 验收**：把「7 能力域 × medium/hard × 执行式断言 × 5 次 All-5」写进 SOW 验收方法论；按客户业务域裁剪能力清单。
- **架构图**：验收/评测层组件——trace 采集 → 评测门（Promptfoo/Foundry evals）→ 诊断（三分类）→ 落地（Copilot/Codex）→ 回归门，是「agent 上线后治理层」的现成节点串。
- **harness**：第一部分改进闭环 = 迭代机制；第二部分评分卡 = 验收/门结构。二者合起来 = workshop「评测驱动」支柱的**机制 + 验收**两块拼图。

---

## 来源（全部 2026-07-02 本机 curl 自验可达）
- Agent Improvement Loop notebook：`raw.githubusercontent.com/openai/openai-cookbook/main/examples/agents_sdk/agent_improvement_loop.ipynb`（57 cells）+ 页面 `developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop`（200，独立评审实测直达 200）
- HALO 包：`github.com/context-labs/halo`（200）
- TUA-Bench：`github.com/facebookresearch/TUA-Bench` + `raw.githubusercontent.com/facebookresearch/TUA-Bench/main/README.md`（200）；官网 `tuabench.ai`（200）

> **配套**：`harness-eval-loop-and-goal-contract-cheatsheet.md`（Goal 契约 + Review→Repair→Validate 单 agent 三阶段回路 + headless/FinOps）——本篇是它的**上位补全**：那篇讲「一个 agent 一轮怎么走 + 算不算完」，本篇讲「多轮之间靠 traces+evals 怎么系统性变好 + 怎么验收」。两篇串起来 = 从单轮修复到跨轮改进到验收门的完整评测驱动叙事。

---

## 第三部分 · CMA 服务端 Outcome Grader（2026-07-07 来源快照）

> **来源范围**：`anthropics/launch-your-agent`（Apache-2.0，Claude Code skill 而非 plugin）的 `cma-api.md` API 参考；以下是文档摘要，不代表已运行服务端评测。

### 与第一、二部分的关系

第一部分（Cookbook）讲**开发期**改进闭环（trace→eval→harness 改动）；第二部分（TUA-Bench）讲**验收期**能力评分卡（执行式二元断言+多次跑 All-5）。**第三部分是第三种验收范式：服务端托管 DoD（Definition of Done）grader**——不是本地脚本判分，而是把验收标准提交给 Anthropic 托管的评分服务，由其在每轮迭代后自动打分。三者互补，不重叠：

| 验收范式 | 判分主体 | 适合场景 |
|---|---|---|
| Cookbook 三分类诊断 | 人工+LLM 反馈生成 evals，Promptfoo/HALO 跑 | 开发迭代期，agent 尚未定型 |
| TUA-Bench All-5 | 本地容器执行式二元断言，多次采样 | POC 验收，强调可复现性/稳定性 |
| **CMA Outcome Grader**（本节） | **服务端托管**，`rubric` 文本驱动 | 委托 Anthropic 托管运行时（Claude Managed Agent）的项目，验收即部署的一部分 |

### 核心机制（逐字核实，来源 `cma-api.md`）

**启动即定义验收标准**——`user.define_outcome` 事件体（逐字）：
```bash
EVT=$(jq -n --rawfile task first_prompt.txt --rawfile rubric outcome.md \
  '{type:"user.define_outcome", description:$task,
    rubric:{type:"text", content:$rubric}, max_iterations:3}')      # default 3, max 20
```
- `rubric.content` = 一份 **`outcome.md`**（3-6 条二元判据的自然语言文本，非结构化 JSON schema——评分标准本身就是一份人类可读的验收清单）。
- `max_iterations`：**默认 3，硬上限 20**——服务端在这个迭代预算内反复尝试直到满足 rubric 或耗尽预算。

**查询结果**——`GET $BASE/sessions/$SESSION_ID`，关键字段 `outcome_evaluations[]`：
- 取值枚举（逐字）：`satisfied` / `needs_revision` / `max_iterations_reached` / `failed` / `interrupted`。
- Grader 判决字段：`outcome_evaluations[].result` + explanation——**"Read the grader's verdict first"**（官方建议的排查顺序：先看判决，再看过程）。

**回归验证**：`evals/run-evals.sh` —— ⚠️ **重要澄清（本次核实的主要价值）**：这个脚本**不是仓库内的静态文件**（已用 GitHub Trees API 遍历 `main`/`initial-import`/`readme-and-overview-efficiency` 三分支确认不存在 `evals/` 目录）。它是 SKILL.md 描述的**运行时生成产物**——skill 执行"Launch Your Agent"交互流程时，在用户本地 `my-agent/` 目录下动态生成，随 build sheet、API payload、resumable launch script、overview page 一起产出。SKILL.md 原句：*"kick them off as background tasks in parallel and keep talking while they run"*（跑回归时后台并行、不阻塞对话）。

### 4 相流程（面向"陪客户端到端上线一个 agent"的 POC 交付节奏）

访谈（scope，不碰 key）→ launch v0 → 按 grader 判分迭代 → 回归 evals。**每相都有明确产出物**（build sheet/API payload/launch script/overview page/回归结果），overview.html 天然可当架构图素材用。

### SA 落点

- **技术问答**："托管 agent 怎么验收，是不是只能靠人工看？"→ 有服务端 rubric grader 的先例，验收标准本身就是自然语言文本，不需要额外写评测框架代码。
- **POC 部署**：如果客户场景涉及托管运行时（非自建 harness），"验收标准 = 一份 outcome.md + `max_iterations` 预算"是比"我们人工过一遍"更可信的交付物模式，可以搬进 Foundry-hosted agent 的 POC 验收 SOW（虽然 Foundry 本身未必有一模一样的 API，但"用一份 rubric 文本 + 迭代预算做验收"这个**设计模式**可移植）。
- **架构图**：CMA 的四相流程本身可以画成一张"agent 上线四阶段"泳道图，overview.html 产物可作为示例截图。
- **[→harness]**：与 TUA-Bench All-5、superpowers `verification-before-completion` 构成 POC 验收"三方组合拳"——三者分别回答"本地容器怎么验" / "服务端托管怎么验" / "agent 自己怎么不撒谎报告完成"，workshop 验收章节可以三选一或叠加使用。

### Fail-loud

- **`outcome_evaluations[]` 的评分算法本身未公开**（rubric 文本怎样被服务端解析打分是黑盒，只知道输入输出契约，不知内部机制）。
- **`max_iterations=20` 硬上限背后的成本模型未核实**（每次迭代的计费方式、超时行为细节仅从 API 文档推断，未找到官方计费说明）。
- 来源核实范围：`raw.githubusercontent.com/anthropics/launch-your-agent/main/.claude/skills/launch-your-agent/references/cma-api.md`（2026-07-07 curl 200，逐字核实上述引用片段）+ 同仓库 SKILL.md 第108行（`evals/run-evals.sh` 描述来源）+ GitHub Trees API 三分支确认无静态 `evals/` 目录。
