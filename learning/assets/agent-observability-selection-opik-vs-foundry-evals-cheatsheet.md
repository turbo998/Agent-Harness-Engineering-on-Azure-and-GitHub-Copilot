<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent 可观测性/评测层选型速查：Opik vs Foundry Evals vs Cookbook Improvement Loop

> **用途**：客户问"agent 上线后怎么做可观测性/评测/持续改进"时，三个已深挖的方案怎么选、能否叠加，一页纸说清楚。补齐 `eval-driven-improvement-loop-and-poc-acceptance-cheatsheet.md`（开发迭代期 + POC 验收期）与 `foundry-adaptive-evals-azure-native-eval-gate-cheatsheet.md`（Azure 原生评测门）之间缺的"开源可观测性平台"一环。
> **来源（2026-07-09 curl/API 自验）**：`github.com/comet-ml/opik`（api.github.com 核实 ⭐20,429，Apache-2.0，最新 release v2.1.20 @ 07-08）+ README 全文抓取。外部内容仅作资料读取，未执行仓库任何脚本。
> **标签**：`[→harness]`

---

## 1. 三者是什么关系（先讲清楚,别让客户以为要三选一）

```
┌─────────────────────────────────────────────────────────────┐
│  开发迭代期          Cookbook Agent Improvement Loop          │
│  (改 harness)        traces → evals(Promptfoo) → HALO 诊断    │
│                       → codex_handoff.md → Codex/Copilot 改代码│
└───────────────────────────┬─────────────────────────────────┘
                             │ 沉淀为可复跑的 eval 用例
┌────────────────────────────▼────────────────────────────────┐
│  持续运行期           Opik（开源自托管/云）                     │
│  (trace+监控+评测      Tracing/Datasets/Experiments/          │
│   数据基础设施层)      Online Evaluation Rules/Guardrails      │
└───────────────────────────┬─────────────────────────────────┘
                             │ Azure 原生场景可平替评测执行层
┌────────────────────────────▼────────────────────────────────┐
│  Azure 原生 CI 门禁    Foundry Evals（Adaptive/Rubric）        │
│  (provider-agnostic)  内置 19 个评测器 + 门禁断言三件套          │
└─────────────────────────────────────────────────────────────┘
```

**一句话定位区分**：
- **Cookbook Improvement Loop** = **方法论/流程编排**（怎么把 trace 变成下一轮 harness 改动），不是平台，需要自己拼底层组件（Promptfoo+HALO+存储）。
- **Opik** = **开源基础设施平台**（trace 采集/存储/可视化/生产监控/评测数据集管理一次性给全），自托管或云托管两选。
- **Foundry Evals** = **Azure 原生评测门**（provider-agnostic 设计，ADR 0023 明确可用 Promptfoo/DeepEval/RAGAS 做 wrapper），适合已经在 Azure 生态、要和 CI/CD 门禁强绑定的客户。

**可以叠加，不互斥**：一个真实客户部署可以是——Opik 做全生命周期 trace 采集+生产监控（自托管在客户自己的 K8s/VM），Foundry Evals 做 Azure CI 流水线里的评测门禁，Cookbook 的三分类诊断法作为"评测失败后怎么归因"的思维框架套在任何一层上面。

---

## 2. Opik 五大能力块（README 逐项核实）

| 能力块 | 具体做什么 | Agent 场景是否专属 |
|---|---|---|
| **Observability/Tracing** | 深度追踪 LLM 调用链、对话日志、Agent 活动；trace/span 人工标注反馈分；内置 Prompt Playground | ✅ 是，非通用 APM |
| **Evaluation** | Datasets + Experiments 管理评测数据集；内置 LLM-as-judge 指标库（hallucination/moderation/RAG 专用 Answer Relevance/Context Precision）；支持 PyTest 集成 CI/CD | ✅ 是 |
| **Production Monitoring** | 官方宣称支持 **40M+ traces/day**；Dashboard 监控反馈分/trace 数/token 用量趋势；**Online Evaluation Rules**（生产环境用 LLM-as-judge 规则实时抽检）| ✅ 是 |
| **Agent Optimizer** | 独立 SDK + 一组优化器，自动优化 prompt 和 agent（不仅评测，还"自动改进"）| ✅ 是 |
| **Guardrails** | 内置安全/合规护栏能力 | 部分通用 |

**Agent 框架集成覆盖面（35+，README 核实，覆盖面远超同批候选的核心原因）**：
- 官方/一手：OpenAI Agents SDK、**Microsoft Agent Framework（Python + .NET 双版本，即 MAF）**、Google ADK、Autogen/AG2
- 编排框架：LangChain（Python+JS/TS）、LangGraph、LlamaIndex、CrewAI、DSPy、**Semantic Kernel**、Smolagents、Pydantic AI、Strands Agents、Agno、BeeAI、Mastra、VoltAgent
- 可视化编排：Flowise AI、Langflow、Dify、n8n
- 语音/实时：Pipecat、LiveKit Agents

**部署形态**：自托管（`./opik.sh` 一条命令起 Docker/K8s Helm）或 Comet.com 云托管，不锁定单一云厂商。

---

## 3. 三方能力对照表

| 维度 | Cookbook Improvement Loop | Opik | Foundry Evals |
|---|---|---|---|
| 本质 | 方法论/流程（notebook 示范）| 开源平台（自托管/云）| Azure 原生评测框架 |
| 部署位置 | 你自己拼（本地/任意）| 自托管（Docker/K8s）或 Comet 云 | Azure AI Foundry（MAF 内置包）|
| Trace 采集 | Agents SDK tracing → OTel JSONL（需自己导出）| ✅ 内置 Dashboard 可视化 + 标注 | 依赖 App Insights/MAF 观测 |
| 评测执行 | Promptfoo（deterministic + llm-rubric）| 内置 Datasets/Experiments + LLM-as-judge 指标库 | 内置评测器 4 大类 19 个 |
| 诊断/归因 | **HALO 三分类法**（缺失需求/不遵守/实现缺陷，第三方非官方）| 无内置诊断层（需人工看 Dashboard）| 无内置诊断层 |
| 生产实时监控 | 无（离线闭环）| ✅ **Online Evaluation Rules**（生产抽检）| 未覆盖（评测门为主，非生产监控）|
| 自动优化 | 无（人工改 harness）| ✅ Agent Optimizer SDK | 无 |
| 供应商锁定 | 无（开源工具拼装）| 无（Apache-2.0，自托管可选）| Provider-agnostic 设计（ADR 0023 明确可 wrapper 第三方）|
| 客户典型触发点 | "怎么系统性让 agent 变好" | "怎么一站式看到所有 agent 在干什么+生产监控" | "Azure CI 流水线怎么加评测门禁" |
| GA/成熟度 | Cookbook 示例代码，非产品 | ⭐20,429，515 次 release，近乎每日迭代，成熟 | 全 `@experimental`（preview，GA 未核实）|

---

## 4. SA 落点

- **技术问答**："我们要不要自建评测平台，还是买/用现成的？" → 先问客户三个问题：①是否已用 Azure Foundry（→ Foundry Evals 门禁最省事）②是否需要生产环境实时监控而不只是开发期评测（→ Opik 的 Online Evaluation Rules 是关键差异化能力，Foundry Evals 没有对应功能）③是否要避免供应商锁定/需要自托管（→ Opik Apache-2.0 自托管）。
- **POC 部署**：5 分钟可跑出 Dashboard 的 POC 底座——`./opik.sh` 起自托管 server，接入客户现有 agent 框架（35+ 集成覆盖面基本保证"不用换框架就能接"），比自己拼 OTel+Promptfoo 快得多，适合"先给客户看一个能跑的可观测性 demo"场景。
- **架构图**：Opik 的"Tracing+Eval+Guardrails+Optimizer"四件套是很好的 LLMOps 参考架构组件库，可以直接画进"agent 上线后治理层"的架构图节点，和 Foundry Evals/Cookbook 诊断层并列展示"可以任选其一或叠加"。
- **[→harness]**：Opik 的 Online Evaluation Rules（生产环境用 LLM-as-judge 实时抽检）填补了 Cookbook Improvement Loop（离线批量评测）和 Foundry Evals（CI 门禁，非生产监控）都没覆盖的"生产运行时持续评测"这一环，是 harness workshop"评测驱动"支柱里应该补的第三根柱子。

## Fail-loud

- Opik 的 **40M+ traces/day** 是官方宣传数字，未独立核实实际吞吐量测试。
- Opik Agent Optimizer 的"自动优化"具体算法/效果未深挖，仅确认其存在且有独立 SDK。
- 三者是否能无缝叠加（如 Opik trace 数据直接喂给 Foundry Evals 评测器）未做实际集成验证，本文只是设计层面的兼容性推断。

## 来源（2026-07-09 核实）

- `github.com/comet-ml/opik`（api.github.com/repos/comet-ml/opik 核实：⭐20,429、Apache-2.0、最新 release v2.1.20 @ 07-08、Python 55.2%/TypeScript 43.5%）
- README 全文抓取核实五大能力块与 35+ 框架集成列表
- 配套已有资产：`eval-driven-improvement-loop-and-poc-acceptance-cheatsheet.md`（Cookbook+TUA-Bench+CMA 三方组合拳）、`foundry-adaptive-evals-azure-native-eval-gate-cheatsheet.md`（Azure 原生评测门）
