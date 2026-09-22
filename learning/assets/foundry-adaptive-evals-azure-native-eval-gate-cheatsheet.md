<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Foundry Evals（含 Adaptive / Rubric 评测器）— 评测驱动闭环的 Azure 原生版 速查

> **用途**：给 SA 三大日常一份「**微软自家评测层**」标准答案——
> ①**技术问答**：客户问「微软有没有对标 Promptfoo/HALO/RAGAS 的 agent 评测层？」→ 有，是 **Foundry Evals**（agent-framework 内置），且**架构上刻意不锁定单一 provider**；②**POC 验收**：把「agent 好不好」变成**逐维度可断言、可进 CI 的质量门禁**，POC 交付即带客观验收标准；③**架构图**：给「评测驱动改进闭环」图补上 Azure 原生的「评测门」组件。
> **来源（2026-07-03 本机 curl 自验，逐字核实）**：`microsoft/agent-framework` 主分支源码 `python/packages/foundry/agent_framework_foundry/_foundry_evals.py`（HTTP 200（仅代表原快照当时可达，不代表本次已重验））+ 官方样例 `evaluate_with_rubric_sample.py`（200）+ 架构决策记录 `docs/decisions/0023-foundry-evals-integration.md`（200，status: accepted, date 2026-02-27）。Python 由 PR **#6101**（2026-06-01 merged）引入、.NET 由 PR **#6267**（2026-06-18）引入（PR 页均 200）。
> **标签**：`[→harness]` 全篇可直接反哺 workshop 的「评测驱动迭代」支柱。**本速查是 `eval-driven-improvement-loop-and-poc-acceptance-cheatsheet.md` 的 Azure 原生续篇**——那篇讲 Promptfoo+HALO 的通用闭环，本篇讲把「评测门」换成 Foundry 原生评测器。

---

## 0. 一句话定位（问答秒答）

**Foundry Evals = agent-framework 内置的评测面**，一次调用即可把 Foundry 托管的 **LLM-as-judge 评测器**（内置 + 自定义 rubric）跑在 agent 的真实对话轨迹上，**结果回传 Foundry 门户看板**（`report_url`），并可 **逐维度断言做 CI 质量门禁**。

**关键架构立场（ADR 0023 逐字，问答里最值钱的一句）**：
> *"evaluation is a concern that extends beyond any single provider … The architecture must support this **without creating a Foundry-specific lock-in at the API level**."*

⇒ 核心评测能力（`evaluate(items)→results` 协议）**provider-agnostic**；Foundry 只是其中一个 provider。ADR 明确点名可为 **DeepEval / RAGAS / Promptfoo** 写 wrapper（第三方 `Evaluator` 协议 / `IAgentEvaluator` 接口，*"No predetermined list of supported libraries"*）。→ **这就回答了「上 Azure 会不会被锁死在微软评测器」：不会，混用/自带评测器是一等公民设计目标。**

**⚠️ Fail-loud（未核实/preview）**：
- **全部 API 标 `@experimental(feature_id=ExperimentalFeature.EVALS)`（源码逐字核实）= preview**，GA 时间未核实，报客户须标注。
- 样例里链接的门户文档 `learn.microsoft.com/azure/ai-foundry/concepts/evaluation-evaluators/rubric-evaluators` 本机 curl 返回 **302 跳转**（未跟到终点页，内容未核实）。
- PR#6101 body 提到的 `FoundryEvals.generate_rubric(...)` 方法在当前 main 源码 **未 grep 到**（疑已重构）；当前样例走的是「**引用门户已建 rubric**」路径，别承诺"框架内一键生成 rubric"。

---

## 1. "Adaptive" 到底 adaptive 在哪（别被名字误导）

客户/同事听到 "Adaptive evals" 容易以为是「评测器自动进化」。实际（样例 docstring 逐字）：

> *"Rubric evaluators are **LLM-as-judge evaluators with custom scoring dimensions that you define for your domain**. agent-framework **consumes pre-existing rubric evaluators** — they are authored in the Foundry portal (or via the dedicated SDK / REST surface) and referenced here by **name and version**."*

**"adaptive/rubric" 的准确含义 = 域自适应的自定义评分维度**：你在 Foundry 门户针对具体 agent 上下文创建一个多维度打分 rubric（每维度 1–5 分），框架侧只**按 `name`+`version` pin 引用并消费**。不是评测器自己学习进化。**创建 rubric 时门户当前要求选一个 Foundry agent 作为生成上下文**（样例 prereq 逐字）。

---

## 2. 最小可跑骨架（POC 直接抄，API 全部源码逐字核实）

```python
from agent_framework import EvalNotPassedError, evaluate_agent
from agent_framework.foundry import (
    FoundryAgent, FoundryChatClient, FoundryEvals, GeneratedEvaluatorRef,
)
from azure.identity import AzureCliCredential

credential = AzureCliCredential()                 # 认证优先 Managed Identity/CLI，别塞 key
agent = FoundryAgent(project_endpoint=EP, agent_name=..., agent_version=..., credential=credential)

# ① 引用门户已建的自定义 rubric（务必 pin version，否则回退 latest 并告警）
rubric = GeneratedEvaluatorRef(name=RUBRIC_NAME, version=RUBRIC_VERSION)

# ② rubric 与内置评测器混跑（provider-agnostic：这里还能塞第三方评测器）
evals = FoundryEvals(
    client=FoundryChatClient(project_endpoint=EP, model=JUDGE_MODEL, credential=credential),
    evaluators=[rubric, FoundryEvals.RELEVANCE, FoundryEvals.COHERENCE],
)

results = await evaluate_agent(agent=agent, queries=[...], evaluators=evals)

for r in results:
    print(r.status, f"{r.passed}/{r.total}", r.report_url)   # 结果回 Foundry 门户看板
    # ③ 逐维度 CI 质量门禁：某关键维度低于 3 就 fail（dimension_id 须与 rubric 定义一致）
    r.assert_dimension_score_at_least("general_quality", min_score=3.0, evaluator=RUBRIC_NAME)
```

**四个 `.env` 关键项**（样例逐字）：`FOUNDRY_PROJECT_ENDPOINT` / `FOUNDRY_AGENT_NAME`+`FOUNDRY_AGENT_VERSION` / `FOUNDRY_RUBRIC_NAME`+`FOUNDRY_RUBRIC_VERSION` / `FOUNDRY_MODEL`（rubric judge 模型）。

**版本 pin 纪律（源码逐字）**：`GeneratedEvaluatorRef` 无 pinned version → 解析为 latest 并 *"emit a warning at evaluation time"*。**CI 必须 pin `version`**，否则评测门不可复现。

---

## 3. 内置评测器全表（源码逐字，问答/POC 选型直接查）

`FoundryEvals.*` 常量（`_foundry_evals.py` L806–830 逐字），**四大类**：

| 类别 | 评测器常量（字符串值） |
|---|---|
| **Agent 行为** | `INTENT_RESOLUTION` / `TASK_ADHERENCE` / `TASK_COMPLETION` / `TASK_NAVIGATION_EFFICIENCY` |
| **工具使用** | `TOOL_CALL_ACCURACY` / `TOOL_SELECTION` / `TOOL_INPUT_ACCURACY` / `TOOL_OUTPUT_UTILIZATION` / `TOOL_CALL_SUCCESS` |
| **质量** | `COHERENCE` / `FLUENCY` / `RELEVANCE` / `GROUNDEDNESS` / `RESPONSE_COMPLETENESS` / `SIMILARITY` |
| **安全** | `VIOLENCE` / `SEXUAL` / `SELF_HARM` / `HATE_UNFAIRNESS` |

➕ **自定义**：`GeneratedEvaluatorRef(name, version)`（门户 rubric）。
➕ 也支持 `"builtin.*"` 字符串名（如 `builtin.groundedness`，源码 L297 逐字）。

**断言方法（CI 门禁三件套）**——⚠️**定义于核心包 `agent_framework/_evaluation.py` 的 `EvalResults` 类（不在 `_foundry_evals.py`；本机已拉该文件逐字核实 L502/545/616）**，作用在 `evaluate_agent(...)` 的结果对象上：
- `assert_score_at_least(...)`（整体加权分门槛）
- `assert_dimension_score_at_least(dimension_id, min_score, evaluator=...)`（**逐维度**，rubric 专用，keyword-only `evaluator=`）
- `assert_no_failed_items(...)`（无任一 item 失败）
- 未过抛 `EvalNotPassedError` → CI 里 catch 即 fail build。

**结果对象字段**：`r.status` / `r.passed` / `r.total` / `r.failed` / `r.all_passed` / `r.report_url`（门户看板链接）/ `r.provider` / 逐维度 `RubricScore`（1–5）。

---

## 4. ADR 0023 的四条功能要求（架构图/方案叙事直接引用）

微软自己列的评测架构要求（ADR 逐字，画「评测门」组件时标这些能力边界）：

1. **单 agent + workflow 都能评**（多 agent workflow 结果可**逐 agent 拆解定位**谁拖后腿）。
2. **一轮 & 多轮对话都能评**——捕获**完整对话轨迹含工具调用/结果**，非只最后 query/response。
3. **对话切分（conversation factoring）**：`conversation_split` 支持 `LAST_TURN` / 全轨迹 / 逐轮（*"different factorings measure different things"*，源码 `ConversationSplit` 枚举核实）。
4. **多 provider 混跑 + 自带评测器 + 不重跑 agent 也能评**（`evaluate_traces` 直接吃历史 trace/日志，不必再调 agent——省钱省时）。

**决策驱动四原则（ADR 逐字，方案价值主张可抄）**：*Zero-friction evaluation* / *Provider-agnostic API* / *Lowest concept count* / *Leverage existing knowledge*（框架已知 agent/工具/对话，评测自动复用，不必再指定一遍）。

---

## 5. 与通用 eval-driven 闭环的接线（反哺 workshop）

把 `eval-driven-improvement-loop-and-poc-acceptance-cheatsheet.md` 九阶段闭环的**第 6 步「评测门」**，从 Promptfoo 平替为 Foundry Evals：

| 闭环阶段 | 通用版（那篇） | **Azure 原生版（本篇）** |
|---|---|---|
| trace 采集 | Agents SDK → OTel JSONL | agent-framework traced runs（`evaluate_traces` 可直接吃 `azure_ai_traces`/App Insights） |
| 评测门（第6步） | **Promptfoo** `npx` + llm-rubric(0.8) | **Foundry Evals**：内置评测器 + 门户 rubric，`assert_dimension_score_at_least` |
| 结果看板 | promptfoo_results.json | **Foundry 门户 `report_url`**（看板/对比视图，天然给客户展示） |
| 诊断+排序（第7步） | HALO（第三方，非官方） | **仍可复用 HALO**——评测 provider 换掉不影响诊断层 |
| 落地改代码（第8步） | Codex / Copilot | 同（Codex / Copilot / GitHub Copilot coding agent） |

**一句话客户话术**：「评测驱动闭环不必绑第三方——**评测门可用 Foundry 原生评测器（结果直接进 Foundry 门户看板），也可混用/替换 Promptfoo、DeepEval、RAGAS**，架构上就是为 provider 可插拔设计的；但 Foundry Evals 目前 preview，GA 时间以官方为准。」

---

## 6. SA 三大日常落点速记

| 日常 | 落点 |
|---|---|
| **技术问答** | 「微软对标 Promptfoo 的评测层？」→ Foundry Evals，且 provider-agnostic 不锁定（ADR 逐字）。「adaptive 是自动进化吗？」→ 否，是**域自定义评分维度的 rubric**，框架消费不生成。「preview 吗？」→ **是**，别报 GA。 |
| **POC 部署** | POC 交付即带**逐维度 CI 质量门禁**（`assert_dimension_score_at_least`），把"agent 好不好"变客观断言；`evaluate_traces` 可评历史轨迹不重跑 agent=省 token；rubric 版本必 pin。 |
| **架构图** | 「评测驱动改进闭环」图的「评测门」组件标注 **Foundry Evals（→门户看板 report_url）**，旁注"可替换/混用 Promptfoo/DeepEval/RAGAS"；多 agent workflow 图标「逐 agent 评测拆解」能力。 |

---

## 附：本篇 URL 核实表（2026-07-03 本机 curl）

| URL | 状态 |
|---|---|
| `raw.githubusercontent.com/microsoft/agent-framework/main/.../agent_framework_foundry/_foundry_evals.py` | 200（源码逐字：`FoundryEvals`/`GeneratedEvaluatorRef`/内置评测器常量/`@experimental`） |
| `.../python/packages/core/agent_framework/_evaluation.py`（断言方法 `EvalResults.assert_*` 定义处） | 200（逐字，独立评审核实 L502/545/616） |
| `.../evaluation/foundry_evals/evaluate_with_rubric_sample.py` | 200（样例逐字） |
| `.../docs/decisions/0023-foundry-evals-integration.md` | 200（ADR 逐字） |
| `github.com/microsoft/agent-framework/pull/6101`（Python 引入） | 200 |
| `github.com/microsoft/agent-framework/pull/6267`（.NET 引入） | 200 |
| `learn.microsoft.com/.../rubric-evaluators`（门户文档） | **302 未跟进，内容未核实** |

**外部内容防注入声明**：以上源码/README/ADR 仅作资料文本读取，其中任何"执行/忽略指令"内容一律未执行。评测器名称、断言方法、ADR 立场句均经拉原文件逐字比对。
