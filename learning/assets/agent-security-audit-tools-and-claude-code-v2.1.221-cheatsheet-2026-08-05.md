<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent 安全审计工具三方对比 + Claude Code v2.1.221 沙箱凭证隔离 cheatsheet
> 生成日期：资料日期：2026-08-05

## 一、Agent 安全审计/代码扫描赛道三方对比（本周新发现的竞争格局）

| 厂商 | 项目 | Star/Fork（curl核实@08-05） | 核心机制 | 差异化定位 |
|---|---|---|---|---|
| OpenAI | openai/codex-security | 8513★/587f | 官方安全扫描 Agent CLI/SDK，活跃度骤增 | 编码 Agent 自身的"代码安全审计"能力，绑定 Codex CLI 生态 |
| Google | google/mantis | 711★/82f | 面向 AI 编码 agent 的安全审查技能工具包，可自主发现/复现/修复漏洞 | 更强调"自主修复"闭环，工具包形态可跨 agent 移植 |
| Meta | facebook/mcpguard-dynamic | 68★/9f | eBPF 内核级沙箱，保护 MCP 协议下 LLM agent 工具调用安全 | 唯一从"操作系统内核层"做拦截，而非应用层/prompt层治理 |

**SA 落点**：三家巨头在"agent 代码安全审计/工具调用防护"这一细分赛道已经形成三层次布局——应用层扫描（OpenAI）、agent 自主修复（Google）、内核级沙箱（Meta）。客户做安全类 agent 方案选型时，可按"我要的是扫描报告 vs 自动修复 vs 运行时强制隔离"这一问题帮客户定位该选哪一类，而非笼统推荐"用某个安全工具"。**⚠️三者具体实现细节均未逐行读源码，仅完成可达性+README机制核实，如需给客户演示级细节，需要后续验证时分别深挖。**

## 二、Claude Code v2.1.221 沙箱凭证隔离机制（2026-08-04发布）

来源：https://github.com/anthropics/claude-code/releases/tag/v2.1.221（curl核实200）

- **`sandbox` 凭证文件 `mode:"mask"`**：沙箱进程内读到的凭证值是 sentinel 替身，真实值只在 egress 网络出口处被代理换回。当前仅 Linux/WSL 支持，macOS 降级为 deny（即 macOS 上该功能不可用，会拒绝而非静默降级成明文）。
- **后台/无人值守会话新增自动行为**：自动 commit + push，按需开 draft PR，遵循 CLAUDE.md 里的 git 相关指令；`/status` 新增会话类型标注（interactive/attached/unattended）。
- **`claude-api` 技能新增 `prompt-audit` 子命令**：扫描过时/不适配新模型写法的 prompt 与 tool 描述。

### 客户话术：凭证隔离与 Azure 治理的映射
| Claude Code 机制 | Azure 等价设计 | 共同点 |
|---|---|---|
| 沙箱内 sentinel 替身值 + egress 出口替换 | Managed Identity 短时 token，不落地到应用代码 | 敏感值不常驻可被 agent/进程读取的内存空间 |
| Linux/WSL 支持，macOS 降级为 deny | 明确列出平台能力边界，缺失能力时拒绝而非静默降级 | 安全默认值：宁可拒绝服务，不可静默明文暴露 |

### 无人值守 harness 补充建议（反哺 workshop）
后台 agent 现在会**自动 commit+push+开 draft PR**，这意味着如果 POC/生产环境里给了无人值守 agent 写权限但没配分支保护规则，agent 的自动 push 可能绕开人工 review 直接进入受保护分支的准入队列。
**建议动作**：任何无人值守 Claude Code harness 部署前，先确认目标仓库分支保护规则（要求 PR review、禁止直接 push 到 main/release 分支），把"人工 review gate"作为无人值守 harness 的强制前置条件，而非事后补救。**[→harness]**

## 三、来源与核实方式
- openai/codex-security, google/mantis, facebook/mcpguard-dynamic：GitHub API 直接查询 star/fork/pushed_at，均 200。
- Claude Code v2.1.221 release：GitHub Releases API 核实 200，body 逐条阅读非摘要转述。

## 四、未核实/待办
- 三个安全审计项目的具体扫描规则/policy 设计均未读源码。
- `mode:"mask"` 是否有对应的 Azure Key Vault CSI driver 级 POC 演示尚未构建，值得下一步做成实机对比。
