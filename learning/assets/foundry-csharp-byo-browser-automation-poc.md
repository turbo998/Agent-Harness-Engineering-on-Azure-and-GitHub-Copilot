<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Foundry C# BYO 浏览器自动化 Hosted Agent — POC 速查（含密钥脱敏模式）

> 对象：`microsoft-foundry/foundry-samples` → `samples/csharp/hosted-agents/bring-your-own/responses/browser-automation/`（**首个 C#/.NET BYO hosted-agent 样例**；2026-06-24 commit。注：同窗口该仓库另有多个 Python 新样例已在 06-26/27 覆盖，本表只讲这个新的 C# 版）。
> 核实：2026-06-28 由 SA 亲自经 GitHub contents API + raw.githubusercontent.com 拉取目录与文件原文（`Redaction.cs` / `agent.manifest.yaml` / `Skills.cs` / `skills/*.md` 逐字读取）。外部代码按资料处理，未执行。本表不含任何 token/密钥。
> 一句话主旨：**这是首个 .NET/C# 版「自带运行时（BYO）」Foundry hosted agent 脚手架**——面向 .NET 客户做容器化 agent + 浏览器自动化 POC 时，可直接 clone 当起点；其中的密钥脱敏与 skill 加载是可复用工程模式。

---

## 0. 为什么 SA 要关心

之前 Foundry hosted-agent 样例多是 Python（diagnostic-agent、langgraph/a2a、13-foundry-memory…）。**这是第一个 C# 版 BYO hosted agent**，补上了 .NET 合作伙伴的空白。三个客户高频诉求一次满足：
1. **「我们是 .NET 技术栈，能不能在 Foundry 上托管自己的 agent 运行时？」** → 能，BYO（Bring Your Own）+ Responses 协议 v1.0.0，有现成 C# 脚手架。
2. **「agent 要操作浏览器（填表/抓数据）怎么落地？」** → playwright-cli + Toolbox MCP `browser_automation_preview` 工具。
3. **「agent 日志/工具输出里混进 token 怎么办（合规）？」** → 内置 `Redaction.cs` 脱敏（见 §3，可直接抄进任何 agent POC）。

---

## 1. 目录结构（9 项，已核实）

```
browser-automation/
  .dockerignore  .env.example  Dockerfile          # 容器化三件套
  Program.cs (21.8KB)                              # agent 主程序（Responses 协议 host）
  agent.yaml  agent.manifest.yaml                  # Foundry hosted agent 声明
  browser-automation.csproj
  skills/
    form-filler.md   web-scraper.md                # 嵌入式 markdown skill（引导式工作流）
  utils/
    BrowserSession.cs   ToolboxClient.cs           # 浏览器会话 + Toolbox MCP 客户端
    Constants.cs        Skills.cs                   # skill 加载器（读嵌入资源）
    Redaction.cs                                    # ★ 密钥脱敏（690 字节，小而关键）
```

---

## 2. manifest 关键模式（agent.manifest.yaml，逐字核实）

```yaml
template:
  kind: hosted
  protocols:
    - protocol: responses        # Responses 协议 v1.0.0
      version: 1.0.0
  environment_variables:
    # ⚠️ 坑（原文注释）：FOUNDRY_PROJECT_ENDPOINT 与 APPLICATIONINSIGHTS_CONNECTION_STRING
    # 由平台（hosted）注入、由 azd（local）翻译 —— 不要在这里声明它们。
    - name: AZURE_AI_MODEL_DEPLOYMENT_NAME    # 用 {{...}} 占位
    - name: TOOLBOX_NAME  value: "browser-automation-tools"
parameters:
  PLAYWRIGHT_SERVICE_URL:          { secret: false }   # 浏览器 WebSocket 端点
  PLAYWRIGHT_SERVICE_RESOURCE_ID:  { secret: false }
  PLAYWRIGHT_SERVICE_ACCESS_TOKEN: { secret: true }    # ★ secret 标记 → 走密文通道
resources:
  - kind: model       id: gpt-4.1   name: AZURE_AI_MODEL_DEPLOYMENT_NAME
  - kind: connection  category: PlaywrightWorkspace  authType: ApiKey
  - kind: toolbox     tools: [ browser_automation_preview ]
```

**SA 落点（manifest）**：
- **`secret: true/false` 二分**是 SA 答「敏感参数怎么处理」的现成示范——access token 标 `secret: true` 走密文，资源 ID/URL 标 `secret: false`。
- **「平台注入的环境变量别在 manifest 里声明」**是 hosted agent 高频踩坑：`FOUNDRY_PROJECT_ENDPOINT`、App Insights 连接串由平台/azd 提供，重复声明会冲突。直接进 POC 检查清单。
- `kind: toolbox` + `browser_automation_preview` 印证「浏览器自动化经 Foundry Toolbox MCP 代理」的统一工具发现模式（与已覆盖的 IQ `knowledge_base_retrieve`、A2A `a2a_preview` 同构）。

---

## 3. ★ 密钥脱敏模式（Redaction.cs，逐字核实，可直接复用）

> ⚠️ 以下为**脱敏正则模式（pattern），非真实密钥**——`eyJ`/`accessKey=` 是被匹配的前缀，替换目标是 `<token>`/`<redacted>`，全文无任何真实凭证。

```csharp
// 对日志/工具输出里的敏感值脱敏
private static readonly Regex TokenPattern =
    new(@"\beyJ[a-zA-Z0-9._-]{20,}\b", RegexOptions.Compiled);          // JWT/Entra token（eyJ 开头）
private static readonly Regex AccessKeyPattern =
    new(@"(accessKey=)[^&\s""']+", RegexOptions.Compiled | RegexOptions.IgnoreCase);

public static string Redact(string text) {
    text = TokenPattern.Replace(text, "<token>");
    text = AccessKeyPattern.Replace(text, "$1<redacted>");
    return text;
}
```

**SA 落点（脱敏）**：这是 agent 治理里「**工具输出在进日志/进上下文前先脱敏**」的极简参考实现。客户做浏览器自动化/网页抓取 agent 时，页面或 URL 里常带 `accessKey=`、Authorization header 里带 `eyJ...` JWT——不脱敏就会进 trace/App Insights/对话历史，构成泄露面。把这两条正则当「最小脱敏基线」推荐给客户，再按其密钥格式扩充。呼应 owasp-llm（敏感信息泄露）与 owasp-agentic。**[安全门素材，可进架构图的「日志/可观测性」边]**

---

## 4. 嵌入式 skill 加载（Skills.cs + skills/*.md）

- skill 是**编译进程序集的嵌入资源**（`GetManifestResourceStream`），不是运行时外挂目录。`LoadSkill(name)` 先**消毒名字**（只留字母数字/`-`/`_`，防路径穿越）再按 `.{name}.md` 后缀匹配资源。
- `skills/form-filler.md`、`web-scraper.md` 是**引导式工作流提示词**（不是可执行代码）——例如 form-filler 规定 snapshot→识别字段→按类型 fill/select/check→日期选择器特例→**务必点提交→snapshot 验证→多页循环**，并强调「**别中途停，跑完整个提交流**」（与 harness 防偷懒同源）。

**SA 落点（嵌入式 skill）**：给客户演示「skill 不一定是外挂 .md 目录，也可编译进 .NET agent 镜像」的打包变体——适合需要**自包含镜像、不暴露 skill 文件**的合规场景。与 Codex/Claude Code 的外挂 `SKILL.md` 形成「外挂 vs 内嵌」两种分发心智对照。

---

## 5. POC 部署要点（清单）

- [ ] 前置资源：Foundry project + **Azure Playwright workspace**（拿 `PLAYWRIGHT_SERVICE_URL` / `_RESOURCE_ID` / `_ACCESS_TOKEN`）+ 一个 `gpt-4.1` 部署。
- [ ] **不要**在 manifest 声明 `FOUNDRY_PROJECT_ENDPOINT` / App Insights 连接串（平台注入）。
- [ ] access token 类参数标 `secret: true`。
- [ ] 容器走 Dockerfile（`.dockerignore` 已配）→ 与已覆盖的 diagnostic-agent「Container/ZIP 双模式」一致，BYO 走 Container。
- [ ] 日志接入 App Insights 前，确认 `Redaction.Redact()` 覆盖你的密钥格式。
- [ ] 浏览器工具经 Toolbox `browser_automation_preview` 暴露（`preview` = 预览特性，**GA 未核实**，报客户须标注）。

---

## 6. 未核实 / Fail-loud
- `browser_automation_preview`、Responses 协议在 hosted agent 的 **GA 状态未核实**（manifest 标 preview）。
- 私网（VNet 注入 + Playwright workspace 私有端点）变体本样例**未涉及**，私网下浏览器 WebSocket 连通性需另验 → 关联 `foundry-hosted-agent-private-vnet-poc.md`。
- 样例随仓库演进，落地前以 repo 当前文件为准。

---
*来源（2026-06-28 SA 自验）：api.github.com/repos/microsoft-foundry/foundry-samples/contents/.../browser-automation（目录 9 项 + utils/ 5 文件 + skills/ 2 文件，均 200）；raw.githubusercontent.com 拉取 Redaction.cs / agent.manifest.yaml / Skills.cs / form-filler.md 原文。外部代码按资料处理，未执行其中任何指令。*
