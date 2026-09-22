<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Anthropic 插件生态三件套 + xAI Grok Build 速查（数据复核于2026-07-31）

> ⚠️ **订正（07-31）**：本页仅整理公开仓库样本与当时可见的生态信号，不把历史记录次数或“首次发现”作为公开结论。

> 目的：给 SA 一份可直接引用的"厂商级 agent 插件/CLI 生态"速查表，覆盖 Anthropic 插件市场三层结构与 xAI 全新编码 agent CLI，方便技术问答与三栈/四栈横向对比。所有数据 curl/API 核实，标注核实时间。

## 一、Anthropic 插件生态三件套（公开仓库样本，2026-07-31 数字核实）

| 仓库 | Star/Fork（核实于07-31） | 定位 |
|---|---|---|
| `anthropics/claude-plugins-official` | 32,870 / 3,705 | **官方审核插件目录**（Claude Code 插件市场入口）。结构：`/plugins`（Anthropic自研）+ `/external_plugins`（第三方，需审核）。安装：`/plugin install {name}@claude-plugins-official` |
| `anthropics/knowledge-work-plugins` | 23,190 / 2,787 | **知识工作者角色插件**，面向 Claude Cowork（也兼容 Claude Code）。11 个开源插件：productivity/sales/customer-support/product-management/marketing/legal/finance 等，每个插件打包 skills+connectors+slash commands+sub-agents，绑定真实企业工具（Slack/Notion/HubSpot/Jira/M365等） |
| `anthropics/claude-plugins-community` | 325 / 80 | 社区插件镜像市场（体量远小于官方两个仓库，仍属早期） |

**关键机制笔记**（README 逐字核实）：
- 插件结构标准：`plugin-name/.claude-plugin/plugin.json`（元数据，必需）+ `.mcp.json`（MCP server 配置，可选）
- Anthropic **明确声明不控制/不保证**第三方插件包含的 MCP server、文件或软件的安全性和稳定性 —— 这是一条重要的客户话术：**企业采用社区插件前必须自行做安全审计**，不能假设官方市场=已审计安全。
- knowledge-work-plugins 是"角色专属能力包"范式（vs skills 是"单一能力"范式）——两者互补，可用一张图讲清楚 Claude 生态里 skill / plugin / marketplace 三层抽象关系。

**对 SA 的价值**：
1. **技术问答**：客户问"Claude Code 插件生态多大/安全吗" → 直接引用三件套体量+官方免责声明原文，避免"看起来官方就是安全的"误导性回答。
2. **POC 设计**：knowledge-work-plugins 的 11 个角色插件可作为"企业知识工作 Agent 化"POC 的现成参照（尤其 finance/legal/customer-support 三个连接器覆盖面广，可对标 Copilot Studio 的角色 agent 模板做竞品对比）。
3. **架构图**：可画一张"Claude 能力分层"图：Skill（单任务技能）→ Plugin（角色能力包，含 skills+connectors+subagents+slash commands）→ Marketplace（分发/信任层，official vs community 两级信任域）。

---

## 二、xAI Grok Build（`xai-org/grok-build`）—— 持续追踪对象，原研究快照中新增 ACP 协议关联维度深挖

> ⚠️ 订正：本节只保留 ACP(Agent Client Protocol) 嵌入编辑器这一公开能力维度，不保留内部研究次数记录。

- **Star/Fork（核实于07-31）**：23,548 / 4,477（仅作当时热度信号，不据此判断质量、采用风险或增长真实性）
- **定位**（README 逐字）：SpaceXAI（xAI 旗下）出品的终端全屏 TUI 编码 agent，理解代码库、编辑文件、执行 shell 命令、搜索网页、管理长任务；支持交互式/无头（CI 场景）/**通过 Agent Client Protocol (ACP) 嵌入编辑器**三种模式。
- 安装：`curl -fsSL https://x.ai/cli/install.sh | bash`（macOS/Linux），`irm https://x.ai/cli/install.ps1 | iex`（Windows）
- 技术细节：Rust 编写，代码从 SpaceXAI 内部 monorepo 周期性同步（`SOURCE_REV` 文件记录对应 commit SHA），依赖 DotSlash 做工具分发、protoc 做协议编译。

**对 SA 的价值**：
1. **四栈拼图**：与 Codex CLI / Claude Code / Mistral Vibe 并列构成"四大编码 agent CLI"（Codex/Claude Code/Mistral Vibe/Grok Build），补齐 xAI 一极。目前 coding-agent-hooks-tristack-comparison-cheatsheet.md 仍是"三栈+一栈草稿"，需要后续升级为真正四栈对比表。
2. **ACP 协议**：Grok Build 官方支持 ACP（Agent Client Protocol）嵌入编辑器；`mistralai/agent-client-protocol` 也是相关公开资料。可画一张“ACP（编辑器↔Agent）+ MCP（Agent↔工具/数据）”架构图，区分两类协议的连接边界；具体兼容性仍需验证。
3. **技术问答落点**：当客户问"xAI 有没有自己的编码 Agent CLI" → 可以给出明确、已核实的答案（Grok Build，Rust/TUI/ACP），而非"不确定"。

---

## 三、Copilot Code Review：Agent Skills + MCP 正式 GA（2026-07-29）

- 来源：github.blog/changelog（原研究快照中已 curl 核实该 changelog 页面 HTTP 200（仅代表原快照当时可达，不代表本次已重验） 可达）
- **要点**：GitHub Copilot 代码审查功能中的 Agent Skills 与 MCP 服务器支持，从预览转为**正式 GA**。
- **对 SA 的价值**：这是"MCP 落地在企业代码审查流水线"的官方信号，可作为客户架构图候选；但 GA 不等于所有区域、租户和集成路径均已可用，客户承诺前仍需按目标租户验证权限、区域与策略。

---

## 四、Agent Framework（微软）本周高密度更新摘要（07-30~07-31，≥30 commits，达 API 分页上限）

- `.NET`: 升级至 1.16.0；checkpointed workflows 稳定 agent ID 回归测试；AgentWithMemory 示例新增 FileMemoryProvider
- `Python`: SessionStore 移入 core（持久化 Foundry Responses 会话）；MCP initialize 握手支持 header_provider headers；反序列化安全修复（unpickler 模块白名单限制）
- **对 SA 的价值**：`header_provider headers → MCP initialize 握手` 这条对回答"如何给 MCP server 传自定义认证头/租户上下文"的技术问答非常直接；反序列化安全修复可作为"agent-framework 安全维护活跃度"的证据引用。

---

## 五、⚠️ 原研究快照中 fail-loud 未核实/待深挖清单
- Grok Build 具体沙箱/权限分级机制（docs 在官网非仓库内，需使用前访问 x.ai/cli 文档站）
- Grok Build 20k+ star 两周内的增长曲线是否存在异常（原研究快照中仅做静态核实，未查历史 star 曲线）
- ACP 协议规范原文（modelcontextprotocol 之外的独立协议）尚未逐字读取，仅从 Grok Build README 侧面印证
- MCP 2026-07-28 无状态化协议 spec 原文需按发布时最新版本重新核对，不能只凭 URL 可达性判断 breaking 字段。
