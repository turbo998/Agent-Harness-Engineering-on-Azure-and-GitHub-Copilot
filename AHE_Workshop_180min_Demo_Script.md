# GitHub Copilot Workshop 180 Minutes — Instructor Demo Script

> This document contains complete scripts for 3 instructor demos, including exact prompts, expected outputs, and teaching points.

---

## Demo 1: Quick Ask → Plan → Agent (10min)

### Scenario
Based on the ticket-service requirements, demonstrate the differences between Copilot's three modes.

### Preparation
- Open VS Code with the `ticket-service/` directory in the project
- Open the Copilot Chat panel

### Steps

#### Step 1: Ask Mode (3min)

**Enter in Copilot Chat:**
```
I need to add a new API endpoint to ticket-service that supports filtering the ticket list by priority.
How should I design this interface? What aspects should I consider?
```

**Expected Output:**
- Copilot provides design suggestions (RESTful paths, query parameters, pagination, etc.)
- No code generated — only suggestions and ideas

**Instructor Teaching Points:**
> "Ask mode is like discussing a solution with a senior colleague. It gives you ideas and suggestions but doesn't write the code. It's ideal for the requirements clarification phase."

#### Step 2: Plan Mode (3min)

**Switch to Plan mode and enter:**
```
/plan Add a GET /api/tickets?priority={level} endpoint to ticket-service for filtering tickets by priority.
Include: modification plan for route definition, Controller, Service, and Repository layers.
```

**Expected Output:**
- Generates a step-by-step plan: 1) Add route 2) Create Controller method 3) Service layer logic 4) Repository query
- Lists files that need to be modified
- No actual code generated

**Instructor Teaching Points:**
> "Plan mode turns vague requirements into clear execution steps. This is the value of the Plan phase in AI-DLC — reducing implementation risk."

#### Step 3: Agent Mode (4min)

**Switch to Agent mode and enter:**
```
Please implement the filter-tickets-by-priority feature for ticket-service:
- GET /api/tickets?priority=high|medium|low
- Support pagination (page, size parameters)
- Include unit tests
- Follow the project's existing code style
```

**Expected Output:**
- Copilot Agent automatically:
  - Analyzes the project structure
  - Creates/modifies multiple files
  - Generates Controller, Service, and Repository code
  - Generates corresponding unit tests
- Executes necessary commands in the terminal

**Instructor Teaching Points:**
> "Agent mode is truly autonomous execution. It doesn't just think — it implements. This is the capability leap from Chat to Agent. But note — we need Harness Engineering to guide its behavior. That's what we'll cover next."

---

## Demo 2: Multi-Role Review (10min)

### Scenario
Show how `@code-reviewer` and `@red-team` find different types of issues in the same code.

### Preparation
- Have a code sample with multiple types of issues ready (in `demo/vulnerable-api.ts`)

### Demo Code
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

### Steps

#### Step 1: @code-reviewer Review (4min)

**Enter in Copilot Chat:**
```
@code-reviewer Please review the code in demo/vulnerable-api.ts, focusing on code quality, maintainability, and best practices.
```

**Expected Output:**
- Points out missing input validation
- Points out missing error handling (try-catch)
- Points out hardcoded strings
- Points out missing type definitions
- Suggests layered architecture (Controller/Service separation)

**Instructor Teaching Points:**
> "code-reviewer approaches from a code quality perspective, focusing on maintainability and engineering best practices. It's like having an experienced senior engineer reviewing your PR."

#### Step 2: @red-team Review (4min)

**Enter in Copilot Chat:**
```
@red-team Please perform a security audit on demo/vulnerable-api.ts, identifying all potential security vulnerabilities and attack surfaces.
```

**Expected Output:**
- 🚨 **SQL Injection**: String concatenation to build SQL queries
- 🚨 **Plaintext Password Storage**: Passwords not hashed
- 🚨 **Hardcoded Secret**: JWT secret hardcoded
- 🚨 **Privilege Escalation**: Users can specify their own role
- 🚨 **Information Leakage**: Error messages may expose database structure
- Provides OWASP Top 10 mapping

**Instructor Teaching Points:**
> "The same code, but red-team approaches from an attacker's perspective and finds completely different issues. SQL injection, plaintext passwords, privilege escalation — these are security concerns that code-reviewer wouldn't focus on. This is the value of multi-role review: multi-perspective coverage."

#### Step 3: Comparison Summary (2min)

**Instructor Teaching Points:**
> "Two Agents examining the same code produce complementary feedback. In a real team, you'd need a senior engineer plus a security expert to cover all these issues. Now, through the multi-role Agent system, a single person can get multi-perspective review. This is the 'Code Review Legion' concept."

---

## Demo 3: ship-release.prompt Driven Release Process (5min)

### Scenario
Demonstrate how a `.prompt.md` template drives an end-to-end release process.

### Preparation
- Ensure the project has a `.github/prompts/ship-release.prompt.md` file

### Steps

#### Step 1: View the Prompt Template (1min)

**Show the `ship-release.prompt.md` content:**
```markdown
---
mode: agent
description: "Drive the complete release process"
---
## Release Checklist

Please complete the release preparation following these steps:

1. **Change Summary**: List all commits since the last tag
2. **CHANGELOG Generation**: Generate a changelog in Conventional Commits format
3. **Version Number Suggestion**: Suggest a semver version based on change types
4. **Breaking Change Check**: Flag any breaking changes
5. **Dependency Audit**: Check for dependencies with known security vulnerabilities
6. **Release PR Draft**: Generate a title and description for the release PR
```

**Instructor Teaching Points:**
> "This is a Prompt template — it defines the workflow. Any team member performing a release just invokes this template to ensure process consistency."

#### Step 2: Execute the Prompt (3min)

**Enter in Copilot Chat:**
```
/ship-release
```

**Expected Output:**
- Agent automatically runs `git log` to analyze changes
- Generates a formatted CHANGELOG
- Suggests a version number (e.g., v1.2.0)
- Flags breaking changes (if any)
- Generates a release PR description

**Instructor Teaching Points:**
> "One command completes what used to take 30 minutes of manual work. And because it's template-driven, every release is standardized. This is the power of Prompt templates — encoding team knowledge into executable workflows."

#### Step 3: Wrap-Up (1min)

**Instructor Teaching Points:**
> "From Think to Ship, the entire AI-DLC can be chained together with Prompt templates. think-clarify, plan-tasks, review-multi, test-generate, ship-release — six templates covering the complete lifecycle. In the upcoming Lab 5, you'll experience this full process hands-on."

---

## Demo Notes

1. **Network**: Ensure the demo environment has a stable network connection; Copilot responses may take 5-10 seconds
2. **Fallback Plan**: Have screenshots/recordings ready as a backup
3. **Interaction**: Leave 30 seconds after each Demo for participant questions
4. **Pacing**: Demo 2 is the highlight — extend if needed; Demo 3 can be shortened
