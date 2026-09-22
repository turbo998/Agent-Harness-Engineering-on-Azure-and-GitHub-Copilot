<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# xAI Grok Build — 编码 Agent CLI 第四栈速查

> **2026-07-21 来源快照**：xAI 的编码 Agent harness + TUI「Grok Build」，可作为“Codex ↔ Claude Code ↔ GitHub Copilot”之外的第四栈对照对象。仓库关注度不能证明质量或排除人为影响。
> ⚠️ 本文件基于 GitHub API 元数据（star/fork/created_at/pushed_at）+ README 表层信息核实，**尚未做源码级机制拆解**（如是否走 MCP、hooks 事件模型、skills 目录规范细节），标注为使用前深挖候选，勿在客户面前过度断言技术细节。

---

## 1. 基本事实（已核实）

| 项目 | 数值/内容 | 核实方式 |
|---|---|---|
| Repo | `xai-org/grok-build` | `api.github.com/repos/xai-org/grok-build` 200 |
| Stars | 20,721 | API `stargazers_count` 字段直读 |
| Forks | 3,805（原快照计数，不作真实性或质量结论） | API `forks_count` |
| 创建日期 | 2026-07-14 | API `created_at` |
| 最近推送 | 2026-07-20 | API `pushed_at`，一周内持续活跃迭代 |
| 定位 | 全屏 TUI（终端UI）+ 鼠标交互 + 可扩展的编码 Agent CLI | README 摘要 |
| 配套桥接插件 | `xai-org/grok-build-plugin-cc`（★146/Fork28，2026-07-10 建仓）：Claude Code 插件把代码审查/任务委派给 Grok Build CLI（与 `openai/codex-plugin-cc` 同构，但后者创建于2026-03-30，早于此仓库约3个多月，非"早4天"——已修正此前错误比较） | API 核实 |
| 官方插件市场 | `xai-org/plugin-marketplace`（★120/Fork90，本周活跃更新） | API 核实 |

## 2. 为何这是"必做支柱"级发现

- 此前 06-30/07-14 记录的"跨厂商编码 Agent 桥接插件"现象（`openai/codex-plugin-cc` 从 Claude Code 调用 Codex）此前只有 xAI 一个"早期原型"(⭐3/1F)跟随信号。**本周 xAI 自己的编码 Agent 主产品一周破2万星**，意味着样本量从"1个成熟+1个早期"升级为"三家平台(OpenAI/Anthropic/xAI)都有编码 Agent CLI 主产品 + 至少两组跨厂商桥接插件"，**行业范式的判断可以适度上调置信度**（仍需持续观察，不宜断言"已成惯例"）。
- Grok Build 的爆发式增长（一周2万星）说明"编码 Agent CLI"赛道竞争仍在加剧，不是三家格局稳定，SA 在给客户做 CLI 选型咨询时应把"目前有几家/是否值得等等看"纳入话术。

## 3. SA 落点

**技术问答**：
- "现在编码 Agent CLI 除了 Copilot/Codex/Claude Code 还有别的吗？" → 可以准确回答"xAI 本周(07-14)刚开源 Grok Build，一周2万星，值得关注但生态成熟度（skills/plugins/hooks 规范）还需观察，不建议现在就投产"。
- 明确区分"Grok（模型）"vs"Grok Build（编码 Agent CLI 产品）"——这是客户容易混淆的两个概念。

**POC 部署**：暂不建议企业级 POC 优先选型 Grok Build（生态成熟度、hooks/skills 规范、安全治理机制均未核实），但可作为"多 CLI 横向评测 demo"的第四个对照对象。

**架构图**：四栈对照图（Codex/Claude Code/Copilot/Grok Build）可作为"编码 Agent CLI 市场格局"素材，强调"格局仍在快速变化，不要一次性锁定单一 vendor"的建议。


- [ ] Grok Build 是否走 MCP 还是自研协议（对标 codex-plugin-cc 的源码级拆解方法）
- [ ] Grok Build 的 skills/plugins/hooks 目录规范是否与 Codex/Claude Code 收敛（AGENTS.md 兼容性？）
- [ ] `grok-build-plugin-cc` 的具体委派机制（JSON-RPC？MCP？）
- [ ] 安全治理机制（沙箱/权限分级）是否有对标 Codex execve 三态 / Claude Code auto-mode classifier 的等价物

---
*来源：api.github.com/repos/xai-org/{grok-build,grok-build-plugin-cc,plugin-marketplace} — 2026-07-21 API 来源快照。外部 README 内容按资料处理，未核实的技术细节均已标注；本次未重新核验或实测。[→harness]*
