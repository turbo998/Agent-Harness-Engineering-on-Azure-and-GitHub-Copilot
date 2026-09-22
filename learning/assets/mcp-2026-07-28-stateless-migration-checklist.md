<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# MCP 2026-07-28 无状态化规范 — POC 启动前置兼容性检查清单

> 产出日期：2026-07-30 | 来源已核实：claude.com/blog/bringing-mcp-2026-07-28-to-claude (curl 200)、
> microsoft/semantic-kernel PR#14236、microsoft-foundry/foundry-samples PR#808、
> openai/codex release rust-v0.146.0 body (`#34747 Register the MCP 2026-07-28 feature flag`)
> ⚠️ 未核实项：MCP 2026-07-28 正式规范文档全文尚未逐字比对，本清单基于三方（Anthropic/微软/OpenAI）对该版本的应对动作反推，
> 使用前建议先访问 modelcontextprotocol.io 官方 spec 页核对具体字段变更。

## 背景（一句话）
MCP 协议 2026-07-28 版本把"有状态双向协议"改为"无状态请求/响应核心"，**与旧协议双向不兼容**。
微软 Semantic Kernel（PR#14236）与 Foundry Samples 托管 Agent 样例（PR#808）均在此次变更后出现异常，
应急方案是把 MCP SDK 依赖临时锁定在 1.x。Codex CLI 0.146.0 已注册该版本 feature flag，Claude Code 侧已发文说明迁移。

## 客户 POC 启动前必查 5 项

| # | 检查项 | 怎么查 | 若不符怎么办 |
|---|--------|--------|--------------|
| 1 | 客户环境里各 MCP Client（Claude Code / Codex / 自研 Agent）当前连接的 MCP SDK 版本号 | 查 `package.json`/`requirements.txt`/`*.csproj` 里 mcp-sdk 依赖版本，或运行时打印协议握手 version 字段 | 若 Client 已升级到 2026-07-28 无状态版，需确认 Server 端同步升级，否则握手失败 |
| 2 | 自建/第三方 MCP Server 是否已适配无状态规范 | 查 Server 侧依赖锁文件；若基于 microsoft/mcp（Azure MCP）需查其对应 beta 版本号是否已声明支持新规范 | 若未适配，POC 阶段建议显式锁定 Client 端 SDK 到 1.x，避免"新 Client 连旧 Server"或反向的隐蔽兼容性事故 |
| 3 | Semantic Kernel / Foundry 托管 Agent 场景 | 直接确认 SK 版本是否 ≥ 已修复版本（含 PR#14236 之后的版本），foundry-samples 相关样例是否已合入 PR#808 修复 | 未合入前，POC 演示环境的 MCP 依赖统一锁 1.x，写入 POC 环境搭建脚本注释说明原因和跟踪链接 |
| 4 | 是否依赖 MCP 的长连接/会话状态特性（如流式工具调用中途更新上下文） | 检查现有工具调用逻辑是否假设"连接保持有状态会话" | ⚠️**该检查项为基于协议变更方向的推断性补充，非claude.com博客原文逐字表述**——无状态化后此类假设可能失效，需评估是否要重构为显式状态传递（每次请求带上下文）或改用 Server 端外部存储保存会话态 |
| 5 | 迁移时间窗口内是否存在"客户端已升级、服务端未升级"或反向的混用场景 | 询问客户是否所有 Agent 工具链统一由同一团队/同一发布节奏管理 | 若多团队各自管理不同组件，建议在 POC 里显式做协议版本协商/降级兼容层，而非假设步调一致 |

## SA 话术模板（可直接转发客户）
> "MCP 协议本周（2026-07-28）刚发布一个从有状态到无状态核心的新版本，且与旧版本不向下兼容。
> 我们建议在启动 POC 前先确认贵司现有 MCP Client/Server 组件的版本号是否一致适配，
> 微软自己的 Semantic Kernel 和 Foundry 托管 Agent 样例这周也因为这次升级出过问题、临时锁版本规避，
> 这提醒我们这类基础设施级协议升级需要有明确的迁移计划，而不是被动等报错。"

## 与既有 skill 的关系
本清单为 `coding-agent-harness-interop-and-longrun-pattern` skill 的 Δ2026-07-30 增补第14条的落地版执行清单，
详细技术背景见该 skill 文件。**[→harness]**：建议在 harness workshop repo 中新增"MCP 协议版本治理"一节，
引用本清单作为 POC 前置检查表模板。
