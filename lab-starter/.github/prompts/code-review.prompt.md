---
variables:
  - name: files_to_review
    description: Comma-separated list of files to review
  - name: pr_description
    description: Pull request description and context
---

# 🔍 Code Review Checklist

## Context
**Files:** {{files_to_review}}
**PR Description:** {{pr_description}}

## Review Pipeline

### Phase 1: Code Quality — @code-reviewer
Invoke @code-reviewer on {{files_to_review}} to evaluate:
- Code correctness and logic errors
- Naming conventions and readability
- DRY violations and dead code
- Error handling completeness
- Test coverage adequacy

### Phase 2: Security — @security-reviewer
Invoke @security-reviewer on {{files_to_review}} to check:
- Input validation and sanitization
- Authentication/authorization gaps
- Injection vulnerabilities (SQL, NoSQL, command)
- Sensitive data exposure
- Dependency vulnerabilities

### Phase 3: Adversarial — @red-team
Invoke @red-team to attempt:
- Edge case exploitation
- Race conditions and concurrency issues
- Resource exhaustion vectors
- API abuse scenarios

## Unified Review Report

Collect all findings and produce a single report:

### Findings Table

| # | Severity | Category | File | Line | Finding | Recommendation |
|---|----------|----------|------|------|---------|----------------|
| 1 | 🔴 Critical | | | | | |
| 2 | 🟠 High | | | | | |
| 3 | 🟡 Medium | | | | | |
| 4 | 🔵 Low | | | | | |

Sort by severity: Critical → High → Medium → Low.

### Summary
- **Total findings:** _count_
- **Blockers:** _count of Critical/High_
- **Recommendation:** Approve / Request Changes / Needs Discussion
