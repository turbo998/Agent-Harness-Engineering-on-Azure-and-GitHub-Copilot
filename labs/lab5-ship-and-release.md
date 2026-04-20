# Lab 5: End-to-End Release Process — From Design to Production

⏱ **Estimated Time**: 25 minutes | **Difficulty**: Advanced

## 🎯 Learning Objectives

After completing this lab, you will be able to:

1. Experience the complete Think → Plan → Build → Review → Test → Ship development cycle
2. Use the appropriate specialized Agent and Prompt at each phase
3. Understand how a gstack-style engineering process can be implemented with Copilot
4. Independently use multi-Agent collaboration to deliver a feature from design to release

## 📋 Prerequisites

- Completed Labs 1–4
- All Agents configured: `@product-reviewer`, `@architect`, `@test-engineer`, `@release-engineer`, `@code-reviewer`
- All Prompts configured: `design-feature.prompt`, `code-review.prompt`, `ship-release.prompt`
- The `lab-starter/` project runs normally and `npm test` passes

---

## 📖 Scenario

The product manager has a requirement: **support updating ticket status**. A new `PATCH /tickets/:id` endpoint is needed that allows updating a ticket's `status` field (`open` → `in-progress` → `closed`).

You will deliver this feature using a complete engineering process.

---

## Phase 1: Think — Requirement Assessment & Architecture Design (5 minutes)

### 1.1 Product Review

```
@product-reviewer We plan to add a PATCH /tickets/:id endpoint that allows updating ticket status.
Status transition rules: open → in-progress → closed, no rollback allowed.
Please review this requirement from a product perspective, pointing out potential issues and improvement suggestions.
```

**✅ Expected feedback**:
- Should `closed → reopen` be supported?
- Should status changes require a note/reason?
- Should relevant people be notified?
- Permission control — who can change the status?

> [!NOTE]
> **Instructor tip**: Emphasize the value of the Think phase — finding requirement-level issues before writing code has the lowest cost. Have participants briefly note down the product suggestions, but this lab focuses on the engineering process — they don't need to adopt all suggestions.

### 1.2 Architecture Design

```
@architect Please design a technical solution for the PATCH /tickets/:id endpoint.
Requirement: Update the ticket status field, status transitions open → in-progress → closed, no rollback.
The current project uses Express + in-memory storage. Please provide an API design, data validation, and error handling plan.
```

**✅ Expected output**:
- API contract: `PATCH /tickets/:id` body: `{ "status": "in-progress" }`
- State machine validation logic
- Error code design: 400 (invalid status), 404 (ticket not found), 409 (illegal status transition)
- Suggested file modification list

---

## Phase 2: Build — Generate Implementation Plan & Code (5 minutes)

### 2.1 Generate Implementation Plan

```
/design-feature PATCH /tickets/:id endpoint
Requirement: Update ticket status, status transitions open → in-progress → closed, no rollback.
Reference architecture plan: [paste key output from Phase 1.2]
```

**✅ Expected output**: A structured implementation step list, including files to modify and specific changes.

### 2.2 Implement Using Agent Mode

In Copilot Chat, switch to **Agent Mode** (click the mode toggle button), then enter:

```
Based on the following design plan, implement the PATCH /tickets/:id endpoint in the lab-starter project:

1. Add PATCH route in src/routes/tickets.js
2. Validate :id parameter format
3. Validate request body contains status field
4. Implement status transition validation (open → in-progress → closed, no rollback)
5. Return the updated ticket object
6. Handle 404 (ticket not found) and 409 (illegal status transition)
```

**Verify the implementation**:

```bash
# Create a test ticket
curl -X POST http://localhost:3000/tickets \
  -H "Content-Type: application/json" \
  -d '{"title": "Test ticket", "status": "open"}'

# Update status
curl -X PATCH http://localhost:3000/tickets/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "in-progress"}'

# Should return 409 — rollback not allowed
curl -X PATCH http://localhost:3000/tickets/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "open"}'
```

> [!TIP]
> **Instructor tip**: Agent Mode will automatically create/modify files. Remind participants to check what file changes Copilot made — don't blindly accept.

---

## Phase 3: Review — Multi-Role Code Review (5 minutes)

### 3.1 Run Unified Review

```
/code-review Please review the PATCH /tickets/:id endpoint I just implemented
```

### 3.2 Fix Discovered Issues

Based on the review report, fix the discovered issues one by one. Common findings:

- Input validation not strict enough
- Missing request rate limiting
- Error messages leaking internal information

```
@code-reviewer I've made the following changes based on the review feedback: [describe changes]. Please confirm whether all issues have been resolved.
```

> [!NOTE]
> **Instructor tip**: In real work, reviews may require multiple rounds. This lab is time-limited — fixing 1–2 critical issues is sufficient.

---

## Phase 4: Test — Generate and Run Tests (5 minutes)

### 4.1 Generate Test Cases

```
@test-engineer Please generate comprehensive test cases for the PATCH /tickets/:id endpoint, covering:
1. Normal status transitions (open → in-progress → closed)
2. Illegal rollback (closed → open)
3. Non-existent ticket (404)
4. Invalid status value (400)
5. Missing status field (400)
6. Invalid id format
```

**✅ Expected output**: A complete set of test code (Jest/Supertest) covering both happy paths and error paths.

### 4.2 Run Tests

Save the generated test code to `lab-starter/tests/tickets-patch.test.js`, then run:

```bash
cd lab-starter
npm test
```

**Expected result**: All tests pass. If any fail, fix the implementation code based on the error messages.

> [!TIP]
> **Instructor tip**: If time is tight, participants can just run the Agent-generated tests without manual adjustments. The focus is experiencing the process, not achieving 100% pass rate.

---

## Phase 5: Ship — Prepare for Release (5 minutes)

### 5.1 Run the Release Process

```
/ship-release Prepare release for the PATCH /tickets/:id feature
Version: minor version upgrade from current version
Change summary: Added ticket status update endpoint, supporting open → in-progress → closed status transitions
```

**Or use an Agent**:

```
@release-engineer Please prepare the release for the following feature change:
- Added PATCH /tickets/:id endpoint
- Supports ticket status transitions: open → in-progress → closed
- Please complete: version bump, CHANGELOG update, release notes
```

**✅ Expected output**:

1. **package.json** version bump (e.g., `1.0.0` → `1.1.0`)
2. **CHANGELOG.md** new entry:

```markdown
## [1.1.0] - 2025-XX-XX

### Added
- PATCH /tickets/:id endpoint for updating ticket status
- Status transition validation: open → in-progress → closed
- Input validation and error handling (400, 404, 409)
```

3. Release checklist: Tests passed ✅, Review completed ✅, Documentation updated ✅

### 5.2 Final Verification

```bash
# Confirm version number
node -e "console.log(require('./package.json').version)"

# Confirm tests pass
npm test

# Confirm CHANGELOG is updated
head -20 CHANGELOG.md
```

> [!NOTE]
> **Instructor tip**: In real projects, the Ship phase also includes CI/CD pipelines, staging environment validation, etc. This lab simplifies to local operations — the focus is understanding the process.

---

## 🤔 Reflection & Discussion (2 minutes)

### Review the Complete Process

```
Think    →  Plan   →  Build  →  Review  →  Test  →  Ship
  │           │         │          │         │        │
  ▼           ▼         ▼          ▼         ▼        ▼
product   architect   Copilot   code-review  test   release
reviewer              Agent      .prompt    engineer engineer
```

### Discussion Questions

1. **Process value**: Which phase's findings were most "surprising" to you?
2. **Efficiency comparison**: Without AI Agent assistance, how long would it take to complete the same process?
3. **Quality gates**: In your team, which phases are most likely to be skipped? How can AI help ensure process completeness?
4. **Customization**: Which Agents' behavior rules would you adjust for your own project?

---

## 📝 Key Takeaways

| # | Takeaway |
|---|----------|
| 1 | The complete engineering process is Think → Plan → Build → Review → Test → Ship |
| 2 | Each phase has a corresponding specialized Agent or Prompt to provide support |
| 3 | Time invested in the Think phase before coding significantly reduces rework later |
| 4 | Unified Prompt files (e.g., `code-review.prompt`, `ship-release.prompt`) codify best practices into reusable processes |
| 5 | AI doesn't replace the engineering process — it makes each step more efficient and consistent |

---

## 🎓 Workshop Summary

Congratulations on completing all 5 Labs! Here's a review of your learning path:

| Lab | Topic | Core Capability |
|-----|-------|----------------|
| 1 | AI-DLC Full Lifecycle | Understanding AI's role in each development phase |
| 2 | Harness Engineering Three-Layer Architecture | Mastering Rule / Role / Workflow configuration |
| 3 | Multi-Agent Sequential Collaboration | Using multiple Agents in relay to complete tasks |
| 4 | Multi-Role Joint Code Review | Different roles reviewing in parallel for full coverage |
| **5** | **End-to-End Release Process** | **Complete Think→Ship engineering loop** |

**Next step**: Go back to your real project, pick a feature you're about to develop, and practice a complete Think → Ship cycle using the process you learned today.
