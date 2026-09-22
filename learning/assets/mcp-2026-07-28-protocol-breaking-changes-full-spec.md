<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# MCP 2026-07-28 正式规范 —— 完整 Breaking Change 逐字清单

> 来源：https://modelcontextprotocol.io/specification/2026-07-28/changelog （已完整抓取全文核实，非摘要推断）
> 相对上一版本：2025-11-25
> 原文核对快照日期：2026-08-01；本次未重新核验协议文档或执行兼容性测试。
> 结论（fail-loud）：这是 MCP 自诞生以来**规模最大的一次 breaking release**——去 session 化、去握手化、新增强制 discover RPC、订阅机制推倒重来、Tasks 移出核心协议、新增 MRTR 交互范式。**不是渐进式更新，任何现存 MCP client/server 若不适配将直接不兼容。**

## 11 项核心 Breaking 变更（逐字提炼）

1. **移除协议级 session 与 `Mcp-Session-Id` 头**（Streamable HTTP transport）—— `tools/list` 等列表接口不再随连接变化；服务器需自行铸造 handle 作为普通工具参数传递跨调用状态。(SEP-2567)

2. **MCP 变为无状态**：移除 `initialize` / `notifications/initialized` 握手流程。每个请求携带 `_meta` 里的 `io.modelcontextprotocol/protocolVersion` 和 `clientCapabilities`；版本不匹配返回 `UnsupportedProtocolVersionError`。(SEP-2575)

3. **新增强制 RPC `server/discover`**：服务器 **必须(MUST)** 实现此 RPC 以声明支持的协议版本/能力/身份，客户端可在任何其他请求前调用它做版本协商。(SEP-2575)

4. **移除 HTTP GET 端点及 `resources/subscribe`/`unsubscribe`**，替换为单一长连接 `subscriptions/listen` 流，客户端需显式 opt-in 订阅类型（`toolsListChanged` 等）。(SEP-2575)

5. **移除 `ping`、`logging/setLevel`、`notifications/roots/list_changed`**；日志级别改为逐请求通过 `_meta.io.modelcontextprotocol/logLevel` 设置。(SEP-2575)

6. **实验性 Tasks 移出核心协议**，独立为官方扩展 `io.modelcontextprotocol/tasks`；`tasks/result` 阻塞方法替换为轮询 `tasks/get` + 新增 `tasks/update`。(SEP-2663)

7. **新增 MRTR (Multi Round-Trip Requests) 模式** 替代原有 server-initiated 请求（`roots/list`/`sampling/createMessage`/`elicitation/create`）：服务器返回 `InputRequiredResult`（`resultType:"input_required"`），客户端携带 `inputResponses` 重试原请求。**所有结果新增必填 `resultType` 字段**（"complete" 或 "input_required"）。(SEP-2322)

8. **移除 SSE 流可恢复性**（`Last-Event-ID` 头及 SSE 事件 ID）—— 中断的响应流会丢失请求，客户端须以新请求 ID 重新发起。(SEP-2575)

9. **错误码变更**：resource not found 从 `-32002` 改为 `-32602`（对齐 JSON-RPC 规范）；新错误码分配策略划定 `-32020~-32099` 为 MCP 规范保留区，重编号 `HeaderMismatch`(-32001→-32020) 等。

10. **弃用（Deprecated，非移除）**：Roots、Sampling、Logging 三大特性整体弃用（迁移建议：用工具参数/资源 URI 替代 Roots，直连 LLM provider API 替代 Sampling，用 stderr/OpenTelemetry 替代 Logging）；HTTP+SSE transport 重新分类为 Deprecated；OAuth Dynamic Client Registration 弃用，转向 Client ID Metadata Documents。

11. **Schema 松绑**：`inputSchema`/`outputSchema` 允许任意 JSON Schema 2020-12 关键字；新增 `CacheableResult` 接口（`ttlMs` + `cacheScope`）用于 `tools/list` 等结果缓存。

## 与原研究快照中同步核实的微软/Anthropic 应对现状

- **microsoft/mcp (Azure.Mcp.Server) beta.30**：升级 ModelContextProtocol 包到 `2.0.0-preview.3`，移除 Core 工具未用参数与遗留 tool design 创建（breaking），已承接本次协议迁移。beta.31 为纯内部重构无新协议修复。
- **microsoft-foundry/foundry-samples #808**："Fix hosted agents after MCP 2.0 release" —— 直接印证 MCP 2.0 对现有托管 agent 样例造成了破坏，需要修复才能继续用。
- **microsoft/semantic-kernel #14236**：MCP 工具/提示名称归一化冲突跳过修复（bug fix 级，非架构级迁移）。
- **claude.com/blog《Bringing MCP 2026-07-28 to Claude》**（2026-07-28）：Anthropic 官方博客正面回应此次协议变更，表述为"有状态双向协议→无状态请求/响应核心"，与协议原文一致，无夸大。

## 对 SA 的落地价值

- **技术问答**：客户问"为什么我的 MCP client 突然连不上了/工具列表变化了"时，可直接引用上面 11 项定位具体断点原因（最常见：GET 端点被移除、session 头消失、resources/subscribe 被替换）。
- **POC 部署清单**：任何新 POC 若涉及 MCP，部署前必须先确认 client SDK 与 server 均已适配 2026-07-28 规范（尤其 `server/discover` 强制实现要求），否则版本不匹配会直接报 `UnsupportedProtocolVersionError`。
- **架构图**：MCP 数据流图需要更新——去掉"握手/session建立"阶段箭头，改为每请求携带协议版本 meta；订阅关系图需要把"HTTP GET 长轮询"改画成"`subscriptions/listen` 单一长连接"。

## 未核实/待续
- 尚未逐一验证社区 MCP SDK（Python/TS/C#）各自的迁移完成度和时间线，仅确认微软 Azure MCP Server 侧的应对。
- MRTR 模式的具体客户端实现示例代码尚未找到官方样例，需使用前补充。
