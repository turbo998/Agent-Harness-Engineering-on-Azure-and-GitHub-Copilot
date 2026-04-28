const PptxGenJS = require('pptxgenjs');

const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'GitHub Copilot CLI';
pptx.company = 'Microsoft';
pptx.subject = 'GitHub Copilot customer workshop with agent mode';
pptx.title = 'GitHub Copilot 从 IDE 助手到 Agent 工作流';
pptx.lang = 'zh-CN';
pptx.theme = {
  headFontFace: 'Microsoft YaHei',
  bodyFontFace: 'Microsoft YaHei',
  lang: 'zh-CN'
};

const C = {
  navy: '0B1F3A',
  blue: '0969DA',
  cyan: '28A5F5',
  green: '1F883D',
  orange: 'FF8A00',
  red: 'CF222E',
  ink: '1F2328',
  gray: '57606A',
  line: 'D0D7DE',
  soft: 'F6F8FA',
  white: 'FFFFFF',
  lightBlue: 'EAF5FF',
  lightGreen: 'EAF7EE',
  lightOrange: 'FFF3E8',
  lightPurple: 'F5EEFF'
};

const path = require('path');
const output = path.join(__dirname, 'GHCP_Workshop_120min_Agent版_升级版.pptx');

function addHeader(slide, title, subtitle = '客户技术团队 · 120分钟') {
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.33,
    h: 0.82,
    fill: { color: C.navy },
    line: { color: C.navy }
  });

  slide.addText(title, {
    x: 0.45,
    y: 0.16,
    w: 8.1,
    h: 0.32,
    fontSize: 24,
    bold: true,
    color: C.white,
    margin: 0
  });

  slide.addText(subtitle, {
    x: 8.45,
    y: 0.19,
    w: 4.4,
    h: 0.2,
    align: 'right',
    fontSize: 10,
    color: 'B6D4FE',
    margin: 0
  });

  slide.addShape(pptx.ShapeType.line, {
    x: 0.45,
    y: 6.95,
    w: 12.35,
    h: 0,
    line: { color: C.line, width: 1 }
  });
}

function addFooter(slide, text = 'GitHub Copilot workshop draft · For customer enablement') {
  slide.addText(text, {
    x: 0.5,
    y: 7.02,
    w: 12.2,
    h: 0.18,
    fontSize: 9,
    color: C.gray,
    align: 'center',
    margin: 0
  });
}

function addBulletList(slide, items, x, y, w, options = {}) {
  const fontSize = options.fontSize ?? 18;
  const gap = options.gap ?? 0.48;
  const bulletColor = options.bulletColor ?? C.blue;

  items.forEach((item, index) => {
    const top = y + index * gap;
    slide.addShape(pptx.ShapeType.rect, {
      x,
      y: top + 0.11,
      w: 0.08,
      h: 0.08,
      fill: { color: bulletColor },
      line: { color: bulletColor }
    });

    slide.addText(item, {
      x: x + 0.18,
      y: top,
      w: w - 0.18,
      h: 0.32,
      fontSize,
      color: C.ink,
      margin: 0,
      breakLine: true
    });
  });
}

function addCard(slide, x, y, w, h, title, body, accent, fill) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.05,
    fill: { color: fill },
    line: { color: accent, width: 1.1 }
  });

  slide.addText(title, {
    x: x + 0.12,
    y: y + 0.12,
    w: w - 0.24,
    h: 0.28,
    fontSize: 15,
    bold: true,
    color: accent,
    margin: 0
  });

  slide.addText(body, {
    x: x + 0.12,
    y: y + 0.48,
    w: w - 0.24,
    h: h - 0.6,
    fontSize: 11,
    color: C.ink,
    margin: 0.03,
    valign: 'top'
  });
}

function addSectionBand(slide, label, title, subtitle) {
  slide.background = { color: C.navy };

  slide.addText(label, {
    x: 0.75,
    y: 1.05,
    w: 1.8,
    h: 0.26,
    fontSize: 12,
    bold: true,
    color: '8CC8FF',
    margin: 0
  });

  slide.addText(title, {
    x: 0.75,
    y: 1.55,
    w: 10.8,
    h: 0.9,
    fontSize: 28,
    bold: true,
    color: C.white,
    margin: 0
  });

  slide.addText(subtitle, {
    x: 0.78,
    y: 2.6,
    w: 10.2,
    h: 0.8,
    fontSize: 16,
    color: 'D8E8FF',
    margin: 0
  });

  slide.addShape(pptx.ShapeType.line, {
    x: 0.78,
    y: 3.65,
    w: 4.5,
    h: 0,
    line: { color: C.cyan, width: 2 }
  });

  slide.addText('GitHub Copilot · IDE + Agents + Best Practices + Demo + Hands-on Lab', {
    x: 0.78,
    y: 5.95,
    w: 7.2,
    h: 0.25,
    fontSize: 11,
    color: 'A9C6E8',
    margin: 0
  });
}

function addTwoColumnTable(slide, rows, x, y, w1, w2, rowHeight, headerTitle1, headerTitle2, headerFill) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w: w1,
    h: rowHeight,
    fill: { color: headerFill },
    line: { color: headerFill }
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: x + w1,
    y,
    w: w2,
    h: rowHeight,
    fill: { color: headerFill },
    line: { color: headerFill }
  });
  slide.addText(headerTitle1, {
    x: x + 0.08,
    y: y + 0.06,
    w: w1 - 0.16,
    h: rowHeight - 0.1,
    fontSize: 11,
    bold: true,
    color: C.white,
    margin: 0
  });
  slide.addText(headerTitle2, {
    x: x + w1 + 0.08,
    y: y + 0.06,
    w: w2 - 0.16,
    h: rowHeight - 0.1,
    fontSize: 11,
    bold: true,
    color: C.white,
    margin: 0
  });

  rows.forEach((row, index) => {
    const top = y + rowHeight * (index + 1);
    const fill = index % 2 === 0 ? 'FFFFFF' : C.soft;
    slide.addShape(pptx.ShapeType.rect, {
      x,
      y: top,
      w: w1,
      h: rowHeight,
      fill: { color: fill },
      line: { color: C.line, width: 0.8 }
    });
    slide.addShape(pptx.ShapeType.rect, {
      x: x + w1,
      y: top,
      w: w2,
      h: rowHeight,
      fill: { color: fill },
      line: { color: C.line, width: 0.8 }
    });
    slide.addText(row[0], {
      x: x + 0.08,
      y: top + 0.05,
      w: w1 - 0.16,
      h: rowHeight - 0.1,
      fontSize: 10,
      color: C.ink,
      margin: 0
    });
    slide.addText(row[1], {
      x: x + w1 + 0.08,
      y: top + 0.05,
      w: w2 - 0.16,
      h: rowHeight - 0.1,
      fontSize: 10,
      color: C.ink,
      margin: 0
    });
  });
}

// Slide 1
{
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };

  slide.addShape(pptx.ShapeType.rect, {
    x: 8.5,
    y: 0,
    w: 4.83,
    h: 7.5,
    fill: { color: C.blue },
    line: { color: C.blue }
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 9.4,
    y: 0,
    w: 3.93,
    h: 7.5,
    fill: { color: C.cyan },
    line: { color: C.cyan, transparency: 100 }
  });

  slide.addText('GitHub Copilot\n从 IDE 助手到 Agent 工作流', {
    x: 0.7,
    y: 1.05,
    w: 7.2,
    h: 1.45,
    fontSize: 26,
    bold: true,
    color: C.white,
    margin: 0
  });
  slide.addText('客户技术团队 Workshop · 120分钟', {
    x: 0.75,
    y: 2.85,
    w: 4.5,
    h: 0.3,
    fontSize: 15,
    color: 'B6D4FE',
    margin: 0
  });
  slide.addText('内容覆盖：GHCP 操作讲解、IDE 使用、Agent Mode、最佳实践、Live Demo、动手实验', {
    x: 0.78,
    y: 4.1,
    w: 6.2,
    h: 0.75,
    fontSize: 18,
    color: C.white,
    margin: 0
  });
  slide.addText('目标：让学员知道什么时候用 Ask / Plan / Agent，并能完成一次完整实验', {
    x: 0.78,
    y: 5.35,
    w: 6.7,
    h: 0.55,
    fontSize: 14,
    color: 'D8E8FF',
    margin: 0
  });
}

// Slide 2
{
  const slide = pptx.addSlide();
  addHeader(slide, 'Workshop 目标与学习成果');
  addFooter(slide);

  addCard(slide, 0.6, 1.2, 4.0, 2.05, '理解产品能力', '从日常 IDE 辅助延伸到 Ask / Plan / Agent 工作流，理解 GitHub Copilot 在开发闭环中的位置。', C.blue, C.lightBlue);
  addCard(slide, 4.75, 1.2, 4.0, 2.05, '掌握使用路径', '知道什么时候用 Ask 解释代码、什么时候先 Plan 控制 scope、什么时候让 Agent 执行明确任务。', C.green, C.lightGreen);
  addCard(slide, 8.9, 1.2, 3.8, 2.05, '完成实操闭环', '基于实验手册独立完成一次 feature enhancement、补测试、运行验证。', C.orange, C.lightOrange);

  addBulletList(slide, [
    '适合对象：客户技术团队、架构师、技术负责人、核心开发成员',
    '强调“工作流与治理边界”，而不是只展示代码生成速度',
    'Demo 与 Lab 采用同一 ticket service 场景，降低学习切换成本',
    '实验结束后，学员应可独立复现 Ask → Plan → Agent 的最小闭环'
  ], 0.75, 3.7, 12.0, { fontSize: 18, gap: 0.56 });
}

// Slide 3
{
  const slide = pptx.addSlide();
  addHeader(slide, '120 分钟议程');
  addFooter(slide);

  addTwoColumnTable(
    slide,
    [
      ['开场与目标对齐（5 min）', 'Workshop 目标、受众定位、今天会交付什么'],
      ['GHCP 核心操作与 IDE 路径（10 min）', 'Chat、Inline、Terminal、代码理解与协同方式'],
      ['Agent Mode 与工作流升级（10 min）', 'Ask / Plan / Agent、local / CLI / cloud、审批与自治'],
      ['Live Demo：Ask → Plan → Agent（15 min）', '在 ticket service 中完成一次完整闭环演示'],
      ['实验 1：AI-DLC 全生命周期（20 min）', '需求理解、规划、实现、测试、review、PR 描述'],
      ['Harness Engineering 讲解 + 实验（25 min）', 'instructions / agents / prompt files / backpressure / 热门参考案例'],
      ['Multi-Agent 讲解 + 实验（20 min）', 'Planner / Developer / Test / Security / Docs 角色协作'],
      ['Q&A 与落地建议（15 min）', '从试点任务到团队 adoption']
    ],
    0.7,
    1.12,
    3.9,
    8.4,
    0.56,
    '环节',
    '讲解重点',
    C.blue
  );
}

// Slide 4
{
  const slide = pptx.addSlide();
  addSectionBand(slide, 'PART 1', '从 IDE 助手到 Agent 工作流', '先把产品能力放到开发流程里，而不是孤立地介绍单个功能。');
}

// Slide 5
{
  const slide = pptx.addSlide();
  addHeader(slide, 'GitHub Copilot 在技术团队中的三层价值');
  addFooter(slide);

  addCard(slide, 0.65, 1.35, 3.95, 2.5, '第 1 层：即时辅助', '代码补全、注释生成、解释代码、写测试样例。适合个人开发的瞬时问题。', C.blue, C.lightBlue);
  addCard(slide, 4.7, 1.35, 3.95, 2.5, '第 2 层：结构化协作', '通过 Chat 明确目标、审查方案、生成分步计划。适合“先讨论，再动手”。', C.green, C.lightGreen);
  addCard(slide, 8.75, 1.35, 3.95, 2.5, '第 3 层：任务代理', 'Agent 跨文件执行、运行命令、回看结果并纠错。适合边界清晰的小到中型任务。', C.orange, C.lightOrange);

  addBulletList(slide, [
    'Workshop 的主线：从“问问题”走向“交任务”',
    '并不是所有场景都应该直接 Agent：解释型问题更适合 Ask',
    '技术团队真正需要的是“生产力 + 治理边界”'
  ], 0.8, 4.5, 11.9, { fontSize: 18, gap: 0.52 });
}

// Slide 6
{
  const slide = pptx.addSlide();
  addHeader(slide, 'IDE 使用主线：从理解到执行');
  addFooter(slide);

  addTwoColumnTable(
    slide,
    [
      ['Chat / Ask', '解释代码、理解项目、找入口、分析错误、识别 TODO'],
      ['Inline / Edit Suggestions', '局部补全、重构片段、生成注释、优化命名'],
      ['Plan', '把需求变成步骤，先锁定范围再执行'],
      ['Agent', '跨文件改动、跑命令、补测试、验证结果'],
      ['Terminal + Review', '把 agent 的输出纳入现有工程流程：测试、审查、提交']
    ],
    0.75,
    1.35,
    3.2,
    8.9,
    0.72,
    '使用形态',
    '适用场景',
    C.green
  );

  slide.addText('建议讲法：先建立“理解 → 规划 → 执行 → 验证”的主线，再把各个模式放入对应环节。', {
    x: 0.82,
    y: 5.55,
    w: 11.7,
    h: 0.45,
    fontSize: 16,
    color: C.gray,
    margin: 0
  });
}

// Slide 7
{
  const slide = pptx.addSlide();
  addHeader(slide, 'Agent Mode 核心概念');
  addFooter(slide, 'Reference: VS Code Copilot agents overview (2026-04)');

  addBulletList(slide, [
    'Agent 是能围绕高层目标自主推进任务的 AI 助手：规划、改代码、跑命令、纠错、再验证',
    'Agent loop 的关键是：理解任务 → 分解步骤 → 调用工具 → 观察结果 → 修正 → 结束',
    '对技术团队的价值，不是替代工程师，而是承担一段边界清晰的执行链路'
  ], 0.8, 1.35, 12.0, { fontSize: 18, gap: 0.62 });

  addCard(slide, 0.8, 3.9, 3.85, 1.9, 'Ask', '只回答问题，不主动改文件。适合理解、调研、解释。', C.blue, C.lightBlue);
  addCard(slide, 4.75, 3.9, 3.85, 1.9, 'Plan', '先产出结构化实现方案，再决定是否交给执行型 agent。', C.green, C.lightGreen);
  addCard(slide, 8.7, 3.9, 3.85, 1.9, 'Agent', '直接执行任务，跨文件修改并使用终端/工具完成闭环。', C.orange, C.lightOrange);
}

// Slide 8
{
  const slide = pptx.addSlide();
  addHeader(slide, 'Agent 类型：local / CLI / cloud / third-party');
  addFooter(slide);

  addTwoColumnTable(
    slide,
    [
      ['Local agent', '交互式、贴近编辑器上下文，适合讨论、调试、逐步推进'],
      ['Copilot CLI', '在本机后台执行，适合定义清楚的任务，让开发者继续做别的事'],
      ['Cloud agent', '远程执行，适合与 PR、issue、团队协作流程结合'],
      ['Third-party agents', '当组织需要指定模型提供方或特定 agent harness 时使用']
    ],
    0.72,
    1.4,
    2.7,
    9.8,
    0.86,
    '类型',
    '适用定位',
    C.orange
  );

  slide.addText('建议讲法：先让客户技术团队记住“本地交互式”与“后台执行式”的区别，再引出 CLI / cloud 的扩展路径。', {
    x: 0.82,
    y: 5.45,
    w: 11.8,
    h: 0.7,
    fontSize: 16,
    color: C.gray,
    margin: 0
  });
}

// Slide 9
{
  const slide = pptx.addSlide();
  addHeader(slide, '审批与自治：如何安全地用 Agent');
  addFooter(slide);

  addCard(slide, 0.8, 1.4, 3.8, 2.2, 'Default Approvals', '大多数团队的起点。读取与安全工具可自动通过，其他动作需要确认。', C.blue, C.lightBlue);
  addCard(slide, 4.8, 1.4, 3.8, 2.2, 'Bypass Approvals', '适合边界明确、影响范围可控的任务，提高执行效率。', C.green, C.lightGreen);
  addCard(slide, 8.8, 1.4, 3.8, 2.2, 'Autopilot', '更高自治，适合标准化流程，但必须搭配清晰 guardrails。', C.orange, C.lightOrange);

  addBulletList(slide, [
    '对客户技术团队要明确说明：权限不是“越高越好”，而是“是否与任务边界匹配”',
    '建议先从小仓库、小任务、默认审批开始',
    '让 agent 改代码前，先把验收标准说清楚：改哪些文件、补哪些测试、如何验证'
  ], 0.8, 4.2, 11.8, { fontSize: 17, gap: 0.52 });
}

// Slide 10
{
  const slide = pptx.addSlide();
  addHeader(slide, '最佳实践：技术团队最该讲清楚什么');
  addFooter(slide);

  addBulletList(slide, [
    '任务表达要具体：目标、范围、约束、验收标准、验证方式',
    '优先让 Agent 处理边界清晰的小任务，再逐步扩大到中型任务',
    '把 Ask / Plan / Agent 当作一个组合，而不是单选题',
    '对高风险仓库保留审批，对重复性任务逐步提高自治',
    '要求 Agent 在完成后运行测试或给出可验证结果',
    '保留工程师审查权：生成结果 != 可直接进入生产'
  ], 0.85, 1.45, 11.8, { fontSize: 18, gap: 0.6, bulletColor: C.green });
}

// Slide 11
{
  const slide = pptx.addSlide();
  addHeader(slide, 'Harness Engineering：重点不是 magic prompt，而是 Agent 的运行环境');
  addFooter(slide, 'References: github/awesome-copilot · walkinglabs/awesome-harness-engineering · Copilot Customization Handbook');

  addCard(slide, 0.7, 1.35, 3.9, 2.1, 'Prompt Engineering', '一次性对话技巧。适合快速尝试，但稳定性依赖个人经验，难以团队复用。', C.blue, C.lightBlue);
  addCard(slide, 4.75, 1.35, 3.9, 2.1, 'Harness Engineering', '把规则、角色、工作流、反馈机制做成仓库资产，让 Agent 更稳而不是更玄学。', C.green, C.lightGreen);
  addCard(slide, 8.8, 1.35, 3.8, 2.1, '企业价值', '可复用、可治理、可版本化、可审计，适合团队级落地，而不是个人技巧秀。', C.orange, C.lightOrange);

  addTwoColumnTable(
    slide,
    [
      ['Always-on 规则', 'copilot-instructions.md：项目共识、架构边界、测试与 PR 规范'],
      ['角色边界', 'custom agents：planner / test / security / docs 等职责划分'],
      ['任务模板', 'prompt files：把高频任务模板化，而不是每次重写 prompt'],
      ['能力扩展', 'MCP：让 Agent 访问外部知识、服务与工具'],
      ['自动纠偏', 'tests / lint / CI / hooks：让 Agent 能自己发现并修正错误']
    ],
    0.78,
    3.9,
    2.45,
    9.5,
    0.5,
    'Harness 维度',
    '在 GitHub Copilot 中的体现',
    C.green
  );
}

// Slide 12
{
  const slide = pptx.addSlide();
  addHeader(slide, '参考案例：为什么顶级团队更重视 Harness，而不是“神奇提示词”');
  addFooter(slide);

  addCard(slide, 0.75, 1.35, 4.0, 2.0, 'github/awesome-copilot', '把 instructions、agents、skills、hooks、workflows 组织成可复用模块，说明 customization 正在从技巧走向资产。', C.blue, C.lightBlue);
  addCard(slide, 4.9, 1.35, 4.0, 2.0, 'walkinglabs/awesome-harness-engineering', '把 harness 拆成 context、guardrails、specs、evals、runtime，说明这是一整层系统设计。', C.green, C.lightGreen);
  addCard(slide, 9.05, 1.35, 3.55, 2.0, '行业共识', '效果差往往不是模型不行，而是缺少结构、边界和反馈闭环。', C.orange, C.lightOrange);

  addBulletList(slide, [
    '没有测试、lint、CI 的仓库，换更强模型通常只是“更会胡来”',
    '好的 Harness 会让同一句 prompt 在不同工程师手里也更稳定',
    '把经验沉淀成 instructions / agents / prompt files，才具备团队复用价值',
    '企业真正需要的是可预测、可治理、可回归的 Agent，而不是偶尔惊艳一次'
  ], 0.85, 3.95, 11.6, { fontSize: 18, gap: 0.58, bulletColor: C.orange });

  slide.addText('讲师建议：这一页可作为“为什么要做 Harness Engineering”的管理层解释页。', {
    x: 0.85,
    y: 6.45,
    w: 11.5,
    h: 0.3,
    fontSize: 13,
    color: C.gray,
    margin: 0
  });
}

// Slide 13
{
  const slide = pptx.addSlide();
  addSectionBand(slide, 'PART 2', 'Live Demo、Harness Engineering 与动手实验', '从 Agent 使用进阶到工程化 harness，再进入 AIDLC / Multi-Agent 实操。');
}

// Slide 12
{
  const slide = pptx.addSlide();
  addHeader(slide, 'Demo 场景：Customer Support Ticket Service');
  addFooter(slide);

  addCard(slide, 0.75, 1.35, 4.0, 2.2, '项目现状', '一个简化版 Express API，支持 list / create / update status。代码可快速理解，适合现场演示。', C.blue, C.lightBlue);
  addCard(slide, 4.9, 1.35, 4.0, 2.2, '演示目标', '新增 /tickets/summary，返回按 status 与 priority 聚合后的统计结果。', C.green, C.lightGreen);
  addCard(slide, 9.05, 1.35, 3.55, 2.2, '展示重点', 'Ask → Plan → Agent、审批、测试验证、讲师解释治理边界。', C.orange, C.lightOrange);

  addBulletList(slide, [
    'Ask：解释项目并识别 TODO',
    'Plan：先产出实现步骤',
    'Agent：跨文件修改、补测试、跑 npm test',
    '讲师补充：什么时候适合 local agent，什么时候可以 handoff 到 CLI / cloud'
  ], 0.82, 4.2, 11.7, { fontSize: 18, gap: 0.56 });
}

// Slide 13
{
  const slide = pptx.addSlide();
  addHeader(slide, 'Demo Prompt 建议');
  addFooter(slide);

  addCard(slide, 0.75, 1.2, 3.95, 2.0, 'Ask Prompt', 'Explain this project as if I just joined the team. Focus on API surface, data model, and obvious TODOs.', C.blue, C.lightBlue);
  addCard(slide, 4.8, 1.2, 3.95, 2.0, 'Plan Prompt', 'Create a plan to add a GET /tickets/summary endpoint with grouped counts and tests.', C.green, C.lightGreen);
  addCard(slide, 8.85, 1.2, 3.75, 2.0, 'Agent Prompt', 'Implement the /tickets/summary endpoint, add tests, and run the test suite.', C.orange, C.lightOrange);

  addBulletList(slide, [
    '现场提示：如果 agent 任务过大，立即缩小目标范围',
    '现场提示：把“run tests when finished”写进 prompt，帮助形成闭环',
    '现场提示：Demo 价值在工作流，不在于 prompt 写得多花哨'
  ], 0.82, 4.05, 11.7, { fontSize: 18, gap: 0.58 });
}

// Slide 14
{
  const slide = pptx.addSlide();
  addHeader(slide, '升级版 Hands-on Lab 设计');
  addFooter(slide);

  addTwoColumnTable(
    slide,
    [
      ['实验 1：AI-DLC', '新增 /tickets/summary，完整走 Ask → Plan → Agent → Test → Review → PR 描述'],
      ['实验 2：Harness Engineering', '构建 instructions / planner agent / test-engineer / workflow prompt，并理解 backpressure'],
      ['实验 3：Multi-Agent', 'Developer → Test Engineer → Security Reviewer → Doc Writer 串行协作'],
      ['验证', '运行 npm test；必要时启动服务验证 API；讨论治理与边界'],
      ['复盘', '总结什么时候该用 Ask / Plan / Agent / custom agents / prompt files']
    ],
    0.75,
    1.45,
    2.6,
    9.6,
    0.82,
    '实验环节',
    '学员动作',
    C.blue
  );

  slide.addText('升级版实验手册原则：不仅给 prompt，还给结构化 harness、角色边界和验证闭环，确保学员理解“为什么这样设计”。', {
    x: 0.82,
    y: 5.3,
    w: 11.8,
    h: 0.5,
    fontSize: 16,
    color: C.gray,
    margin: 0
  });
}

// Slide 15
{
  const slide = pptx.addSlide();
  addHeader(slide, '实验引导话术：学员要学会的不是“一个 prompt”');
  addFooter(slide);

  addBulletList(slide, [
    '先 Ask：理解系统与待办项',
    '再 Plan：把任务拆成清楚步骤',
    '再 Agent：执行边界清晰的变更，并要求测试验证',
    '最后 Review：检查改动范围、运行结果、是否符合团队规范',
    '这套流程可以迁移到真实项目中的 bug fix、小功能增强、测试补齐等任务'
  ], 0.85, 1.45, 11.7, { fontSize: 19, gap: 0.68, bulletColor: C.orange });
}

// Slide 16
{
  const slide = pptx.addSlide();
  addHeader(slide, '落地建议：从 Workshop 到团队试点');
  addFooter(slide);

  addCard(slide, 0.75, 1.45, 3.8, 2.1, '第 1 步：选择试点任务', '从低风险、边界清晰、可测试的小任务开始，例如补测试、加小接口、修局部 bug。', C.blue, C.lightBlue);
  addCard(slide, 4.75, 1.45, 3.8, 2.1, '第 2 步：确定治理方式', '决定哪些仓库保留审批，哪些任务允许更高自治，谁来 review 结果。', C.green, C.lightGreen);
  addCard(slide, 8.75, 1.45, 3.8, 2.1, '第 3 步：沉淀团队模板', '积累常见 prompt 模板、实验脚本、review 清单、handoff 方式。', C.orange, C.lightOrange);

  addBulletList(slide, [
    'Workshop 的目标不是一次性讲完所有能力，而是让团队拿到一条清晰的采用路径',
    '客户技术团队通常最关心：可控性、验证性、与现有工程流程的兼容性'
  ], 0.8, 4.3, 11.8, { fontSize: 18, gap: 0.58 });
}

// Slide 17
{
  const slide = pptx.addSlide();
  addHeader(slide, '附录：交付清单');
  addFooter(slide);

  addTwoColumnTable(
    slide,
    [
      ['PPT', '120 分钟 workshop deck，覆盖 IDE、agent mode、best practices、demo、lab'],
      ['讲师 Demo 脚本', '包含时间分配、推荐 prompts、话术和备用方案'],
      ['实验操作手册', '学员可逐步执行的 Ask / Plan / Agent 实验说明'],
      ['Lab Starter', '可直接打开并运行的 Node.js ticket service 项目']
    ],
    0.75,
    1.45,
    2.7,
    9.5,
    0.86,
    '资产',
    '说明',
    C.green
  );
}

// Slide 18
{
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };
  slide.addText('Q&A', {
    x: 0.8,
    y: 1.8,
    w: 3.0,
    h: 0.6,
    fontSize: 30,
    bold: true,
    color: C.white,
    margin: 0
  });
  slide.addText('建议收尾问题：\n1. 你会先在哪类任务中试点 Agent？\n2. 你们更适合从 Default Approvals 还是 Bypass Approvals 开始？\n3. 哪些任务仍然更适合 Ask / Plan？', {
    x: 0.82,
    y: 2.7,
    w: 7.0,
    h: 2.0,
    fontSize: 18,
    color: 'D8E8FF',
    margin: 0
  });
  slide.addText('GitHub Copilot Workshop Draft', {
    x: 0.82,
    y: 6.4,
    w: 3.5,
    h: 0.25,
    fontSize: 11,
    color: 'A9C6E8',
    margin: 0
  });
}

pptx.writeFile({ fileName: output });
