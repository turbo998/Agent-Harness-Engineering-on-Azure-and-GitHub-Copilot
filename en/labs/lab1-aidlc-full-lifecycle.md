# Lab 1: AI-DLC Full Lifecycle

## Lab Objective

Use GitHub Copilot to walk through a complete **AI-Driven Development Life Cycle**:

```
Requirement Understanding → Planning → Implementation → Testing → Review → PR Description
```

After completing this lab, participants should understand that GHCP is not just for writing code — it can participate in the entire development lifecycle.

## Duration
20 minutes

## Scenario

**Requirement**: Add a new `GET /tickets/summary` endpoint to the ticket service

- Return aggregated statistics grouped by `status` and `priority`
- Add corresponding tests
- Generate a PR description

## Steps

### Phase 1: Requirement Understanding (Ask) — 3 min

Switch to **Ask** mode.

**Prompt:**
```text
I need to add a GET /tickets/summary endpoint to this project.
Before I start, help me understand:
1. What is the current data model and API surface?
2. What existing patterns should I follow?
3. Are there any potential edge cases for a summary endpoint?
```

**What you should observe:**
- Copilot analyzes the data structure in ticketStore.js
- Identifies the existing routing style (Express, JSON responses)
- Mentions edge cases (empty data, unknown status values, etc.)

**Learning point:**
In the AI-DLC, the first step is never writing code — it's having the AI help you understand the context and identify risks.

---

### Phase 2: Planning (Plan) — 3 min

Switch to **Plan** mode.

**Prompt:**
```text
Create a detailed implementation plan for GET /tickets/summary.
Include:
- Which files to modify
- Function signatures
- Test cases to add
- Verification steps
```

**What you should observe:**
Plan outputs a structured list of steps, typically including:
1. Add a `getSummary()` function in ticketStore.js
2. Add a `GET /tickets/summary` route in app.js
3. Add at least 2–3 test cases in the test file
4. Run `npm test` to verify

**Learning point:**
The Plan output can be viewed as an "AI-generated technical design" — the team can review the plan before deciding whether to execute it.

---

### Phase 3: Implementation (Agent) — 5 min

Switch to **Agent** mode.

**Prompt:**
```text
Implement the /tickets/summary endpoint based on the plan.

Requirements:
- Add a getSummary() function in ticketStore.js
- Add GET /tickets/summary route in app.js
- Return JSON with countByStatus and countByPriority
- Add tests covering: normal case, empty data, single-status data
- Run tests when finished
```

**What you should observe:**
- Agent modifies multiple files step by step
- Automatically runs `npm test`
- If tests fail, Agent attempts to fix them

**Learning point:**
Agent doesn't do a "one-shot generation" — it runs a loop: implement → verify → fix → verify again.

---

### Phase 4: Test Verification — 3 min

Confirm in the terminal:

```powershell
npm test
```

Start the service and verify manually:

```powershell
npm start
# Open another terminal
curl http://localhost:3000/tickets/summary
```

**Expected output example:**
```json
{
  "countByStatus": { "open": 1, "in_progress": 1, "resolved": 1 },
  "countByPriority": { "high": 1, "medium": 1, "low": 1 }
}
```

---

### Phase 5: Review + PR Description (Ask) — 3 min

Switch back to **Ask** mode.

**Prompt 1 — Code Review:**
```text
Review the changes I just made for the /tickets/summary endpoint.
Check for:
- Security issues
- Performance concerns
- Missing edge cases
- Code style consistency
```

**Prompt 2 — PR Description:**
```text
Draft a pull request description for the /tickets/summary feature.
Include: problem statement, solution summary, test coverage, and how to verify.
```

**Learning point:**
The final step of the AI-DLC is not "code is done, let's commit" — it's having the AI help you do a self-review and documentation.

---

### Phase 6: Retrospective — 3 min

Review the complete AI-DLC you just walked through:

| Phase | GHCP Mode | Output |
|-------|-----------|--------|
| Requirement Understanding | Ask | Context analysis, risk identification |
| Planning | Plan | Structured implementation plan |
| Implementation | Agent | Cross-file code changes |
| Testing | Agent + Terminal | Automated test execution |
| Review | Ask | Code review feedback |
| Documentation | Ask | PR description |

**Instructor closing remarks:**
> This is the AI-DLC: it's not about having AI write code for you, but about having AI participate in every step of the development lifecycle.
> The key is: you are always in control of the direction; AI provides the acceleration.

---

## Completion Criteria

- [ ] Used Ask to understand the requirement context
- [ ] Used Plan to produce a structured plan
- [ ] Used Agent to complete cross-file implementation
- [ ] Tests pass and the API is callable
- [ ] Used Ask to complete a code review
- [ ] Generated a PR description

---

## FAQ

**Q: What if the files Agent modified don't match the Plan?**
A: This is normal. Agent may discover a better path during execution. What matters is whether the final result meets the requirements.

**Q: What if the tests fail?**
A: Let Agent continue fixing, or narrow the scope and retry. The core of the AI-DLC is "iteration."
