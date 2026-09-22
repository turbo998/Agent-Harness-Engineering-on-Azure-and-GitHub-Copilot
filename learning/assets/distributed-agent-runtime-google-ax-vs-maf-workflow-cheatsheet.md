<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 分布式 Agent 运行时架构参考：google/ax vs MAF Workflow vs Azure AI Foundry Agent Service

> 来源：github.com/google/ax（curl 核实 200，Apache-2.0，star 1907/fork 106，2026-03-30 创建，2026-07-23 最后 push）。⚠️ 项目仍处 early development，暂停外部 PR，无 stable release，**不建议作为生产选型直接推荐给客户**，仅作架构参考/客户教育素材。
>

## 一句话定位
google/ax 不是 Agent 编排框架（不管 Agent 逻辑怎么写），而是**分布式 Agent 执行运行时**——假设你已经有 Agent（Harness），给你一个跑得稳、能恢复、能审计的分布式执行底座。

## 三层拓扑（可直接套用做架构图模板）
```
Client <--resumable stream--> AX Server(多租户) <--append/scan--> Event Log(sqlite/postgres)
                             │
                             └──> Actor Controller --resume/suspend--> AX Harness Server(有状态/单会话)
                                                                              │
                                                                    └──> Model / MCP Server / Environment
```
映射到 Azure：Server 层→APIM/AI Gateway；Controller→Foundry Agent Service；Harness/Actor 层→Container Apps/AKS 托管执行环境。

## 核心机制（可讲给客户的技术点）
1. **单写者（Single-Writer）不变量**：Controller 保证同一 conversation_id 同一时刻最多一个 Execution 在跑，用架构约束代替并发锁/CAS。
2. **事件溯源驱动恢复**：ConversationEvent(conversation_id/step/exec_id/harness_id/state) 落 Event Log，重连时按 last_step 回放"补课不倒带"（catch up, not rewind）。
3. **Harness 是可插拔黑盒**：接口仅 `Start(ctx, conversationID, harnessConfig) (Execution, error)`，Execution 仅 `Run/Queue/ID/Close`——与具体 Agent 实现语言/框架完全解耦，只需实现 `HarnessService`（README 原文表述为可插拔扩展接口；⚠️"双向流 gRPC"这一具体传输协议细节推断自 proto 目录命名与常见 gRPC streaming 模式，**未逐行读取 .proto 源文件确认**，如需向客户做实现级别的精确陈述，需先核实 proto/ax.proto 原文）。
4. **K8s 原生"为什么不够用"的官方论据**：README History 明确指出 K8s 为无状态微服务/可预测批处理设计，不适合挂起/恢复有状态沙箱化的 Agent——这段话本身是很好的客户教育话术，用于解释"为什么需要 Agent 专用运行时而非直接上原生 K8s"。

## 三方对比表

| 维度 | google/ax | MAF Workflow | Azure AI Foundry Agent Service |
|---|---|---|---|
| 定位 | 分布式执行运行时（不含 Agent 逻辑） | Agent 编排框架（图/工作流 DSL） | 全托管 Agent 平台服务 |
| 编排模型 | 单写者 Controller + Event Log 恢复；Harness 黑盒 | Workflow Graph(Executor+Edge)，支持 Fan-out/Fan-in | 托管 Thread+Run 模型 |
| 状态恢复 | 显式 Event Sourcing，可指定 last_step 断点续传 | Checkpoint/Resume（耦合在 SDK 内） | 平台托管 Threads 持久化，客户不可见底层机制 |
| 部署形态 | 自托管，需自建 K8s+Substrate | 库/SDK，嵌入客户应用进程 | Azure 托管，无需自建基建 |
| 与 LLM/工具耦合度 | 完全解耦（Harness 可任意语言） | 与 .NET/Python SDK 强耦合 | 与 Azure AI 模型/工具生态强耦合 |
| 成熟度 | 早期（暂停外部 PR） | 相对成熟 | GA 商用 |

**关键结论**：层次不同，非竞品关系，理论上可互补（把 MAF 写的 Agent 包装成 Harness 跑在 ax+Substrate 之上）。

## 对 SA 三大日常的具体落点
- **技术问答**：客户问"微软生态外有没有 K8s 原生的 Agent 运行时"→ 直接引用 ax+Substrate 组合与其官方论据。
- **架构图**：三层拓扑图可直接作模板，替换为 Azure 对应组件。
- **POC 部署**：不建议直接部署 ax 本身（early dev/暂停 PR），但"单写者+事件溯源+可插拔执行体"设计范式可用于自建方案的架构说明。

## 未核实/待跟进
- Agent Substrate（agent-substrate/substrate）源码未深挖，仅确认 URL 可达。
- Python sidecar（harness_server.py）协议细节未逐行读取。
- 覆盖了 README+8 个关键源文件，未覆盖全部约 50 个源文件（如 eventlog 三种后端完整实现）。
