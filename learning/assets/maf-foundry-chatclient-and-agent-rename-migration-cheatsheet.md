<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# MAF `Agent→AIAgent` 重命名 + Python `FoundryChatClient` 官方落地 —— POC 迁移速查

> 来源核实（07-19研究）：
> - https://github.com/microsoft/agent-framework/commit/fc999e2be8a8da37d973f18eff5e61a86c25ae73 （#201，Agent→AIAgent 重命名，07-18）
> - https://github.com/microsoft/agent-framework/commit/ccd7a44ec7a2218b4f9f1489467730f1284ee058 （#193，Python FoundryChatClient，26文件/+2050行）
> - https://github.com/microsoft/agent-framework/commit/dd32a6d3998ab08ee8c04c686aab0ef201dd766e （#191，.NET Foundry Client 扩展方法）
> - https://github.com/microsoft-foundry/foundry-samples/commit/9f5b2fc6f69459f6817ed82cac911020ff3dc544 （#717，样例仓库同步改名，07-16）
> - https://github.com/microsoft/agent-framework/commit/6e57489a441374ffb89bb8d32a34b562383d2bc7 （#182，.NET OpenTelemetry 支持+样例）
> ⚠️ 均未打正式版本tag（main分支commit），落地前需确认已发布的release是否包含这些变更。

## 1. 为什么这条值得单独固化

本周（07-16~07-18）微软 Agent 生态出现了**两条同时发生、互相印证**的信号：
1. **命名规范化**：`agent-framework` 核心类型 `Agent` → `AIAgent`（+`DisplayName`属性），`foundry-samples` 样例仓库同期做"renaming agents"同步。这不是孤立事件，是**全生态统一命名**的过渡期动作。
2. **Foundry 官方客户端首次落地**：Python 侧独立包 `agent-framework-foundry` 实现 `FoundryChatClient`/`FoundrySettings`，是 AF 对接 Azure AI Foundry 托管 Agent 的**第一个官方原生客户端**（此前客户/伙伴需要自建 Foundry 连接封装代码）。

对 SA 而言，这两条直接影响**技术问答**（"AF 和 Foundry 到底什么关系"）与**架构图**（集成层画法）。

## 2. 技术问答话术

**Q: Agent Framework 和 Azure AI Foundry 是什么关系？**
> A: 07月中旬起，Agent Framework 提供了官方的 `FoundryChatClient`（Python，独立包 `agent-framework-foundry`）与对应 .NET 扩展方法，可以直接从已有 Foundry Project/Client 拿到一个 AF `AIAgent`。这是**官方一手集成路径**，不再需要自己写 Foundry SDK 到 AF 的桥接代码。

**Q: 我们已经有基于早期预览版 AF 写的 POC 代码，会受影响吗？**
> A: 会有一处破坏性变更——核心类型从 `Agent` 改名为 `AIAgent`。如果代码里直接 import/引用了 `Agent` 类型（非工厂函数返回值的隐式用法），升级后编译会报错，需要批量替换。这是**范式命名统一**的一部分，非功能倒退。

## 3. 架构图落点

```
[Client App]
    │
    ▼
[Agent Framework AIAgent]  ← 07-18改名(原 Agent)
    │  FoundryChatClient (Python) / Foundry扩展方法(.NET)  ← 07-16新增官方原生桥接
    ▼
[Azure AI Foundry Project]
    │
    ├─ Model Deployment
    ├─ Toolbox (MCP)
    └─ OpenTelemetry 导出 (.NET 新增原生支持样例 #182)
```

## 4. POC 迁移清单（给已有 AF+Foundry 客户）

- [ ] grep 代码库中 `Agent` 类型直接引用（区分变量名 vs 类型名，避免误报）
- [ ] Python：改用 `agent-framework-foundry` 包的 `FoundryChatClient`，替换自建 Foundry 封装
- [ ] .NET：改用官方 Foundry Client 扩展方法，删除样板桥接代码
- [ ] 若使用 OpenTelemetry：参考新样例（#182）对齐官方推荐的 span/trace 命名
- [ ] ⚠️ 确认目标使用的是已发布 release 而非仅 main 分支 commit（截至07-19，这些变更尚**未见对应tag**，需在升级前二次确认release notes）

## 5. 未核实/风险标注

- 这些 commit 均为 main 分支提交，**未核实**对应哪个即将发布的 tag（python-1.x 或 dotnet-1.x）；生产环境采纳前必须等正式 release。
- `DisplayName` 属性的具体用途（UI展示 vs 日志标识）未展开阅读源码，仅从 commit 标题推断。
- "全生态统一命名"是基于两个仓库同期动作的**判断性推论**，非官方声明，标注为推测非确定性事实。
