<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Codex / Claude Code 本周进展速查（截至 2026-07-26）

> 配套 `coding-agent-cli-parity-cheatsheet.md`（四栈对比）、`coding-agent-hooks-tristack-comparison-cheatsheet.md`（hooks三态）。本文只记录本周(07-19~07-26) delta，不重复历史内容。全部 URL 已 curl -sI 核实 200。[→harness]

## 一、Claude Code

### 1. v2.1.219 / v2.1.220（07-24/07-25）—— 新版本号 ⚠️独立评审核实
- Claude Opus 5 成为默认 Opus 模型（1M 上下文）
- **`sandbox.network.strictAllowlist`**：拒绝非白名单主机，**无需弹窗提示**（比原有 allowlist 更硬的网络出口边界配置）
- **`DirectoryAdded` hook**：`/add-dir` 或 SDK `register_repo_root` 注册新工作目录时触发 —— 可直接固化为"工作区变更审计"技能
- headless stream-json 新增 `mcp_server_errors` 事件
- `workflowSizeGuideline`：控制 Dynamic workflow 建议规模（默认 <15 个子代理，官方推荐基线）
- stream-json 支持深层(depth-2+)嵌套子代理转发

**SA 落点**：`strictAllowlist` + `DirectoryAdded` hook 组合可写成"零信任目录变更审计"技能，直接反哺 harness workshop 安全章节。`workflowSizeGuideline` 的 <15 子代理基线值得写入多代理编排最佳实践。

### 2. Week 29 数字周报（2026-w29，07-13~07-17，v2.1.207–v2.1.212）
- Artifacts 现可调用 MCP 连接器（发布的 Artifact 打开时能拉取实时数据、触发操作）
- **`/fork`**：将当前对话复制到新的后台会话，同时保留主会话继续工作 —— 等价于"会话分叉/并行探索"原语
- screen reader 模式（终端界面→纯文本线性输出，适配 VoiceOver/NVDA）
- auto mode 在 Amazon Bedrock/Google Cloud/**Microsoft Foundry** 上无需 opt-in 变量即可使用

**SA 落点**：`/fork` 可映射到"多路径试探(best-of-N)"或"安全回滚探索"技能设计。auto mode 原生支持 Foundry 是"Claude Code 接入 Azure 生态"技术问答的直接素材。

### 3. Anthropic 工程博客《How we contain Claude across products》（05-25，仍是首页置顶）
- 三类 agentic 产品隔离架构对比：无状态容器(gVisor, claude.ai)/人在环沙箱(Seatbelt+bubblewrap, Claude Code)/封闭VM(Cowork)
- 3 类真实安全事故：信任对话框前执行的 hook 被滥用；员工被钓鱼直接注入恶意 prompt 导致 AWS 凭证外泄；白名单域名"能力授权非目的地过滤"导致越权外泄
- 设计原则："环境层优先于模型层做遏制"

**SA 落点**：唯一系统阐述三种容器化隔离模式对比矩阵的一手来源，"允许清单=能力授权非目的地过滤"教训直接反哺 workshop MCP/网络出口白名单设计章节。

### 4. 《Quantifying infrastructure noise in agentic coding evals》（02-05，仍在列表靠前）
- 基础设施资源配置(容器CPU/内存)可使 Terminal-Bench 2.0 等基准分数波动最高6个百分点
- 建议评测应分别指定"保证分配量"与"硬性上限"两个参数

**SA 落点**：自建 coding agent 评测环境时应引用"3倍资源上限、保证分配≠硬上限"量化建议，避免基础设施噪声误导评测结果。

## 二、OpenAI Codex

### 5. Codex CLI 0.145.0（07-21，最新稳定版）⚠️比已知基线0.144.5更新
- 实验性分页线程历史（高效resume/搜索/持久化命名/子代理支持/记忆能力）
- **`/import` 扩展**：支持从 Cursor 和 Claude Code 迁移设置、MCP服务器、插件、会话、命令、项目级记忆
- Amazon Bedrock 实验性登录/自定义endpoint支持，GPT-5.6 Sol成为Bedrock默认模型
- **多代理V2体验(sub-agent)正式稳定**：可配置子代理模型/推理级别/并发数/角色恢复
- 音频输入/工具输出及流式实时V3对话

**SA 落点**：多代理V2稳定化 + `/import`扩展迁移Claude Code配置是本周最重磅进展——前者可与Claude Code的subagent/后台代理生态对标写入"跨厂商多代理编排对比表"；后者是OpenAI"一键从竞品迁移"生态抢夺的案例。

### 6. Codex changelog 域名迁移
- 官方 changelog 已从 `developers.openai.com/codex/changelog` 308迁移至 `learn.chatgpt.com/docs/changelog`
- **维护提醒**：后续监控脚本/RSS订阅需更新抓取目标URL

### 7. OpenAI Cookbook 近期commit（Agent记忆相关notebook重构，非Codex专属新增）
- "将Oracle agent memory cookbook迁移到vector databases分类"(07-21)
- "取消归档Agents SDK memory cookbooks"(07-20)
- 本周重点是Agent长期记忆(memory)示例整理，非Codex CLI本身新notebook；与Codex 0.145.0"记忆能力"呼应

## 三、本周综合结论

1. **趋势收敛**：Claude Code `/fork` 与 Codex 0.145.0"分页线程历史+子代理"共同指向"多路径/多代理并行探索"——建议 workshop 新增对比章节。
2. **安全反哺重点**：《How we contain Claude across products》三层隔离架构对比表应作为 workshop 安全设计核心引用素材。
3. **评测方法论**：《Quantifying infrastructure noise》的资源配置量化建议应写入自建评测环境checklist。
4. **本周无颠覆性变化**：现有 hooks 三态对比、四段prompt框架基线仍然有效，本周是渐进式功能加固（auto mode扩展云、多代理稳定化、迁移工具）与安全加固，非范式级新发现。
5. **未能验证项**：`npmjs.com/package/@anthropic-ai/claude-code` 返回403无法直接核实包版本，已通过 code.claude.com/docs/en/changelog 交叉确认版本号。
