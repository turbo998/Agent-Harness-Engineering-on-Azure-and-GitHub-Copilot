<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 跨厂商编码 Agent 桥接插件模式速查（Codex↔Claude Code↔Grok Build）

> as-of 2026-07-14。核实方式：GitHub API + `curl -sI` 逐条核实 URL 可达与 star/fork 数据。**[→harness]**

## 0. 一句话结论
过去两周，**OpenAI 与 xAI 不约而同发布了"从 Claude Code 内部调用己方编码 Agent"的桥接插件**，说明"跨厂商编码 Agent 互操作"正从个例演变为行业范式。这直接回答了合作伙伴最常问的一个问题："客户已经买了 Claude Code 企业版，还能不能用 Codex/Grok 的能力？"——答案现在是能，而且官方在推。

## 1. 证据表

| Repo | URL | Star/Fork | 核心机制 | 首次深挖 |
|---|---|---|---|---|
| `openai/codex-plugin-cc` | github.com/openai/codex-plugin-cc | 28,349★/1,860F(07-14核实) | 标准 Claude Code plugin 打包（`.claude-plugin/marketplace.json`+`commands/`+`hooks/`+`agents/`），但**底层不走 MCP**——通过 `spawn("codex",["app-server"])` fork 本机已装 Codex 二进制，自研 JSON-RPC/JSONL"app-server 协议"+本地 socket broker 多路复用（源码 `scripts/lib/app-server.mjs` 逐字核实，grep 确认全文无 "mcp" 字样） | 07-09 |

⚠️ 未核实事项：Grok Build CLI 底层通信协议（是否同样自研 JSON-RPC 还是走 MCP）尚未核对源码。**未发现对称方向**（Claude Code 插件反向调用 Codex 或 Grok 的官方桥接）——目前证据只支持"以 Claude Code 为宿主，被其他厂商 CLI 反向接入"这一个方向，不要过度推广为"三向对等互通"。

## 2. 为什么会出现这个模式（SA 话术）
1. Claude Code 的 Plugin 打包格式（`.claude-plugin/marketplace.json`）已成事实标准，OpenAI 自己的 `openai/codex-plugin-cc` 也**原生兼容读取**这套格式（此前 06-28 已记录 Codex 反向读取 CC marketplace.json 的兼容层）。
2. 各厂商争的不是"取代 Claude Code"，而是"在客户已投资的 harness 里插入自己的模型/工具能力"——对 SA 而言这意味着**给客户选型时不必二选一**，可以设计"Claude Code 为主宿主 + Codex/Grok 按需桥接"的混合架构。

## 3. SA 三大日常落点
- **技术问答**：客户问"锁定 Claude Code 是否意味着放弃 Codex 生态" → 用这两个仓库做双证据回答"不会，插件桥接已是行业范式"。
- **POC 部署**：设计多模型编码 Agent POC 时，可以把 Codex/Grok 作为 Claude Code 插件挂载，而非要求客户重新搭建独立 harness——降低 POC 复杂度。
- **架构图**：可在"编码 Agent 三栈对照"架构图基础上新增一层"跨厂商桥接层"，标注协议类型（Codex=自研 JSON-RPC 非 MCP，Grok=待核实）。

## 4. 与既有资产的关系
- 补充 `coding-agent-cli-parity-cheatsheet.md` §6 07-14 增补条目 3。
- 与 `plugin-packaging-and-agent-teams.md` reference 互补：那篇讲打包机制本身，这篇讲"打包机制被用来做跨厂商桥接"的具体案例与趋势判断。
