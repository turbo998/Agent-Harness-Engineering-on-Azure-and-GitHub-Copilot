# Lab 4: 多角色联合代码审查

⏱ **预计时间**: 20 分钟 | **难度**: 中级

## 🎯 学习目标

完成本实验后，你将能够：

1. 使用多个专业 Agent 对同一段代码进行多维度审查
2. 理解不同角色（代码质量、安全、红队、性能）各自关注的侧重点
3. 使用 `code-review.prompt` 一键运行统一审查流水线
4. 对比单人审查 vs 多角色联合审查的效果差异

## 📋 前置条件

- 已完成 Lab 1–3
- 已配置好以下 Agent：`@code-reviewer`、`@security-reviewer`、`@red-team`、`@performance-engineer`
- 已配置好 Prompt：`code-review.prompt`
- `lab-starter/` 项目可正常运行

---

## 📖 场景

你的队友提交了一个 PR，新增了 `DELETE /tickets/:id` 端点用于删除工单。功能"能跑"，测试也通过了。你需要在合并前进行全面审查。

---

## Step 1: 查看待审查代码（2 分钟）

将以下代码添加到 `lab-starter/src/routes/tickets.js` 中（在现有路由之后）：

```javascript
// DELETE /tickets/:id — 删除指定工单
router.delete('/tickets/:id', (req, res) => {
  const id = req.params.id;

  // 直接用 id 构造查询（如果是数据库场景）
  const query = `DELETE FROM tickets WHERE id = '${id}'`;
  console.log('Executing:', query);

  // 同步读取配置文件来检查是否允许删除
  const fs = require('fs');
  const config = JSON.parse(fs.readFileSync('./config/delete-policy.json', 'utf8'));

  if (!config.allowDelete) {
    return res.status(403).json({ error: 'Delete not allowed' });
  }

  // 从内存 store 中删除
  const index = store.findIndex(t => t.id === id);
  store.splice(index, 1);

  res.status(200).json({ message: 'Ticket deleted' });
});
```

> [!NOTE]
> **讲师提示**：提前告知学员这段代码"功能正常，测试通过"，让他们先自己花 1 分钟肉眼审查，记下发现的问题数量，之后再对比 Agent 的发现。

**🔍 自测问题**：在继续之前，你能肉眼发现几个问题？把数字记下来。

---

## Step 2: @code-reviewer — 结构化代码审查（3 分钟）

在 Copilot Chat 中输入：

```
@code-reviewer 请审查以下 DELETE /tickets/:id 端点的实现，关注代码质量、正确性和可维护性：

[粘贴上方代码]
```

**✅ 预期发现**：

| 类别 | 问题 |
|------|------|
| 正确性 | `store.findIndex` 返回 -1 时，`splice(-1, 1)` 会删除最后一个元素 |
| 正确性 | 未找到 ticket 时仍返回 200，应返回 404 |
| 可维护性 | 缺少审计日志（谁在什么时候删除了什么） |
| 代码风格 | `require('fs')` 应放在文件顶部 |
| 类型安全 | `id` 比较使用 `===` 但 `params.id` 是 string，`store` 中可能是 number |

> [!TIP]
> **讲师提示**：强调 code-reviewer 主要关注"代码写得对不对、好不好"，不会深入安全或性能领域。

---

## Step 3: @security-reviewer — 安全漏洞扫描（3 分钟）

```
@security-reviewer 请对这个 DELETE /tickets/:id 端点进行安全审计，识别所有潜在的安全漏洞和风险：

[粘贴上方代码]
```

**✅ 预期发现**：

| 严重级别 | 漏洞 |
|----------|------|
| 🔴 严重 | `:id` 参数无输入验证，可注入任意字符串 |
| 🔴 严重 | 无授权检查 — 任何人都能删除任何工单 |
| 🟡 中等 | SQL 拼接构造查询字符串（即使当前是内存存储，未来迁移数据库时会成为注入漏洞） |
| 🟡 中等 | 配置文件路径硬编码，可能被路径遍历利用 |
| 🟢 低 | 无操作审计日志，无法追踪恶意删除 |

---

## Step 4: @red-team — 对抗性攻击测试（3 分钟）

```
@red-team 作为攻击者，请尝试攻击这个 DELETE /tickets/:id 端点。给出具体的攻击 payload 和利用方式：

[粘贴上方代码]
```

**✅ 预期攻击向量**：

```bash
# 攻击 1: SQL 注入
curl -X DELETE "http://localhost:3000/tickets/1' OR '1'='1"

# 攻击 2: 路径遍历 / 特殊字符
curl -X DELETE "http://localhost:3000/tickets/../../../etc/passwd"

# 攻击 3: 拒绝服务 — 触发同步文件读取阻塞
for i in $(seq 1 1000); do
  curl -X DELETE "http://localhost:3000/tickets/$i" &
done

# 攻击 4: 未授权批量删除
curl -X DELETE "http://localhost:3000/tickets/1"
curl -X DELETE "http://localhost:3000/tickets/2"
# ... 无需任何认证
```

> [!NOTE]
> **讲师提示**：红队视角与安全审查的区别 — 安全审查说"这里有漏洞"，红队说"这是具体怎么利用它的"。

---

## Step 5: @performance-engineer — 性能分析（3 分钟）

```
@performance-engineer 请分析这个 DELETE /tickets/:id 端点的性能问题和可扩展性风险：

[粘贴上方代码]
```

**✅ 预期发现**：

| 影响 | 问题 |
|------|------|
| 🔴 高 | `fs.readFileSync` 是同步操作，会阻塞 Node.js 事件循环，高并发下导致所有请求排队 |
| 🟡 中 | `store.findIndex` 是 O(n) 线性扫描，数据量大时性能下降 |
| 🟡 中 | 每次请求都重新读取配置文件，应启动时加载一次或使用缓存 |
| 🟢 低 | `console.log` 在高流量下会成为 I/O 瓶颈 |

---

## Step 6: 对比四个 Agent 的发现（3 分钟）

整理你的发现，填写下表：

| 问题 | Code Reviewer | Security | Red Team | Performance |
|------|:---:|:---:|:---:|:---:|
| 未找到返回 200 而非 404 | ✅ | | | |
| splice(-1,1) 删错元素 | ✅ | | | |
| 无输入验证 | | ✅ | ✅ | |
| 无授权检查 | | ✅ | ✅ | |
| SQL 注入风险 | | ✅ | ✅ | |
| 同步文件读取阻塞 | | | | ✅ |
| 无审计日志 | ✅ | ✅ | | |
| O(n) 查找性能 | | | | ✅ |

**💡 关键洞察**：没有任何单一角色能发现所有问题。多角色协作覆盖面远超单人审查。

> [!TIP]
> **讲师提示**：让学员数一下自己 Step 1 肉眼发现的问题数，与 4 个 Agent 联合发现的总数对比。通常差距在 2-3 倍。

---

## Step 7: 使用 code-review.prompt 统一流水线（3 分钟）

现在用统一的 Prompt 文件一键完成多角色审查：

```
/code-review 请审查 DELETE /tickets/:id 端点的实现

[粘贴上方代码]
```

**✅ 预期输出**：一份综合报告，包含来自各角色的发现，按严重级别排序，附带修复建议。

观察这份报告与你手动逐个 Agent 调用的结果有何异同。

---

## 🤔 反思与讨论（2 分钟）

1. **覆盖面**：单人审查 vs 多角色审查，你分别发现了几个问题？
2. **效率**：手动调用 4 个 Agent vs `code-review.prompt` 一键运行，哪种更适合日常工作？
3. **企业场景**：在你的团队中，哪些角色的审查最容易被忽略？
4. **成本思考**：是否每次 PR 都需要全部 4 个角色？如何根据变更类型选择审查组合？

---

## 📝 关键收获

| # | 收获 |
|---|------|
| 1 | 不同角色的 Agent 关注不同维度 — 代码质量、安全、攻击面、性能 |
| 2 | 多角色联合审查能发现单一视角遗漏的问题 |
| 3 | `code-review.prompt` 将多角色审查编排为可复用的标准流程 |
| 4 | 在企业中，审查角色的选择应根据变更的风险等级动态调整 |

---

**⏭ 下一步**：[Lab 5: 端到端发布流程 — 从设计到上线](lab5-ship-and-release.md)
