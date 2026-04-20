# GitHub Copilot Workshop 180分钟 — 讲师Demo脚本

> 本文档包含3个讲师演示的完整脚本，含精确提示词、预期输出与讲解要点。

---

## Demo 1：Quick Ask → Plan → Agent (10min)

### 场景
基于 ticket-service 需求，演示 Copilot 三种模式的差异。

### 准备
- 打开 VS Code，确保项目中有 `ticket-service/` 目录
- 打开 Copilot Chat 面板

### 步骤

#### Step 1: Ask 模式 (3min)

**在 Copilot Chat 中输入：**
```
我需要为 ticket-service 添加一个新的 API 端点，支持按优先级筛选工单列表。
请问应该如何设计这个接口？需要考虑哪些方面？
```

**预期输出：**
- Copilot 会给出设计建议（RESTful 路径、查询参数、分页等）
- 不会生成代码，只提供建议和思路

**讲师讲解要点：**
> "Ask 模式就像和一个资深同事讨论方案。它给你思路、给你建议，但不直接动手。适合需求澄清阶段。"

#### Step 2: Plan 模式 (3min)

**切换到 Plan 模式，输入：**
```
/plan 为 ticket-service 添加按优先级筛选工单的 GET /api/tickets?priority={level} 端点。
包含：路由定义、Controller、Service、Repository 层的修改计划。
```

**预期输出：**
- 生成分步计划：1) 添加路由 2) 创建 Controller 方法 3) Service 层逻辑 4) Repository 查询
- 列出需要修改的文件清单
- 不生成实际代码

**讲师讲解要点：**
> "Plan 模式帮你把模糊需求变成明确的执行步骤。这就是 AI-DLC 中 Plan 阶段的价值——降低实施风险。"

#### Step 3: Agent 模式 (4min)

**切换到 Agent 模式，输入：**
```
请为 ticket-service 实现按优先级筛选工单的功能：
- GET /api/tickets?priority=high|medium|low
- 支持分页 (page, size 参数)
- 包含单元测试
- 遵循项目现有代码风格
```

**预期输出：**
- Copilot Agent 自动：
  - 分析项目结构
  - 创建/修改多个文件
  - 生成 Controller、Service、Repository 代码
  - 生成对应的单元测试
- 在终端执行必要命令

**讲师讲解要点：**
> "Agent 模式是真正的自主执行。它不仅思考，还动手实现。这就是从 Chat 到 Agent 的能力跃迁。但注意——我们需要通过 Harness Engineering 来引导它的行为。这就是接下来要讲的内容。"

---

## Demo 2：多角色审查 (10min)

### 场景
展示 `@code-reviewer` 和 `@red-team` 对同一段代码发现不同类型的问题。

### 准备
- 准备一段包含多类问题的代码（已在 `demo/vulnerable-api.ts` 中）

### 演示代码
```typescript
// demo/vulnerable-api.ts
app.post('/api/users', async (req, res) => {
  const { username, password, role } = req.body;
  const query = `INSERT INTO users (username, password, role) VALUES ('${username}', '${password}', '${role}')`;
  const result = await db.execute(query);
  const token = jwt.sign({ id: result.insertId, role }, 'secret123');
  res.json({ token, message: `Welcome ${username}` });
});
```

### 步骤

#### Step 1: @code-reviewer 审查 (4min)

**在 Copilot Chat 中输入：**
```
@code-reviewer 请审查 demo/vulnerable-api.ts 中的代码，关注代码质量、可维护性和最佳实践。
```

**预期输出：**
- 指出缺少输入验证
- 指出缺少错误处理 (try-catch)
- 指出硬编码字符串
- 指出缺少类型定义
- 建议分层架构（Controller/Service 分离）

**讲师讲解要点：**
> "code-reviewer 从代码质量角度出发，关注可维护性和工程最佳实践。它像一个经验丰富的高级工程师在 review 你的 PR。"

#### Step 2: @red-team 审查 (4min)

**在 Copilot Chat 中输入：**
```
@red-team 请对 demo/vulnerable-api.ts 进行安全审计，识别所有潜在的安全漏洞和攻击面。
```

**预期输出：**
- 🚨 **SQL 注入**: 字符串拼接构造 SQL 查询
- 🚨 **密码明文存储**: 未 hash 密码
- 🚨 **硬编码密钥**: JWT secret 硬编码
- 🚨 **权限提升**: 用户可自行指定 role
- 🚨 **信息泄露**: 错误信息可能暴露数据库结构
- 给出 OWASP Top 10 映射

**讲师讲解要点：**
> "同样的代码，red-team 从攻击者视角出发，发现了完全不同维度的问题。SQL 注入、密码明文、权限提升——这些是 code-reviewer 不会重点关注的安全问题。这就是多角色审查的价值：多视角覆盖。"

#### Step 3: 对比总结 (2min)

**讲师讲解要点：**
> "两个 Agent 看同一段代码，给出互补的反馈。在真实团队中，你可能需要一个高级工程师+一个安全专家才能覆盖这些问题。现在通过多角色 Agent 体系，一个人也能获得多视角审查的效果。这就是'代码审查军团'的理念。"

---

## Demo 3：ship-release.prompt 驱动发布流程 (5min)

### 场景
演示 `.prompt.md` 模板如何驱动端到端发布流程。

### 准备
- 确保项目中有 `.github/prompts/ship-release.prompt.md` 文件

### 步骤

#### Step 1: 查看 Prompt 模板 (1min)

**展示 `ship-release.prompt.md` 内容：**
```markdown
---
mode: agent
description: "驱动完整发布流程"
---
## 发布检查清单

请按以下步骤完成发布准备：

1. **变更汇总**: 列出自上次 tag 以来的所有 commit
2. **CHANGELOG 生成**: 按 Conventional Commits 格式生成变更日志
3. **版本号建议**: 基于变更类型建议 semver 版本号
4. **破坏性变更检查**: 标注任何 breaking changes
5. **依赖审计**: 检查是否有已知安全漏洞的依赖
6. **发布 PR 草稿**: 生成发布 PR 的标题和描述
```

**讲师讲解要点：**
> "这就是一个 Prompt 模板——它定义了工作流程。任何团队成员执行发布时，只需调用这个模板，就能保证流程一致性。"

#### Step 2: 执行 Prompt (3min)

**在 Copilot Chat 中输入：**
```
/ship-release
```

**预期输出：**
- Agent 自动执行 `git log` 分析变更
- 生成格式化的 CHANGELOG
- 建议版本号（如 v1.2.0）
- 标注破坏性变更（如有）
- 生成发布 PR 描述

**讲师讲解要点：**
> "一个命令，完成了过去需要 30 分钟手工操作的发布流程。而且因为是模板驱动的，每次发布都是标准化的。这就是 Prompt 模板的威力——把团队知识编码为可执行的工作流。"

#### Step 3: 收尾 (1min)

**讲师讲解要点：**
> "从 Think 到 Ship，整个 AI-DLC 都可以用 Prompt 模板串联起来。think-clarify、plan-tasks、review-multi、test-generate、ship-release——六个模板覆盖完整生命周期。接下来的 Lab 5，你们将亲手体验这个全流程。"

---

## 演示注意事项

1. **网络**: 确保演示环境网络稳定，Copilot 响应可能需要 5-10 秒
2. **备选方案**: 准备截图/录屏作为 fallback
3. **互动**: 每个 Demo 后留 30 秒让学员提问
4. **节奏**: Demo 2 是重点，可适当延长；Demo 3 可压缩
