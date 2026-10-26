# Agent 调用级归因、沙箱凭据字节替换与闭卷评测网关验收实验室（2026-10-27）

**2026-10-27 范围与执行声明：本包中的 Python 3.11+ 标准库参考契约（`harness_contracts.py`）与 24 项单测 / 6 项单点变异校准套件（`test_harness_contracts.py`）已在本地无网络正常模式（`python3 -B`）与优化模式（`python3 -B -O`）下实际执行，24/24 基线测试 PASS、6/6 定向单点 mutation KILLED；各上游产品宿主运行时（Microsoft Agent Framework Python/.NET、Azure AI AgentServer、GitHub Copilot SDK AHP Host、Google ADK `/run_live` 服务端、MCP Go SDK、NVIDIA NeMo Helix、OpenAI Codex MITM Proxy & CLI、Anthropic Claude Code CLI）均为 `NOT_RUN`（仅基于 2026-10-27 固定 SHA 源码补丁静态审阅与本地标准库契约建模）。**

本入口汇集三支柱 6 组核心控制面/数据面机制的无模型离线参考契约、12 张 POC 验收卡、架构边界图与选型问答：
1. **微软 Agent Framework (`microsoft/agent-framework`)**：`agent-hooks-declaration/1.0` 零反射加载器与 `terminate` 姿态门禁（`18adf808`）、FIDES `quarantined_llm` 作用域客户端隔离防全局槽位串台（`7db56c05`）及 .NET `FoundryToolboxService` 工具审批策略 Fail-Closed 映射（`264439f7`）。
2. **微软 Azure AI AgentServer & GitHub Copilot SDK**：AgentServer `x-ms-original-subject` RFC 9651 结构化字典解析与状态键/平台工具/模型归因三通道隔离（`a7dd9f37`），以及 Copilot SDK `AhpHostAuthentication`（`github`/`none`/`custom`）准入控制、推理凭据隔离与 `setAllowCreatingNewSessions` 排水开关（`f2b720c8`）。
3. **Google ADK Python & MCP 官方 Go SDK**：ADK `/run_live` 双向流 `FIRST_COMPLETED` 防挂死、WebSocket `1007` 关闭码与仅记录错误 `type` 的 PII 零泄漏日志（`3b227d6e`）；MCP Go SDK 企业授权 RFC 9207 `iss` 防混淆校验与 RFC 8693 `issued_token_type == id-jag` 强制门禁（`fa799c5f` / `6f47cb79`）。
4. **NVIDIA NeMo Helix (`NVIDIA-NeMo/nemo-helix`)**：Harbor `no-network` 离线评测任务集防“模型托管联网工具”旁路门禁，强制校验 `VirtualModel` 读取权限及 `request_middleware[-1] == "nemo-evals-closed-book"` 末尾位置铁律（`8c3ef7f5`）。
5. **OpenAI Codex & OpenAI Cookbook**：`codex-network-proxy` MITM v2 请求体不透明占位符（16~256 字节 ASCII）单遍字节替换与后置 AWS SigV4 重签名（拒绝压缩/Trailers/客户端摘要头，`61953122`）、`RolloutBudget` 软硬双模控制（`enforce_limit` vs Advisory 零余额提醒，`77eb019a`）及 Databricks 沙箱 `codex exec-server` 最小权限环境密钥隔离（`8495326b`）。
6. **Anthropic Claude Code (`v2.1.305`–`v2.1.310`) & 嵌套 CLI 防护**：`mods/sec-default` 组织级 `prepend` 层 `next.to(e, "user")` Reopen 边界与 65,536 字符正则上限（`318b7e6a`）、`claude_code.safety_event` OTel 安全审计事件（`b70dc411`）及 `/tmp` 下派生嵌套 `claude -p` 强制注入 `--restricted --tools ""` 防提权与 `apiKeyHelper` RCE（对照 `yonatangross/orchestkit@b850f51a`）。

## 配套文件导航

- [完整实验说明、12 张 POC 验收卡与架构图](agent-attribution-secret-substitution-and-closed-book-lab-2026-10-27/README.md) (`522ef39077e9f98761da945758ad96a909dd04490e26c6e49c7357fd7d867d36`)
- [标准库参考契约实现 `harness_contracts.py`](agent-attribution-secret-substitution-and-closed-book-lab-2026-10-27/harness_contracts.py) (`2629addcb05b3006b93f547767a8b8c85c48051d749b03d806460274c907fe7a`)
- [24 项单测与 6 项变异校准套件 `test_harness_contracts.py`](agent-attribution-secret-substitution-and-closed-book-lab-2026-10-27/test_harness_contracts.py) (`c7a188a58bbbd746bfddfc49c19b841e4f67e021d1c7680b1065c6c8701b9d04`)
- [14 项固定源码补丁溯源清单 `fixtures/provenance.json`](agent-attribution-secret-substitution-and-closed-book-lab-2026-10-27/fixtures/provenance.json) (`01ef8960e9edfcac6c0ecdaa2d7be914a0ddfcf101be28730a7bf9e51f591094`)
- [离线执行摘要 `run-summary.json`](agent-attribution-secret-substitution-and-closed-book-lab-2026-10-27/run-summary.json) (`7f0efa47c9d4f1e134e307fb33c112baa2b03652e55dc77fb21e78de01d17261`)
- [字节 SHA256 清单 `SHA256SUMS`](agent-attribution-secret-substitution-and-closed-book-lab-2026-10-27/SHA256SUMS) (`914838e1b8aa642e4ec1fc040382b47007d61774a6761daf34c7ee32df38cdf3`)

叶文件 SHA-256 详见子目录 `README.md` 与 `SHA256SUMS`（`SHA256SUMS` 覆盖子目录内 5 个文件，不包含清单自身；本顶层入口文件由 `learning/catalog.json` 索引绑定 SHA-256）。
