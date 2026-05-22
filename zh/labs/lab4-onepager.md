# Lab 4 · Spec-Driven Development with GitHub Spec-Kit

> **一句话 Hook**:Lab 3 教你"为什么"要多 agent 协作,Lab 4 把它**工业化**——用脚本 + 宪法把 SDD 流程固化成一条可复用的流水线。

---

## 🎯 4 个关键点

- 🧱 **从手作到工业化**:Lab 3 是裸手编排 handoff,Lab 4 是 spec-kit 把流程"焊死"成可复制的流水线。
- 📜 **宪法驱动,而非 LLM 推理**:`constitution.md` + 脚本强约束,不靠模型"自觉",保证多人多次执行结果一致。
- ⚙️ **9 个 `/speckit.*` slash 命令**:从 `constitution` → `specify` → `plan` → `tasks` → `implement`,自动建分支、自动 commit、独立 `analyze` 审查。
- 🎟️ **30–35 分钟跑通一个 mini feature**:为 Ticket Service 增加 `GET /tickets/search?q=`,端到端体验 SDD 全链路。

---

## 🛤️ 迷你时间轴(8 步,~30 min)

```
① constitution  → ② specify   → ③ clarify   → ④ plan
    宪法基线         写需求 spec     消除歧义       技术方案
        │                                            │
        ▼                                            ▼
⑤ tasks       → ⑥ analyze   → ⑦ implement → ⑧ verify
    任务拆分        独立审查        分支落码       验收 + PR
```

每一步:**自动新分支** · **自动 commit** · **产物落盘 `.specify/`**

---

## 🔁 Lab 3 vs Lab 4 对照表

| 维度 | Lab 3 · 手作多 Agent | Lab 4 · Spec-Kit 工业化 |
|---|---|---|
| 编排方式 | 人工 prompt handoff | 9 个 slash 命令固化 |
| 一致性保障 | 依赖 LLM 推理 | 宪法 + 脚本强约束 |
| 版本控制 | 手动 commit | 自动分支 + 自动 commit |
| 质量门禁 | review 靠人 | 独立 `analyze` 审查阶段 |
| 教学目的 | 理解 **why** | 体验 **industrial how** |

---

### 🎨 Designer Note

- **版式类别**:Phase Progression(阶段演进)——8 步时间轴是主视觉锚点,占页面 35–40%。
- **配色建议**:阶段色块渐变,推荐 `深紫 #2D1B4E → 蓝 #1E4FBA → 青 #00C2C7 → 亮黄 #FFD23F`,体现从"模糊需求"到"可交付代码"的能量递增。
- **字体**:标题用 Inter / 思源黑体 Bold;正文用 Inter Regular,代码块用 JetBrains Mono。
- **图形语言**:8 步用圆角胶囊 + 箭头连接;对照表用左灰右亮双列,Lab 4 列高亮青色描边。
- **避免**:深色霓虹高对比(那是 benchmark 类专用);本页走"工程演进 + 暖色收尾"的明快路线。
- **页面层级**:Hook(15%)→ 4 关键点(25%)→ 时间轴(35%)→ 对照表(20%)→ 页脚 logo(5%)。
