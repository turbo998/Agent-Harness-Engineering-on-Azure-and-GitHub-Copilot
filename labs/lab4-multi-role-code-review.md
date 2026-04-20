# Lab 4: Multi-Role Joint Code Review

⏱ **Estimated Time**: 20 minutes | **Difficulty**: Intermediate

## 🎯 Learning Objectives

After completing this lab, you will be able to:

1. Use multiple specialized Agents to perform multi-dimensional review on the same piece of code
2. Understand the different focus areas of each role (code quality, security, red team, performance)
3. Use `code-review.prompt` to run a unified review pipeline with one command
4. Compare the effectiveness of single-person review vs multi-role joint review

## 📋 Prerequisites

- Completed Labs 1–3
- The following Agents are configured: `@code-reviewer`, `@security-reviewer`, `@red-team`, `@performance-engineer`
- The Prompt `code-review.prompt` is configured
- The `lab-starter/` project runs normally

---

## 📖 Scenario

Your teammate submitted a PR adding a `DELETE /tickets/:id` endpoint for deleting tickets. The feature "works" and tests pass. You need to perform a thorough review before merging.

---

## Step 1: Review the Code Under Inspection (2 minutes)

Add the following code to `lab-starter/src/routes/tickets.js` (after the existing routes):

```javascript
// DELETE /tickets/:id — Delete a specific ticket
router.delete('/tickets/:id', (req, res) => {
  const id = req.params.id;

  // Directly use id to construct a query (in a database scenario)
  const query = `DELETE FROM tickets WHERE id = '${id}'`;
  console.log('Executing:', query);

  // Synchronously read a config file to check if deletion is allowed
  const fs = require('fs');
  const config = JSON.parse(fs.readFileSync('./config/delete-policy.json', 'utf8'));

  if (!config.allowDelete) {
    return res.status(403).json({ error: 'Delete not allowed' });
  }

  // Delete from in-memory store
  const index = store.findIndex(t => t.id === id);
  store.splice(index, 1);

  res.status(200).json({ message: 'Ticket deleted' });
});
```

> [!NOTE]
> **Instructor tip**: Tell participants upfront that this code "works and passes tests." Have them spend 1 minute doing a visual review and note down how many issues they find, then compare with what the Agents discover.

**🔍 Self-check question**: Before continuing, how many issues can you spot by eye? Write down that number.

---

## Step 2: @code-reviewer — Structured Code Review (3 minutes)

In Copilot Chat, enter:

```
@code-reviewer Please review the following DELETE /tickets/:id endpoint implementation, focusing on code quality, correctness, and maintainability:

[paste the code above]
```

**✅ Expected findings**:

| Category | Issue |
|----------|-------|
| Correctness | When `store.findIndex` returns -1, `splice(-1, 1)` removes the last element |
| Correctness | Returns 200 when ticket is not found; should return 404 |
| Maintainability | Missing audit log (who deleted what, and when) |
| Code style | `require('fs')` should be at the top of the file |
| Type safety | `id` comparison uses `===` but `params.id` is a string, while `store` values might be numbers |

> [!TIP]
> **Instructor tip**: Emphasize that code-reviewer focuses on "is the code correct and well-written" — it won't dive deep into security or performance.

---

## Step 3: @security-reviewer — Security Vulnerability Scan (3 minutes)

```
@security-reviewer Please perform a security audit on this DELETE /tickets/:id endpoint, identifying all potential security vulnerabilities and risks:

[paste the code above]
```

**✅ Expected findings**:

| Severity | Vulnerability |
|----------|--------------|
| 🔴 Critical | No input validation on `:id` parameter — arbitrary strings can be injected |
| 🔴 Critical | No authorization check — anyone can delete any ticket |
| 🟡 Medium | SQL string concatenation to construct queries (even though it's in-memory storage now, this becomes an injection vulnerability when migrating to a database) |
| 🟡 Medium | Config file path is hardcoded, potentially exploitable via path traversal |
| 🟢 Low | No operation audit log — cannot trace malicious deletions |

---

## Step 4: @red-team — Adversarial Attack Testing (3 minutes)

```
@red-team As an attacker, try to attack this DELETE /tickets/:id endpoint. Provide specific attack payloads and exploitation methods:

[paste the code above]
```

**✅ Expected attack vectors**:

```bash
# Attack 1: SQL Injection
curl -X DELETE "http://localhost:3000/tickets/1' OR '1'='1"

# Attack 2: Path traversal / special characters
curl -X DELETE "http://localhost:3000/tickets/../../../etc/passwd"

# Attack 3: Denial of Service — trigger synchronous file read blocking
for i in $(seq 1 1000); do
  curl -X DELETE "http://localhost:3000/tickets/$i" &
done

# Attack 4: Unauthorized mass deletion
curl -X DELETE "http://localhost:3000/tickets/1"
curl -X DELETE "http://localhost:3000/tickets/2"
# ... no authentication required
```

> [!NOTE]
> **Instructor tip**: The difference between the red team perspective and security review — security review says "there's a vulnerability here," while red team says "here's exactly how to exploit it."

---

## Step 5: @performance-engineer — Performance Analysis (3 minutes)

```
@performance-engineer Please analyze the performance issues and scalability risks of this DELETE /tickets/:id endpoint:

[paste the code above]
```

**✅ Expected findings**:

| Impact | Issue |
|--------|-------|
| 🔴 High | `fs.readFileSync` is a synchronous operation that blocks the Node.js event loop; under high concurrency, all requests queue up |
| 🟡 Medium | `store.findIndex` is an O(n) linear scan; performance degrades with large data volumes |
| 🟡 Medium | Config file is re-read on every request; should be loaded once at startup or cached |
| 🟢 Low | `console.log` becomes an I/O bottleneck under high traffic |

---

## Step 6: Compare Findings Across the Four Agents (3 minutes)

Organize your findings and fill in the table below:

| Issue | Code Reviewer | Security | Red Team | Performance |
|-------|:---:|:---:|:---:|:---:|
| Returns 200 instead of 404 when not found | ✅ | | | |
| splice(-1,1) deletes wrong element | ✅ | | | |
| No input validation | | ✅ | ✅ | |
| No authorization check | | ✅ | ✅ | |
| SQL injection risk | | ✅ | ✅ | |
| Synchronous file read blocking | | | | ✅ |
| No audit log | ✅ | ✅ | | |
| O(n) lookup performance | | | | ✅ |

**💡 Key insight**: No single role can find all the issues. Multi-role collaboration provides far greater coverage than single-person review.

> [!TIP]
> **Instructor tip**: Have participants count how many issues they found by eye in Step 1, and compare with the total found by the 4 Agents combined. The gap is typically 2–3x.

---

## Step 7: Use code-review.prompt for a Unified Pipeline (3 minutes)

Now use the unified Prompt file to complete multi-role review with one command:

```
/code-review Please review the DELETE /tickets/:id endpoint implementation

[paste the code above]
```

**✅ Expected output**: A comprehensive report containing findings from all roles, sorted by severity, with fix recommendations.

Observe how this report compares to your results from manually calling each Agent one by one.

---

## 🤔 Reflection & Discussion (2 minutes)

1. **Coverage**: Single-person review vs multi-role review — how many issues did you find in each?
2. **Efficiency**: Manually calling 4 Agents vs running `code-review.prompt` with one command — which is better suited for daily work?
3. **Enterprise scenarios**: In your team, which roles' reviews are most likely to be overlooked?
4. **Cost consideration**: Does every PR need all 4 roles? How would you choose review combinations based on change type?

---

## 📝 Key Takeaways

| # | Takeaway |
|---|----------|
| 1 | Different Agent roles focus on different dimensions — code quality, security, attack surface, performance |
| 2 | Multi-role joint review catches issues that a single perspective would miss |
| 3 | `code-review.prompt` orchestrates multi-role review into a reusable standard process |
| 4 | In enterprises, the choice of review roles should be dynamically adjusted based on the risk level of the change |

---

**⏭ Next**: [Lab 5: End-to-End Release Process — From Design to Production](lab5-ship-and-release.md)
