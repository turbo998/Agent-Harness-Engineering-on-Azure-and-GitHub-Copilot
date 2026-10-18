# Agent 授权域、双重派发护栏与异步唤醒验收实验室（2026-10-19）

**2026-10-19 范围与执行声明：本包中的 Python 3.11+ 标准库参考契约（`harness_contracts.py`）与测试套件（`test_harness_contracts.py`）已在本地无网络正常模式（`python3 -B`）与优化模式（`python3 -B -O`）下实际执行，22/22 基线测试 PASS、6/6 定向单点 mutation KILLED；各上游产品运行时（MAF FastAPI/.NET 宿主、Azure MCP Server 二进制、Google ADK 运行时、OpenAI Codex CLI、Anthropic Claude Code CLI）均为 `NOT_RUN`（仅固定 SHA 源码/diff 静态审阅）。**

本入口汇集三支柱 6 组核心控制面机制的无模型离线参考契约、12 张 POC 验收卡、架构边界图与选型问答：
1. **微软 MAF Python AG-UI**：显式授权域三选一配置强校验与客户端 Shared State 审批状态形状级防篡改（`9a1d66b3` / `abeed6c6`）。
2. **微软 Azure MCP Server 3.0.0 GA**：废除进程级可变全局设置，引入 `CommandContextAccessor`、`ArmUriValidationPipelinePolicy` 与双轨代理/SSRF 传输分流（`da75e4d3`）。
3. **微软 MAF .NET（ADR 0045）**：未答复工具审批在下一轮自动拒绝、深拷贝隔离 `InformationalOnly` 与多 Agent 工作流完成后转发（`95feea60`）。
4. **Google ADK Python**：动态子节点重试回滚至当前 Attempt 起点快照（防重放已拒绝缓存）与循环 `JoinNode` 到达集合消费屏障（`e2dbc0f5` / `a6ed8590`）。
5. **OpenAI Codex & Cookbook**：异步子 Agent 邮件唤醒空闲 Root 会话三道边界（`8c076942`）与 MCP `initialize.instructions` 跨 Harness 轨迹差集判分（`5bd6cb40`）。
6. **Anthropic Claude Code**：组织级内置安全模块 `mods/sec-default` 双重派发防篡改、19 个高危环境变量 Pin 死与策略读取失败 fail-closed（`dd6bee38`）。

## 配套文件导航

- [完整实验说明、12 张 POC 验收卡与架构图](agent-harness-scope-verdict-wakeup-lab-2026-10-19/README.md)
- [标准库参考契约实现 `harness_contracts.py`](agent-harness-scope-verdict-wakeup-lab-2026-10-19/harness_contracts.py)
- [22 项单测与 6 项变异校准 `test_harness_contracts.py`](agent-harness-scope-verdict-wakeup-lab-2026-10-19/test_harness_contracts.py)
- [固定源码溯源清单 `fixtures/provenance.json`](agent-harness-scope-verdict-wakeup-lab-2026-10-19/fixtures/provenance.json)
- [离线执行摘要 `run-summary.json`](agent-harness-scope-verdict-wakeup-lab-2026-10-19/run-summary.json)
- [字节 SHA256 清单 `SHA256SUMS`](agent-harness-scope-verdict-wakeup-lab-2026-10-19/SHA256SUMS)

叶文件 SHA-256 详见子目录 `README.md` 与 `SHA256SUMS`（`SHA256SUMS` 覆盖子目录内 5 个文件，不包含清单自身；本顶层入口文件由 `learning/catalog.json` 索引绑定 SHA-256）。
